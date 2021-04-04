from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Mention:
    sent_idx: int
    start: int
    end: int
    token: str
    cluster_idx: int


@dataclass_json
@dataclass
class DocumentLine:
    document_name: str
    is_begin_document: bool


class PartialClusterType:
    BEGIN = "BEGIN"
    END = "END"
    BEGIN_AND_END = "BEGIN_AND_END"


@dataclass_json
@dataclass
class PartialCluster:
    cluster_idx: int
    partial_cluster_type: PartialClusterType


@dataclass_json
@dataclass
class TokenLine:
    token_idx: int
    token: str
    clusters: List[PartialCluster]


