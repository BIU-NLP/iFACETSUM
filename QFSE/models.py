from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class SummarySent:
    sent_id: str
    sent: str


@dataclass_json
@dataclass
class Summary:
    summary_sents: List[SummarySent]
    length_in_words: int
