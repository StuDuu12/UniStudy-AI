"""Inspect the same PDF index used by the API, without calling an AI provider."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from backend.services.course_manager import CourseManager
from backend.services.evidence import EVIDENCE_THRESHOLD


def main():
    parser = argparse.ArgumentParser(description="Xem top-k đoạn PDF và trang nguồn, không gọi AI.")
    parser.add_argument("--course", help="course_id; bỏ trống để liệt kê học phần")
    parser.add_argument("--question", help="Câu hỏi cần truy xuất")
    parser.add_argument("--top-k", type=int, default=3, choices=range(1, 11), metavar="1..10")
    args = parser.parse_args()
    manager = CourseManager(Path(__file__).resolve().parents[1])
    if not args.course:
        output = [course.model_dump() for course in manager.list_courses()]
    else:
        if not args.question:
            parser.error("--question là bắt buộc khi dùng --course")
        if args.course not in {course.course_id for course in manager.list_courses()}:
            parser.error("Không tìm thấy course_id")
        # Diagnostic access to the exact index snapshot used by CourseManager.
        retriever = manager._catalog.retrievers.get(args.course)
        sources = retriever.search(args.question, limit=args.top_k) if retriever else []
        output = {
            "course_id": args.course,
            "question": args.question,
            "top_k": args.top_k,
            "threshold": EVIDENCE_THRESHOLD,
            "sources": [
                {**asdict(source), "passes_threshold": source.score >= EVIDENCE_THRESHOLD}
                for source in sources
            ],
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
