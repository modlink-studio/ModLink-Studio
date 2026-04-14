from __future__ import annotations

from pathlib import Path

from .experiments import ExperimentStore
from .recordings import RecordingStore
from .sessions import SessionStore


class StorageBackend:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.recordings = RecordingStore(self.root_dir)
        self.sessions = SessionStore(self.root_dir)
        self.experiments = ExperimentStore(self.root_dir)
