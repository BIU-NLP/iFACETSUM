from QFSE.SummarizerClustering import SummarizerClustering

class SummarizerAddMore(SummarizerClustering):
    # Inheriting from SummarizerClustering, since the only difference is in the query expansions,
    # not in the initial summary logic.

    def __init__(self, corpus, evaluateOnTheFly=False):
        super().__init__(corpus, evaluateOnTheFly=evaluateOnTheFly)

    def _getQuerySummaryText(self, query, numSentencesNeeded, sentences):
        # the query is ignored, as we simply add the next best sentence each time.

        if self._noMoreSentences():
            return ["NO MORE INFORMATION."], [], 0

        finalSummaryTxtList, finalSummaryIds, numWordsInSummary = self._getNextGeneralSentences(numSentencesNeeded * 20)
        return finalSummaryTxtList, finalSummaryIds, numWordsInSummary