import json
from pathlib import Path
from typing import List

from pipeline.models import KBArticle, RawTicket


def load_tickets(path: str = "tickets.json") -> List[RawTicket]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RawTicket(**t) for t in data]


def load_kb_articles(path: str = "kb_articles.json") -> List[KBArticle]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [KBArticle(**a) for a in data]
