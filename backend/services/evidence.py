import re
import unicodedata
from collections.abc import Sequence

# The merge-sort slide is concise but directly answers its suggested question.
EVIDENCE_THRESHOLD = 0.19

_FOLLOW_UP_QUESTION = re.compile(
    r"(?:(?:vay|the) )?(?:"
    r"(?:hay )?(?:giai thich|noi ro|phan tich) (?:ve )?(?:cai nay|cai do|cai kia|no|phan nay|doan nay)"
    r"(?: (?:giup (?:minh|toi)|voi|di))*"
    r"|con (?:cai nay|cai kia|truong hop nay|truong hop kia|truong hop do)(?: thi sao)?"
    r"|(?:(?:hay )?(?:cho(?: (?:minh|toi))?|neu|dua ra) )?(?:(?:mot|them) )?vi du"
    r"(?: (?:minh hoa|khac|nua|them))?(?: (?:voi|di))?"
    r"|co vi du (?:nao )?khong"
    r"|(?:(?:no )?(?:co|gom) )?(?:may|bao nhieu) (?:loai|dang|phan|buoc)"
    r"|(?:(?:nam )?o )?(?:trang|chuong|muc) (?:nao|bao nhieu|may)"
    r"|(?:no|cai nay|cai do|cai kia) (?:la gi|co tac dung gi|dung de lam gi|hoat dong the nao)"
    r"|(?:vay )?neu .+ thi (?:ket qua|dap an|gia tri) (?:la (?:gi|bao nhieu)|the nao)"
    r"|tai sao|vi sao|the nao|nhu the nao"
    r")"
)


def _needs_prior_topic(question: str) -> bool:
    cleaned = normalize_text(" ".join(question.split())).strip(" ?!.,…")
    return bool(_FOLLOW_UP_QUESTION.fullmatch(cleaned))


def retrieval_query(question: str, previous_questions: Sequence[str]) -> tuple[str, str] | None:
    question = question.strip()
    if not _needs_prior_topic(question):
        return question, question
    for previous in reversed(previous_questions):
        if any(character.isalnum() for character in previous) and not _needs_prior_topic(previous):
            topic = previous.strip()
            return f"{topic} {question}", topic
    return None


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(character for character in decomposed if not unicodedata.combining(character))
