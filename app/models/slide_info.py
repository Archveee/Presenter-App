from dataclasses import dataclass, field
from typing import List

@dataclass
class SlideInfo:
    index: int
    title: str
    notes: List[str] = field(default_factory=list)
    image_path: str = ""