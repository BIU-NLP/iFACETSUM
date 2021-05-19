import json
import logging
import os
import re
from collections import defaultdict
from typing import List, Dict, Tuple

from QFSE.Corpus import Corpus
from QFSE.consts import COREF_TYPE_EVENTS
from QFSE.coref.coref_expr import get_clusters
from QFSE.coref.models import DocumentLine, TokenLine, Mention, PartialCluster, PartialClusterType
from QFSE.models import CorefClusters


def convert_corpus_to_coref_input_format(corpus: Corpus, topic_id: str):
    docs_formatted = {}
    for doc in corpus.documents:
        token_idx = 1
        sentences_formatted = []
        for sentence in doc.sentences:
            for token in sentence.tokens:
                sentences_formatted.append([sentence.sentIndex, token_idx, token, True])
                token_idx += 1

        docs_formatted[f"0_{doc.id}"] = sentences_formatted

    # with open("docs_formatted.json", "w") as f:
    #     f.write(json.dumps(docs_formatted))

    return docs_formatted


def get_coref_clusters(formatted_topics, corpus):
    path_to_dir = os.getcwd()

    # with open(f"{path_to_dir}/data/coref/spacy_wd_coref_duc.json") as f:
    #     data = f.read()
    with open(f"{path_to_dir}/data/coref/duc_predictions_ments.json") as json_file:
        data = json.load(json_file)

    # TODO: Call external coref API with `formatted_topics`

    coref_clusters = CorefClusters(*get_clusters(data))
    coref_clusters_dict = coref_clusters.to_dict()
    doc_names_to_clusters = coref_clusters_dict['doc_name_to_clusters']
    for document in corpus.documents:
        if document.id in doc_names_to_clusters:
            document_coref_clusters = doc_names_to_clusters[document.id]
            document.coref_clusters = document_coref_clusters
            # for coref_cluster in document_coref_clusters.values():
            #     for mention in coref_cluster:
            #           document.sentences[mention['sent_idx']].coref_clusters.append(mention)
            for mention in document_coref_clusters:
                document.sentences[mention['sent_idx']].coref_clusters.append(mention)

    corpus.coref_clusters = coref_clusters_dict['cluster_idx_to_mentions']

    return coref_clusters


def filter_clusters(parsed, all_clusters):
    singleton_clusters = [cluster_idx for cluster_idx, mentions in all_clusters.items() if len(mentions) == 1]

    for doc_clusters in parsed.values():
        for cluster_to_remove in singleton_clusters:
            if cluster_to_remove in doc_clusters:
                doc_clusters.pop(cluster_to_remove)
    [all_clusters.pop(cluster_to_remove) for cluster_to_remove in singleton_clusters]



def parse_conll_coref_file(data) -> Tuple[Dict[str, List[Mention]], Dict[str, List[Mention]]]:
    lines = data.splitlines()
    parsed, all_clusters = parse_lines(lines)
    filter_clusters(parsed, all_clusters)
    return parsed, all_clusters


def parse_line(line):
    items = line.split('\t')
    if line.startswith('#'):
        if line.startswith("#begin document"):
            doc_name = re.findall(".*? .*? (.*)", line)[0]
            return DocumentLine(doc_name, True)
        if line.startswith("#end document"):
            return DocumentLine(None, False)
    elif len(items) == 8:
        row_id_splitted = items[2].split("_")
        topic_id = row_id_splitted[0]
        doc_id = "_".join(row_id_splitted[1:])
        sent_idx = int(items[3])
        token_idx = int(items[4])
        token = items[5]
        clusters = parse_clusters(items[7])
        return TokenLine(topic_id, doc_id, sent_idx, token_idx, token, clusters)
    else:
        return None


def parse_clusters(clusters_str):
    clusters = []
    partial_cluster_type = None
    idx_str = ""

    def close_cluster(partial_cluster_type, idx_str):
        try:
            cluster_idx = int(idx_str)
        except:
            logging.error(f"couldn't parse idx_str ; {idx_str}")
            return None
        return PartialCluster(cluster_idx, partial_cluster_type)

    for char in clusters_str:
        if char == "(":
            partial_cluster_type = PartialClusterType.BEGIN
        elif char == "_" or char == "|" or char == ")":
            # Skip cases like `)_` where the cluster was already closed
            if idx_str != "":
                if char == ")" and partial_cluster_type == PartialClusterType.BEGIN:
                    partial_cluster_type = PartialClusterType.BEGIN_AND_END
                cluster = close_cluster(partial_cluster_type, idx_str)
                if cluster is not None:
                    clusters.append(cluster)

                partial_cluster_type = None
                idx_str = ""
        elif char == "-":
            pass
        else:
            idx_str += char
            if partial_cluster_type is None:
                partial_cluster_type = PartialClusterType.END

    if idx_str != "":
        cluster = close_cluster(partial_cluster_type, idx_str)
        if cluster is not None:
            clusters.append(cluster)

    return clusters


def parse_lines(lines):
    parsed = {}
    all_clusters = defaultdict(list)
    open_clusters = defaultdict(list)
    prev_sent_idx = 0
    tokens_in_doc_before_curr_sent = 0  # Will be used to change token_idx to be per sentence instead of per document
    def get_fixed_token_idx(token_idx, tokens_in_doc_before_curr_sent):
        return token_idx - tokens_in_doc_before_curr_sent - 1  # minus 1 because we later start from 0 not 1


    for line in lines:
        parsed_line = parse_line(line)
        if line is None:
            continue

        if type(parsed_line) == TokenLine:

            sent_changed = prev_sent_idx != parsed_line.sent_idx
            if sent_changed:
                tokens_in_doc_before_curr_sent = parsed_line.token_idx - 1

            curr_token_idx_per_sent = get_fixed_token_idx(parsed_line.token_idx, tokens_in_doc_before_curr_sent)

            curr_sent_idx = parsed_line.sent_idx
            curr_doc_name = parsed_line.doc_id
            mentions = parsed.setdefault(curr_doc_name, defaultdict(list))
            for cluster in parsed_line.clusters:
                if cluster.partial_cluster_type == PartialClusterType.BEGIN_AND_END:
                    mentions_list = mentions[cluster.cluster_idx]
                    mention = Mention(curr_doc_name, curr_sent_idx, curr_token_idx_per_sent, curr_token_idx_per_sent, parsed_line.token, cluster.cluster_idx, COREF_TYPE_EVENTS)
                    mentions_list.append(mention)
                    all_clusters[cluster.cluster_idx].append(mention)
                elif cluster.partial_cluster_type == PartialClusterType.BEGIN:
                    open_clusters[cluster.cluster_idx].append(parsed_line)
                elif cluster.partial_cluster_type == PartialClusterType.END:
                    open_cluster = open_clusters.pop(cluster.cluster_idx)
                    open_cluster.append(parsed_line)

                    token_str = " ".join([line.token for line in open_cluster])

                    mentions_list = mentions[cluster.cluster_idx]
                    mention = Mention(curr_doc_name, curr_sent_idx, get_fixed_token_idx(open_cluster[0].token_idx, tokens_in_doc_before_curr_sent), curr_token_idx_per_sent, token_str, cluster.cluster_idx, COREF_TYPE_EVENTS)
                    mentions_list.append(mention)
                    all_clusters[cluster.cluster_idx].append(mention)

            # If there are open clusters, all the entities in between are part of it
            for open_cluster in open_clusters.values():
                # If it wasn't just added
                if open_cluster[-1] != parsed_line:
                    open_cluster.append(parsed_line)

            prev_sent_idx = parsed_line.sent_idx

    return parsed, all_clusters


if __name__ == "__main__":
    get_coref_clusters(None, [])
