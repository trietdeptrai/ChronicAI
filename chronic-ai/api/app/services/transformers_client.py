"""
HuggingFace Transformers Client for VietAI EnviT5 Translation.

Provides async interface for Vietnamese-English bidirectional translation
with automatic text chunking for context length limitations (512 tokens).
"""
import asyncio
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


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
            translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translation.strip()
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise RuntimeError(f"EnviT5 translation error: {e}")
    
    async def translate_vi_to_en(self, text: str) -> str:
        """
        Translate Vietnamese to English.
        
        Automatically chunks long texts to handle 512 token limit.
        
        Args:
            text: Vietnamese text to translate
            
        Returns:
            English translation
        """
        if not text.strip():
            return ""
        
        await self._ensure_loaded()
        
        # Check if chunking needed
        chunks = self._chunk_text(text)
        
        if len(chunks) == 1:
            logger.debug("Translating single chunk (Vi→En)")
            return await self._translate_single(f"vi: {text}")
        
        # Translate multiple chunks
        logger.info(f"Translating {len(chunks)} chunks (Vi→En)")
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Translating chunk {i+1}/{len(chunks)}")
            translation = await self._translate_single(f"vi: {chunk}")
            translated_chunks.append(translation)
        
        # Reassemble with proper spacing
        return ' '.join(translated_chunks)
    
    async def translate_en_to_vi(self, text: str) -> str:
        """
        Translate English to Vietnamese.
        
        Automatically chunks long texts to handle 512 token limit.
        
        Args:
            text: English text to translate
            
        Returns:
            Vietnamese translation
        """
        if not text.strip():
            return ""
        
        await self._ensure_loaded()
        
        # Check if chunking needed
        chunks = self._chunk_text(text)
        
        if len(chunks) == 1:
            logger.debug("Translating single chunk (En→Vi)")
            return await self._translate_single(f"en: {text}")
        
        # Translate multiple chunks
        logger.info(f"Translating {len(chunks)} chunks (En→Vi)")
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Translating chunk {i+1}/{len(chunks)}")
            translation = await self._translate_single(f"en: {chunk}")
            translated_chunks.append(translation)
        
        # Reassemble with proper spacing
        return ' '.join(translated_chunks)
    
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
