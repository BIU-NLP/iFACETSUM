from typing import Optional, List, Dict, Set

from QFSE.models import ClusterQuery, QueryResult


class QueryRegistry:
    def __init__(self):
        self._registry: List[QueryResult] = []

    def get_query(self, clusters_query: List[ClusterQuery]) -> Optional[QueryResult]:
        for prev_result in self._registry:
            if set(clusters_query) == set(prev_result.query):
                return prev_result

    def save_query(self, query_result: QueryResult):
        self._registry.append(query_result)
