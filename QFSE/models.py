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
class Cluster:
    cluster_id: int
    cluster_type: str
    mentions: List[Mention]
    cluster_label: str
    most_representative_mention: str


@dataclass_json
@dataclass
class CorefClusters:
    doc_name_to_clusters: Dict[str, List[Mention]]
    cluster_idx_to_mentions: Dict[str, Cluster]


@dataclass_json
@dataclass
class PropositionClusters:
    doc_name_to_clusters: Dict[str, List[Mention]]
    cluster_idx_to_mentions: Dict[str, List[Mention]]
