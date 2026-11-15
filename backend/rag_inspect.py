"""Inspect the PDF evidence selected by the API without calling an AI provider."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from backend.services.course_manager import CourseManager
from backend.services.evidence import EVIDENCE_THRESHOLD


def main():
    parser = argparse.ArgumentParser(description="Xem các đoạn PDF và trang nguồn được tra cứu.")
    parser.add_argument("--course", help="Mã học phần. Bỏ trống để liệt kê học phần.")
    parser.add_argument("--question", help="Câu hỏi cần tra cứu")
    parser.add_argument("--top-k", type=int, choices=range(1, 11), metavar="1..10")
    args = parser.parse_args()
    manager = CourseManager(Path(__file__).resolve().parents[1])
    if not args.course:
        output = [course.model_dump() for course in manager.list_courses()]
    else:
        if not args.question or not args.question.strip():
            parser.error("--question là bắt buộc khi dùng --course")
        if manager.get_course_documents(args.course) is None:
            parser.error("Không tìm thấy mã học phần")
        retriever = manager._catalog.retrievers.get(args.course)
        sources = manager._lookup_sources(retriever, args.question, limit=args.top_k) if retriever else []
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
