from QFSE.SuggestedQueriesBase import SuggestedQueriesBase
import Levenshtein

class SuggestedQueriesTextRank(SuggestedQueriesBase):

    def __init__(self, corpus, summarizerTextRankBased):
        super().__init__(corpus)
        self.possiblePhrasesInOrder = self._initalizeAllPossibleKeyphrase(summarizerTextRankBased.summarySpacyObject)

    def _initalizeAllPossibleKeyphrase(self, summarySpacyObject):
        # Get the possible phrases from the TextRank SpaCy object
        # Uses phrases of upto 3 words, and chooses the longer ones if one is contained by another by one no more than
        # one word
        # input: summarySpacyObject -- the SpaCy object of the corpus
        # output: a list of phrases in order of importance

        possiblePhrases = []
        possiblePhrasesWordLen = []
        for phrase in summarySpacyObject._.phrases:
            phraseText = phrase.text
            phraseWordLen = len(phraseText.split())
            # skip phrases with more than 3 words
            if phraseWordLen > 3:
                continue
            keepNewPhrase = True
            for idx, chosenPhrase in enumerate(possiblePhrases):
                # if the new phrase is one word longer than the prev phrase, and the prev phrase is within the new phrase:
                if phraseWordLen - possiblePhrasesWordLen[idx] == 1 and chosenPhrase in phraseText:
                    # replace with the new longer phrase with the shorter one in its place (so stays in order)
                    possiblePhrases[idx] = phraseText
                    possiblePhrasesWordLen[idx] = phraseWordLen
                    keepNewPhrase = False
                    break
                # if the prev phrase is one word longer than the new phrase, and the new phrase is within the prev phrase:
                elif possiblePhrasesWordLen[idx] - phraseWordLen == 1 and phraseText in chosenPhrase:
                    # don't use this phrase
                    keepNewPhrase = False
                    break

            # keep the new phrase:
            if keepNewPhrase:
                possiblePhrases.append(phraseText)
                possiblePhrasesWordLen.append(phraseWordLen)

        return possiblePhrases

    def _getNextTopSuggestions(self, extractionStartIndex, numKeywordsNeeded):
        return self.possiblePhrasesInOrder[extractionStartIndex : extractionStartIndex + numKeywordsNeeded]