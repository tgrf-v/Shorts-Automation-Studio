from typing import Optional
from app.core.config import settings


def count_words(text: str) -> int:
    """Counts non-empty words in text."""
    if not text:
        return 0
    return len([w for w in text.strip().split() if w])


def calculate_speaking_duration(text: str, target_wpm: Optional[int] = None) -> float:
    """
    Estimates spoken audio duration in seconds based on words-per-minute (WPM).
    Formula: (word_count / target_wpm) * 60
    """
    wpm = target_wpm or settings.SCRIPT_TARGET_WPM or 150
    words = count_words(text)
    if words == 0 or wpm <= 0:
        return 0.0
    return round((words / wpm) * 60.0, 2)


def calculate_duration_ratio(estimated_duration: float, source_duration: Optional[float]) -> Optional[float]:
    """Calculates duration ratio (estimated_duration / source_duration)."""
    if source_duration and source_duration > 0.1:
        return round(estimated_duration / source_duration, 3)
    return None


def is_duration_within_bounds(
    ratio: Optional[float],
    min_ratio: Optional[float] = None,
    max_ratio: Optional[float] = None
) -> bool:
    """Checks whether duration ratio is within configured tolerance bounds."""
    if ratio is None:
        return True
    low = min_ratio or settings.SCRIPT_MIN_DURATION_RATIO or 0.85
    high = max_ratio or settings.SCRIPT_MAX_DURATION_RATIO or 1.15
    return low <= ratio <= high


def calculate_duration_diff_percentage(
    estimated_duration: float,
    source_duration: Optional[float]
) -> Optional[float]:
    """Calculates percentage difference: ((estimated - source) / source) * 100."""
    if source_duration and source_duration > 0.1:
        diff = ((estimated_duration - source_duration) / source_duration) * 100.0
        return round(diff, 1)
    return None
