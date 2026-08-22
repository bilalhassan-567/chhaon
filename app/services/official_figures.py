import json
from dataclasses import dataclass
from functools import lru_cache

from app.config import DATA_DIR

OFFICIAL_FIGURES_FILE = DATA_DIR / "official_figures.json"


@dataclass(frozen=True)
class OfficialFigure:
    id: str
    period_label: str
    figure_text: str
    context: str
    citation: str


@lru_cache
def load_official_figures() -> list[OfficialFigure]:
    data = json.loads(OFFICIAL_FIGURES_FILE.read_text(encoding="utf-8"))
    return [OfficialFigure(**f) for f in data["figures"]]
