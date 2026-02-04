"""
HuggingFace Transformers Client for VietAI EnviT5 Translation.

Provides async interface for Vietnamese-English bidirectional translation
with automatic text chunking for context length limitations (512 tokens).
"""
import asyncio
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


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
    
    EnviT5 is trained on natural language, not markdown, so
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


def clean_translation_output(text: str) -> str:
    """
    Clean EnviT5 output by removing any language prefixes.
    
    Sometimes the model echoes its prompt prefix (vi:/en:) in the output.
    
    Args:
        text: Raw translation output
        
    Returns:
        Cleaned translation
    """
    if not text:
        return text
    
    # Remove vi: or en: prefix at start (with optional whitespace and punctuation)
    text = re.sub(r'^(vi|en):\s*[?!.]*\s*', '', text, flags=re.IGNORECASE)
    
    # Also check for prefix after any leading whitespace
    text = text.strip()
    text = re.sub(r'^(vi|en):\s*[?!.]*\s*', '', text, flags=re.IGNORECASE)
    
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
            lines.append(f"**{content}**")  # Use bold instead of # for better rendering
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


class TransformersClient:
    """Client for VietAI EnviT5 translation model with chunking support."""
    
    def __init__(self):
        self.model_name = "VietAI/envit5-translation"
        self.model = None
        self.tokenizer = None
        self.device = None
        self._lock = asyncio.Lock()
        self.max_chunk_tokens = 400  # Buffer for 512 token limit
    
    async def _ensure_loaded(self):
        """Lazy load model on first use."""
        if self.model is not None:
            return
        
        async with self._lock:
            # Double-check after acquiring lock
            if self.model is not None:
                return
            
            try:
                # Import here to avoid loading at module import time
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                import torch
                
                logger.info(f"Loading EnviT5 model: {self.model_name}")
                
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                
                # Determine device
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Using device: {self.device}")
                
                # Move model to device
                self.model.to(self.device)
                self.model.eval()  # Set to evaluation mode
                
                logger.info("EnviT5 model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load EnviT5 model: {e}")
                raise RuntimeError(f"EnviT5 model loading failed: {e}")
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks respecting sentence boundaries.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks, each <= max_chunk_tokens
        """
        if not text.strip():
            return [text]
        
        # First check if chunking is needed
        token_count = len(self.tokenizer.encode(text))
        if token_count <= self.max_chunk_tokens:
            return [text]
        
        # Split by sentences (basic splitting on common punctuation)
        import re
        # Split on period, exclamation, question mark followed by space or end
        sentences = re.split(r'([.!?]+\s+|[.!?]+$)', text)
        
        # Rejoin sentence with their punctuation
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
            sentence_tokens = len(self.tokenizer.encode(sentence))
            
            # If single sentence exceeds limit, split it by words
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
                    word_tokens = len(self.tokenizer.encode(word))
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
    
    async def _translate_single(self, prefixed_text: str) -> str:
        """
        Translate a single text chunk.
        
        Args:
            prefixed_text: Text with "vi:" or "en:" prefix
            
        Returns:
            Translated text
        """
        await self._ensure_loaded()
        
        logger.debug(f"[EnviT5] Input: {prefixed_text[:200]}..." if len(prefixed_text) > 200 else f"[EnviT5] Input: {prefixed_text}")
        
        try:
            import torch
            
            # Tokenize
            inputs = self.tokenizer(
                prefixed_text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            inputs = inputs.to(self.device)
            
            # Generate translation
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_length=512,
                    num_beams=5,
                    early_stopping=True,
                    no_repeat_ngram_size=2
                )
            
            # Decode
            raw_translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.debug(f"[EnviT5] Raw output: {raw_translation[:200]}..." if len(raw_translation) > 200 else f"[EnviT5] Raw output: {raw_translation}")
            
            # Clean the output (remove any echoed prefix)
            translation = clean_translation_output(raw_translation)
            logger.debug(f"[EnviT5] Cleaned output: {translation[:200]}..." if len(translation) > 200 else f"[EnviT5] Cleaned output: {translation}")
            
            return translation
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise RuntimeError(f"EnviT5 translation error: {e}")
    
    async def translate_vi_to_en(self, text: str) -> str:
        """
        Translate Vietnamese to English.
        
        Automatically chunks long texts to handle 512 token limit.
        Strips markdown before translation for better results.
        
        Args:
            text: Vietnamese text to translate
            
        Returns:
            English translation
        """
        if not text.strip():
            return ""
        
        logger.info(f"[Vi→En] Original input ({len(text)} chars): {text[:100]}..." if len(text) > 100 else f"[Vi→En] Original input: {text}")
        
        # Strip markdown before translation
        clean_text = strip_markdown(text)
        logger.info(f"[Vi→En] After markdown strip ({len(clean_text)} chars): {clean_text[:100]}..." if len(clean_text) > 100 else f"[Vi→En] After markdown strip: {clean_text}")
        
        await self._ensure_loaded()
        
        # Check if chunking needed
        chunks = self._chunk_text(clean_text)
        
        if len(chunks) == 1:
            logger.debug("Translating single chunk (Vi→En)")
            result = await self._translate_single(f"vi: {clean_text}")
            logger.info(f"[Vi→En] Final result: {result[:100]}..." if len(result) > 100 else f"[Vi→En] Final result: {result}")
            return result
        
        # Translate multiple chunks
        logger.info(f"Translating {len(chunks)} chunks (Vi→En)")
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Translating chunk {i+1}/{len(chunks)}")
            translation = await self._translate_single(f"vi: {chunk}")
            translated_chunks.append(translation)
        
        # Reassemble with proper spacing
        result = ' '.join(translated_chunks)
        logger.info(f"[Vi→En] Final result ({len(result)} chars): {result[:100]}..." if len(result) > 100 else f"[Vi→En] Final result: {result}")
        return result
    
    async def translate_en_to_vi(self, text: str) -> str:
        """
        Translate English to Vietnamese with structure preservation.
        
        Parses text into segments (headers, bullets, paragraphs), translates
        each segment, then reconstructs with proper formatting for readability.
        
        Args:
            text: English text to translate
            
        Returns:
            Vietnamese translation with preserved formatting
        """
        if not text.strip():
            return ""
        
        logger.info(f"[En→Vi] Original input ({len(text)} chars): {text[:100]}..." if len(text) > 100 else f"[En→Vi] Original input: {text}")
        
        await self._ensure_loaded()
        
        # Parse into structured segments
        segments = parse_structured_text(text)
        
        if not segments:
            # Fallback to simple translation
            clean_text = strip_markdown(text)
            result = await self._translate_single(f"en: {clean_text}")
            return result
        
        logger.info(f"[En→Vi] Parsed into {len(segments)} segments")
        
        # Translate each content segment
        translated_segments = []
        for seg_type, marker, content in segments:
            if seg_type == 'break' or not content.strip():
                translated_segments.append((seg_type, marker, content))
                continue
            
            # Clean inline markdown before translating
            clean_content = strip_markdown_inline(content)
            
            # Chunk if needed
            chunks = self._chunk_text(clean_content)
            
            if len(chunks) == 1:
                translated_content = await self._translate_single(f"en: {clean_content}")
            else:
                # Translate and reassemble chunks
                translated_chunks = []
                for chunk in chunks:
                    translated_chunk = await self._translate_single(f"en: {chunk}")
                    translated_chunks.append(translated_chunk)
                translated_content = ' '.join(translated_chunks)
            
            translated_segments.append((seg_type, marker, translated_content))
        
        # Reconstruct formatted text
        result = reconstruct_formatted_text(translated_segments)
        
        logger.info(f"[En→Vi] Final result ({len(result)} chars): {result[:100]}..." if len(result) > 100 else f"[En→Vi] Final result: {result}")
        return result
    
    async def translate_batch(
        self,
        texts: List[str],
        direction: str = "vi_to_en"
    ) -> List[str]:
        """
        Translate multiple texts.
        
        Args:
            texts: List of texts to translate
            direction: "vi_to_en" or "en_to_vi"
            
        Returns:
            List of translations
        """
        results = []
        
        for text in texts:
            if direction == "vi_to_en":
                result = await self.translate_vi_to_en(text)
            elif direction == "en_to_vi":
                result = await self.translate_en_to_vi(text)
            else:
                raise ValueError(f"Invalid direction: {direction}")
            
            results.append(result)
        
        return results
    
    async def unload_model(self) -> bool:
        """
        Unload model from memory.
        
        Returns:
            True if successful
        """
        async with self._lock:
            if self.model is None:
                return True
            
            try:
                import torch
                
                # Move to CPU and delete
                if self.device == "cuda":
                    self.model.cpu()
                    torch.cuda.empty_cache()
                
                del self.model
                del self.tokenizer
                
                self.model = None
                self.tokenizer = None
                self.device = None
                
                logger.info("EnviT5 model unloaded from memory")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unload model: {e}")
                return False
    
    def is_loaded(self) -> bool:
        """Check if model is currently loaded."""
        return self.model is not None


# Singleton instance
transformers_client = TransformersClient()
