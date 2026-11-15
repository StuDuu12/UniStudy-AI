"""Development checks on supplied PDFs; --live also checks the configured AI service."""
import argparse
import json
from pathlib import Path
from time import monotonic
from backend.services.course_manager import CourseManager

CASES = [
    ("short", "Tập hợp là gì?", "success", {2}),
    ("intro", "Mình đang học môn Toán rời rạc nhưng chưa hiểu bài. Bạn giải thích giúp mình tập hợp là gì nhé.", "success", {2}),
    ("polite", "Bạn có thể giải thích cho mình tập hợp là gì không?", "success", {2}),
    ("boole", "Đại số Boole có những tính chất và tiên đề cơ bản nào?", "success", {6, 9, 10}),
    ("operations", "Các phép toán tập hợp cơ bản gồm những phép toán nào?", "success", {9, 10}),
    ("multiple", "Tập con là gì? Lực lượng của tập hợp là gì?", "success", {4, 27}),
    ("outside", "Cách nấu phở bò?", "insufficient_evidence", set()),
    ("invalid", "!!!", "invalid_input", set()),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Send selected excerpts to the configured AI API")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", default="docs/rag_evaluation.json")
    args = parser.parse_args()
    manager = CourseManager(args.root)
    if args.live and not manager._ai:
        parser.error("AI configuration is missing; no live evaluation was performed")
    if not args.live:
        manager._ai = None
    results = []
    for name, question, expected_status, pages in CASES:
        started = monotonic()
        response = manager.answer_question("toan_roi_rac", question)
        retrieved = {s.page for s in response.sources}
        passed = response.status == expected_status and pages <= retrieved
        record = {"case": name, "question": question, "passed": passed,
                  "seconds": round(monotonic()-started, 2), "expected_pages": sorted(pages),
                  "response": response.model_dump()}
        results.append(record)
        print(f"{name}: {'PASS' if passed else 'FAIL'} status={response.status} mode={response.mode} pages={sorted(retrieved)}", flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"development_set": True, "live": args.live, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{sum(r['passed'] for r in results)}/{len(results)} passed. Answers require manual review. Report: {output}")
    raise SystemExit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
