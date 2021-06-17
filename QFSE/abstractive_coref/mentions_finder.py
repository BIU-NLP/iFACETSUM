from collections import defaultdict
from typing import Dict, List

from spacy.tokens.doc import Doc

from QFSE.propositions.utils import find_indices_by_char_idx, _find_indices_by_char_idx


class MentionsFinder:
    """
    Searches for mentions in the abstractive summary
    """

    def find_mentions(self, abstractive_summary: Doc, original_sentences) -> Dict[str, List]:
        token_to_mention = defaultdict(list)

        for orig_sent in original_sentences:
            for cluster_type, cluster in orig_sent.coref_clusters.items():
                for mention in cluster:
                    if mention['token'] in abstractive_summary.text:
                        _, mention_start, mention_end = _find_indices_by_char_idx(None, abstractive_summary.text, abstractive_summary, mention['token'])

                        if mention_start is not None and mention_end is not None:
                            abstractive_mention = {
                                "start": mention_start,
                                "end": mention_end,
                                "doc_id": mention['doc_id'],
                                "sent_idx": mention['sent_idx'],
                                "token": mention['token'],
                                "cluster_idx": mention['cluster_idx'],
                                "cluster_type": mention['cluster_type']
                            }
                            for token_idx in range(mention_start, mention_end + 1):
                                token_to_mention[token_idx].append(abstractive_mention)

        return token_to_mention

