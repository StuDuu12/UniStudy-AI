"""Prepare Vietnamese subqueries for lexical retrieval."""

import re

from backend.services.evidence import normalize_text


def query_parts(question: str) -> list[str]:
    text = normalize_text(question)
    useful = []
    for part in re.split(r"[.!?;\n]+", text):
        part = part.strip(" ,:")
        if not part:
            continue
        part = re.sub(r"^(?:vay|the thi|cho minh biet|cho toi biet)\s+", "", part)
        part = re.sub(r"^(?:minh|toi|em) (?:muon|can) (?:biet|hoi|tim hieu)\s+", "", part)
        # The request verb and conversational wrapper can occur in either order.
        for _ in range(3):
            part = re.sub(
                r"^(?:(?:ban|thay|co)\s+)?(?:co the\s+)?(?:hay\s+)?"
                r"(?:giai thich|trinh bay|neu|phan biet)\s+", "", part,
            )
            part = re.sub(r"^(?:giup|cho) (?:minh|toi|em)(?: hoi| biet)?\s+", "", part)
        part = re.sub(r"\s+(?:(?:nhe|nha|voi|a|di|vay ban|cam on)\s*)+$", "", part)
        part = re.sub(r"(\bla gi) khong$", r"\1", part)
        if re.match(
            r"^(?:minh|toi) (?:dang|can|muon|da)|^(?:neu|voi tung y|sau do|uu tien|dung cac|chi ro trang)\b",
            part,
        ):
            continue
        # Conjunctions between two explicit definitions introduce a second topic.
        clauses = re.split(r"(?<=\bla gi)\s+(?:va(?:\s+con)?|con)\s+(?=.+\bla gi\b)", part)
        useful.extend(item.strip() for clause in clauses for item in clause.split(",") if item.strip())
    return list(dict.fromkeys(useful or [text.strip()]))[:6]
