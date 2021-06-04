from collections import Counter, defaultdict
from QFSE.Utilities import get_item
from QFSE.models import Cluster


def create_objs(clusters, cluster_type):
    clusters_objs = {}
    nlp = get_item("spacy")
    for cluster_id, mentions in clusters.items():
        ents_counter = Counter()
        labels_to_mentions = defaultdict(list)
        for mention in mentions:
            doc = nlp(mention.token)
            for ent in doc.ents:
                ents_counter[ent.label_] += 1
                labels_to_mentions[ent.label_].append(mention)

        if any(ents_counter):
            cluster_label = ents_counter.most_common()[0][0]
            token_counter = Counter()
            for mention in labels_to_mentions[cluster_label]:
                token_counter[mention.token] += 1
            most_representative_mention = token_counter.most_common()[0][0]
            clusters_objs[cluster_id] = Cluster(cluster_id, cluster_type, mentions, cluster_label, most_representative_mention)

    return clusters_objs
