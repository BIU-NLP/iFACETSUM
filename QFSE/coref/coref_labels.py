from collections import Counter, defaultdict
from QFSE.Utilities import get_item
from QFSE.models import Cluster


PROPOSITIONS_DEFAULT_CLUSTER = "Key statements"
EVENTS_DEFAULT_CLUSTER = "Key concepts"
ENTITIES_DEFAULT_CLUSTER = "Miscellaneous"

# Note: If you change these also change UI

LABELS_MAP = {
    "GPE": "Location",
    "EVENT": ENTITIES_DEFAULT_CLUSTER,
    "ORG": "Organization",
    "PERSON": "Person",
    "DATE": "Date",
    "NORP": "Nationality, Religious, Political",
    "LOC": "Location"
}


def create_objs(clusters, cluster_type, default_cluster):
    clusters_objs = {}
    for cluster_id, mentions in clusters.items():
        clusters_objs[cluster_id] = create_cluster_obj(cluster_id, cluster_type, mentions, default_cluster)

    return clusters_objs


def create_cluster_obj(cluster_id, cluster_type, mentions, default_cluster):
    nlp = get_item("spacy")

    ents_counter = Counter()
    labels_to_mentions = defaultdict(list)
    for mention in mentions:
        doc = nlp(mention.token)
        label = "NO_LABEL"
        for ent in doc.ents:
            # Only if the whole string is an entity
            if clean_text(ent.text) == clean_text(mention.token):
                label = ent.label_
        ents_counter[label] += 1
        labels_to_mentions[label].append(mention)

    mentions_used_for_representative = mentions
    cluster_label = None
    if any(ents_counter):
        cluster_label = ents_counter.most_common()[0][0]
        mentions_used_for_representative = labels_to_mentions[cluster_label]
    token_counter = Counter()
    for mention in mentions_used_for_representative:
        token_counter[mention.token] += 1
    most_representative_mention = token_counter.most_common()[0][0]
    cluster_label = LABELS_MAP.get(cluster_label, default_cluster)
    return Cluster(cluster_id, cluster_type, mentions, cluster_label, most_representative_mention, len(mentions))


def clean_text(text):
    return text.lower().replace("the", "").strip()
