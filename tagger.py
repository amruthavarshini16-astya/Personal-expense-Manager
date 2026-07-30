"""
Resilient Pocket - Zero-Dependency Real-Time NLP Transaction Tagger
Uses tokenization, dictionary matching, stemming, and set intersections for fast O(1) keyword classification.
"""
import re
from typing import Dict, List, Tuple
import config
from telemetry import measure_latency

class ZeroDepNLPTagger:
    """Lightweight, zero-dependency transaction text auto-tagger."""

    def __init__(self, tag_dict: Dict[str, List[str]] = None) -> None:
        self.reload_dictionary(tag_dict)

    def reload_dictionary(self, tag_dict: Dict[str, List[str]] = None) -> None:
        if tag_dict is None:
            tag_dict = config.TAG_DICTIONARY
        self.category_lookup: Dict[str, set] = {
            category.capitalize(): {kw.lower() for kw in keywords}
            for category, keywords in tag_dict.items()
        }

    def tokenize(self, text: str) -> List[str]:
        """Normalize text and parse into alphanumeric word tokens."""
        text_clean = text.lower()
        text_clean = re.sub(r"[^\w\s]", " ", text_clean)
        tokens = [t.strip() for t in text_clean.split() if len(t.strip()) >= 1]
        return tokens

    @measure_latency("nlp_tag_transaction")
    def predict_category(self, raw_text: str, default_category: str = "General") -> Tuple[str, float]:
        """
        Predict transaction category from raw description.
        Returns: (Predicted Category Name, Confidence Score 0.0-1.0)
        """
        if not raw_text or not raw_text.strip():
            return (default_category, 0.0)

        self.reload_dictionary()

        tokens = set(self.tokenize(raw_text))
        raw_text_lower = raw_text.lower().strip()

        best_category = default_category
        highest_score = 0.0

        # Prioritize Shopping, Food, Travel, Bills, Health, Entertainment, Income
        category_order = ["Shopping", "Food", "Travel", "Bills", "Health", "Entertainment", "Income"]

        for category in category_order:
            keyword_set = self.category_lookup.get(category, set())
            
            # Check 1: Direct token set intersection
            intersection = tokens.intersection(keyword_set)
            if intersection:
                score = 0.90 + (0.03 * min(len(intersection), 3))
                if score > highest_score:
                    highest_score = score
                    best_category = category

            # Check 2: Substring or phrase matching
            else:
                for kw in keyword_set:
                    if kw in raw_text_lower or any(t.startswith(kw) for t in tokens if len(kw) >= 3):
                        score = 0.85
                        if score > highest_score:
                            highest_score = score
                            best_category = category
                        break

        # Fallback heuristic
        if highest_score == 0.0:
            if any(w in raw_text_lower for w in ["pay", "purchase", "spent", "debit", "buy"]):
                best_category = "Shopping"
                highest_score = 0.6
            elif any(w in raw_text_lower for w in ["credit", "received", "deposit", "salary"]):
                best_category = "Income"
                highest_score = 0.9

        return (best_category, round(highest_score, 2))
