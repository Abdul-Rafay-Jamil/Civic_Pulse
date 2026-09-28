"""Rule-based triage provider — deterministic keyword fallback. Always available, never fails."""

import re

from app.models import Category, Priority, TriageResult


# Keyword → category mapping
_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.WATER: [
        "water", "pani", "burst", "pipe", "leak", "flood", "tanker", "supply",
        "sewage", "drain", "nala", "gutter", "tap", "boring", "tube well",
        "overhead tank", "filtration", "paani",
    ],
    Category.ELECTRICITY: [
        "electricity", "bijli", "power", "transformer", "wire", "cable",
        "outage", "blackout", "voltage", "meter", "pole", "load shedding",
        "short circuit", "electric", "light",
    ],
    Category.SANITATION: [
        "garbage", "kachra", "waste", "trash", "sanitation", "sweeper",
        "dump", "smell", "stink", "dirty", "cleaning", "dustbin",
        "disposal", "mosquito", "flies", "dengue",
    ],
    Category.ROADS: [
        "road", "pothole", "crack", "pavement", "footpath", "bridge",
        "construction", "speed breaker", "signal", "divider", "highway",
        "asphalt", "tar", "sarak",
    ],
    Category.STREETLIGHTS: [
        "streetlight", "street light", "lamp", "bulb", "dark", "lighting",
        "pole light", "park light", "night", "broken light",
    ],
}

# Keywords indicating high priority
_HIGH_PRIORITY_KEYWORDS = [
    "emergency", "flood", "fire", "danger", "hazard", "urgent", "critical",
    "collapse", "accident", "injury", "injured", "electrocution", "burst",
    "overflow", "children", "hospital", "school", "fajr",
]

_LOW_PRIORITY_KEYWORDS = [
    "minor", "small", "cosmetic", "paint", "decoration", "suggestion",
    "request", "improvement", "dim",
]


class RuleBasedTriage:
    """Deterministic keyword-based triage. Always available, never fails.

    Used as the ultimate fallback when LLM providers are unavailable.
    """

    @property
    def name(self) -> str:
        return "rules"

    async def triage(self, text: str, location: str) -> TriageResult:
        """Classify based on keyword matching."""
        combined = f"{text} {location}".lower()

        # Determine category
        category = self._match_category(combined)

        # Determine priority
        priority = self._match_priority(combined)

        # Generate summary
        summary = self._generate_summary(text, category)

        # Confidence is lower for rule-based since it's just keyword matching
        confidence = 0.6 if category != Category.OTHER else 0.3

        return TriageResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=confidence,
        )

    def _match_category(self, text: str) -> Category:
        """Find the best-matching category by keyword count."""
        scores: dict[Category, int] = {}
        for cat, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score

        if not scores:
            return Category.OTHER
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    def _match_priority(self, text: str) -> Priority:
        """Determine priority from urgency keywords."""
        high_hits = sum(1 for kw in _HIGH_PRIORITY_KEYWORDS if kw in text)
        low_hits = sum(1 for kw in _LOW_PRIORITY_KEYWORDS if kw in text)

        if high_hits > low_hits:
            return Priority.HIGH
        if low_hits > high_hits:
            return Priority.LOW
        return Priority.NORMAL

    def _generate_summary(self, text: str, category: Category) -> str:
        """Create a brief summary from the complaint text."""
        # Take first sentence or first 130 chars
        first_sentence = re.split(r'[.!?\n]', text)[0].strip()
        if len(first_sentence) > 130:
            first_sentence = first_sentence[:127] + "..."
        if not first_sentence:
            first_sentence = f"{category.value.title()} complaint reported"
        return first_sentence
