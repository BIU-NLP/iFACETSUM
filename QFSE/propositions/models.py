from dataclasses import dataclass
from typing import List, Set, Dict

from dataclasses_json import dataclass_json



@dataclass_json
@dataclass(eq=False)
class PropositionLine:
    topic: str
    summary_file: str
    scu_sent_char_idx: int
    scu_sentence: str
    document_file: str
    doc_sent_char_idx: int
    doc_sent_text: str
    doc_span_offsets: List[List[int]]
    summary_span_offsets: List[List[int]]
    doc_span_text: str
    summary_span_text: str
    quality: int
    pred_prob: float


# Setting `eq` to false because we want to dedup by id

@dataclass_json
@dataclass(eq=False)
class PropositionCluster:
    proposition_lines: List[PropositionLine]



