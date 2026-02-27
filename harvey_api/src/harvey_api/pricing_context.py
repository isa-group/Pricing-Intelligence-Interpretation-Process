from dataclasses import dataclass
from typing import Dict
from datetime import datetime


@dataclass
class DbUrlItem:
    id: str
    url: str
    created_at: datetime


pricing_context_db: Dict[str, DbUrlItem] = {}
