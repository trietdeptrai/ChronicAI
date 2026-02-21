"""
OCR Service using PaddleOCR.

Provides Vietnamese medical document text extraction from:
- PDF documents
- Images (X-ray labels, prescriptions, lab results)
"""
from __future__ import annotations
from typing import Callable, List, Optional, TYPE_CHECKING, Any
from pathlib import Path
from functools import partial
import tempfile
import os
import shutil
import logging
import re
import time

if TYPE_CHECKING:
    from PIL import Image as PILImage

_OCR_DEPENDENCY_INSTALL_HINT = (
    "Install OCR dependencies in the API virtualenv: "
    "pip install paddlepaddle paddleocr pdf2image pillow"
)


class OCRDependencyError(RuntimeError):
    """Raised when OCR runtime dependencies are missing."""


def _build_ocr_dependency_error(exc: Optional[BaseException] = None) -> OCRDependencyError:
    if isinstance(exc, ModuleNotFoundError) and exc.name == "paddle":
        return OCRDependencyError(
            "OCR runtime dependency is missing: module 'paddle' (package 'paddlepaddle'). "
            f"{_OCR_DEPENDENCY_INSTALL_HINT}"
        )
    if exc is not None:
        return OCRDependencyError(f"OCR dependencies are unavailable: {exc}. {_OCR_DEPENDENCY_INSTALL_HINT}")
    return OCRDependencyError(f"OCR dependencies are unavailable. {_OCR_DEPENDENCY_INSTALL_HINT}")


def _resolve_poppler_path() -> Optional[str]:
    """
    Locate Poppler binaries directory for pdf2image when PATH is incomplete.

    Priority:
    1) explicit env vars (directory or full pdfinfo path)
    2) current PATH
    3) common local install paths
    """
    env_candidates = [
        os.getenv("OCR_POPPLER_PATH", "").strip(),
        os.getenv("POPPLER_PATH", "").strip(),
        os.getenv("PDF2IMAGE_POPPLER_PATH", "").strip(),
    ]

    def normalize(candidate: str) -> Optional[str]:
        if not candidate:
            return None
        path = Path(candidate).expanduser()
        if path.is_file():
            path = path.parent
        if not path.exists() or not path.is_dir():
            return None
        if (path / "pdfinfo").exists():
            return str(path)
        return None

    for candidate in env_candidates:
        normalized = normalize(candidate)
        if normalized:
            return normalized

    # If available in PATH, no explicit poppler_path is required.
    if shutil.which("pdfinfo"):
        return None

    for candidate in ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"):
        normalized = normalize(candidate)
        if normalized:
            return normalized

    return None


def _is_missing_poppler_error(exc: BaseException) -> bool:
    name = exc.__class__.__name__
    message = str(exc).lower()
    if name == "PDFInfoNotInstalledError":
        return True
    if isinstance(exc, FileNotFoundError) and "pdfinfo" in message:
        return True
    if "unable to get page count" in message and "poppler" in message:
        return True
    if "no such file or directory" in message and "pdfinfo" in message:
        return True
    return False


try:
    import paddle  # type: ignore  # noqa: F401
    from paddleocr import PaddleOCR
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np
    PADDLEOCR_AVAILABLE = True
except ImportError as exc:
    PADDLEOCR_AVAILABLE = False
    _PADDLEOCR_IMPORT_ERROR: Optional[BaseException] = exc
    PaddleOCR = None
    convert_from_path = None
    Image = None
    ImageEnhance = None
    ImageFilter = None
    np = None
else:
    _PADDLEOCR_IMPORT_ERROR = None


def _safe_unlink(path: str, retries: int = 8, delay_seconds: float = 0.2) -> None:
    """
    Delete a temp file with retries for Windows file-lock timing.
    """
    for attempt in range(retries):
        try:
            os.unlink(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == retries - 1:
                raise
            time.sleep(delay_seconds)


class OCRService:
    """Vietnamese medical document OCR using PaddleOCR."""

    def __init__(self):
        """Initialize PaddleOCR with Vietnamese language support."""
        if not PADDLEOCR_AVAILABLE:
            raise _build_ocr_dependency_error(_PADDLEOCR_IMPORT_ERROR)

        # Initialize PaddleOCR for Vietnamese.
        # PaddleOCR keyword support differs across versions, so degrade gracefully.
        kwargs: dict[str, Any] = {
            "use_angle_cls": True,  # Detect text orientation
            "lang": "vi",           # Vietnamese language
            "show_log": False,      # Suppress verbose logging (not supported in all versions)
            "use_gpu": False,       # CPU-only for compatibility
        }

        logger = logging.getLogger(__name__)
        while True:
            try:
                self.ocr = PaddleOCR(**kwargs)
                break
            except ValueError as exc:
                match = re.search(r"Unknown argument:\s*([A-Za-z_][A-Za-z0-9_]*)", str(exc))
                if not match:
                    raise
                bad_arg = match.group(1)
                if bad_arg in kwargs:
                    kwargs.pop(bad_arg, None)
                    logger.warning("PaddleOCR does not support '%s'; retrying without it.", bad_arg)
                    continue
                raise
            except TypeError as exc:
                # Older/newer versions may raise TypeError for unsupported kwargs.
                msg = str(exc)
                removed = False
                for key in list(kwargs.keys()):
                    if f"'{key}'" in msg and ("unexpected keyword" in msg or "got an unexpected" in msg):
                        kwargs.pop(key, None)
                        logger.warning("PaddleOCR rejected '%s'; retrying without it.", key)
                        removed = True
                        break
                if removed:
                    continue
                raise
            except ModuleNotFoundError as exc:
                raise _build_ocr_dependency_error(exc) from exc

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

    def _run_ocr_on_pil_image(self, image: Any) -> Any:
        """
        Run OCR directly from PIL image buffer (no disk temp files when possible).
        """
        logger = logging.getLogger(__name__)

        if np is not None:
            try:
                rgb_image = image.convert("RGB")
                image_array = np.array(rgb_image)
                return self.ocr.ocr(image_array)
            except Exception:
                logger.debug("[ocr] ndarray OCR path failed; fallback to temp file", exc_info=True)

        tmp_name = None
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False
        ) as tmp:
            tmp_name = tmp.name
            image.save(tmp_name)
        try:
            return self.ocr.ocr(tmp_name)
        finally:
            if tmp_name:
                _safe_unlink(tmp_name)

    @staticmethod
    def _normalize_ocr_text(text: str) -> str:
        """
        Fix common OCR spacing artifacts without changing semantic content.

        Example: "202 6" -> "2026" (split year).
        """
        if not text:
            return text
        normalized = text
        # Join 4-digit years split as 3+1 digits, e.g. "202 6" -> "2026".
        normalized = re.sub(r"\b((?:19|20)\d)\s+(\d)\b", r"\1\2", normalized)
        return normalized
    
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
            with Image.open(image_path) as image:
                processed = self.preprocess_image(image)
                result = self._run_ocr_on_pil_image(processed)
        else:
            result = self.ocr.ocr(image_path)
        
        return self._format_ocr_result(result)
    
    def extract_text_from_pdf(
        self,
        pdf_path: str,
        dpi: int = 200,
        max_pages: Optional[int] = None,
        preprocess: bool = True,
        render_threads: int = 1,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for PDF to image conversion
            
        Returns:
            Extracted text from all pages
        """
        logger = logging.getLogger(__name__)
        convert_kwargs: dict[str, Any] = {"dpi": dpi}
        if render_threads and render_threads > 1:
            convert_kwargs["thread_count"] = int(render_threads)
        if isinstance(max_pages, int) and max_pages > 0:
            convert_kwargs["first_page"] = 1
            convert_kwargs["last_page"] = max_pages
        poppler_path = _resolve_poppler_path()
        if poppler_path:
            convert_kwargs["poppler_path"] = poppler_path

        logger.info(
            "[ocr] converting pdf path=%s dpi=%s max_pages=%s poppler_path=%s",
            pdf_path,
            dpi,
            max_pages if isinstance(max_pages, int) and max_pages > 0 else "all",
            poppler_path or "<PATH>",
        )
        # Convert PDF pages to images
        try:
            images = convert_from_path(pdf_path, **convert_kwargs)
        except Exception as exc:
            if _is_missing_poppler_error(exc):
                raise OCRDependencyError(
                    "PDF OCR requires Poppler ('pdfinfo'). Install Poppler and ensure it is discoverable. "
                    "On macOS: `brew install poppler`. "
                    "If already installed but not in runtime PATH, set `POPPLER_PATH` "
                    "(or `OCR_POPPLER_PATH`) to the directory containing `pdfinfo` "
                    "(common Homebrew path: `/opt/homebrew/bin`)."
                ) from exc
            raise
        logger.info("[ocr] pdf converted pages=%s", len(images))

        dump_ocr_text = logger.isEnabledFor(logging.DEBUG)
        started_at = time.perf_counter()
        all_text = []

        for page_num, image in enumerate(images, 1):
            page_started_at = time.perf_counter()
            logger.info("[ocr] processing page=%s/%s", page_num, len(images))
            if progress_callback:
                try:
                    progress_callback(page_num, len(images))
                except Exception:
                    logger.debug("[ocr] progress callback failed", exc_info=True)
            try:
                if preprocess:
                    processed = self.preprocess_image(image)
                else:
                    processed = image
                result = self._run_ocr_on_pil_image(processed)
            finally:
                try:
                    image.close()
                except Exception:
                    pass

            page_text = self._format_ocr_result(result)
            elapsed_ms = (time.perf_counter() - page_started_at) * 1000.0
            logger.info(
                "[ocr] page=%s/%s done chars=%s elapsed_ms=%.1f",
                page_num,
                len(images),
                len(page_text or ""),
                elapsed_ms,
            )
            if dump_ocr_text:
                logger.debug(
                    "[ocr] page=%s/%s text_begin\n%s\n[ocr] page=%s/%s text_end",
                    page_num,
                    len(images),
                    page_text or "<empty>",
                    page_num,
                    len(images),
                )
            if page_text:
                all_text.append(f"--- Trang {page_num} ---\n{page_text}")

        full_text = "\n\n".join(all_text)
        total_elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        logger.info(
            "[ocr] completed pages=%s extracted_chars=%s elapsed_ms=%.1f",
            len(images),
            len(full_text or ""),
            total_elapsed_ms,
        )
        if dump_ocr_text:
            logger.debug(
                "[ocr] full_text_begin\n%s\n[ocr] full_text_end",
                full_text or "<empty>",
            )
        return full_text
    
    def _format_ocr_result(self, result: List) -> str:
        """
        Format PaddleOCR result to plain text.
        
        Args:
            result: Raw PaddleOCR output
            
        Returns:
            Formatted text string
        """
        if not result:
            return ""

        logger = logging.getLogger(__name__)
        entries: list[tuple[str, float]] = []

        def add_entry(text_val: Any, score_val: Any = 1.0) -> None:
            text = str(text_val or "").strip()
            text = self._normalize_ocr_text(text)
            if not text:
                return
            try:
                score = float(score_val)
            except Exception:
                score = 1.0
            entries.append((text, score))

        def walk(node: Any) -> None:
            if node is None:
                return

            if isinstance(node, dict):
                # Common dict formats in newer OCR pipeline outputs.
                if isinstance(node.get("text"), str):
                    add_entry(node.get("text"), node.get("score", node.get("confidence", 1.0)))
                if isinstance(node.get("rec_text"), str):
                    add_entry(node.get("rec_text"), node.get("rec_score", node.get("score", 1.0)))
                rec_texts = node.get("rec_texts")
                if isinstance(rec_texts, list):
                    rec_scores = node.get("rec_scores")
                    for idx, txt in enumerate(rec_texts):
                        score = rec_scores[idx] if isinstance(rec_scores, list) and idx < len(rec_scores) else 1.0
                        add_entry(txt, score)
                # Continue walking nested structures.
                for value in node.values():
                    if isinstance(value, (list, tuple, dict)):
                        walk(value)
                return

            if isinstance(node, (list, tuple)):
                # Legacy PaddleOCR format: [bbox, (text, confidence)]
                if len(node) >= 2:
                    second = node[1]
                    if isinstance(second, (list, tuple)) and len(second) >= 1 and isinstance(second[0], str):
                        score = second[1] if len(second) >= 2 else 1.0
                        add_entry(second[0], score)
                    elif isinstance(second, str):
                        add_entry(second, 1.0)
                    elif isinstance(node[0], str):
                        # Fallback format: (text, score)
                        add_entry(node[0], second if isinstance(second, (int, float)) else 1.0)
                elif len(node) == 1 and isinstance(node[0], str):
                    add_entry(node[0], 1.0)

                for item in node:
                    if isinstance(item, (list, tuple, dict)):
                        walk(item)
                return

            if isinstance(node, str):
                add_entry(node, 1.0)

        try:
            walk(result)
        except Exception as exc:
            logger.warning("Failed while parsing OCR result structure: %s", exc)

        # Keep high-confidence lines, de-duplicate preserving order.
        seen: set[str] = set()
        lines: list[str] = []
        for text, confidence in entries:
            if confidence < 0.5:
                continue
            if text in seen:
                continue
            seen.add(text)
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
    file_type: str = "auto",
    *,
    pdf_dpi: int = 200,
    pdf_max_pages: Optional[int] = None,
    pdf_preprocess: bool = True,
    pdf_render_threads: int = 1,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
            partial(
                ocr.extract_text_from_pdf,
                file_path,
                pdf_dpi,
                pdf_max_pages,
                pdf_preprocess,
                pdf_render_threads,
                progress_callback,
            ),
        )
    else:
        text = await loop.run_in_executor(
            None,
            ocr.extract_text_from_image,
            file_path
        )
    
    return text
