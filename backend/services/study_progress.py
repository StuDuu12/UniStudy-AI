import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from backend.schemas.study import StudyState


@dataclass(frozen=True)
class SavedStudy:
    session_id: str
    revision: int
    state: StudyState


class StaleStudyProgress(Exception):
    pass


class StudyProgress:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "study_progress.sqlite3"

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS study_progress (
                    session_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state TEXT NOT NULL
                )"""
            )
            yield connection

    def read(self, course_id: str, topic_id: str, session_id: str, *, create: bool = False) -> SavedStudy | None:
        with self._connect() as connection:
            if create:
                connection.execute(
                    """INSERT INTO study_progress (session_id, course_id, topic_id, revision, state)
                       VALUES (?, ?, ?, 1, ?) ON CONFLICT(session_id) DO NOTHING""",
                    (session_id, course_id, topic_id, StudyState().model_dump_json()),
                )
            row = connection.execute(
                "SELECT revision, state FROM study_progress WHERE session_id = ? AND course_id = ? AND topic_id = ?",
                (session_id, course_id, topic_id),
            ).fetchone()
        if row is None:
            return None
        revision, state = row
        return SavedStudy(session_id, revision, StudyState.model_validate_json(state))

    def save(self, course_id: str, topic_id: str, state: StudyState, previous: SavedStudy | None) -> SavedStudy:
        encoded = state.model_dump_json()
        with self._connect() as connection:
            if previous is None:
                session_id = str(uuid4())
                connection.execute(
                    "INSERT INTO study_progress (session_id, course_id, topic_id, revision, state) VALUES (?, ?, ?, 1, ?)",
                    (session_id, course_id, topic_id, encoded),
                )
                return SavedStudy(session_id, 1, state)

            updated = connection.execute(
                """UPDATE study_progress SET revision = revision + 1, state = ?
                   WHERE session_id = ? AND course_id = ? AND topic_id = ? AND revision = ?""",
                (encoded, previous.session_id, course_id, topic_id, previous.revision),
            )
            if updated.rowcount != 1:
                raise StaleStudyProgress
            return SavedStudy(previous.session_id, previous.revision + 1, state)
