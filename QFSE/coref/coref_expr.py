from typing import Tuple, Dict, List

from QFSE.coref.models import Mention


def get_clusters(data) -> Tuple[Dict[str, List[Mention]], Dict[int, List[Mention]]]:
    clusters = dict()
    document = dict()
    for ment in data:
        doc_id = ment['doc_id'][ment['doc_id'].index("_")+1:]
        doc_num_id = ment['doc_id'].split("_")[1]
        cluster_id = int(doc_num_id + ment['coref_chain'])
        tok_star = int(ment['tokens_number'][0])
        tok_end = int(ment['tokens_number'][-1])
        if tok_end - tok_star < 5:
            if doc_id not in document:
                document[doc_id] = list()
            if cluster_id not in clusters:
                clusters[cluster_id] = list()
            ment_obj = Mention(doc_id, int(ment['sent_id']), tok_star, tok_end,
                               ment['tokens_str'], cluster_id)

            document[doc_id].append(ment_obj)
            clusters[cluster_id].append(ment_obj)

    return document, clusters
