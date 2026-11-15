from backend.services.pdf_text import (
    clean_pdf_artifacts,
    fix_vietnamese_pdf_spacing,
    format_academic_document_content,
    readable_pdf_text,
)


def test_known_set_symbols_are_readable():
    assert readable_pdf_text("A\uf0c8B; x\uf0cfA; \uf0c6") == "A∪B; x∉A; ∅"


def test_unknown_symbols_are_disclosed_not_guessed():
    assert readable_pdf_text("A\ue123B") == "A[ký hiệu cần xem PDF gốc]B"


def test_latex_is_preserved():
    assert readable_pdf_text(r"$A \cup B$") == r"$A \cup B$"


def test_bullet_glyphs_and_email_stripping():
    sample = "nghiệpvụlongth@hnue.edu.vn 3 ❑ Điều tra  Sáng tạo Ø Quan sát  Hỗ trợ ■ A □ B ▪ C ▫ D ► E ▸ F ◆ G \x11 H \uf076 I"
    cleaned = readable_pdf_text(sample)
    assert "longth@hnue.edu.vn" not in cleaned
    assert "nghiệp vụ" in cleaned
    assert "• Điều tra" in cleaned
    assert "• Sáng tạo" in cleaned
    assert "• Quan sát" in cleaned


def test_vietnamese_glued_words_repair():
    raw = "thểvừa đồthị tất cảm cạnh độtin từgóc độngười quan hệgiữa đượckết nghiệpvụ"
    fixed = fix_vietnamese_pdf_spacing(raw)
    assert fixed == "thể vừa đồ thị tất cả m cạnh độ tin từ góc độ người quan hệ giữa được kết nghiệp vụ"


def test_format_academic_document_content_hierarchical():
    text = (
        "5. Các kỹthuật hỗtrợ\n"
        "4. Các kỹthuật quan sát\n"
        "3. Các kỹthuật lấy tài liệu làm trung tâm\n"
        "2. Các kỹthuật sáng tạo\n\n"
        "Các kỹ thuật khám phá yêu cầu\n\n"
        "1. Các kỹthuật điều tra\n\n29"
    )
    formatted = format_academic_document_content(text)
    assert "### 📘 Các kỹ thuật khám phá yêu cầu" in formatted
    assert "- **1.** Các kỹ thuật điều tra" in formatted
    assert "- **2.** Các kỹ thuật sáng tạo" in formatted
    assert "- **3.** Các kỹ thuật lấy tài liệu làm trung tâm" in formatted
    assert "- **4.** Các kỹ thuật quan sát" in formatted
    assert "- **5.** Các kỹ thuật hỗ trợ" in formatted
    assert "29" not in formatted.splitlines()[-1]
