from collections import Counter, defaultdict
from typing import List

from QFSE.Utilities import get_item
from QFSE.models import Cluster


PROPOSITIONS_DEFAULT_CLUSTER = "Statements"
EVENTS_DEFAULT_CLUSTER = "Concepts"
ENTITIES_DEFAULT_CLUSTER = "Entities"
UNCATEGORIZED_ENTITIES_DEFAULT_CLUSTER = "Miscellaneous"

# Note: If you change these also change UI

FACETS_MAP = {
    "GPE": ENTITIES_DEFAULT_CLUSTER,
    "EVENT": ENTITIES_DEFAULT_CLUSTER,
    "ORG": ENTITIES_DEFAULT_CLUSTER,
    "PERSON": ENTITIES_DEFAULT_CLUSTER,
    "DATE": ENTITIES_DEFAULT_CLUSTER,
    "NORP": ENTITIES_DEFAULT_CLUSTER,
    "LOC": ENTITIES_DEFAULT_CLUSTER
}

LABELS_MAP = {
    "GPE": "Location",
    "EVENT": UNCATEGORIZED_ENTITIES_DEFAULT_CLUSTER,
    "ORG": "Organization",
    "PERSON": "Person",
    "DATE": "Date",
    "NORP": "Organization",
    "LOC": "Location"
}


def create_objs(clusters, cluster_type, default_label, default_cluster):
    clusters_objs = {}
    for cluster_id, mentions in clusters.items():
        clusters_objs[cluster_id] = create_cluster_obj(cluster_id, cluster_type, mentions, default_label, default_cluster)

    return clusters_objs


def create_cluster_obj(cluster_id, cluster_type, mentions, default_label, default_facet):
    nlp = get_item("spacy")

    ents_counter = Counter()
    pos_counter = Counter()
    labels_to_mentions = defaultdict(list)
    pos_to_mentions = defaultdict(list)
    unique_sents_ids = set()
    for mention in mentions:
        clean_mention = clean_text(mention.token)

        doc = nlp(mention.token)
        label = "NO_LABEL"
        pos = "NO_LABEL"
        for ent in doc.ents:
            # Only if the whole string is an entity
            if clean_text(ent.text) == clean_mention:
                label = ent.label_

        for token in doc:
            if clean_text(token.text) == clean_mention:
                pos = token.pos_

        ents_counter[label] += 1
        pos_counter[pos] += 1
        labels_to_mentions[label].append(mention)
        pos_to_mentions[pos].append(mention)
        unique_sents_ids.add(f"{mention.doc_id} {mention.sent_idx}")

    most_representative_mention, ner_label = _choose_most_representative_mention(
        mentions, ents_counter, labels_to_mentions)

    cluster_label = LABELS_MAP.get(ner_label, default_label)
    cluster_facet = FACETS_MAP.get(ner_label, default_facet)

    pos_label = None
    if any(pos_counter):
        pos_label = pos_counter.most_common()[0][0]

    return Cluster(cluster_id, cluster_type, mentions, pos_label, cluster_label, cluster_facet,
                   most_representative_mention, len(mentions), len(unique_sents_ids))


def _choose_most_representative_mention(mentions, ents_counter, labels_to_mentions):
    mentions_used_for_representative = mentions
    ner_label = None
    if any(ents_counter):
        ner_label = ents_counter.most_common()[0][0]
        mentions_used_for_representative = labels_to_mentions[ner_label]
    token_counter = Counter()
    for mention in mentions_used_for_representative:
        token_counter[mention.token] += 1
    most_representative_mention = _get_shortest_most_common(token_counter)

    return most_representative_mention, ner_label


def _get_shortest_most_common(counter) -> str:
    """
    From the most common tokens, take the longest, written especially to avoid short propositions without context
    """

    most_common_count = counter.most_common(n=1)[0][1]
    most_commons: List[str] = [token for token, count in counter.items() if count == most_common_count]
    return max(most_commons, key=len)


def clean_text(text):
    return text.lower().replace("the", "").replace("'s", "").strip()
