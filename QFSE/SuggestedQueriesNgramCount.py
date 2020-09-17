from QFSE.SuggestedQueriesBase import SuggestedQueriesBase
import Levenshtein

class SuggestedQueriesNgramCount(SuggestedQueriesBase):

    def __init__(self, corpus):
        super().__init__(corpus)

    def _getNextTopSuggestions(self, extractionStartIndex, numKeywordsNeeded):
        # get the next numKeywords keywords (not already sent):
        # wordsToReturn = self.wordCounter.most_common(self._numKeywordsExtracted + numKeywordsNeeded)[
        #                self._numKeywordsExtracted:]
        # wordsToReturn = self._bigramCounter.most_common(self._numKeywordsExtracted + numKeywordsNeeded)[
        #                self._numKeywordsExtracted:]

        potentialWords = self.corpus.ngramCounter.most_common()[extractionStartIndex:]
        curOptionInd = 0
        wordsToReturn = []
        while len(wordsToReturn) < numKeywordsNeeded and curOptionInd < len(potentialWords):
            curPotentialWord = potentialWords[curOptionInd][0]
            if self._isNearDuplicate(wordsToReturn, curPotentialWord) < 0:
                wordsToReturn.append(curPotentialWord)
            curOptionInd += 1

        # return [word for word, frequency in wordsToReturn]
        return wordsToReturn

    def _isNearDuplicate(self, stringList, newString, distance=2):
        for sInd, s in enumerate(stringList):
            if Levenshtein.distance(s, newString) <= distance:
                return sInd
        return -1