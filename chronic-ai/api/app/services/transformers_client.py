"""
VinAI Translate Client for Vietnamese-English Bidirectional Translation.

Uses VinAI's mBART-based models (vinai-translate-vi2en and vinai-translate-en2vi)
which achieve state-of-the-art BLEU scores, outperforming Google Translate.

Performance optimizations:
- True batch processing with torch tensor batching
- LRU translation cache with TTL
- Adaptive beam search (fewer beams for short texts)
- Cached tokenization for chunking decisions
- Persistent model loading (no load/unload cycles)
- Async parallel chunk processing
"""
import asyncio
import hashlib
import re
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Text Processing Utilities
# =============================================================================

def strip_markdown_inline(text: str) -> str:
    """
    Remove ONLY inline markdown formatting from text, preserving line breaks.

    This removes bold/italic markers but keeps the text structure intact.

    Args:
        text: Text potentially containing markdown

    Returns:
        Text with inline formatting removed but structure preserved
    """
    if not text:
        return text

    # Remove bold/italic markers (**text**, *text*, __text__, _text_)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove inline code backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)

    return text


def strip_markdown(text: str) -> str:
    """
    Remove markdown formatting from text before translation.

    VinAI Translate is trained on natural language, not markdown, so
    structured formatting can confuse it.

    Args:
        text: Text potentially containing markdown

    Returns:
        Clean text without markdown formatting
    """
    if not text:
        return text

    # Remove headers (# ## ### etc.)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

    # Remove bold/italic markers
    text = strip_markdown_inline(text)

    # Remove bullet points (- or *)
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

    # Remove numbered lists (1. 2. etc.)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)

    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def parse_structured_text(text: str) -> list:
    """
    Parse text into structured segments preserving headers, bullets, etc.

    Args:
        text: Text potentially containing markdown formatting

    Returns:
        List of (segment_type, marker, content) tuples
        segment_type: 'header', 'bullet', 'numbered', 'paragraph'
        marker: The original prefix (e.g., '## ', '- ', '1. ')
        content: The text content to translate
    """
    if not text:
        return []

    segments = []
    lines = text.split('\n')
    current_paragraph = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Empty line - flush current paragraph
            if current_paragraph:
                segments.append(('paragraph', '', ' '.join(current_paragraph)))
                current_paragraph = []
            segments.append(('break', '', ''))
            continue

        # Check for header (# ## ### etc.)
        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            if current_paragraph:
                segments.append(('paragraph', '', ' '.join(current_paragraph)))
                current_paragraph = []
            segments.append(('header', header_match.group(1) + ' ', header_match.group(2)))
            continue

        # Check for bullet points (- or *)
        bullet_match = re.match(r'^([\-\*])\s+(.+)$', stripped)
        if bullet_match:
            if current_paragraph:
                segments.append(('paragraph', '', ' '.join(current_paragraph)))
                current_paragraph = []
            segments.append(('bullet', '- ', bullet_match.group(2)))
            continue

        # Check for numbered list (1. 2. etc.)
        numbered_match = re.match(r'^(\d+\.)\s+(.+)$', stripped)
        if numbered_match:
            if current_paragraph:
                segments.append(('paragraph', '', ' '.join(current_paragraph)))
                current_paragraph = []
            segments.append(('numbered', numbered_match.group(1) + ' ', numbered_match.group(2)))
            continue

        # Regular line - add to current paragraph
        current_paragraph.append(stripped)

    # Flush any remaining paragraph
    if current_paragraph:
        segments.append(('paragraph', '', ' '.join(current_paragraph)))

    return segments


def reconstruct_formatted_text(translated_segments: list) -> str:
    """
    Reconstruct formatted text from translated segments.

    Args:
        translated_segments: List of (segment_type, marker, translated_content) tuples

    Returns:
        Formatted text with proper markdown structure
    """
    lines = []
    last_was_break = False

    for seg_type, marker, content in translated_segments:
        if seg_type == 'break':
            if not last_was_break:
                lines.append('')
            last_was_break = True
            continue

        last_was_break = False

        if seg_type == 'header':
            # Add extra newline before header for spacing
            if lines and lines[-1] != '':
                lines.append('')
            lines.append(f"## {content}")  # Use proper markdown headers
            lines.append('')
        elif seg_type == 'bullet':
            lines.append(f"• {content}")
        elif seg_type == 'numbered':
            lines.append(f"{marker}{content}")
        else:  # paragraph
            lines.append(content)

    # Clean up multiple empty lines
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


# =============================================================================
# Translation Cache
# =============================================================================

@dataclass
class TranslationCacheEntry:
    """Cached translation result with metadata."""
    translation: str
    timestamp: float
    hit_count: int = 0


class TranslationCache:
    """
    LRU cache for translation results with TTL expiration.

    Thread-safe for use in async FastAPI context.
    """

    def __init__(self, max_size: int = 2000, ttl: float = 7200.0):
        self._cache: OrderedDict[str, TranslationCacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, direction: str) -> str:
        """Generate cache key from normalized text and direction."""
        # Normalize text for better cache hit rate
        normalized = " ".join(text.lower().strip().split())
        return hashlib.sha256(f"{direction}:{normalized}".encode()).hexdigest()[:32]

    def get(self, text: str, direction: str) -> Optional[str]:
        """
        Get translation from cache if valid.

        Args:
            text: Original text
            direction: 'vi2en' or 'en2vi'

        Returns:
            Cached translation or None
        """
        key = self._make_key(text, direction)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check TTL
            if time.time() - entry.timestamp > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.hit_count += 1
            self._hits += 1

            return entry.translation

    def put(self, text: str, direction: str, translation: str):
        """
        Add translation to cache with LRU eviction.

        Args:
            text: Original text
            direction: 'vi2en' or 'en2vi'
            translation: Translated text
        """
        key = self._make_key(text, direction)

        with self._lock:
            # Evict oldest entries if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = TranslationCacheEntry(
                translation=translation,
                timestamp=time.time()
            )

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%"
            }


# =============================================================================
# VinAI Translation Client
# =============================================================================

class TransformersClient:
    """
    High-performance VinAI Translate client for Vietnamese-English translation.

    Features:
    - Bidirectional translation with separate optimized models
    - True batch processing with torch tensor batching
    - LRU translation cache with TTL
    - Adaptive beam search (fewer beams for short texts)
    - Cached tokenization for efficient chunking
    - Persistent model loading (no load/unload overhead)
    - Thread-safe for async FastAPI
    """

    def __init__(self):
        # Model identifiers from config
        self.vi2en_model_name = settings.vinai_vi2en_model
        self.en2vi_model_name = settings.vinai_en2vi_model

        # Model instances (lazy loaded)
        self._vi2en_model = None
        self._vi2en_tokenizer = None
        self._en2vi_model = None
        self._en2vi_tokenizer = None

        # Device
        self._device = None

        # Locks for thread-safe model loading
        self._vi2en_lock = asyncio.Lock()
        self._en2vi_lock = asyncio.Lock()

        # Translation cache
        self._cache = TranslationCache(
            max_size=settings.translation_cache_max_size,
            ttl=settings.translation_cache_ttl
        ) if settings.translation_cache_enabled else None

        # Performance settings
        self.max_chunk_tokens = 400  # Buffer for 512 token limit
        self.batch_size = settings.translation_batch_size
        self.adaptive_beams = settings.translation_adaptive_beams
        self.short_text_threshold = settings.translation_short_text_threshold

        # Tokenization cache for length checking
        self._token_length_cache: Dict[str, int] = {}
        self._token_cache_lock = threading.Lock()

    def _get_device(self) -> str:
        """
        Get the compute device, initializing if needed.

        Supports:
        - "auto": Auto-detect best available (CUDA > MPS > CPU)
        - "cuda": NVIDIA GPU
        - "mps": Apple Silicon GPU (M1/M2/M3)
        - "cpu": CPU fallback
        """
        if self._device is None:
            import torch

            configured_device = settings.translation_device.lower()

            if configured_device == "auto":
                # Auto-detect best available device
                if torch.cuda.is_available():
                    self._device = "cuda"
                    logger.info(f"Using NVIDIA GPU: {torch.cuda.get_device_name(0)}")
                elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    self._device = "mps"
                    logger.info("Using Apple Silicon GPU (MPS)")
                else:
                    self._device = "cpu"
                    logger.warning("No GPU available, using CPU (slower)")
                    torch.set_num_threads(4)
            elif configured_device == "cuda":
                if torch.cuda.is_available():
                    self._device = "cuda"
                    logger.info(f"Using NVIDIA GPU: {torch.cuda.get_device_name(0)}")
                else:
                    logger.warning("CUDA requested but not available, falling back to CPU")
                    self._device = "cpu"
                    torch.set_num_threads(4)
            elif configured_device == "mps":
                if torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    self._device = "mps"
                    logger.info("Using Apple Silicon GPU (MPS)")
                else:
                    logger.warning("MPS requested but not available, falling back to CPU")
                    self._device = "cpu"
                    torch.set_num_threads(4)
            else:
                self._device = "cpu"
                logger.info("Using CPU for translation")
                torch.set_num_threads(4)

        return self._device

    async def _ensure_vi2en_loaded(self):
        """Lazy load Vi->En model. Kept persistent once loaded."""
        if self._vi2en_model is not None:
            return

        async with self._vi2en_lock:
            # Double-check after acquiring lock
            if self._vi2en_model is not None:
                return

            try:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                import torch

                logger.info(f"Loading Vi->En model: {self.vi2en_model_name}")

                self._vi2en_tokenizer = AutoTokenizer.from_pretrained(
                    self.vi2en_model_name,
                    src_lang="vi_VN"
                )
                self._vi2en_model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.vi2en_model_name
                )

                device = self._get_device()
                self._vi2en_model.to(device)
                self._vi2en_model.eval()

                # Try torch.compile() for PyTorch 2.0+ (optional optimization)
                # Note: torch.compile() works best on CUDA, limited support on MPS
                if hasattr(torch, 'compile') and device in ("cuda", "mps"):
                    try:
                        self._vi2en_model = torch.compile(
                            self._vi2en_model,
                            mode="reduce-overhead"
                        )
                        logger.info("Applied torch.compile() to Vi->En model")
                    except Exception as e:
                        logger.debug(f"torch.compile() not applied: {e}")

                logger.info(f"Vi->En model loaded on {device}")

            except Exception as e:
                logger.error(f"Failed to load Vi->En model: {e}")
                raise RuntimeError(f"VinAI Vi->En model loading failed: {e}")

    async def _ensure_en2vi_loaded(self):
        """Lazy load En->Vi model. Kept persistent once loaded."""
        if self._en2vi_model is not None:
            return

        async with self._en2vi_lock:
            # Double-check after acquiring lock
            if self._en2vi_model is not None:
                return

            try:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                import torch

                logger.info(f"Loading En->Vi model: {self.en2vi_model_name}")

                self._en2vi_tokenizer = AutoTokenizer.from_pretrained(
                    self.en2vi_model_name,
                    src_lang="en_XX"
                )
                self._en2vi_model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.en2vi_model_name
                )

                device = self._get_device()
                self._en2vi_model.to(device)
                self._en2vi_model.eval()

                # Try torch.compile() for PyTorch 2.0+
                # Note: torch.compile() works best on CUDA, limited support on MPS
                if hasattr(torch, 'compile') and device in ("cuda", "mps"):
                    try:
                        self._en2vi_model = torch.compile(
                            self._en2vi_model,
                            mode="reduce-overhead"
                        )
                        logger.info("Applied torch.compile() to En->Vi model")
                    except Exception as e:
                        logger.debug(f"torch.compile() not applied: {e}")

                logger.info(f"En->Vi model loaded on {device}")

            except Exception as e:
                logger.error(f"Failed to load En->Vi model: {e}")
                raise RuntimeError(f"VinAI En->Vi model loading failed: {e}")

    def _get_token_length(self, text: str, tokenizer) -> int:
        """
        Get token length with caching for efficiency.

        Args:
            text: Text to tokenize
            tokenizer: Tokenizer to use

        Returns:
            Number of tokens
        """
        # Create cache key from text hash and tokenizer name
        cache_key = f"{hash(text)}_{id(tokenizer)}"

        with self._token_cache_lock:
            if cache_key in self._token_length_cache:
                return self._token_length_cache[cache_key]

        length = len(tokenizer.encode(text))

        with self._token_cache_lock:
            # Limit cache size to prevent memory issues
            if len(self._token_length_cache) > 10000:
                # Clear half the cache
                keys_to_remove = list(self._token_length_cache.keys())[:5000]
                for key in keys_to_remove:
                    del self._token_length_cache[key]

            self._token_length_cache[cache_key] = length

        return length

    def _chunk_text(self, text: str, tokenizer) -> List[str]:
        """
        Split text into chunks respecting sentence boundaries.

        Uses cached tokenization for efficiency.

        Args:
            text: Text to chunk
            tokenizer: Tokenizer to use for length calculation

        Returns:
            List of text chunks, each <= max_chunk_tokens
        """
        if not text.strip():
            return [text]

        # Check if chunking is needed
        token_count = self._get_token_length(text, tokenizer)
        if token_count <= self.max_chunk_tokens:
            return [text]

        # Split by sentences
        sentences = re.split(r'([.!?]+\s+|[.!?]+$)', text)

        # Rejoin sentences with their punctuation
        normalized_sentences = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i+1].strip() in ['.', '!', '?', '. ', '! ', '? ']:
                normalized_sentences.append(sentences[i] + sentences[i+1])
                i += 2
            else:
                if sentences[i].strip():
                    normalized_sentences.append(sentences[i])
                i += 1

        # Build chunks respecting token limit
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in normalized_sentences:
            sentence_tokens = self._get_token_length(sentence, tokenizer)

            # If single sentence exceeds limit, split by words
            if sentence_tokens > self.max_chunk_tokens:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long sentence by words
                words = sentence.split()
                word_chunk = []
                word_length = 0

                for word in words:
                    word_tokens = self._get_token_length(word, tokenizer)
                    if word_length + word_tokens > self.max_chunk_tokens:
                        if word_chunk:
                            chunks.append(' '.join(word_chunk))
                        word_chunk = [word]
                        word_length = word_tokens
                    else:
                        word_chunk.append(word)
                        word_length += word_tokens

                if word_chunk:
                    chunks.append(' '.join(word_chunk))
                continue

            # Check if adding this sentence exceeds limit
            if current_length + sentence_tokens > self.max_chunk_tokens:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]

    def _get_num_beams(self, texts: List[str], tokenizer) -> int:
        """
        Determine beam count based on text length (adaptive beam search).

        Shorter texts can use fewer beams for faster inference
        without quality loss.

        Args:
            texts: List of texts to translate
            tokenizer: Tokenizer for length calculation

        Returns:
            Number of beams to use
        """
        if not self.adaptive_beams:
            return 5

        # Calculate average token length
        total_tokens = sum(self._get_token_length(t, tokenizer) for t in texts)
        avg_tokens = total_tokens / len(texts) if texts else 0

        # Use fewer beams for short texts
        if avg_tokens < self.short_text_threshold:
            return 3
        return 5

    async def _translate_batch_vi2en(self, texts: List[str]) -> List[str]:
        """
        Translate batch of Vietnamese texts to English using true torch batching.

        Args:
            texts: List of Vietnamese texts (already cleaned/chunked)

        Returns:
            List of English translations
        """
        await self._ensure_vi2en_loaded()

        import torch

        num_beams = self._get_num_beams(texts, self._vi2en_tokenizer)

        # Batch tokenization
        inputs = self._vi2en_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self._get_device())

        # Batch generation
        with torch.no_grad():
            outputs = self._vi2en_model.generate(
                **inputs,
                decoder_start_token_id=self._vi2en_tokenizer.lang_code_to_id["en_XX"],
                num_return_sequences=1,
                num_beams=num_beams,
                early_stopping=True,
                max_length=512,
                no_repeat_ngram_size=2
            )

        # Batch decode
        translations = self._vi2en_tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True
        )

        return translations

    async def _translate_batch_en2vi(self, texts: List[str]) -> List[str]:
        """
        Translate batch of English texts to Vietnamese using true torch batching.

        Args:
            texts: List of English texts (already cleaned/chunked)

        Returns:
            List of Vietnamese translations
        """
        await self._ensure_en2vi_loaded()

        import torch

        num_beams = self._get_num_beams(texts, self._en2vi_tokenizer)

        # Batch tokenization
        inputs = self._en2vi_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self._get_device())

        # Batch generation
        with torch.no_grad():
            outputs = self._en2vi_model.generate(
                **inputs,
                decoder_start_token_id=self._en2vi_tokenizer.lang_code_to_id["vi_VN"],
                num_return_sequences=1,
                num_beams=num_beams,
                early_stopping=True,
                max_length=512,
                no_repeat_ngram_size=2
            )

        # Batch decode
        translations = self._en2vi_tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True
        )

        return translations

    async def translate_vi_to_en(self, text: str) -> str:
        """
        Translate Vietnamese to English with caching and batch processing.

        Automatically chunks long texts to handle 512 token limit.
        Strips markdown before translation for better results.

        Args:
            text: Vietnamese text to translate

        Returns:
            English translation
        """
        if not text.strip():
            return ""

        logger.info(f"[Vi->En] Input ({len(text)} chars): {text[:100]}..." if len(text) > 100 else f"[Vi->En] Input: {text}")

        # Check cache first
        if self._cache:
            cached = self._cache.get(text, "vi2en")
            if cached:
                logger.debug("[Vi->En] Cache hit")
                return cached

        # Strip markdown before translation
        clean_text = strip_markdown(text)

        await self._ensure_vi2en_loaded()

        # Chunk if needed
        chunks = self._chunk_text(clean_text, self._vi2en_tokenizer)

        if len(chunks) == 1:
            # Single chunk - direct batch translation
            results = await self._translate_batch_vi2en([clean_text])
            result = results[0]
        else:
            # Multiple chunks - batch translate all at once
            logger.info(f"[Vi->En] Processing {len(chunks)} chunks")
            all_translations = []

            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                batch_results = await self._translate_batch_vi2en(batch)
                all_translations.extend(batch_results)

            result = ' '.join(all_translations)

        # Cache result
        if self._cache:
            self._cache.put(text, "vi2en", result)

        logger.info(f"[Vi->En] Result ({len(result)} chars): {result[:100]}..." if len(result) > 100 else f"[Vi->En] Result: {result}")
        return result

    async def translate_en_to_vi(self, text: str) -> str:
        """
        Translate English to Vietnamese with structure preservation.

        Parses text into segments (headers, bullets, paragraphs), translates
        all segments in batch, then reconstructs with proper formatting.

        Args:
            text: English text to translate

        Returns:
            Vietnamese translation with preserved formatting
        """
        if not text.strip():
            return ""

        logger.info(f"[En->Vi] Input ({len(text)} chars): {text[:100]}..." if len(text) > 100 else f"[En->Vi] Input: {text}")

        # Check cache first
        if self._cache:
            cached = self._cache.get(text, "en2vi")
            if cached:
                logger.debug("[En->Vi] Cache hit")
                return cached

        await self._ensure_en2vi_loaded()

        # Parse into structured segments
        segments = parse_structured_text(text)

        if not segments:
            # Fallback to simple translation
            clean_text = strip_markdown(text)
            results = await self._translate_batch_en2vi([clean_text])
            result = results[0]

            if self._cache:
                self._cache.put(text, "en2vi", result)
            return result

        logger.debug(f"[En->Vi] Parsed into {len(segments)} segments")

        # Collect all texts that need translation
        texts_to_translate = []
        segment_map = []  # Track (segment_index, chunk_index) for each text

        for seg_idx, (seg_type, marker, content) in enumerate(segments):
            if seg_type == 'break' or not content.strip():
                continue

            # Clean inline markdown before translating
            clean_content = strip_markdown_inline(content)

            # Chunk if needed
            chunks = self._chunk_text(clean_content, self._en2vi_tokenizer)

            for chunk_idx, chunk in enumerate(chunks):
                texts_to_translate.append(chunk)
                segment_map.append((seg_idx, chunk_idx, len(chunks)))

        # Batch translate ALL texts
        all_translations = []
        for i in range(0, len(texts_to_translate), self.batch_size):
            batch = texts_to_translate[i:i + self.batch_size]
            batch_results = await self._translate_batch_en2vi(batch)
            all_translations.extend(batch_results)

        # Reassemble translations into segments
        translated_segments = []
        translation_idx = 0

        for seg_idx, (seg_type, marker, content) in enumerate(segments):
            if seg_type == 'break' or not content.strip():
                translated_segments.append((seg_type, marker, content))
                continue

            # Collect all chunks for this segment
            segment_translations = []
            while translation_idx < len(segment_map) and segment_map[translation_idx][0] == seg_idx:
                segment_translations.append(all_translations[translation_idx])
                translation_idx += 1

            translated_content = ' '.join(segment_translations)
            translated_segments.append((seg_type, marker, translated_content))

        # Reconstruct formatted text
        result = reconstruct_formatted_text(translated_segments)

        # Cache result
        if self._cache:
            self._cache.put(text, "en2vi", result)

        logger.info(f"[En->Vi] Result ({len(result)} chars): {result[:100]}..." if len(result) > 100 else f"[En->Vi] Result: {result}")
        return result

    async def translate_batch(
        self,
        texts: List[str],
        direction: str = "vi_to_en"
    ) -> List[str]:
        """
        Translate multiple texts efficiently using true batch processing.

        Args:
            texts: List of texts to translate
            direction: "vi_to_en" or "en_to_vi"

        Returns:
            List of translations
        """
        if not texts:
            return []

        # For simple texts (no structure preservation needed), use direct batching
        if direction == "vi_to_en":
            # Clean all texts
            clean_texts = [strip_markdown(t) for t in texts]

            # Check cache for each
            results = [None] * len(texts)
            texts_to_translate = []
            indices_to_translate = []

            for i, (orig, clean) in enumerate(zip(texts, clean_texts)):
                if self._cache:
                    cached = self._cache.get(orig, "vi2en")
                    if cached:
                        results[i] = cached
                        continue
                texts_to_translate.append(clean)
                indices_to_translate.append(i)

            # Batch translate remaining
            if texts_to_translate:
                await self._ensure_vi2en_loaded()

                # Handle chunking for long texts
                all_chunks = []
                chunk_map = []  # (original_index, num_chunks)

                for idx, text in zip(indices_to_translate, texts_to_translate):
                    chunks = self._chunk_text(text, self._vi2en_tokenizer)
                    for chunk in chunks:
                        all_chunks.append(chunk)
                    chunk_map.append((idx, len(chunks)))

                # Batch translate all chunks
                all_translations = []
                for i in range(0, len(all_chunks), self.batch_size):
                    batch = all_chunks[i:i + self.batch_size]
                    batch_results = await self._translate_batch_vi2en(batch)
                    all_translations.extend(batch_results)

                # Reassemble
                trans_idx = 0
                for orig_idx, num_chunks in chunk_map:
                    chunk_translations = all_translations[trans_idx:trans_idx + num_chunks]
                    trans_idx += num_chunks
                    result = ' '.join(chunk_translations)
                    results[orig_idx] = result

                    # Cache
                    if self._cache:
                        self._cache.put(texts[orig_idx], "vi2en", result)

            return results

        elif direction == "en_to_vi":
            # For En->Vi, we need structure preservation, so use individual calls
            # but they internally use batching
            results = []
            for text in texts:
                result = await self.translate_en_to_vi(text)
                results.append(result)
            return results

        else:
            raise ValueError(f"Invalid direction: {direction}. Use 'vi_to_en' or 'en_to_vi'")

    async def unload_model(self) -> bool:
        """
        DEPRECATED: Models are now kept persistent for performance.

        This method is a no-op and will be removed in future versions.
        Use clear_cache() if you need to free memory.

        Returns:
            True (always succeeds as no-op)
        """
        import warnings
        warnings.warn(
            "unload_model() is deprecated. Models are now kept persistent for performance. "
            "Use clear_cache() to free cache memory if needed.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.info("unload_model() called but models are kept persistent")
        return True

    def clear_cache(self):
        """Clear the translation cache to free memory."""
        if self._cache:
            self._cache.clear()
            logger.info("Translation cache cleared")

        # Also clear token length cache
        with self._token_cache_lock:
            self._token_length_cache.clear()

    def is_loaded(self) -> bool:
        """Check if any model is currently loaded."""
        return self._vi2en_model is not None or self._en2vi_model is not None

    def is_vi2en_loaded(self) -> bool:
        """Check if Vi->En model is loaded."""
        return self._vi2en_model is not None

    def is_en2vi_loaded(self) -> bool:
        """Check if En->Vi model is loaded."""
        return self._en2vi_model is not None

    def get_cache_stats(self) -> Optional[dict]:
        """Get translation cache statistics."""
        if self._cache:
            return self._cache.stats()
        return None


# Singleton instance
transformers_client = TransformersClient()
