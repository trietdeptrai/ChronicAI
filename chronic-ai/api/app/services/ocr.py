"""
OCR Service using PaddleOCR.

Provides Vietnamese medical document text extraction from:
- PDF documents
- Images (X-ray labels, prescriptions, lab results)
"""
from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Any
from pathlib import Path
import tempfile
import os

if TYPE_CHECKING:
    from PIL import Image as PILImage

try:
    from paddleocr import PaddleOCR
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None
    Image = None
    ImageEnhance = None
    ImageFilter = None


class OCRService:
    """Vietnamese medical document OCR using PaddleOCR."""
    
    def __init__(self):
        """Initialize PaddleOCR with Vietnamese language support."""
        if not PADDLEOCR_AVAILABLE:
            raise ImportError(
                "PaddleOCR not available. Install with: "
                "pip install paddleocr pdf2image pillow"
            )
        
        # Initialize PaddleOCR for Vietnamese
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # Detect text orientation
            lang='vi',           # Vietnamese language
            show_log=False,      # Suppress verbose logging
            use_gpu=False        # CPU-only for compatibility
        )
    
    def preprocess_image(self, image: Any) -> Any:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Apply slight sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        # Denoise with median filter
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def extract_text_from_image(
        self,
        image_path: str,
        preprocess: bool = True
    ) -> str:
        """
        Extract text from an image file.
        
        Args:
            image_path: Path to image file
            preprocess: Whether to apply preprocessing
            
        Returns:
            Extracted text as string
        """
        if preprocess:
            # Load and preprocess
            image = Image.open(image_path)
            image = self.preprocess_image(image)
            
            # Save to temp file for PaddleOCR
            with tempfile.NamedTemporaryFile(
                suffix='.png',
                delete=False
            ) as tmp:
                image.save(tmp.name)
                result = self.ocr.ocr(tmp.name)
                os.unlink(tmp.name)
        else:
            result = self.ocr.ocr(image_path)
        
        return self._format_ocr_result(result)
    
    def extract_text_from_pdf(
        self,
        pdf_path: str,
        dpi: int = 200
    ) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for PDF to image conversion
            
        Returns:
            Extracted text from all pages
        """
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        all_text = []
        
        for page_num, image in enumerate(images, 1):
            # Preprocess each page
            processed = self.preprocess_image(image)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(
                suffix='.png',
                delete=False
            ) as tmp:
                processed.save(tmp.name)
                result = self.ocr.ocr(tmp.name)
                os.unlink(tmp.name)
            
            page_text = self._format_ocr_result(result)
            if page_text:
                all_text.append(f"--- Trang {page_num} ---\n{page_text}")
        
        return "\n\n".join(all_text)
    
    def _format_ocr_result(self, result: List) -> str:
        """
        Format PaddleOCR result to plain text.
        
        Args:
            result: Raw PaddleOCR output
            
        Returns:
            Formatted text string
        """
        if not result or not result[0]:
            return ""
        
        lines = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0]  # Get text content
                confidence = line[1][1]  # Get confidence score
                
                # Only include text with reasonable confidence
                if confidence > 0.5:
                    lines.append(text)
        
        return "\n".join(lines)
    
    def extract_structured_data(
        self,
        image_path: str,
        document_type: str = "general"
    ) -> dict:
        """
        Extract structured data from medical documents.
        
        Args:
            image_path: Path to image
            document_type: Type of document ('prescription', 'lab', 'xray')
            
        Returns:
            Structured data dict based on document type
        """
        raw_text = self.extract_text_from_image(image_path)
        
        result = {
            "raw_text": raw_text,
            "document_type": document_type,
            "extracted_fields": {}
        }
        
        # Basic field extraction patterns
        if document_type == "prescription":
            result["extracted_fields"] = self._extract_prescription_fields(raw_text)
        elif document_type == "lab":
            result["extracted_fields"] = self._extract_lab_fields(raw_text)
        
        return result
    
    def _extract_prescription_fields(self, text: str) -> dict:
        """Extract common prescription fields."""
        import re
        
        fields = {}
        
        # Try to extract patient name (common patterns)
        name_patterns = [
            r"Họ\s*(?:và\s*)?tên:\s*(.+)",
            r"Bệnh\s*nhân:\s*(.+)",
            r"Tên:\s*(.+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields["patient_name"] = match.group(1).strip()
                break
        
        # Try to extract diagnosis
        diagnosis_patterns = [
            r"Chẩn\s*đoán:\s*(.+)",
            r"Diagnosis:\s*(.+)"
        ]
        for pattern in diagnosis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields["diagnosis"] = match.group(1).strip()
                break
        
        return fields
    
    def _extract_lab_fields(self, text: str) -> dict:
        """Extract common lab result fields."""
        import re
        
        fields = {}
        
        # Common lab value patterns
        lab_patterns = {
            "glucose": r"(?:Glucose|Đường\s*huyết)[\s:]+(\d+(?:\.\d+)?)",
            "hba1c": r"HbA1c[\s:]+(\d+(?:\.\d+)?)",
            "creatinine": r"Creatinine[\s:]+(\d+(?:\.\d+)?)",
            "cholesterol": r"Cholesterol[\s:]+(\d+(?:\.\d+)?)"
        }
        
        for field, pattern in lab_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field] = float(match.group(1))
        
        return fields


# Lazy singleton - only initialize when needed
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create OCR service singleton."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


async def extract_text(
    file_path: str,
    file_type: str = "auto"
) -> str:
    """
    Async wrapper for text extraction.
    
    Args:
        file_path: Path to file
        file_type: 'pdf', 'image', or 'auto' (detect from extension)
        
    Returns:
        Extracted text
    """
    import asyncio
    
    path = Path(file_path)
    
    if file_type == "auto":
        if path.suffix.lower() == ".pdf":
            file_type = "pdf"
        else:
            file_type = "image"
    
    ocr = get_ocr_service()
    
    # Run OCR in thread pool (CPU-bound operation)
    loop = asyncio.get_event_loop()
    
    if file_type == "pdf":
        text = await loop.run_in_executor(
            None,
            ocr.extract_text_from_pdf,
            file_path
        )
    else:
        text = await loop.run_in_executor(
            None,
            ocr.extract_text_from_image,
            file_path
        )
    
    return text
