from collections import Counter
from QFSE.Utilities import get_item


def extract_labels(clusters):
    nlp = get_item("spacy")
    cluster_to_label = {}
    for cluster_id, mentions in clusters.items():
        ents_counter = Counter()
        for mention in mentions:
            doc = nlp(mention.token)
            for ent in doc.ents:
                ents_counter[ent.label_] += 1

        if any(ents_counter):
            cluster_label = ents_counter.most_common()[0][0]
            cluster_to_label[cluster_id] = cluster_label
    return cluster_to_label
