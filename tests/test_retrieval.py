import csv
from pathlib import Path

import pymupdf

from services.retrieval import CourseIndex


def _pdf(path, *pages):
    with pymupdf.open() as document:
        for text in pages:
            page = document.new_page()
            if text:
                page.insert_text((40, 60), text)
        document.save(path)


def _manifest(data_dir, *rows):
    with (data_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["course_id", "document_id", "document_name", "path", "license"])
        writer.writerows(rows)


def test_ranks_within_course_before_top_k(tmp_path):
    _pdf(tmp_path / "testing.pdf", "Boundary analysis and representative examples")
    _pdf(tmp_path / "algorithms.pdf", "Boundary analysis")
    _manifest(
        tmp_path,
        ("testing", "testing-notes", "Testing notes", "testing.pdf", "project_demo"),
        ("algorithms", "algo-notes", "Algorithm notes", "algorithms.pdf", "project_demo"),
    )

    index = CourseIndex(tmp_path)

    assert [source.document_id for source in index.search("testing", "Boundary analysis", limit=1)] == [
        "testing-notes"
    ]
    assert index.search("testing", "zqxw") == ()
    assert index.search("unknown", "Boundary analysis") == ()


def test_keeps_physical_pdf_page_and_original_accented_excerpt(tmp_path):
    _pdf(tmp_path / "source.pdf", "Unrelated first sheet", "", "Café   policy")
    _manifest(tmp_path, ("testing", "notes", "Học liệu", "source.pdf", "project_demo"))

    index = CourseIndex(tmp_path)
    source, = index.search("testing", "cafe policy", limit=1)

    assert source.document_name == "Học liệu"
    assert source.page == 3
    assert source.excerpt == "Café policy"
    assert index.search("testing", "Cafe\u0301 policy", limit=1) == (source,)


def test_omits_blank_missing_and_corrupt_pdfs(tmp_path):
    _pdf(tmp_path / "blank.pdf", "")
    (tmp_path / "broken.pdf").write_bytes(b"This is not a readable PDF")
    _pdf(tmp_path / "valid.pdf", "Partitioning")
    _manifest(
        tmp_path,
        ("testing", "blank", "Blank", "blank.pdf", "project_demo"),
        ("testing", "missing", "Missing", "missing.pdf", "project_demo"),
        ("testing", "broken", "Broken", "broken.pdf", "project_demo"),
        ("testing", "valid", "Valid", "valid.pdf", "project_demo"),
    )

    index = CourseIndex(tmp_path)

    assert [document.document_id for document in index.documents("testing")] == ["valid"]
    assert len(index.issues) == 3
    assert all(str(tmp_path) not in issue for issue in index.issues)


def test_rejects_absolute_outside_non_pdf_and_unlicensed_rows(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _pdf(tmp_path / "private.pdf", "Private outside source")
    _pdf(data_dir / "allowed.pdf", "Allowed source")
    _pdf(data_dir / "renamed.txt", "PDF content under wrong extension")
    _manifest(
        data_dir,
        ("testing", "outside", "Outside", "../private.pdf", "project_demo"),
        ("testing", "absolute", "Absolute", str(data_dir / "allowed.pdf"), "project_demo"),
        ("testing", "wrong_ext", "Wrong extension", "renamed.txt", "project_demo"),
        ("testing", "unlicensed", "Unlicensed", "allowed.pdf", "internal_development_only"),
        ("testing", "allowed", "Allowed", "allowed.pdf", "project_demo"),
    )

    index = CourseIndex(data_dir)

    assert [document.document_id for document in index.documents("testing")] == ["allowed"]
    assert len(index.issues) == 4
    assert all(str(tmp_path) not in issue for issue in index.issues)


def test_invalid_manifest_leaves_index_empty_with_safe_diagnostic(tmp_path):
    (tmp_path / "manifest.csv").write_text("private,invalid,header\n", encoding="utf-8")

    index = CourseIndex(tmp_path)

    assert index.documents("testing") == ()
    assert index.issues
    assert all("private" not in issue and str(tmp_path) not in issue for issue in index.issues)


def test_private_subtree_cannot_be_indexed_in_demo_mode(tmp_path):
    private_dir = tmp_path / "local_course_pdfs"
    private_dir.mkdir()
    _pdf(private_dir / "notes.pdf", "An internal exercise")
    _manifest(tmp_path, ("testing", "local", "Local", "local_course_pdfs/notes.pdf", "project_demo"))
    _manifest(private_dir, ("testing", "local", "Local", "notes.pdf", "local_only"))

    assert CourseIndex(tmp_path).documents("testing") == ()
    assert CourseIndex(private_dir, private=True).documents("testing")[0].license == "local_only"


def test_demo_questions_rank_the_expected_pdf_page_first():
    index = CourseIndex(Path(__file__).resolve().parents[1] / "data")

    testing, = index.search("software_testing", "Phân vùng tương đương là gì?", limit=1)
    algorithm, = index.search(
        "algorithm_analysis", "Quy tắc tuần tự khi phân tích thời gian tính là gì?", limit=1
    )

    assert (testing.document_id, testing.page) == ("testing_basics", 2)
    assert (algorithm.document_id, algorithm.page) == ("algorithm_basics", 2)
