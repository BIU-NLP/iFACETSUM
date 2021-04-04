from dataclasses import dataclass
from typing import List, Dict

from dataclasses_json import dataclass_json

from QFSE.coref.models import Mention


@dataclass_json
@dataclass
class SummarySent:
    doc_id: str
    sent_id: str
    sent_idx: int
    sent: str


@dataclass_json
@dataclass
class Summary:
    summary_sents: List[SummarySent]
    length_in_words: int


@dataclass_json
@dataclass
class CorefClusters:
    doc_name_to_clusters: Dict[str, List[Mention]]
