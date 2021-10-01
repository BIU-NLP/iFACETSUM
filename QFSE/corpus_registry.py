import os
import pickle
from dataclasses import dataclass
from typing import Optional, Set, Dict, List

from QFSE.Corpus import Corpus
import data.Config as config
from QFSE.Utilities import REPRESENTATION_STYLE_SPACY, REPRESENTATION_STYLE_BERT, get_item, loadBert
from QFSE.coref.models import Mention
from QFSE.coref.utils import convert_corpus_to_coref_input_format, get_coref_clusters
from QFSE.models import DocSent, Cluster, ClusterUserWrapper
from QFSE.propositions.utils import get_proposition_clusters
from QFSE.consts import COREF_TYPE_EVENTS, COREF_TYPE_PROPOSITIONS, COREF_TYPE_ENTITIES


# The SpaCy and BERT objects must be loaded before anything else, so that classes using them get the initialized objects.
# The SpaCy and BERT objects are initialized only when needed since these init processes take a long time.
REPRESENTATION_STYLE = REPRESENTATION_STYLE_SPACY  # REPRESENTATION_STYLE_W2V REPRESENTATION_STYLE_BERT
get_item("spacy")
if REPRESENTATION_STYLE == REPRESENTATION_STYLE_BERT:
    loadBert()


class CorpusRegistry:
    def __init__(self):
        self._registry = {}

    def get_corpus(self, topicId) -> Optional[Corpus]:
        if topicId not in self._registry:
            # make sure the topic ID is valid:
            if topicId in config.CORPORA_LOCATIONS:
                referenceSummsFolder = os.path.join(config.CORPORA_LOCATIONS[topicId],
                                                    config.CORPUS_REFSUMMS_RELATIVE_PATH)
                questionnaireFilepath = os.path.join(config.CORPORA_LOCATIONS[topicId],
                                                     config.CORPUS_QUESTIONNAIRE_RELATIVE_PATH)
                corpus = Corpus(topicId, config.CORPORA_LOCATIONS[topicId], referenceSummsFolder, questionnaireFilepath,
                                representationStyle=REPRESENTATION_STYLE)
            else:
                return None

            formatted_topics = convert_corpus_to_coref_input_format(corpus, topicId)
            get_coref_clusters(formatted_topics, corpus, COREF_TYPE_EVENTS)
            get_coref_clusters(formatted_topics, corpus, COREF_TYPE_ENTITIES)
            get_proposition_clusters(formatted_topics, corpus)

            self._registry[topicId] = corpus

        return self._registry[topicId]


def get_clusters_filtered(clusters_meta: Dict[str, Cluster], doc_sent_indices: Set[DocSent] = None) -> Dict[str, dict]:
    """
    Filters clusters based on a query (faceted search)
    """

    clusters_filtered = {}
    for cluster_idx, cluster in clusters_meta.items():
        # Return all if no query
        query_is_empty = doc_sent_indices is None or not any(doc_sent_indices)
        cluster_sentences_shown_in_query = []
        if doc_sent_indices:
            cluster_sentences_shown_in_query = [mention for mention in cluster['mentions']
                                                if _is_mention_in_query(mention, doc_sent_indices)]

        should_return_cluster = query_is_empty or any(cluster_sentences_shown_in_query)

        if should_return_cluster:
            num_mentions_filtered = cluster['num_mentions'] if query_is_empty else len(
                cluster_sentences_shown_in_query)
            clusters_filtered[cluster_idx] = ClusterUserWrapper(cluster, num_mentions_filtered).custom_to_dict()

    return clusters_filtered


def _is_mention_in_query(mention: Mention, doc_sent_indices) -> bool:
    return DocSent(mention['doc_id'], mention['sent_idx']) in doc_sent_indices
