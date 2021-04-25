import json
import logging
from collections import defaultdict
from typing import List, Dict, Tuple
import os

import conllu

from QFSE.Corpus import Corpus
from QFSE.coref.models import DocumentLine, TokenLine, Mention, PartialCluster, PartialClusterType
import re

from QFSE.models import CorefClusters


def convert_corpus_to_coref_input_format(corpus: Corpus, topic_id: str):
    sentences_formatted = []
    token_idx = 1
    for sentence in corpus.allSentences:
        for token in sentence.tokens:
            sentences_formatted.append([sentence.sentIndex, token_idx, token, True])
            token_idx += 1

    topic_idx = 0

    formatted_topics = {
        f"{topic_idx}_{topic_id.replace(' ', '_')}": sentences_formatted
    }

    # with open("formatted_topic.json", "w") as f:
    #     f.write(json.dumps(formatted_topics))

    return formatted_topics


def get_coref_clusters(formatted_topics, corpus):
    path_to_dir = os.getcwd()

    with open(f"{path_to_dir}/data/sample.conll") as f:
        data = f.read()

    # TODO: Call external coref API with `formatted_topics`

    coref_clusters = CorefClusters(*parse_conll_coref_file(data))
    coref_clusters_dict = coref_clusters.to_dict()
    doc_names_to_clusters = coref_clusters_dict['doc_name_to_clusters']
    for document in corpus.documents:
        if document.id in doc_names_to_clusters:
            document_coref_clusters = doc_names_to_clusters[document.id]
            document.coref_clusters = document_coref_clusters
            for coref_cluster in document_coref_clusters.values():
                for mention in coref_cluster:
                    document.sentences[mention['sent_idx']].coref_clusters.append(mention)

    corpus.coref_clusters = coref_clusters_dict['cluster_idx_to_mentions']

    return coref_clusters


def parse_conll_coref_file(data) -> Tuple[Dict[str, List[Mention]], Dict[str, List[Mention]]]:
    lines = data.splitlines()
    parsed, all_clusters = parse_lines(lines)
    return parsed, all_clusters


def parse_line(line):
    items = line.split('\t')
    if line.startswith('#'):
        if line.startswith("#begin document"):
            doc_name = re.findall(".*? .*? (.*)", line)[0]
            return DocumentLine(doc_name, True)
        if line.startswith("#end document"):
            return DocumentLine(None, False)
    elif len(items) == 4:
        doc_id = items[0]
        token_idx = int(items[1])
        token = items[2]
        clusters = parse_clusters(items[3])
        return TokenLine(doc_id, token_idx, token, clusters)
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
        elif char == "_" or char == ")":
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
    mentions = None
    curr_topic_name = None
    curr_doc_name = None
    open_clusters = defaultdict(list)
    curr_sent_idx = -1
    for line in lines:
        parsed_line = parse_line(line)
        if line is None:
            continue

        if curr_topic_name is None:
            if type(parsed_line) == DocumentLine and parsed_line.is_begin_document:
                curr_topic_name = parsed_line.document_name
        else:
            if type(parsed_line) == DocumentLine and not parsed_line.is_begin_document:
                curr_doc_name = None
            elif type(parsed_line) == TokenLine:
                if parsed_line.token_idx == 0:
                    curr_sent_idx += 1
                    curr_doc_name = parsed_line.doc_id
                    mentions = parsed.setdefault(curr_doc_name, defaultdict(list))
                for cluster in parsed_line.clusters:
                    if cluster.partial_cluster_type == PartialClusterType.BEGIN_AND_END:
                        mentions_list = mentions[cluster.cluster_idx]
                        mention = Mention(curr_doc_name, curr_sent_idx, parsed_line.token_idx, parsed_line.token_idx, parsed_line.token, cluster.cluster_idx)
                        mentions_list.append(mention)
                        all_clusters[cluster.cluster_idx].append(mention)
                    elif cluster.partial_cluster_type == PartialClusterType.BEGIN:
                        open_clusters[cluster.cluster_idx].append(parsed_line)
                    elif cluster.partial_cluster_type == PartialClusterType.END:
                        open_cluster = open_clusters.pop(cluster.cluster_idx)
                        open_cluster.append(parsed_line)

                        token_str = " ".join([line.token for line in open_cluster])

                        mentions_list = mentions[cluster.cluster_idx]
                        mention = Mention(curr_doc_name, curr_sent_idx, open_cluster[0].token_idx, parsed_line.token_idx, token_str, cluster.cluster_idx)
                        mentions_list.append(mention)
                        all_clusters[cluster.cluster_idx].append(mention)

                # If there are open clusters, all the entities in between are part of it
                for open_cluster in open_clusters.values():
                    # If it wasn't just added
                    if open_cluster[-1] != parsed_line:
                        open_cluster.append(parsed_line)

    return parsed, all_clusters


if __name__ == "__main__":
    get_coref_clusters(None, [])
