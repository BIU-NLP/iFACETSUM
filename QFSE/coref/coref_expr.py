from typing import Tuple, Dict, List

from QFSE.coref.models import Mention


def get_clusters(data, cluster_type) -> Tuple[Dict[str, List[Mention]], Dict[int, List[Mention]]]:
    clusters = dict()
    for ment in data:
        topic_id, doc_id = parse_doc_id(ment['doc_id'])
        cluster_id = int(ment['coref_chain'])
        tok_star = int(ment['tokens_number'][0])
        tok_end = int(ment['tokens_number'][-1])
        ment_obj = Mention(doc_id, int(ment['sent_id']), tok_star, tok_end,
                           ment['tokens_str'], cluster_id, cluster_type)

        if cluster_id not in clusters:
            clusters[cluster_id] = list()

        clusters[cluster_id].append(ment_obj)

    singletons = [c_id for c_id, c in clusters.items() if len(c) < 2]
    for singleton_cluster_id in singletons:
        clusters.pop(singleton_cluster_id)

    # Create documents only after filtering clusters
    documents = dict()
    for mentions in clusters.values():
        for mention in mentions:
            if mention.doc_id not in documents:
                documents[mention.doc_id] = list()

            documents[mention.doc_id].append(mention)

    return documents, clusters


def parse_doc_id(doc_id):
    row_id_splitted = doc_id.split("_")
    topic_id = row_id_splitted[0]
    doc_id = "_".join(row_id_splitted[2:])  # Remove both topic id and document id

    return topic_id, doc_id
