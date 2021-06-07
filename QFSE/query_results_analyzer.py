from typing import List

from QFSE.models import QueryResult


class QueryResultsAnalyzer:
    def __init__(self):
        self._previous_results: List[QueryResult] = []

    def add_query_results(self, query_result: QueryResult):
        self._previous_results.append(query_result)

    def analyze_repeating(self, query_result: QueryResult):
        previous_sentences = [result_sent.get_text() for previous_result in self._previous_results for result_sent in previous_result.result_sentences]

        for result_sent in query_result.result_sentences:
            if result_sent.get_text() in previous_sentences:
                result_sent.is_first_time_seen = False
