

class SuggestedQueriesBase:

    def __init__(self, corpus):
        self.corpus = corpus
        # the number of keywords already returned until now:
        self._keywordsExtracted = []

    def getNextTopSuggestions(self, numKeywordsNeeded):
        suggestions = self._getNextTopSuggestions(len(self._keywordsExtracted), numKeywordsNeeded)
        self._keywordsExtracted.extend(suggestions)
        return suggestions

    def _getNextTopSuggestions(self, extractionStartIndex, numKeywordsNeeded):
        return []

    def getSuggestionAtIndex(self, index):
        # if we didn't extract the suggestion at the index requested, get the suggestions up until that index first:
        if index >= len(self._keywordsExtracted):
            self.getNextTopSuggestions(index - len(self._keywordsExtracted) + 1)
        return self._keywordsExtracted[index]

    def getSuggestionsFromToIndices(self, fromInd, toInd):
        # if we didn't extract the suggestion at the toInd requested, get the suggestions up until that index first:
        if toInd >= len(self._keywordsExtracted):
            self.getNextTopSuggestions(toInd - len(self._keywordsExtracted) + 1)
        return self._keywordsExtracted[fromInd : toInd+1]