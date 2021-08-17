import logging
import pickle
from collections import defaultdict
from typing import Dict, List, Tuple

import nltk
import pandas as pd

from QFSE.consts import COREF_TYPE_PROPOSITIONS, MAX_MENTIONS_IN_CLUSTER
from QFSE.coref.coref_labels import create_objs, PROPOSITIONS_DEFAULT_CLUSTER
from QFSE.coref.models import Mention
from QFSE.coref.utils import get_clusters_ids_to_filter
from QFSE.models import PropositionClusters
from QFSE.propositions.models import PropositionLine, PropositionCluster
from data.Config import COREF_LOCATIONS


def parse_line(line):
    def offset_str2list(offset):
        return [[int(start_end) for start_end in offset.split(',')] for offset in offset.split(';')]

    def offset_decreaseSentOffset(sentOffset, scu_offsets):
        return [[start_end[0] - sentOffset, start_end[1] - sentOffset] for start_end in scu_offsets]

    doc_sent_offset = int(line['docSentCharIdx'])
    doc_offsets = offset_decreaseSentOffset(doc_sent_offset, offset_str2list(line['docSpanOffsets']))
    scu_sent_offset = int(line['scuSentCharIdx'])
    scu_offsets = offset_decreaseSentOffset(scu_sent_offset, offset_str2list(line['summarySpanOffsets']))

    return PropositionLine(
        line['topic'], line['summaryFile'], scu_sent_offset, line['scuSentence'], line['documentFile'],
        doc_sent_offset, line['docSentText'], doc_offsets, scu_offsets,
        line['docSpanText'], line['summarySpanText'], line['Quality'],
        line['pred_prob'])


def get_sentences_by_doc_id(doc_id, corpus):
    found_docs = [doc for doc in corpus.documents if doc_id in doc.id]
    if len(found_docs) != 1:
        # raise ValueError("# of found docs is different than 1")
        logging.error("parsing proposition error: # of found docs is different than 1")
        return None

    doc = found_docs[0]

    assert len(doc.sentences) == len(list(doc.spacyDoc.sents))
    return doc.sentences


def find_indices_by_char_idx(sentences, sent_text, span_text):
    """
    The data is in a format where we have only the char index, but we have a unit of a sentence / token so we need to know
    how to map between them
    """

    for sent_idx, curr_sent in enumerate(sentences):
        curr_sent_text = curr_sent.text
        if sent_text in curr_sent_text:
            return _find_indices_by_char_idx(sent_idx, curr_sent_text, curr_sent.tokens, span_text)

    logging.warning("Skipping proposition because couldn't find text")
    return None, None, None


def _find_indices_by_char_idx(sent_idx, corpus_sent: str, corpus_tokens, span_text):
    """
    Gets the spacy token indices of a span in a text
    """

    span_text_split = span_text.split("...")

    start_char_idx = corpus_sent.index(span_text_split[0])
    end_char_idx = corpus_sent.index(span_text_split[-1]) + len(span_text_split[-1]) - 1

    sent_split_lengths = [len(x) + 1 if isinstance(x, str) else len(x.text_with_ws) for x in corpus_tokens]
    sent_split_accumulated = [sent_split_lengths[i] + sum(sent_split_lengths[:i]) for i in range(len(sent_split_lengths))]

    span_start_word_idx = [i for i, word_accumulated in enumerate(sent_split_accumulated) if start_char_idx + 1 < word_accumulated][0]
    span_end_word_idx = [i for i, word_accumulated in enumerate(sent_split_accumulated) if end_char_idx < word_accumulated][0]

    if span_start_word_idx is None or span_end_word_idx is None:
        logging.warning("Skipping proposition because couldn't find text")
        return None, None, None

    return sent_idx, span_start_word_idx, span_end_word_idx


def parse_lines(df, corpus):

    all_clusters = {}
    parsed = {}

    # Remove same sentence exactly
    df = df[df['docSentText'] != df['scuSentence']]

    sent_hash_to_cluster: Dict[int, PropositionCluster] = _pairwise_to_connected_components(df)

    # Extract mentions from clusters

    def create_mention_from_doc_or_scu(doc_file, span_offsets, sent_char_idx, sent_text, span_text, corpus, cluster_idx):
        # sent_start = span_offsets[0][0]
        # sent_end = span_offsets[-1][-1]

        sentences = get_sentences_by_doc_id(doc_file, corpus)
        if sentences:
            sent_idx, span_start_idx, span_end_idx = find_indices_by_char_idx(sentences, sent_text, span_text)

            if sent_idx is None:
                return None
            return Mention(doc_file, sent_idx, span_start_idx, span_end_idx, span_text, cluster_idx, COREF_TYPE_PROPOSITIONS)

    def dedup_seq_keep_order(seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    cluster_idx = 0
    mentions_seen = set()
    for propositions_cluster in dedup_seq_keep_order(sent_hash_to_cluster.values()):
        cluster = []
        mentions_seen_in_cluster = set()

        for proposition_line in propositions_cluster.proposition_lines:
            try:
                doc_mention = create_mention_from_doc_or_scu(proposition_line.document_file, proposition_line.doc_span_offsets, proposition_line.doc_sent_char_idx, proposition_line.doc_sent_text, proposition_line.doc_span_text, corpus, cluster_idx)
                scu_mention = create_mention_from_doc_or_scu(proposition_line.summary_file, proposition_line.summary_span_offsets, proposition_line.scu_sent_char_idx, proposition_line.scu_sentence, proposition_line.summary_span_text, corpus, cluster_idx)
                if doc_mention is not None and scu_mention is not None and doc_mention:
                    # Avoid adding the same mention, in propositions it is unlikely and it is only because we work pairwise
                    if doc_mention.token not in mentions_seen_in_cluster:
                        mentions_seen_in_cluster.add(doc_mention.token)
                        mentions_seen.add(doc_mention.token)
                        cluster.append(doc_mention)
                        doc_mentions = parsed.setdefault(proposition_line.document_file, [])
                        doc_mentions.append(doc_mention)

                    if scu_mention.token not in mentions_seen_in_cluster:
                        mentions_seen.add(scu_mention.token)
                        mentions_seen_in_cluster.add(scu_mention.token)
                        cluster.append(scu_mention)
                        scu_mentions = parsed.setdefault(proposition_line.summary_file, [])
                        scu_mentions.append(scu_mention)
            except:
                logging.exception("Skipping proposition line")

        if any(cluster):
            all_clusters[cluster_idx] = cluster
            cluster_idx = cluster_idx + 1

    return parsed, all_clusters


def _pairwise_to_connected_components(df) -> Dict[int, PropositionCluster]:
    """
    Turns a dataframe where each row is a pair to a cluster based on connected components strategy
    """

    sent_hash_to_cluster = {}

    for i, line in df.iterrows():
        parsed_line = parse_line(line)
        sent_one_hash = hash(parsed_line.summary_span_text)
        sent_two_hash = hash(parsed_line.doc_span_text)

        if sent_one_hash in sent_hash_to_cluster and sent_two_hash in sent_hash_to_cluster:
            # If same cluster - add to any
            if sent_hash_to_cluster[sent_one_hash] == sent_hash_to_cluster[sent_two_hash]:
                sent_hash_to_cluster[sent_one_hash].proposition_lines.append(parsed_line)
            # If not same cluster - merge
            else:
                sent_hash_to_cluster[sent_one_hash].proposition_lines.extend(sent_hash_to_cluster[sent_two_hash].proposition_lines)

                proposition_lines_to_change = sent_hash_to_cluster[sent_two_hash].proposition_lines
                for proposition_line in proposition_lines_to_change:
                    sent_hash_to_cluster[hash(proposition_line.summary_span_text)] = sent_hash_to_cluster[sent_one_hash]
                    sent_hash_to_cluster[hash(proposition_line.doc_span_text)] = sent_hash_to_cluster[sent_one_hash]

        elif sent_one_hash in sent_hash_to_cluster:
            # Add to existing cluster
            sent_hash_to_cluster[sent_two_hash] = sent_hash_to_cluster[sent_one_hash]
            sent_hash_to_cluster[sent_two_hash].proposition_lines.append(parsed_line)
        elif sent_two_hash in sent_hash_to_cluster:
            # Add to existing cluster
            sent_hash_to_cluster[sent_one_hash] = sent_hash_to_cluster[sent_two_hash]
            sent_hash_to_cluster[sent_two_hash].proposition_lines.append(parsed_line)
        else:
            # New clusters
            new_cluster = PropositionCluster([])
            new_cluster.proposition_lines.append(parsed_line)
            sent_hash_to_cluster[sent_one_hash] = new_cluster
            sent_hash_to_cluster[sent_two_hash] = new_cluster

    return sent_hash_to_cluster



def parse_propositions_file(df, corpus) -> Tuple[Dict[int, List[Mention]], Dict[int, List[Mention]]]:
    parsed, all_clusters = parse_lines(df, corpus)
    return parsed, all_clusters


def get_proposition_clusters(formatted_topics, corpus):
    import os
    path_to_dir = os.getcwd()
    file_path = COREF_LOCATIONS[corpus.topic_id][COREF_TYPE_PROPOSITIONS]
    cache_file_path = f"{path_to_dir}/{file_path}.cache"
    try:
        with open(cache_file_path, "rb") as f:
            documents, clusters_objs = pickle.load(f)
    except:
        df = pd.read_csv(f"{path_to_dir}/{file_path}")

        # TODO: Call external proposition alignment with `formatted_topics`

        documents, all_clusters = parse_propositions_file(df, corpus)

        clusters_objs = create_objs(all_clusters, COREF_TYPE_PROPOSITIONS, PROPOSITIONS_DEFAULT_CLUSTER, PROPOSITIONS_DEFAULT_CLUSTER)

        with open(cache_file_path, "wb") as f:
            pickle.dump((documents, clusters_objs), f)

    clusters_ids_to_filter = get_clusters_ids_to_filter(clusters_objs)
    clusters_objs = {cluster_id: cluster for cluster_id, cluster in clusters_objs.items() if cluster_id not in clusters_ids_to_filter}

    propositions_clusters = PropositionClusters(documents, clusters_objs)
    propositions_clusters_dict = propositions_clusters.to_dict()
    doc_names_to_clusters = propositions_clusters_dict['doc_name_to_clusters']
    for document in corpus.documents:
        doc_id = document.id
        if doc_id in doc_names_to_clusters:
            mentions = doc_names_to_clusters[doc_id]
            # document.coref_clusters[COREF_TYPE_PROPOSITIONS] = document_proposition_clusters
            mentions = [mention for mention in mentions if mention['cluster_idx'] not in clusters_ids_to_filter]
            for mention in mentions:
                document.sentences[mention['sent_idx']].coref_clusters[COREF_TYPE_PROPOSITIONS].append(mention)

    corpus.coref_clusters[COREF_TYPE_PROPOSITIONS] = propositions_clusters_dict['cluster_idx_to_mentions']

    return propositions_clusters


if __name__ == "__main__":
    get_proposition_clusters(None, [])
