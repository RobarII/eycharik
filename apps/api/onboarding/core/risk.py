"""Risk radar: turn survey signals into a level, tags, and one routing decision.

The rules are deliberately small and explainable. A recruiter must be able to read why the bot
raised a flag, and a test must be able to pin the answer. The model, when it is available, supplies
sentiment and tags; the keyword classifier below is both the offline fallback and the last line of
defense when the provider returns low confidence.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import RiskAssessment, RiskLevel, RiskSignal, Sentiment, SignalTag

HIGH_SCORE = 3
MEDIUM_SCORE = 1
LOW_CONFIDENCE = 0.5
NEGATIVE_WEIGHT = 3
CRISIS_WEIGHT = 1

_TAG_KEYWORDS: dict[SignalTag, tuple[str, ...]] = {
    SignalTag.ACCESS: (
        "доступ",
        "пропуск",
        "учетн",
        "логин",
        "парол",
        "портал",
    ),
    SignalTag.IT: (
        "ноутбук",
        "компьютер",
        "техник",
        "оборудован",
        "почт",
        "1с",
    ),
    SignalTag.MANAGER: (
        "руководител",
        "начальник",
        "наставник",
        "ментор",
        "руководств",
    ),
    SignalTag.COLLEAGUES: (
        "коллег",
        "команд",
        "коллектив",
        "никто не помог",
        "никто не отвечает",
    ),
    SignalTag.WORKLOAD: (
        "нагрузк",
        "переработ",
        "устал",
        "завал",
        "стресс",
        "выгора",
        "много задач",
    ),
    SignalTag.CLARITY: (
        "непонятн",
        "не понял",
        "неясн",
        "задач",
        "ожидан",
        "инструкц",
    ),
    SignalTag.HR: (
        "кадр",
        "hr",
        "отдел подбора",
        "оформлен",
        "документ",
        "отпуск",
        "зарплат",
    ),
    SignalTag.INTEGRATION: (
        "другой отдел",
        "смежн",
        "подразделен",
        "взаимодейств",
    ),
}

_CRISIS_MARKERS = (
    "увольн",
    "уволить",
    "ухожу",
    "не могу больше",
    "конфликт",
    "хамств",
    "унижа",
    "буллинг",
    "травл",
    "обман",
)

_POSITIVE_MARKERS = (
    "отлично",
    "здорово",
    "супер",
    "нравится",
    "помогли",
    "поддерж",
    "понятно",
    "комфортно",
    "доволен",
)

_TAG_ORDER = tuple(_TAG_KEYWORDS)


def assess_text(text: str, *, source: str, confidence: float = 0.5) -> RiskAssessment:
    """Classify one free-text answer with keywords and assess it. No model, no network."""
    normalized = _normalize(text)
    tags = tuple(tag for tag in _TAG_ORDER if _matches(normalized, _TAG_KEYWORDS[tag]))
    sentiment = _keyword_sentiment(normalized, tags)
    signal = RiskSignal(
        source=source,
        sentiment=sentiment,
        tags=tags,
        confidence=confidence,
        text=text,
    )
    return assess((signal,))


def assess(signals: Iterable[RiskSignal]) -> RiskAssessment:
    """Combine signals into one decision for one employee."""
    score = 0
    tags: list[SignalTag] = []
    reasons: list[str] = []
    material = False
    confident = False
    for signal in signals:
        if signal.tags:
            tags.extend(tag for tag in signal.tags if tag not in tags)
        weighed = False
        if signal.sentiment is Sentiment.NEGATIVE:
            score += NEGATIVE_WEIGHT
            reasons.append(f"negative sentiment at {signal.source}")
            weighed = True
        if _is_crisis(signal.text):
            score += CRISIS_WEIGHT
            reasons.append(f"crisis wording at {signal.source}")
            weighed = True
        deficit = _deficit(signal)
        if deficit >= 3:
            score += 2
            reasons.append(f"score {signal.score} is far below threshold at {signal.source}")
            weighed = True
        elif deficit > 0:
            score += 1
            reasons.append(f"score {signal.score} is below threshold at {signal.source}")
            weighed = True
        if weighed:
            material = True
            confident = confident or signal.confidence >= LOW_CONFIDENCE

    if score >= HIGH_SCORE and material and not confident:
        return RiskAssessment(
            level=RiskLevel.MEDIUM,
            tags=tuple(tags),
            escalate_to=None,
            reasons=(*reasons, "low classifier confidence, kept for the digest"),
            score=score,
        )
    if score >= HIGH_SCORE:
        return RiskAssessment(
            level=RiskLevel.HIGH,
            tags=tuple(tags),
            escalate_to="recruiter",
            reasons=tuple(reasons),
            score=score,
        )
    if score >= MEDIUM_SCORE:
        return RiskAssessment(
            level=RiskLevel.MEDIUM,
            tags=tuple(tags),
            escalate_to=None,
            reasons=tuple(reasons),
            score=score,
        )
    return RiskAssessment(
        level=RiskLevel.LOW,
        tags=tuple(tags),
        escalate_to=None,
        reasons=tuple(reasons),
        score=score,
    )


def _deficit(signal: RiskSignal) -> int:
    if signal.score is None or signal.low_threshold is None:
        return 0
    return max(0, signal.low_threshold - signal.score)


def _keyword_sentiment(normalized: str, tags: tuple[SignalTag, ...]) -> Sentiment:
    if _is_crisis(normalized):
        return Sentiment.NEGATIVE
    negative = any(
        word in normalized
        for word in (
            "плохо",
            "ужас",
            "не помог",
            "нет доступа",
            "не выдали",
            "не работ",
            "не подход",
            "не получ",
            "проблем",
            "опазд",
            "задерж",
            "непонят",
            "игнор",
            "жалоб",
            "тяжело",
            "сложно",
            "долго",
        )
    )
    if negative:
        return Sentiment.NEGATIVE
    if any(word in normalized for word in _POSITIVE_MARKERS):
        return Sentiment.POSITIVE
    if tags:
        return Sentiment.NEUTRAL
    return Sentiment.UNKNOWN


def _is_crisis(text: str | None) -> bool:
    if not text:
        return False
    return any(marker in _normalize(text) for marker in _CRISIS_MARKERS)


def _matches(normalized: str, words: tuple[str, ...]) -> bool:
    return any(word in normalized for word in words)


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())
