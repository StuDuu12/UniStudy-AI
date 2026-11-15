"""Known Symbol-font and bullet mappings from the supplied PDFs, with academic formatting."""
import re
from dataclasses import dataclass

SYMBOLS = {
    "\uf0c6": "∅", "\uf0cd": "⊆", "\uf0cc": "⊂", "\uf0ce": "∈",
    "\uf0cf": "∉", "\uf0c7": "∩", "\uf0c8": "∪", "\uf022": "∀",
    "\uf024": "∃", "\uf0ac": "¬", "\uf0de": "⇒", "\uf0db": "⇔",
    "\uf0d7": "×",
}

# Wingdings, Symbol, and PPT bullet glyphs commonly found in slide decks
BULLET_GLYPHS = {
    "\uf076": "\n• ",  # Right arrow / round bullet
    "\uf071": "\n• ",  # Square bullet
    "\uf0a7": "\n• ",  # Square bullet
    "\uf0b7": "\n• ",  # Round bullet
    "\uf06e": "\n• ",  # Square bullet
    "\uf0a0": "\n• ",  # Bullet
    "\uf06c": "\n• ",  # Bullet
    "\uf06d": "\n• ",  # Bullet
    "\uf0d8": "\n• ",  # Bullet
    "\u2751": "\n• ",  # ❑
    "\u25a0": "\n• ",  # ■
    "\u25a1": "\n• ",  # □
    "\u25aa": "\n• ",  # ▪
    "\u25ab": "\n• ",  # ▫
    "\u25ba": "\n• ",  # ►
    "\u25b8": "\n• ",  # ▸
    "\u25c6": "\n• ",  # ◆
    "❑": "\n• ",
    "■": "\n• ",
    "□": "\n• ",
    "▪": "\n• ",
    "▫": "\n• ",
    "►": "\n• ",
    "▸": "\n• ",
    "◆": "\n• ",
    "": "\n• ",
    "\uf0fc": "✓ ",    # Checkmark
    "\uf0fe": "☑ ",    # Ballot check
    "\x11": "\n• ",    # ASCII DC1 used as bullet in PPT slides
}

COMMON_GLUED_PATTERNS = [
    ("thểvừa", "thể vừa"), ("đồthịvà", "đồ thị và"), ("đồthị", "đồ thị"),
    ("cảmcạnh", "cả m cạnh"), ("cảm cạnh", "cả m cạnh"), ("tất cảm cạnh", "tất cả m cạnh"),
    ("độtin", "độ tin"), ("từgóc độngười", "từ góc độ người"), ("từgóc độ", "từ góc độ"),
    ("góc độngười", "góc độ người"), ("quan hệgiữa", "quan hệ giữa"),
    ("đượckết", "được kết"), ("nghiệpvụ", "nghiệp vụ"), ("kỹthuật", "kỹ thuật"),
    ("hỗtrợ", "hỗ trợ"),
    ("thểlà", "thể là"), ("hệthống", "hệ thống"), ("đặctính", "đặc tính"),
    ("sửdụng", "sử dụng"), ("sởđểthương", "sở để thương"), ("sởđểxác", "sở để xác"),
    ("sởđể", "sở để"), ("kỹnghệyêu", "kỹ nghệ yêu"),
    ("kỹnghệ", "kỹ nghệ"), ("mô tảsản", "mô tả sản"), ("cơ sởcho", "cơ sở cho"),
    ("thu thập từ", "thu thập từ"), ("thểxung", "thể xung"),
    ("bổsung", "bổ sung"), ("ngôn ngữtựnhiên", "ngôn ngữ tự nhiên"), ("vềcác", "về các"),
    ("nhiệm vụtài", "nhiệm vụ tài"), ("Biểu đồlớp", "Biểu đồ lớp"),
    ("Biểu đồđối", "Biểu đồ đối"), ("ThẻCRC", "Thẻ CRC"),
    ("đồtuần", "đồ tuần"), ("đồcộng", "đồ cộng"), ("đồtương", "đồ tương"),
    ("đồtrạng", "đồ trạng"), ("đồgiao", "đồ giao"),
]

PARTICLE_SPLIT_REGEX = re.compile(
    r"(?<=[a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])"
    r"(?=(?:là|và|cho|của|trong|từ|với|để|được|có|các|những|hệ|thống|phần|mềm|yêu|cầu|nghiệp|vụ|đặc|tính|sử|dụng|kỹ|thuật|tài|liệu|báo|cáo|thực|hiện|chức|năng|phát|biểu|thị|tin|giữa)\b)"
)


def clean_pdf_artifacts(text: str) -> str:
    # Remove email and slide footer patterns like longth@hnue.edu.vn 3 or vụlongth@hnue.edu.vn 3
    text = re.sub(r"(?:email:\s*)?[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+(?:\s+\d+)?", "", text)
    # Remove ASCII control characters except \n and \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    # Remove Unicode Supplementary Private Use characters that render as boxes
    text = re.sub(r"[\U000f0000-\U0010ffff]", "", text)
    # Normalize excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Preserve paragraph breaks (\n\n) while removing redundant empty lines
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def fix_vietnamese_pdf_spacing(text: str) -> str:
    """Repair glued words and missing spaces caused by PDF font metrics."""
    for glued, separated in COMMON_GLUED_PATTERNS:
        text = text.replace(glued, separated)
    text = PARTICLE_SPLIT_REGEX.sub(" ", text)
    # Normalize multiple spaces
    return re.sub(r"[ \t]+", " ", text)


def format_academic_document_content(text: str) -> str:
    """Format raw PDF slide excerpts into clean, properly-indented Markdown lists."""
    if not text:
        return ""

    text = text.replace("\xa0", " ")

    # 1. Decode known symbols and bullet glyphs with explicit hierarchy tags
    for glyph, symbol in SYMBOLS.items():
        text = text.replace(glyph, symbol)

    # Bullet Ø
    text = re.sub(r"(?:^|\n|\s)Ø\s+", "\n__LVL2__ ", text)

    # Level 1 bullets
    for glyph in ("\uf076", "►", "▸", "◆", "\u25ba", "\u25b8", "\u25c6"):
        text = text.replace(glyph, "\n__LVL1__ ")
    # Level 2 bullets
    for glyph in (
        "\uf071", "\uf0d8", "\uf075", "\uf0a7", "\uf0b7", "\uf06e", "\uf0a0", "\uf06c", "\uf06d",
        "\x11", "❑", "\u2751", "", "■", "□", "▪", "▫", "\u25a0", "\u25a1", "\u25aa", "\u25ab"
    ):
        text = text.replace(glyph, "\n__LVL2__ ")
    for glyph in ("\uf0fc", "\uf0fe"):
        text = text.replace(glyph, "\n- ✓ ")

    # 2. Fix spacing and glued words
    text = fix_vietnamese_pdf_spacing(text)
    text = clean_pdf_artifacts(text)

    # Split lines, strip whitespace
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Remove standalone page numbers
    lines = [l for l in lines if not re.fullmatch(r"\d+", l)]
    if not lines:
        return ""

    # Check if lines have numbered items out of order with a title (e.g. 5, 4, 3, 2, Title, 1)
    numbered = []
    others = []
    for l in lines:
        m = re.match(r"^(\d+)\.\s*(.*)", l)
        if m:
            numbered.append((int(m.group(1)), l))
        else:
            others.append(l)

    if numbered and len(numbered) >= 2:
        num_keys = [n[0] for n in numbered]
        if num_keys != sorted(num_keys) or others:
            numbered.sort(key=lambda x: x[0])
            lines = others + [item[1] for item in numbered]

    formatted = []
    # If first line doesn't start with a bullet tag or number, it's a section title
    if lines and not lines[0].startswith("__LVL") and not re.match(r"^\d+\.", lines[0]) and not lines[0].startswith("- "):
        first = lines.pop(0)
        formatted.append(f"### 📘 {first}\n")

    for line in lines:
        if line.startswith("__LVL1__"):
            content = line.replace("__LVL1__", "").strip()
            if content.endswith(":"):
                formatted.append(f"\n- **{content}**")
            else:
                formatted.append(f"- **{content}**" if len(content) < 60 and not content.startswith("-") else f"- {content}")
        elif line.startswith("__LVL2__"):
            content = line.replace("__LVL2__", "").strip()
            formatted.append(f"  - {content}")
        elif re.match(r"^\d+\.\s*", line):
            m = re.match(r"^(\d+\.\s*)(.*)", line)
            num_prefix, rest = m.group(1).strip(), m.group(2).strip()
            formatted.append(f"- **{num_prefix}** {rest}")
        elif line.startswith("- ") or line.startswith("* "):
            formatted.append(line)
        else:
            formatted.append(f"\n{line}\n")

    result = "\n".join(formatted).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def readable_pdf_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    for glyph, symbol in SYMBOLS.items():
        text = text.replace(glyph, symbol)
    for glyph, bullet in BULLET_GLYPHS.items():
        text = text.replace(glyph, bullet)
    text = re.sub(r"(?:^|\n|\s)Ø\s+", "\n• ", text)
    text = fix_vietnamese_pdf_spacing(text)
    text = clean_pdf_artifacts(text)
    return re.sub(r"[\ue000-\uf8ff]", "[ký hiệu cần xem PDF gốc]", text)


_PDF_BULLETS = {
    **dict.fromkeys(BULLET_GLYPHS, "-"),
    **dict.fromkeys("•●○◦‣Ø", "-"),
    **dict.fromkeys("◆❖\uf076►▸", "+"),
    **dict.fromkeys("□■▪▫❑\uf071\uf0a7", "*"),
}
_LIST_LABEL = re.compile(r"^((?:\d{1,9}|[A-Za-z]|[IVXLCDMivxlcdm]{2,})[.)]|[-+*])[ \t]+")


@dataclass(frozen=True)
class PdfLine:
    text: str
    x: float
    y: float
    size: float


@dataclass
class PdfBlock:
    start: int
    stop: int
    x: float
    text: str
    label: str = ""
    title: bool = False


def pdf_layout_blocks(lines: list[PdfLine], page_number: int, width: float, height: float) -> list[PdfBlock]:
    """Keep the source markers and join visual lines that belong to the same item."""
    blocks: list[PdfBlock] = []
    offset = 0
    previous_line = None
    for index, line in enumerate(lines):
        start = offset
        offset += len(line.text.split())
        raw = line.text.strip()
        if raw == str(page_number) and line.x > width * 0.8 and line.y > height * 0.8:
            continue

        label = _PDF_BULLETS.get(raw[:1], "")
        if label:
            raw = raw[1:].lstrip()
        else:
            match = _LIST_LABEL.match(raw)
            if match:
                label, raw = match[1], raw[match.end():]
        body = readable_pdf_text(raw)
        if not body:
            continue

        previous = blocks[-1] if blocks else None
        if previous and previous_line and not previous.title and not label:
            same_size = abs(line.size - previous_line.size) <= line.size * 0.15
            wraps = 0 < line.y - previous_line.y <= line.size * 1.5
            indent = line.x - previous.x
            aligned = (line.size * 0.4 < indent <= line.size * 2.5 if previous.label
                       else abs(indent) <= line.size * 0.35)
            if same_size and wraps and aligned:
                previous.text += " " + body
                previous.stop = offset
                previous_line = line
                continue

        title = index == 0 and not label and len(lines) > 1 and line.size >= lines[1].size * 1.2
        blocks.append(PdfBlock(start, offset, line.x, body, label, title))
        previous_line = line
    return blocks


def format_pdf_blocks(blocks: list[PdfBlock], start: int, stop: int) -> str:
    """Format the complete paragraphs and list items intersecting a retrieval chunk."""
    output: list[str] = []
    columns: list[tuple[float, int, int]] = []
    for block in blocks:
        if block.stop <= start or block.start >= stop:
            continue
        if not block.label:
            if output and output[-1]:
                output.append("")
            output.extend([("### " if block.title else "") + block.text, ""])
            columns.clear()
            continue

        marker = block.label
        text = block.text
        if marker[0].isalpha():
            text = f"{marker} {text}"
            marker = "-"

        while columns and block.x < columns[-1][0] - 5:
            columns.pop()
        if columns and block.x > columns[-1][0] + 5:
            indent = columns[-1][1] + columns[-1][2]
        elif columns:
            _, indent, _ = columns.pop()
        else:
            indent = 0
        columns.append((block.x, indent, len(marker) + 1))
        output.append(f"{' ' * indent}{marker} {text}")
    return "\n".join(output).strip()
