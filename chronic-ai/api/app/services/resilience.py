"""
Resilience utilities for ChronicAI.

Provides retry logic, circuit breakers, and defensive response patterns
for robust medical AI application handling.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# RETRY LOGIC
# ============================================================================

class RetryStrategy(str, Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple = (Exception,)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        else:
            delay = self.base_delay
        return min(delay, self.max_delay)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    operation_name: str = "operation",
    **kwargs
) -> T:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: Retry configuration
        operation_name: Name for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            if attempt < config.max_attempts - 1:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"[Retry] {operation_name} failed (attempt {attempt + 1}/{config.max_attempts}): "
                    f"{type(e).__name__}: {str(e)[:100]}. Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[Retry] {operation_name} failed after {config.max_attempts} attempts: "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )

    raise last_exception


def with_retry(
    config: Optional[RetryConfig] = None,
    operation_name: Optional[str] = None
):
    """
    Decorator for adding retry logic to async functions.

    Usage:
        @with_retry(config=RetryConfig(max_attempts=3))
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            name = operation_name or func.__name__
            return await retry_async(func, *args, config=config, operation_name=name, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Tracks failures and opens circuit when threshold is exceeded,
    preventing further calls to failing services.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    # State tracking
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"[CircuitBreaker] {self.name}: OPEN -> HALF_OPEN (testing recovery)")
        return self._state

    def record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"[CircuitBreaker] {self.name}: HALF_OPEN -> CLOSED (recovered)")
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self, error: Exception):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens circuit
            self._state = CircuitState.OPEN
            logger.warning(f"[CircuitBreaker] {self.name}: HALF_OPEN -> OPEN (recovery failed)")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"[CircuitBreaker] {self.name}: CLOSED -> OPEN "
                f"(failure threshold {self.failure_threshold} reached)"
            )

    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        state = self.state  # Triggers recovery check
        if state == CircuitState.OPEN:
            return False
        return True

    def reset(self):
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info(f"[CircuitBreaker] {self.name}: Manually reset to CLOSED")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, breaker_name: str):
        self.breaker_name = breaker_name
        super().__init__(f"Circuit breaker '{breaker_name}' is OPEN - service unavailable")


# Global circuit breakers for critical services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _circuit_breakers[name]


async def with_circuit_breaker(
    breaker: CircuitBreaker,
    func: Callable[..., T],
    *args,
    fallback: Optional[Callable[..., T]] = None,
    **kwargs
) -> T:
    """
    Execute a function with circuit breaker protection.

    Args:
        breaker: Circuit breaker instance
        func: Async function to execute
        fallback: Optional fallback function if circuit is open

    Returns:
        Result from function or fallback

    Raises:
        CircuitBreakerOpen if circuit is open and no fallback
    """
    if not breaker.is_available():
        if fallback:
            logger.info(f"[CircuitBreaker] {breaker.name}: Using fallback")
            return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
        raise CircuitBreakerOpen(breaker.name)

    try:
        result = await func(*args, **kwargs)
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure(e)
        raise


# ============================================================================
# DEFENSIVE RESPONSES
# ============================================================================

@dataclass
class UncertaintyIndicator:
    """Indicators of AI uncertainty in a response."""
    low_confidence: bool = False
    missing_context: bool = False
    ambiguous_query: bool = False
    out_of_scope: bool = False
    contradictory_data: bool = False

    @property
    def needs_disclaimer(self) -> bool:
        """Check if response needs uncertainty disclaimer."""
        return any([
            self.low_confidence,
            self.missing_context,
            self.ambiguous_query,
            self.out_of_scope,
            self.contradictory_data
        ])

    def get_reasons(self) -> List[str]:
        """Get list of uncertainty reasons."""
        reasons = []
        if self.low_confidence:
            reasons.append("low_confidence")
        if self.missing_context:
            reasons.append("missing_context")
        if self.ambiguous_query:
            reasons.append("ambiguous_query")
        if self.out_of_scope:
            reasons.append("out_of_scope")
        if self.contradictory_data:
            reasons.append("contradictory_data")
        return reasons


# Vietnamese uncertainty disclaimers
UNCERTAINTY_DISCLAIMERS_VI = {
    "low_confidence": "⚠️ Lưu ý: Độ tin cậy của phân tích này thấp hơn bình thường. Vui lòng xác minh với bác sĩ chuyên khoa.",
    "missing_context": "⚠️ Lưu ý: Thiếu một số thông tin cần thiết để đưa ra đánh giá chính xác. Vui lòng bổ sung thông tin hoặc tham khảo hồ sơ bệnh án đầy đủ.",
    "ambiguous_query": "⚠️ Lưu ý: Câu hỏi có thể được hiểu theo nhiều cách khác nhau. Phản hồi dựa trên cách hiểu phổ biến nhất.",
    "out_of_scope": "⚠️ Lưu ý: Câu hỏi này nằm ngoài phạm vi hỗ trợ của hệ thống. Vui lòng tham khảo ý kiến chuyên gia.",
    "contradictory_data": "⚠️ Lưu ý: Phát hiện dữ liệu mâu thuẫn trong hồ sơ. Vui lòng kiểm tra lại thông tin.",
}

UNCERTAINTY_DISCLAIMERS_EN = {
    "low_confidence": "⚠️ Note: This analysis has lower confidence than usual. Please verify with a specialist.",
    "missing_context": "⚠️ Note: Some necessary information is missing for accurate assessment. Please provide additional context.",
    "ambiguous_query": "⚠️ Note: The query may be interpreted in multiple ways. Response based on most common interpretation.",
    "out_of_scope": "⚠️ Note: This question is outside the system's scope. Please consult a specialist.",
    "contradictory_data": "⚠️ Note: Contradictory data detected in records. Please verify the information.",
}


def get_uncertainty_disclaimer(indicator: UncertaintyIndicator, language: str = "vi") -> str:
    """Get appropriate disclaimer text for uncertainty indicators."""
    disclaimers = UNCERTAINTY_DISCLAIMERS_VI if language == "vi" else UNCERTAINTY_DISCLAIMERS_EN

    disclaimer_parts = []
    for reason in indicator.get_reasons():
        if reason in disclaimers:
            disclaimer_parts.append(disclaimers[reason])

    return "\n\n".join(disclaimer_parts)


def create_defensive_response(
    message: str,
    confidence: float,
    context_available: bool = True,
    language: str = "vi"
) -> tuple[str, UncertaintyIndicator]:
    """
    Create a defensive response with appropriate uncertainty indicators.

    Returns:
        Tuple of (modified message, uncertainty indicator)
    """
    indicator = UncertaintyIndicator(
        low_confidence=confidence < 0.6,
        missing_context=not context_available
    )

    if indicator.needs_disclaimer:
        disclaimer = get_uncertainty_disclaimer(indicator, language)
        message = f"{message}\n\n{disclaimer}"

    return message, indicator


# ============================================================================
# "I DON'T KNOW" RESPONSE PATTERNS
# ============================================================================

IDK_TRIGGERS_EN = [
    "i don't have enough information",
    "cannot determine",
    "unable to assess",
    "insufficient data",
    "no records found",
    "outside my expertise",
    "beyond my knowledge",
    "i cannot provide",
    "not enough context",
]

IDK_TRIGGERS_VI = [
    "không đủ thông tin",
    "không thể xác định",
    "thiếu dữ liệu",
    "không tìm thấy hồ sơ",
    "ngoài phạm vi",
    "không thể cung cấp",
    "thiếu ngữ cảnh",
]


def detect_uncertainty_in_response(response: str, language: str = "en") -> bool:
    """Detect if an AI response indicates uncertainty."""
    triggers = IDK_TRIGGERS_EN if language == "en" else IDK_TRIGGERS_VI
    response_lower = response.lower()

    return any(trigger in response_lower for trigger in triggers)


def create_idk_response(
    reason: str,
    original_query: str,
    language: str = "vi",
    suggestions: Optional[List[str]] = None
) -> str:
    """
    Create a proper "I don't know" response.

    Instead of hallucinating, provides honest uncertainty with next steps.
    """
    if language == "vi":
        response = f"""## Không thể trả lời

Tôi không thể đưa ra câu trả lời chính xác cho câu hỏi này vì: **{reason}**

### Gợi ý tiếp theo:
"""
        if suggestions:
            for suggestion in suggestions:
                response += f"- {suggestion}\n"
        else:
            response += """- Cung cấp thêm thông tin chi tiết
- Kiểm tra hồ sơ bệnh án
- Tham khảo ý kiến bác sĩ chuyên khoa
"""
    else:
        response = f"""## Unable to Answer

I cannot provide an accurate answer to this question because: **{reason}**

### Suggested next steps:
"""
        if suggestions:
            for suggestion in suggestions:
                response += f"- {suggestion}\n"
        else:
            response += """- Provide more detailed information
- Check medical records
- Consult with a specialist
"""

    return response


# ============================================================================
# AUDIT LOGGING
# ============================================================================

@dataclass
class AuditEntry:
    """Audit log entry for safety-critical decisions."""
    timestamp: float
    event_type: str
    patient_id: Optional[str]
    query: str
    decision: str
    confidence: float
    risk_factors: List[str]
    human_review_required: bool
    human_approved: Optional[bool]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafetyAuditLogger:
    """Logger for safety-critical medical AI decisions."""

    def __init__(self, max_entries: int = 10000):
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries
        self._logger = logging.getLogger("safety_audit")

    def log_decision(
        self,
        event_type: str,
        query: str,
        decision: str,
        confidence: float,
        risk_factors: List[str] = None,
        patient_id: Optional[str] = None,
        human_review_required: bool = False,
        human_approved: Optional[bool] = None,
        **metadata
    ):
        """Log a safety-critical decision."""
        entry = AuditEntry(
            timestamp=time.time(),
            event_type=event_type,
            patient_id=patient_id,
            query=query[:500],  # Truncate for storage
            decision=decision,
            confidence=confidence,
            risk_factors=risk_factors or [],
            human_review_required=human_review_required,
            human_approved=human_approved,
            metadata=metadata
        )

        # Store in memory (could be extended to persistent storage)
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # Also log to standard logger for persistence
        log_level = logging.WARNING if human_review_required else logging.INFO
        self._logger.log(
            log_level,
            f"[SafetyAudit] {event_type}: decision={decision}, confidence={confidence:.2f}, "
            f"patient={patient_id or 'N/A'}, review_required={human_review_required}, "
            f"risks={risk_factors}"
        )

        return entry

    def get_recent_entries(self, count: int = 100) -> List[AuditEntry]:
        """Get recent audit entries."""
        return self._entries[-count:]

    def get_entries_for_patient(self, patient_id: str) -> List[AuditEntry]:
        """Get all audit entries for a specific patient."""
        return [e for e in self._entries if e.patient_id == patient_id]


# Global audit logger instance
safety_audit = SafetyAuditLogger()
