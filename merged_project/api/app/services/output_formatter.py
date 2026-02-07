"""
Output Formatter Service for ChronicAI.

Transforms raw AI responses into structured, user-friendly formats
with clear sections, icons, and priority highlighting.
"""
import re
from typing import List, Optional, Tuple
import logging

from app.services.graph_state import FormattedResponse, ResponseSection

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION DETECTION PATTERNS
# ============================================================================

SECTION_PATTERNS = {
    "assessment": [
        r"(?:^|\n)(?:#+\s*)?(?:assessment|đánh giá|diagnosis|chẩn đoán|tình trạng)",
        r"(?:^|\n)(?:the patient (?:has|is|shows)|bệnh nhân (?:có|đang|bị))",
        r"(?:^|\n)(?:current condition|tình trạng hiện tại)",
    ],
    "analysis": [
        r"(?:^|\n)(?:#+\s*)?(?:analysis|phân tích|findings|kết quả)",
        r"(?:^|\n)(?:based on|dựa trên|according to|theo)",
        r"(?:^|\n)(?:the (?:test|lab|results) (?:show|indicate)|xét nghiệm cho thấy)",
    ],
    "recommendations": [
        r"(?:^|\n)(?:#+\s*)?(?:recommend|đề xuất|suggest|khuyến nghị|advice|lời khuyên)",
        r"(?:^|\n)(?:should|nên|consider|cân nhắc|i recommend|tôi khuyên)",
        r"(?:^|\n)(?:\d+\.\s+|[-•]\s+)(?:continue|take|monitor|tiếp tục|uống|theo dõi)",
    ],
    "warnings": [
        r"(?:^|\n)(?:#+\s*)?(?:warning|cảnh báo|caution|lưu ý|important|quan trọng)",
        r"(?:^|\n)(?:seek (?:immediate|urgent)|đến (?:bệnh viện|cấp cứu) ngay)",
        r"(?:^|\n)(?:if (?:you experience|symptoms)|nếu (?:có|xuất hiện) triệu chứng)",
    ],
    "follow_up": [
        r"(?:^|\n)(?:#+\s*)?(?:follow[- ]?up|tái khám|next steps|bước tiếp)",
        r"(?:^|\n)(?:schedule|hẹn|return in|quay lại sau)",
    ],
}

SECTION_ICONS = {
    "assessment": "📋",
    "analysis": "🔬",
    "recommendations": "💊",
    "warnings": "⚠️",
    "follow_up": "📅",
    "general": "ℹ️",
}

SECTION_TITLES_VI = {
    "assessment": "Đánh giá tình trạng",
    "analysis": "Phân tích",
    "recommendations": "Đề xuất điều trị",
    "warnings": "Lưu ý quan trọng",
    "follow_up": "Kế hoạch theo dõi",
    "general": "Thông tin",
}


# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_response(
    response_text: str,
    language: str = "vi",
    confidence: float = 0.8,
    sources: Optional[List[str]] = None
) -> FormattedResponse:
    """
    Format a raw AI response into structured sections.
    
    Args:
        response_text: Raw response text
        language: Output language ("vi" or "en")
        confidence: Confidence score for the response
        sources: List of data sources used
        
    Returns:
        FormattedResponse with structured sections
    """
    if not response_text.strip():
        return FormattedResponse(
            sections=[],
            confidence=0.0,
            sources=[],
            raw_text=""
        )
    
    # Clean the input
    cleaned = _clean_text(response_text)
    
    # Try to detect and split sections
    sections = _detect_sections(cleaned, language)
    
    # If no clear sections detected, create a single general section
    if not sections:
        sections = [_create_single_section(cleaned, language)]
    
    return FormattedResponse(
        sections=sections,
        confidence=confidence,
        sources=sources or [],
        raw_text=cleaned
    )


def format_as_html(formatted: FormattedResponse) -> str:
    """
    Convert FormattedResponse to HTML for rendering.
    
    Args:
        formatted: Structured response
        
    Returns:
        HTML string
    """
    html_parts = []
    
    for section in formatted["sections"]:
        html_parts.append(f'<div class="response-section section-{section["type"]}">')
        html_parts.append(f'  <h3>{section["icon"]} {section["title"]}</h3>')
        
        if section.get("content"):
            html_parts.append(f'  <p>{section["content"]}</p>')
        
        if section.get("items"):
            html_parts.append('  <ul>')
            for item in section["items"]:
                html_parts.append(f'    <li>{item}</li>')
            html_parts.append('  </ul>')
        
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def format_as_markdown(formatted: FormattedResponse) -> str:
    """
    Convert FormattedResponse to Markdown.
    
    Args:
        formatted: Structured response
        
    Returns:
        Markdown string
    """
    md_parts = []
    
    for section in formatted["sections"]:
        md_parts.append(f"### {section['icon']} {section['title']}\n")
        
        if section.get("content"):
            md_parts.append(f"{section['content']}\n")
        
        if section.get("items"):
            for item in section["items"]:
                md_parts.append(f"- {item}")
            md_parts.append("")
    
    return '\n'.join(md_parts)


def format_as_plain_text(formatted: FormattedResponse) -> str:
    """
    Convert FormattedResponse to plain text with visual structure.
    
    Args:
        formatted: Structured response
        
    Returns:
        Plain text string
    """
    text_parts = []
    
    for section in formatted["sections"]:
        # Section header with underline
        header = f"{section['icon']} {section['title']}"
        text_parts.append(header)
        text_parts.append("─" * len(header))
        
        if section.get("content"):
            text_parts.append(section["content"])
        
        if section.get("items"):
            for item in section["items"]:
                text_parts.append(f"  • {item}")
        
        text_parts.append("")  # Blank line between sections
    
    return '\n'.join(text_parts)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _clean_text(text: str) -> str:
    """Clean and normalize response text."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove markdown artifacts that shouldn't be displayed
    text = re.sub(r'\*{3,}', '', text)
    
    return text.strip()


def _detect_sections(text: str, language: str) -> List[ResponseSection]:
    """
    Detect and split text into sections based on patterns.
    
    Args:
        text: Cleaned response text
        language: Target language
        
    Returns:
        List of detected sections
    """
    sections = []
    remaining_text = text
    found_positions = []
    
    # Find all section matches
    for section_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                found_positions.append((match.start(), section_type, match.end()))
    
    if not found_positions:
        return []
    
    # Sort by position
    found_positions.sort(key=lambda x: x[0])
    
    # Extract sections
    for i, (start, section_type, header_end) in enumerate(found_positions):
        # Find end of this section (start of next or end of text)
        if i + 1 < len(found_positions):
            end = found_positions[i + 1][0]
        else:
            end = len(text)
        
        content = text[header_end:end].strip()
        
        if content:
            section = _create_section(section_type, content, language)
            if section:
                sections.append(section)
    
    return sections


def _create_section(
    section_type: str,
    content: str,
    language: str
) -> Optional[ResponseSection]:
    """Create a ResponseSection from type and content."""
    if not content.strip():
        return None
    
    # Check if content is a list
    items = _extract_list_items(content)
    
    titles = SECTION_TITLES_VI if language == "vi" else {
        "assessment": "Assessment",
        "analysis": "Analysis",
        "recommendations": "Recommendations",
        "warnings": "Important Warnings",
        "follow_up": "Follow-up Plan",
        "general": "Information",
    }
    
    return ResponseSection(
        type=section_type,
        icon=SECTION_ICONS.get(section_type, "ℹ️"),
        title=titles.get(section_type, titles["general"]),
        content=None if items else content,
        items=items if items else None
    )


def _create_single_section(content: str, language: str) -> ResponseSection:
    """Create a single general section for unstructured content."""
    # Check if content has list items
    items = _extract_list_items(content)
    
    # Try to determine best section type from content
    section_type = _guess_section_type(content)
    
    titles = SECTION_TITLES_VI if language == "vi" else {
        "assessment": "Assessment",
        "analysis": "Analysis", 
        "recommendations": "Recommendations",
        "warnings": "Important Warnings",
        "follow_up": "Follow-up Plan",
        "general": "Response",
    }
    
    return ResponseSection(
        type=section_type,
        icon=SECTION_ICONS.get(section_type, "ℹ️"),
        title=titles.get(section_type, titles["general"]),
        content=None if items else content,
        items=items if items else None
    )


def _extract_list_items(text: str) -> Optional[List[str]]:
    """Extract list items from text if present."""
    # Look for bullet points or numbered lists
    patterns = [
        r'^[-•*]\s+(.+)$',
        r'^\d+\.\s+(.+)$',
        r'^[a-z]\)\s+(.+)$',
    ]
    
    items = []
    for line in text.split('\n'):
        line = line.strip()
        for pattern in patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                items.append(match.group(1).strip())
                break
    
    # Only return if we found multiple items
    return items if len(items) >= 2 else None


def _guess_section_type(content: str) -> str:
    """Guess the most appropriate section type for content."""
    content_lower = content.lower()
    
    # Check for warning indicators
    if any(w in content_lower for w in ["warning", "cảnh báo", "urgent", "khẩn", "emergency", "cấp cứu"]):
        return "warnings"
    
    # Check for recommendation indicators
    if any(w in content_lower for w in ["recommend", "đề xuất", "should", "nên", "suggest"]):
        return "recommendations"
    
    # Check for follow-up indicators
    if any(w in content_lower for w in ["follow", "tái khám", "schedule", "hẹn", "next"]):
        return "follow_up"
    
    # Check for analysis indicators
    if any(w in content_lower for w in ["based on", "dựa trên", "results", "kết quả", "shows"]):
        return "analysis"
    
    return "general"


# ============================================================================
# PRIORITY HIGHLIGHTING
# ============================================================================

def highlight_priority_items(sections: List[ResponseSection]) -> List[ResponseSection]:
    """
    Add priority highlighting to sections.
    
    Warnings and urgent items should be visually distinct.
    
    Args:
        sections: List of sections to process
        
    Returns:
        Sections with priority markers
    """
    for section in sections:
        if section["type"] == "warnings":
            # Mark as high priority
            section["priority"] = "high"
        elif section["type"] == "recommendations":
            section["priority"] = "medium"
        else:
            section["priority"] = "normal"
    
    return sections


def get_urgency_indicator(formatted: FormattedResponse) -> Tuple[str, str]:
    """
    Get urgency indicator for the response.
    
    Args:
        formatted: Formatted response
        
    Returns:
        Tuple of (urgency_level, urgency_message)
    """
    has_warnings = any(s["type"] == "warnings" for s in formatted["sections"])
    
    # Check warning content for emergency keywords
    emergency_keywords = ["emergency", "cấp cứu", "immediately", "ngay lập tức", "urgent", "khẩn cấp"]
    
    for section in formatted["sections"]:
        content = section.get("content", "") or ""
        items = section.get("items", []) or []
        all_text = content + " ".join(items)
        
        if any(kw in all_text.lower() for kw in emergency_keywords):
            return ("emergency", "⚠️ Cần can thiệp y tế khẩn cấp")
    
    if has_warnings:
        return ("warning", "⚡ Có lưu ý quan trọng cần chú ý")
    
    return ("normal", "")
