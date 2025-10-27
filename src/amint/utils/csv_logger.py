import csv
import threading
from pathlib import Path
from typing import List, Dict

class CSVLogger:
    """
    Thread-safe CSV logger for appending rows with header management.
    """
    _locks = {}

    def __init__(self, filepath: str, fieldnames: List[str]):
        self.filepath = Path(filepath)
        self.fieldnames = fieldnames
        self._ensure_dir()
        if filepath not in CSVLogger._locks:
            CSVLogger._locks[filepath] = threading.Lock()
        self._lock = CSVLogger._locks[filepath]
        self._ensure_header()

    def _ensure_dir(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_header(self):
        if not self.filepath.exists() or self.filepath.stat().st_size == 0:
            with self._lock, open(self.filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames, delimiter=';')
                writer.writeheader()

    def log(self, row: Dict):
        with self._lock, open(self.filepath, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames, delimiter=';')
            writer.writerow(row) 