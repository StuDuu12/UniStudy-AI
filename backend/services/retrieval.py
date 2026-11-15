import re
from dataclasses import dataclass, replace
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import spmatrix

from backend.services.evidence import normalize_text
from backend.services.ingest import ChunkSource, DocumentInfo
from backend.services.query import query_parts


_MIN_QUERY_COVERAGE = 0.15


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

    def search(
        self, question: str, limit: int = 3, *, minimum_score: float = 0.0, contextual: bool = False
    ) -> list[ChunkSource]:
        if limit <= 0:
            return []
        parts = [question] if contextual else query_parts(question)
        batches = [self._search_part(part, limit, minimum_score, contextual=contextual) for part in parts]
        results = []
        seen = set()
        for rank in range(max(map(len, batches), default=0)):
            for batch in batches:
                if rank < len(batch) and batch[rank].chunk_id not in seen:
                    results.append(batch[rank])
                    seen.add(batch[rank].chunk_id)
                    if len(results) == limit:
                        return results
        return results

    def _search_part(
        self, question: str, limit: int, minimum_score: float, *, contextual: bool
    ) -> list[ChunkSource]:
        if self.matrix is None or self.vectorizer is None:
            return []
        query = self.vectorizer.transform([question])
        # Cosine ignores grams absent from the course vocabulary, even on unrelated queries.
        query_grams = set(self.vectorizer.build_analyzer()(question))
        if not query.nnz or query.nnz < len(query_grams) * _MIN_QUERY_COVERAGE:
            return []
        scores = cosine_similarity(query, self.matrix)[0]
        normalized_question = normalize_text(question)
        expansions = []
        for term, synonyms in (("tinh chat", "luat hang dang thuc"), ("tien de", "dinh nghia dang thuc")):
            if term in normalized_question:
                expansions.append(normalized_question.replace(term, synonyms))

        # Apply standalone subject rules only to standalone queries.
        # A contextual query can end in “nó là gì” after an earlier topic.
        subjects = []
        if not contextual:
            shared_subject = re.match(r"^(.+?) co (?:nhung|cac)\b", normalized_question)
            if shared_subject:
                subjects.append(shared_subject.group(1))
            operations = re.search(
                r"phep toan (?:tren )?(.+?)(?: co ban| gom| la gi|[?]|$)", normalized_question
            )
            if operations:
                subjects.append(operations.group(1))
            definition = re.fullmatch(
                r"([\w\s]+?)(?:\s*\([^()]+\))?\s+la\s+gi\s*[?!.]*", normalized_question.strip()
            )
            if definition:
                topic = definition.group(1).strip()
                subjects.append(topic)
                expansions.append(f"khai niem {topic}")
        required_words = set(re.findall(r"\w+", " ".join(subjects)))
        for expanded in expansions:
            expanded_scores = cosine_similarity(self.vectorizer.transform([expanded]), self.matrix)[0]
            for index, expanded_score in enumerate(expanded_scores):
                scores[index] = max(scores[index], expanded_score)

        for index, chunk in enumerate(self.chunks):
            excerpt = normalize_text(chunk.excerpt)
            if required_words and not required_words <= set(re.findall(r"\w+", excerpt)):
                scores[index] = 0.0
                continue
            # A heading alone offers less evidence than an explanatory passage.
            scores[index] *= min(len(chunk.excerpt.split()) / 20, 1.0) ** 0.5
            if re.match(r"^(?:noi dung|muc tieu|chuong\s+\d)", excerpt):
                scores[index] *= 0.35

        ranked = sorted(enumerate(scores), key=lambda item: -item[1])
        results: list[ChunkSource] = []
        for index, score in ranked[:limit]:
            if score <= 0 or score < minimum_score:
                break
            results.append(replace(self.chunks[index], score=min(float(score), 1.0)))
        return results
