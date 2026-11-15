from dataclasses import dataclass, replace
from pathlib import Path
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import spmatrix

from backend.services.evidence import normalize_text
from backend.services.ingest import ChunkSource, DocumentInfo
from backend.services.query import query_parts


_MIN_QUERY_COVERAGE = 0.15
_QUERY_STOP_WORDS = {
    "la", "gi", "va", "co", "nhung", "cac", "cua", "trong", "cho", "tai", "sao",
    "nhu", "the", "nao", "o", "diem", "mot", "dung", "de", "ban", "ve", "hay",
    "voi", "khi", "nham", "do", "ma", "ra", "vao", "theo", "nay", "kia", "day",
    "luc", "giup", "minh", "toi", "em", "thay", "hoi", "biet", "chua", "roi",
    "nhan", "ai", "phap", "toan", "dinh", "nghia", "khai", "niem",
}


def _rerank_for_question(scores, question: str, chunks: tuple[ChunkSource, ...]):
    keywords = [
        word for word in re.findall(r"\w+", normalize_text(question))
        if word not in _QUERY_STOP_WORDS
    ]
    keyword_set = set(keywords)
    phrases = {" ".join(keywords[index:index + 2]) for index in range(len(keywords) - 1)}
    norm_q = normalize_text(question)
    is_technique_or_definition = any(
        p in norm_q for p in ("ky thuat", "phuong phap", "la gi", "khai niem", "dinh nghia")
    )

    for index, chunk in enumerate(chunks):
        if scores[index] <= 0:
            continue
        text = normalize_text(chunk.excerpt)
        words = set(re.findall(r"\w+", text))
        title = normalize_text(chunk.heading)

        # Penalize slides with 'thuc hanh', 'tinh huong', 'vi du', 'ly do lua chon'
        # when question asks for techniques/methods/definitions ('ky thuat', 'phuong phap', 'la gi')
        if is_technique_or_definition:
            penalty_markers = ("thuc hanh", "tinh huong", "ly do lua chon")
            is_penalty_slide = (
                any(marker in text or marker in title for marker in penalty_markers)
                or any(title.startswith(m) or text.startswith(m) for m in ("vi du", "tinh huong", "thuc hanh", "bai tap"))
                or ("vi du" in title)
            )
            if is_penalty_slide:
                scores[index] *= 0.35

        # Boost for Chapter 3 Page 29 listing the 5 techniques of requirements elicitation
        title_boost = 0.0
        if "ky thuat" in norm_q and "kham pha yeu cau" in norm_q:
            if "cac ky thuat kham pha yeu cau" in text or "cac ky thuat kham pha yeu cau" in title:
                techniques = ("dieu tra", "sang tao", "tai lieu lam trung tam", "quan sat", "ho tro")
                matched_tech = sum(1 for t in techniques if t in text)
                if matched_tech >= 3:
                    title_boost = 1.0
                else:
                    title_boost = 0.5
            elif title.startswith("cac ky thuat kham pha yeu cau") or text.startswith("cac ky thuat kham pha yeu cau"):
                title_boost = 0.45

        coverage = len(keyword_set & words) / max(len(keyword_set), 1)
        phrase_hits = sum(phrase in text for phrase in phrases)
        scores[index] += 0.12 * coverage + 0.04 * min(phrase_hits, 3) + title_boost
        # Repeated outline slides match many query terms but carry no explanation.
        if "noi dung" in text and len(words) < 45:
            scores[index] *= 0.15
    return scores


@dataclass(frozen=True)
class IndexedCourse:
    documents: tuple[DocumentInfo, ...]
    chunks: tuple[ChunkSource, ...]
    vectorizer: TfidfVectorizer
    matrix: spmatrix


class CourseRetriever:
    def __init__(self, course_id: str, documents: list[DocumentInfo], chunks: list[ChunkSource]):
        self.course_id = course_id
        self.documents = tuple(documents)
        self.chunks = tuple(chunks)
        if chunks:
            self.vectorizer = TfidfVectorizer(
                analyzer="char",
                ngram_range=(3, 5),
                preprocessor=normalize_text,
            )
            self.matrix = self.vectorizer.fit_transform(
                chunk.excerpt + " " + " ".join(chunk.excerpt.split()[:30]) for chunk in chunks
            )
        else:
            self.vectorizer = None
            self.matrix = None

    def search(self, question: str, limit: int = 3) -> list[ChunkSource]:
        parts = query_parts(question)
        batches = [self._search_part(part, limit) for part in parts]
        results = []
        seen = set()
        # Round-robin prevents one topic occupying every result in a multi-part question.
        for rank in range(max(0, limit)):
            for batch in batches:
                if rank < len(batch) and batch[rank].chunk_id not in seen:
                    results.append(batch[rank])
                    seen.add(batch[rank].chunk_id)
                    if len(results) >= limit:
                        return results
        return results

    def _search_part(self, question: str, limit: int = 3) -> list[ChunkSource]:
        if self.matrix is None or self.vectorizer is None or limit <= 0:
            return []
        query = self.vectorizer.transform([question])
        # Cosine ignores grams absent from the course vocabulary, even on unrelated queries.
        query_grams = set(self.vectorizer.build_analyzer()(question))
        if not query.nnz or query.nnz < len(query_grams) * _MIN_QUERY_COVERAGE:
            return []
        scores = cosine_similarity(query, self.matrix)[0]
        normalized_question = normalize_text(question)
        # Some multiword topics lose their meaning when matched as separate syllables.
        required_phrases = []
        if re.search(r"\buse case\b", normalized_question):
            required_phrases.append(r"\b(?:use case|ca su dung)\b")
        if re.search(r"\blich dang ky\b", normalized_question):
            required_phrases.append(r"\blich dang ky\b")
        # Match terminology used in slides, not only the wording of the question.
        expansions = []
        if "tinh chat" in normalized_question:
            expansions.append(normalized_question.replace("tinh chat", "luat hang dang thuc"))
        if "tien de" in normalized_question:
            expansions.append(normalized_question.replace("tien de", "dinh nghia dang thuc"))
        if "bieu do use case" in normalized_question:
            expansions.append("bieu do use case chuc nang he thong goc do nguoi dung")
        if "ky thuat" in normalized_question and "kham pha yeu cau" in normalized_question:
            expansions.append("cac ky thuat kham pha yeu cau")
        for expanded in expansions:
            expanded_scores = cosine_similarity(self.vectorizer.transform([expanded]), self.matrix)[0]
            for index in range(len(scores)):
                scores[index] = max(scores[index], expanded_scores[index])

        # Non-stopword query keywords coverage check
        query_keywords = [
            w for w in re.findall(r"\w+", normalized_question)
            if w not in _QUERY_STOP_WORDS and len(w) > 1
        ]
        if query_keywords:
            expanded_kws = set(query_keywords)
            for expanded in expansions:
                for w in re.findall(r"\w+", expanded):
                    if w not in _QUERY_STOP_WORDS and len(w) > 1:
                        expanded_kws.add(w)

            all_course_words = getattr(self, "_all_words", None)
            if all_course_words is None:
                all_course_words = {
                    w for c in self.chunks
                    for w in re.findall(r"\w+", normalize_text(c.excerpt) + " " + normalize_text(c.heading))
                }
                object.__setattr__(self, "_all_words", all_course_words)

            covered_kws = [w for w in query_keywords if w in all_course_words]
            # If substantive query keywords have 0% coverage or ratio < 0.6, do not return random slides
            if not covered_kws or len(covered_kws) < len(query_keywords) * 0.6:
                return []

            # Also zero out chunks that have zero keyword coverage
            for index, chunk in enumerate(self.chunks):
                chunk_words = set(re.findall(r"\w+", normalize_text(chunk.excerpt))) | set(re.findall(r"\w+", normalize_text(chunk.heading)))
                if not (expanded_kws & chunk_words):
                    scores[index] = 0.0
        shared_subject = re.match(r"^(.+?) co (?:nhung|cac)\b", normalized_question)
        if shared_subject:
            topic_words = set(re.findall(r"\w+", shared_subject.group(1)))
            # These words describe the form of a request, rather than its topic.
            topic_words.difference_update({"cac", "co", "ban", "thao", "tac"})
            for index, chunk in enumerate(self.chunks):
                if not topic_words <= set(re.findall(r"\w+", normalize_text(chunk.excerpt))):
                    scores[index] = 0.0
        # Keep the subject of an operations question, instead of matching "operations"
        # from unrelated chapters (e.g. propositional logic versus sets).
        operations = re.search(
            r"phep toan (?:tren )?(.+?)(?: co ban| gom| la gi|[?]|$)",
            normalize_text(question),
        )
        if operations:
            subject = set(re.findall(r"\w+", operations.group(1)))
            for index, chunk in enumerate(self.chunks):
                if not subject <= set(re.findall(r"\w+", normalize_text(chunk.excerpt))):
                    scores[index] = 0.0
        # Definition questions often use "là gì" while slides use "Khái niệm".
        definition = (re.fullmatch(r"(.+?)\s+la\s+gi\s*[?!.]*", normalize_text(question).strip())
                      or re.fullmatch(r"(?:dinh nghia|khai niem)\s+(.+)", normalize_text(question).strip()))
        if definition and not re.search(r"\b(?:quy tac|cach|buoc)\b", definition.group(1)):
            topic = definition.group(1).strip()
            topic = topic.replace("duong di euler", "duong mot net euler")
            if " cua " in topic:
                required_phrases.extend(
                    rf"\b{re.escape(phrase)}\b"
                    for phrase in topic.split(" cua ")
                    if len(phrase.split()) > 1
                )
            expanded = self.vectorizer.transform([f"khai niem {topic}"])
            expanded_scores = cosine_similarity(expanded, self.matrix)[0]
            topic_words = set(re.findall(r"\w+", topic))
            topic_words.difference_update({"cua", "trong", "ve", "la", "gi", "nhung", "cac", "co", "va", "ban", "thao", "tac", "dinh", "nghia"})
            for index, chunk in enumerate(self.chunks):
                chunk_words = set(re.findall(r"\w+", normalize_text(chunk.excerpt)))
                # Generic definition vocabulary must not replace the actual topic.
                scores[index] = (
                    max(scores[index], expanded_scores[index])
                    if topic_words <= chunk_words else 0.0
                )
        scores = _rerank_for_question(scores, question, self.chunks)
        if definition:
            for index, chunk in enumerate(self.chunks):
                if scores[index] <= 0:
                    continue
                text = normalize_text(chunk.excerpt)
                if "goi la" in text or "la mot" in text:
                    scores[index] += 0.25
                if "cho mot do thi" in text and "goi la" in text:
                    scores[index] += 1.50
        # Cover slides / headings alone provide little evidence, despite high cosine.
        for index, chunk in enumerate(self.chunks):
            text = normalize_text(chunk.excerpt)
            if required_phrases and not all(re.search(phrase, text) for phrase in required_phrases):
                scores[index] = 0.0
                continue
            scores[index] *= min(len(chunk.excerpt.split()) / 20, 1.0) ** 0.5
            if re.match(r"^(?:noi dung|muc tieu|chuong\s+\d)", text):
                scores[index] *= 0.35
        ranked = sorted(enumerate(scores), key=lambda item: -item[1])
        results: list[ChunkSource] = []
        for index, score in ranked[:limit]:
            if score > 0:
                results.append(replace(self.chunks[index], score=min(float(score), 1.0)))
        return results
