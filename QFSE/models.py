from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Set

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
    cluster_id: str
    cluster_type: str
    mentions: List[Mention]
    pos_label: str
    cluster_label: str
    cluster_facet: str
    display_name: str
    num_mentions: int
    num_sents: int


@dataclass_json
@dataclass
class ClusterUserWrapper:
    shared_cluster: Cluster  # Since it is shared it should stay immutable, should not be updated per request
    num_mentions_filtered: int

    def custom_to_dict(self) -> dict:
        """
        We want to avoid having to change the UI for the wrapper
        """

        dict = self.to_dict()
        shared_obj = dict.pop('shared_cluster')
        for key, value in shared_obj.items():
            dict[key] = value

        return dict


@dataclass_json
@dataclass
class CorefClusters:
    doc_name_to_clusters: Dict[str, List[Mention]]
    cluster_idx_to_mentions: Dict[str, Cluster]


@dataclass_json
@dataclass
class PropositionClusters:
    doc_name_to_clusters: Dict[str, List[Mention]]
    cluster_idx_to_mentions: Dict[str, Cluster]


@dataclass_json
@dataclass(frozen=True, eq=True)
class DocSent:
    doc_id: str
    sent_idx: int

    def __repr__(self):
        return f"{self.doc_id}_{self.sent_idx}"


@dataclass_json
@dataclass(frozen=True, eq=True)
class ClusterQuery:
    cluster_id: int
    cluster_type: str
    token: str


@dataclass_json
@dataclass
class TokensCluster:
    tokens: List
    cluster_id: int
    cluster_type: str

    def get_text(self):
        return " ".join([token.get_text() if isinstance(token, TokensCluster) else " ".join(token) for token in self.tokens])


@dataclass_json
@dataclass
class QueryResultSentence:
    tokens: List[Union[TokensCluster, List[str]]]
    doc_id: Optional[str] = None
    sent_idx: Optional[int] = None
    is_first_time_seen: bool = True

    def get_text(self):
        return " ".join([token.get_text() if isinstance(token, TokensCluster) else " ".join(token) for token in self.tokens])


@dataclass_json
@dataclass
class QueryResult:
    result_sentences: List[QueryResultSentence]
    query: List[ClusterQuery]
    orig_sentences: List[QueryResultSentence]
    result_created: str

    def get_doc_sent_indices(self) -> Set[DocSent]:
        return {DocSent(sent.doc_id, sent.sent_idx) for sent in self.orig_sentences}


@dataclass_json
@dataclass
class QueryResultUserWrapper:
    shared_query_result: QueryResult  # Since it is shared it should stay immutable, should not be updated per request
    query_idx: int

    def custom_to_dict(self) -> dict:
        """
        We want to avoid having to change the UI for the wrapper
        """

        dict = self.to_dict()
        shared_obj = dict.pop('shared_query_result')
        for key, value in shared_obj.items():
            dict[key] = value

        return dict


@dataclass_json
@dataclass
class DocumentResult:
    doc_id: int
    orig_sentences: List[QueryResultSentence]


@dataclass_json
@dataclass
class UIAction:
    action: str
    action_details: dict
    result_created: str
