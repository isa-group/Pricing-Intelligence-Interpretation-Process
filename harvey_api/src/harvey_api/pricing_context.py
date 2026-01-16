from dataclasses import dataclass
from typing import Dict


@dataclass
class DbUrlItem:
    id: str
    url: str

pricing_context_db: Dict[str, DbUrlItem] = {}
