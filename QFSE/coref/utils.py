import json
import logging
import os
import pickle
import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

from nltk import word_tokenize, sent_tokenize

from QFSE.Corpus import Corpus
from QFSE.consts import COREF_TYPE_EVENTS, COREF_TYPE_ENTITIES, MAX_MENTIONS_IN_CLUSTER
from QFSE.coref.coref_expr import get_clusters, parse_doc_id
from QFSE.coref.coref_labels import create_objs, EVENTS_DEFAULT_CLUSTER, \
    UNCATEGORIZED_ENTITIES_DEFAULT_CLUSTER, ENTITIES_DEFAULT_CLUSTER, clean_text
from QFSE.coref.models import DocumentLine, TokenLine, Mention, PartialCluster, PartialClusterType
from QFSE.models import CorefClusters, Cluster
from data.Config import COREF_LOCATIONS


def convert_corpus_to_coref_input_format(corpus: Corpus, topic_id: str):
    docs_formatted = {}
    for doc in corpus.documents:
        token_idx = 1
        sentences_formatted = []

        # # NLTK tokenizer
        # for sent_idx, sentence in enumerate(sent_tokenize(doc.text)):
        # # sentence.first_token_idx = token_idx - 1
        # for token in word_tokenize(sentence):
        #     sentences_formatted.append([sent_idx, token_idx, token, True])
        #     token_idx += 1

        for sentence in doc.sentences:
            sentence.first_token_idx = token_idx - 1
            for token in sentence.tokens:
                sentences_formatted.append([sentence.sentIndex, token_idx, token, True])
                token_idx += 1

        docs_formatted[f"0_{doc.id}"] = sentences_formatted

    # with open(f"{topic_id.replace(' ', '_')}_docs_formatted.json", "w") as f:
    #     f.write(json.dumps(docs_formatted))

    return docs_formatted


def get_coref_clusters(formatted_topics, corpus: Corpus, cluster_type):
    path_to_dir = os.getcwd()

    file_path = COREF_LOCATIONS[corpus.topic_id][cluster_type]

    if cluster_type == COREF_TYPE_EVENTS:
        with open(f"{path_to_dir}/{file_path}") as f:
            data = f.read()
        default_label = EVENTS_DEFAULT_CLUSTER
        default_facet = EVENTS_DEFAULT_CLUSTER
    else:  # if cluster_type == COREF_TYPE_ENTITIES:
        with open(f"{path_to_dir}/{file_path}") as f:
            data = f.read()
        default_label = UNCATEGORIZED_ENTITIES_DEFAULT_CLUSTER
        default_facet = ENTITIES_DEFAULT_CLUSTER

    cache_file_path = f"{path_to_dir}/{file_path}.cache"
    try:
        with open(cache_file_path, "rb") as f:
            documents, clusters_objs = pickle.load(f)
    except:

        # with open(f"{path_to_dir}/data/coref/spacy_wd_coref_duc.json") as f:
        #     data = f.read()
        # with open(f"{path_to_dir}/data/coref/duc_predictions_ments.json") as json_file:
        #     data = json.load(json_file)

        # TODO: Call external coref API with `formatted_topics`

        is_conll_file = file_path.endswith(".conll")

        if is_conll_file:
            documents, clusters = parse_conll_coref_file(data)
        else:
            data = json.loads(data)
            documents, clusters = get_clusters(data, cluster_type)

        clusters_objs = create_objs(clusters, cluster_type, default_label, default_facet)

        with open(cache_file_path, "wb") as f:
            pickle.dump((documents, clusters_objs), f)

    clusters_ids_to_filter = get_clusters_ids_to_filter(clusters_objs)
    clusters_objs = {cluster_id: cluster for cluster_id, cluster in clusters_objs.items() if cluster_id not in clusters_ids_to_filter}
    for cluster_obj in clusters_objs.values():
        _choose_display_name(cluster_obj)

    coref_clusters = CorefClusters(documents, clusters_objs)
    coref_clusters_dict = coref_clusters.to_dict()
    doc_names_to_clusters = coref_clusters_dict['doc_name_to_clusters']
    for document in corpus.documents:
        if document.id in doc_names_to_clusters:
            mentions = doc_names_to_clusters[document.id]
            # document.coref_clusters[cluster_type] = mentions
            if isinstance(mentions, dict):
                mentions = [mention for coref_cluster in mentions.values() for mention in coref_cluster]
            mentions = [mention for mention in mentions if mention['cluster_idx'] not in clusters_ids_to_filter]
            for mention in mentions:
                document.sentences[mention['sent_idx']].coref_clusters[cluster_type].append(mention)

    corpus.coref_clusters[cluster_type] = coref_clusters_dict['cluster_idx_to_mentions']

    return coref_clusters


def get_clusters_ids_to_filter(clusters_objs):
    # Max mentions
    clusters_ids_to_filter = [cluster_idx for cluster_idx, cluster in clusters_objs.items() if cluster.num_mentions > MAX_MENTIONS_IN_CLUSTER]

    # Singletons
    clusters_ids_to_filter += [cluster_idx for cluster_idx, cluster in clusters_objs.items() if cluster.num_mentions == 1 or cluster.num_sents == 1]

    # Verbs
    clusters_ids_to_filter += [cluster_idx for cluster_idx, cluster in clusters_objs.items() if cluster.pos_label == "VERB"]

    # Noisy values (only 2 letters like "`s" or "QL")
    clusters_ids_to_filter += [cluster_idx for cluster_idx, cluster in clusters_objs.items() if len(cluster.display_name) <= 2]

    clusters_ids_to_filter += merge_repeating_clusters(clusters_objs)

    return clusters_ids_to_filter


def merge_repeating_clusters(clusters_objs):
    """
    Merges clusters (because we want to present the user with generic, and let the user go to specific by faceted-navigation)
    """

    clusters_ids_to_filter = []

    clusters_seen = {}
    for cluster_idx, cluster_obj in sorted(clusters_objs.items(), key=lambda item: item[1].num_mentions, reverse=True):
        cluster_key = cluster_obj.display_name.lower()
        cluster_key_cleaned = clean_text(cluster_key)
        if cluster_key_cleaned not in clusters_seen:
            clusters_seen[cluster_key_cleaned] = cluster_obj
        else:
            clusters_ids_to_filter.append(cluster_idx)
            _merge_clusters(clusters_seen[cluster_key_cleaned], cluster_obj)

    return clusters_ids_to_filter


def _choose_display_name(cluster: Cluster) -> None:
    """
    After all the merging, recalculate the display name
    """

    token_counter = Counter()
    for mention in cluster.mentions:
        token_counter[mention.token] += 1

    cluster.display_name = token_counter.most_common()[0][0]


def _merge_clusters(cluster_kept: Cluster, cluster_merged: Cluster):
    cluster_kept.num_mentions += cluster_merged.num_mentions
    cluster_kept.num_sents += cluster_merged.num_sents
    cluster_kept.mentions += cluster_merged.mentions


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
    elif len(items) == 8:
        topic_id, doc_id = parse_doc_id(items[2])
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
                    # Bug - skip clusters encapsulating the same cluster (13|(13...13)..13)
                    if cluster.cluster_idx not in open_clusters:
                        mentions_list = mentions[cluster.cluster_idx]
                        mention = Mention(curr_doc_name, curr_sent_idx, curr_token_idx_per_sent, curr_token_idx_per_sent, parsed_line.token, cluster.cluster_idx, COREF_TYPE_EVENTS)
                        mentions_list.append(mention)
                        all_clusters[cluster.cluster_idx].append(mention)
                elif cluster.partial_cluster_type == PartialClusterType.BEGIN:
                    # Bug - skip clusters encapsulating the same cluster (13|(13...13)..13)
                    if cluster.cluster_idx not in open_clusters:
                        open_clusters[cluster.cluster_idx].append(parsed_line)
                elif cluster.partial_cluster_type == PartialClusterType.END:
                    # Bug - can happen because we skip clusters encapsulating the same cluster (13|(13...13)..13)
                    if cluster.cluster_idx in open_clusters:
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
