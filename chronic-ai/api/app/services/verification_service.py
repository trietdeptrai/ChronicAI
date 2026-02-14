"""
Input Verification Service for ChronicAI.

Uses Gemma 2B to verify query clarity, detect ambiguities,
and assess whether human clarification is needed before processing.

Enhanced with:
- Retry logic for LLM calls
- Better safety thresholds calibrated for medical use
- Comprehensive logging for audit trail
"""
import json
import logging
from typing import List, Optional, Tuple

from app.services.ollama_client import ollama_client
from app.services.graph_state import VerificationResult
from app.services.resilience import (
    retry_async,
    RetryConfig,
    get_circuit_breaker,
    with_circuit_breaker,
    CircuitBreakerOpen,
    safety_audit,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Circuit breaker for verification model
_verification_breaker = get_circuit_breaker("verification", failure_threshold=5, recovery_timeout=30.0)

# Retry config for verification calls (faster than main reasoning)
VERIFICATION_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=0.5,
    max_delay=5.0,
    retryable_exceptions=(RuntimeError, TimeoutError, ConnectionError)
)


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

VERIFICATION_SYSTEM = """You are a medical query analyzer. Analyze the given query and assess:
1. Clarity: Is the query clear and unambiguous?
2. Patient References: Are patient names/references clear?
3. Medical Context: Is there enough context for a meaningful response?
4. Safety: Does it contain harmful or inappropriate content?

Output a JSON object with these fields:
{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues found"],
    "suggested_rewrites": ["clearer versions if needed"],
    "needs_clarification": true/false
}

Output ONLY the JSON, no other text."""


SAFETY_CHECK_SYSTEM = """You are a medical response safety reviewer. Analyze the given medical AI response for:

1. Risk Level: Does it contain potentially dangerous recommendations?
2. Medication Safety: Any dosage or drug interaction concerns?
3. Emergency Indicators: Should this trigger urgent medical attention?
4. Scope: Is the AI overstepping appropriate boundaries?

Output a JSON object:
{
    "safety_score": 0.0-1.0 (1.0 = completely safe, 0.0 = very risky),
    "risk_factors": ["list of identified risks"],
    "requires_review": true/false,
    "recommendations": ["suggested modifications if any"]
}

Output ONLY the JSON, no other text."""


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

async def verify_input(query_en: str) -> VerificationResult:
    """
    Verify the input query for clarity and appropriateness.

    Args:
        query_en: English query to verify

    Returns:
        VerificationResult with confidence and any issues
    """
    if not query_en.strip():
        return VerificationResult(
            is_valid=False,
            confidence=0.0,
            issues=["Empty query"],
            suggested_rewrites=[],
            needs_clarification=True
        )

    try:
        logger.info(f"[Verification] Analyzing query: {query_en[:100]}...")

        async def _verify_call():
            return await ollama_client.generate(
                model=settings.verification_model,
                prompt=f"Query to analyze: {query_en}",
                system=VERIFICATION_SYSTEM,
                stream=False,
                num_predict=max(int(settings.verification_max_tokens), 64)
            )

        response = await with_circuit_breaker(
            _verification_breaker,
            retry_async,
            _verify_call,
            config=VERIFICATION_RETRY_CONFIG,
            operation_name="verify_input"
        )

        # Parse JSON response
        result = _parse_verification_response(response)

        logger.info(f"[Verification] Result: confidence={result['confidence']:.2f}, "
                   f"valid={result['is_valid']}, issues={len(result['issues'])}")

        return result

    except CircuitBreakerOpen:
        logger.warning("[Verification] Circuit breaker open, accepting query with caution")
        return VerificationResult(
            is_valid=True,
            confidence=0.6,
            issues=["Verification service temporarily unavailable"],
            suggested_rewrites=[],
            needs_clarification=False
        )

    except Exception as e:
        logger.warning(f"[Verification] Failed, defaulting to valid with lower confidence: {e}")
        # On failure, accept the query but flag for potential review
        return VerificationResult(
            is_valid=True,
            confidence=0.5,
            issues=[f"Verification error: {str(e)[:100]}"],
            suggested_rewrites=[],
            needs_clarification=False
        )


async def check_response_safety(response_en: str) -> Tuple[float, List[str], bool]:
    """
    Check the safety of a medical AI response.

    Args:
        response_en: English response to check

    Returns:
        Tuple of (safety_score, risk_factors, requires_review)
    """
    if not response_en.strip():
        return (1.0, [], False)

    try:
        logger.info(f"[Safety] Checking response: {response_en[:100]}...")

        async def _safety_call():
            return await ollama_client.generate(
                model=settings.verification_model,
                prompt=f"Medical AI response to review:\n\n{response_en}",
                system=SAFETY_CHECK_SYSTEM,
                stream=False,
                num_predict=max(int(settings.verification_max_tokens), 64)
            )

        response = await with_circuit_breaker(
            _verification_breaker,
            retry_async,
            _safety_call,
            config=VERIFICATION_RETRY_CONFIG,
            operation_name="check_response_safety"
        )

        result = _parse_safety_response(response)

        # Log safety check for audit
        safety_audit.log_decision(
            event_type="response_safety_check",
            query=response_en[:200],
            decision=f"score_{result[0]:.2f}",
            confidence=result[0],
            risk_factors=result[1],
            human_review_required=result[2],
        )

        logger.info(f"[Safety] Score: {result[0]:.2f}, "
                   f"risks: {len(result[1])}, needs_review: {result[2]}")

        return result

    except CircuitBreakerOpen:
        logger.warning("[Safety] Circuit breaker open, defaulting to requiring review")
        # When verification is unavailable, be cautious and require review
        return (0.6, ["Safety verification service unavailable - manual review recommended"], True)

    except Exception as e:
        logger.warning(f"[Safety] Check failed, defaulting to requiring review: {e}")
        # On failure, be cautious and require review
        return (0.6, [f"Safety check error: {str(e)[:100]}"], True)


async def detect_patient_mentions(query_en: str) -> List[str]:
    """
    Detect patient name mentions in a query.
    
    Uses simple pattern matching + LLM fallback for ambiguous cases.
    
    Args:
        query_en: English query to analyze
        
    Returns:
        List of detected patient names
    """
    # Quick pattern-based detection for common patterns
    import re
    
    patterns = [
        r"patient\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"(?:Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'s\s+(?:condition|status|health|record)",
    ]
    
    detected = []
    for pattern in patterns:
        matches = re.findall(pattern, query_en)
        detected.extend(matches)
    
    if detected:
        return list(set(detected))
    
    # Fall back to LLM if no pattern matches
    return await _llm_extract_names(query_en)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_verification_response(response: str) -> VerificationResult:
    """Parse verification LLM response into VerificationResult."""
    try:
        # Clean up response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        
        data = json.loads(clean)
        
        return VerificationResult(
            is_valid=data.get("is_valid", True),
            confidence=float(data.get("confidence", 0.8)),
            issues=data.get("issues", []),
            suggested_rewrites=data.get("suggested_rewrites", []),
            needs_clarification=data.get("needs_clarification", False)
        )
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse verification response: {e}")
        return VerificationResult(
            is_valid=True,
            confidence=0.6,
            issues=["Parse error in verification"],
            suggested_rewrites=[],
            needs_clarification=False
        )


def _parse_safety_response(response: str) -> Tuple[float, List[str], bool]:
    """Parse safety check LLM response."""
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        
        data = json.loads(clean)
        
        return (
            float(data.get("safety_score", 0.8)),
            data.get("risk_factors", []),
            data.get("requires_review", False)
        )
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse safety response: {e}")
        return (0.7, ["Parse error"], True)


async def _llm_extract_names(query_en: str) -> List[str]:
    """Extract patient names using LLM when patterns fail."""
    try:
        response = await ollama_client.generate(
            model=settings.verification_model,
            prompt=f"Extract patient names from: {query_en}",
            system="Extract patient names. Output JSON array: [\"Name1\", \"Name2\"] or [] if none.",
            stream=False,
            num_predict=128
        )
        
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        
        names = json.loads(clean)
        return names if isinstance(names, list) else []
        
    except Exception as e:
        logger.warning(f"LLM name extraction failed: {e}")
        return []


# ============================================================================
# CONFIDENCE THRESHOLDS (Calibrated for Medical Use)
# ============================================================================

# Medical-specific high-risk keywords that ALWAYS trigger human review
CRITICAL_RISK_KEYWORDS = [
    # Medication risks
    "dosage", "dose", "overdose", "underdose",
    "allergic", "allergy", "anaphylaxis",
    "contraindication", "interaction", "drug interaction",
    # Emergency indicators
    "emergency", "urgent", "critical", "life-threatening",
    "cardiac arrest", "stroke", "seizure", "hemorrhage",
    # Procedure risks
    "surgery", "procedure", "invasive",
    # Vulnerable populations
    "pregnant", "pregnancy", "pediatric", "infant", "elderly",
    # Mental health
    "suicide", "self-harm", "overdose",
]

# Vietnamese equivalents
CRITICAL_RISK_KEYWORDS_VI = [
    "liều lượng", "quá liều", "dị ứng", "chống chỉ định",
    "khẩn cấp", "cấp cứu", "nguy kịch", "đe dọa tính mạng",
    "phẫu thuật", "mang thai", "trẻ em", "người già",
    "tự tử", "tự hại",
]


def should_request_clarification(
    verification: VerificationResult,
    threshold: Optional[float] = None
) -> bool:
    """
    Determine if human clarification should be requested.

    Args:
        verification: Result from verify_input
        threshold: Confidence threshold (default from settings)

    Returns:
        True if clarification needed
    """
    threshold = threshold or settings.hitl_confidence_threshold

    if not verification["is_valid"]:
        return True

    if verification["needs_clarification"]:
        return True

    if verification["confidence"] < threshold:
        return True

    # Check for multiple issues even with decent confidence
    if len(verification["issues"]) >= 2 and verification["confidence"] < 0.85:
        return True

    return False


def should_require_safety_review(
    safety_score: float,
    risk_factors: List[str],
    threshold: Optional[float] = None
) -> bool:
    """
    Determine if human safety review is required.

    Medical AI best practice: err on the side of caution.
    Better to have unnecessary reviews than miss dangerous content.

    Args:
        safety_score: Score from check_response_safety (0.0-1.0)
        risk_factors: List of identified risks
        threshold: Safety threshold (default from settings)

    Returns:
        True if review required
    """
    threshold = threshold or settings.hitl_safety_threshold

    # Low safety score always requires review
    if safety_score < (1.0 - threshold):
        logger.info(f"[Safety] Review required: score {safety_score:.2f} below threshold")
        return True

    # Very low score = immediate flag
    if safety_score < 0.5:
        logger.warning(f"[Safety] Critical: score {safety_score:.2f} very low")
        return True

    # Check for critical risk keywords in any risk factor
    risk_text = " ".join(risk_factors).lower()
    for keyword in CRITICAL_RISK_KEYWORDS:
        if keyword in risk_text:
            logger.info(f"[Safety] Review required: critical keyword '{keyword}' found")
            return True

    # Multiple risk factors = flag for review
    if len(risk_factors) >= 3:
        logger.info(f"[Safety] Review required: {len(risk_factors)} risk factors")
        return True

    return False


def get_safety_level(safety_score: float, risk_factors: List[str]) -> str:
    """
    Get human-readable safety level for UI display.

    Returns:
        Safety level: "safe", "caution", "warning", or "critical"
    """
    if safety_score >= 0.9 and len(risk_factors) == 0:
        return "safe"
    elif safety_score >= 0.7:
        return "caution"
    elif safety_score >= 0.5:
        return "warning"
    else:
        return "critical"
