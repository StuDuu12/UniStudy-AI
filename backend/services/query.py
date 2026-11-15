"""Bounded Vietnamese query preparation; original questions still go to the LLM."""
import re
from backend.services.evidence import normalize_text


def query_parts(question: str) -> list[str]:
    text = normalize_text(question)
    # Keep numeric examples out of search terms. The original is passed to the answer model.
    text = re.sub(r"\{(?:[^{}]|\{[^{}]*\})*\}", " ", text)
    parts = re.split(r"[!?;\n]+|(?<!\d)\.|\.(?!\d)", text)
    useful = []
    for part in parts:
        part = part.strip(" ,:")
        if not part:
            continue
        # Remove conversational introductions, not the requested academic subject.
        part = re.sub(r"^(?:vay|the thi|cho minh biet|cho toi biet)\s+", "", part)
        part = re.sub(r"^(?:minh|toi|em) (?:muon|can) (?:biet|hoi|tim hieu)\s+", "", part)
        # Conversational wrappers can occur on either side of the request verb:
        # "giúp mình giải thích" and "giải thích giúp mình" are equivalent.
        for _ in range(3):
            part = re.sub(
                r"^(?:(?:ban|thay|co)\s+)?(?:co the\s+)?(?:hay\s+)?"
                r"(?:giai thich|trinh bay|neu|phan biet)\s+", "", part,
            )
            part = re.sub(r"^(?:giup|cho) (?:minh|toi|em)(?: hoi| biet)?\s+", "", part)
        part = re.sub(r"\s+(?:(?:nhe|nha|voi|a|di|vay ban|cam on)\s*)+$", "", part)
        part = re.sub(r"(\bla gi) khong$", r"\1", part)
        if re.match(r"^(?:minh|toi) (?:dang|can|muon|da)|^(?:neu|voi tung y|sau do|uu tien|dung cac|chi ro trang)\b", part):
            continue
        comparison = re.fullmatch(r"(.+?) khac (.+?)(?: o diem nao)?", part)
        if comparison:
            useful.extend(comparison.group(index).strip() for index in (1, 2))
            continue
        paired_definition = re.fullmatch(r"(?:dinh nghia|khai niem) (.+?) va (.+)", part)
        if paired_definition:
            useful.extend(
                f"dinh nghia {paired_definition.group(index).strip()}"
                for index in (1, 2)
            )
            continue
        # "X có tính chất A và B" shares one subject. Splitting at "và"
        # discarded X from the second half and searched a different topic.
        useful.extend(p.strip() for p in part.split(",") if p.strip())
    return list(dict.fromkeys(useful or [text.strip()]))[:6]
