from sumy.parsers.plaintext import PlaintextParser as SumyPlaintextParser
from sumy.nlp.tokenizers import Tokenizer as SumyTokenizer
from sumy.nlp.stemmers import Stemmer as SumyStemmer
from sumy.summarizers.lex_rank import LexRankSummarizer as SumyLexRankSummarizer
from sumy.summarizers.kl import KLSummarizer as SumyKLSummarizer
from sumy.summarizers.lsa import LsaSummarizer as SumyLsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer as SumyLuhnSummarizer
from sumy.summarizers.sum_basic import SumBasicSummarizer as SumySumBasicSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer as SumyTextRankSummarizer
from sumy.utils import get_stop_words as SumyStopWords

from QFSE.SummarizerClustering import SummarizerClustering

from QFSE.Utilities import isPotentialSummarySentence

ALGORITHM_LEXRANK = 'lexrank'
ALGORITHM_KL = 'kl'
ALGORITHM_LSA = 'lsa'
ALGORITHM_TEXTRANK = 'textrank'
ALGORITHM_LUHN = 'luhn'
ALGORITHM_BASIC = 'basic'

QUERY_DOC_ALIAS = '_QUERY_'

class SummarizerSumy(SummarizerClustering):

    # Inheriting from SummarizerClustering for the query functionality.
    # The generic summary is different.

    def __init__(self, corpus, evaluateOnTheFly=False, algorithm=ALGORITHM_LEXRANK):
        super().__init__(corpus, evaluateOnTheFly=evaluateOnTheFly)

        # notice in usedSentences: The key is the Sentence ID, and the value is either the Sentence object or 'True'
        # when used by the initial generic summary. The value is not actually used.

        self.algorithm = algorithm


    def _initGenericSummarizer(self):
        langauage = "english"
        stemmer = SumyStemmer(langauage)

        if self.algorithm == ALGORITHM_KL:
            summarizer = SumyKLSummarizer(stemmer)
        elif self.algorithm == ALGORITHM_LSA:
            summarizer = SumyLsaSummarizer(stemmer)
        elif self.algorithm == ALGORITHM_TEXTRANK:
            summarizer = SumyTextRankSummarizer(stemmer)
        elif self.algorithm == ALGORITHM_LUHN:
            summarizer = SumyLuhnSummarizer(stemmer)
        elif self.algorithm == ALGORITHM_BASIC:
            summarizer = SumySumBasicSummarizer(stemmer)
        else:
            summarizer = SumyLexRankSummarizer(stemmer)

        summarizer.stop_words = SumyStopWords(langauage)

        return summarizer, langauage

    def _getGenericSummaryText(self, desiredWordCount):
        # Notice that in this function, the Sentence object is internal to the Sumy library.
        # In the rest of this project, the Sentence is the local type. That also why we use corpus.getSentenceIdByText
        # to get the possible ID of the sentence being used. Since the Sumy library may be using a different sentence
        # tokenizer, the sentence segmentation may not match to the one we used, so we may not actually find
        # the ID of the sentence in the corpus.getSentenceIdByText function.

        summarizer, langauage = self._initGenericSummarizer()
        parser = SumyPlaintextParser.from_string(self.corpus.getAllText(), SumyTokenizer(langauage))
        # we must pass a sentence count to Sumy, so we divide the word count specified by 5 to make sure we have enough sentences:
        potentialSummarySentences = summarizer(parser.document, desiredWordCount / 5)
        numWordsInSummary = 0
        finalSummary = []
        for sentence in potentialSummarySentences:
            if isPotentialSummarySentence(sentence._text, len(sentence.words)):
                finalSummary.append(sentence._text)
                numWordsInSummary += len(sentence.words)
                self.usedSentences[self.corpus.getSentenceIdByText(sentence._text)] = True
                if numWordsInSummary >= desiredWordCount:
                    break

        return ' '.join(finalSummary)