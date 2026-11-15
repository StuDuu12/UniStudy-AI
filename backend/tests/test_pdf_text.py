from backend.services.pdf_text import readable_pdf_text


def test_known_set_symbols_are_readable():
    assert readable_pdf_text("A\uf0c8B; x\uf0cfA; \uf0c6") == "A∪B; x∉A; ∅"


def test_unknown_symbols_are_disclosed_not_guessed():
    assert readable_pdf_text("A\ue123B") == "A[ký hiệu cần xem PDF gốc]B"


def test_latex_is_preserved():
    assert readable_pdf_text(r"$A \cup B$") == r"$A \cup B$"
