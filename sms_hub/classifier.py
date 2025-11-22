import re
from typing import Dict, Tuple


CRITICAL_KEYWORDS = {
    "urgent",
    "asap",
    "immediately",
    "help",
    "emergency",
    "alert",
    "911",
    "medical",
}


class MessageClassifier:
    """Classify and stabilize inbound text before SMS dispatch."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    @staticmethod
    def _heuristic_classification(text: str) -> Tuple[str, str]:
        normalized = text.lower()
        if any(keyword in normalized for keyword in CRITICAL_KEYWORDS):
            return "critical", "Message flagged as critical based on keyword detection."
        return "stable", "Message appears stable based on heuristic analysis."

    def classify(self, text: str) -> Dict[str, str]:
        """Return classification and stabilized text using heuristics with optional LLM support."""

        sanitized = re.sub(r"\s+", " ", text).strip()
        label, rationale = self._heuristic_classification(sanitized)

        # If an LLM client is provided, prefer its classification but keep heuristics as fallback.
        if self.llm_client:
            llm_result = self.llm_client(sanitized)
            if llm_result and "classification" in llm_result and "stabilized_text" in llm_result:
                return {
                    "classification": llm_result["classification"],
                    "stabilized_text": llm_result["stabilized_text"],
                    "rationale": llm_result.get("rationale", rationale),
                }

        return {
            "classification": label,
            "stabilized_text": sanitized,
            "rationale": rationale,
        }
