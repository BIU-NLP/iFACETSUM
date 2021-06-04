from QFSE.Sentence import Sentence
from collections import defaultdict
import operator
from sklearn import cluster
import numpy as np
from sklearn.decomposition import PCA
from QFSE.SummarizerBase import SummarizerBase
from QFSE.Utilities import isPotentialSentence

QUERY_DOC_ALIAS = '_QUERY_'
REDUNDANCY_THRESHOLD = 0.95

class SummarizerClustering(SummarizerBase):

    def __init__(self, corpus, evaluateOnTheFly=False):
        super().__init__(corpus, evaluateOnTheFly=evaluateOnTheFly)

        # A dictionary of pairs of Sentence IDs (symettrical) with the similarity score between them,
        # this is to save time computing it when needed again.
        self.sentencesSimilarities = defaultdict(lambda: {})
        # the following will be initialized in the _getGenericSummaryText call
        self.sentenceClusters = {} # dict { clusterLabel -> [listOfSentencesInCluster] }
        self.sentenceClusterLabelsOrdered = [] # order list of clusters to use
        self.sentenceClusterIndexLast = -1 # the last index used in sentenceClusterLabelsOrdered

    def _getGenericSummaryText(self, desiredWordCount):
        # The algorithm here is:
        #   PCA on each of the sentences' average word w2v vectors
        #   K-means to clusters on the reduced-sized vectors
        #   Take the best representative sentence from the largest clusters until max word count is reached

        # reduce the dimensionality of the vectors (from 300(w2v)/768(bert) to 20), since high dimensionality vectors are tough on K-Means:
        pca = PCA(n_components=20, random_state=0)
        vectors = [sent.representation for sent in self.allSentencesForPotentialSummaries]
        pca.fit(vectors)
        reducedVectors = pca.transform(vectors)

        # cluster the sentences by their reduced representation embeddings:
        k_means = cluster.KMeans(n_clusters=30, random_state=0)
        #vectorToSentence = {str(sent.spacyDoc.vector):sent for sent in corpus.allSentences}
        k_means.fit(reducedVectors)
        # count the number of sentences in each cluster:
        labels, labelCounts = np.unique(k_means.labels_[k_means.labels_ >= 0], return_counts=True)

        # group together the indices of the sentences that were labeled into the same cluster:
        self.sentenceClusters = defaultdict(lambda : []) # { labelOfCluster -> [list of sentence indices] }
        for idx, label in enumerate(k_means.labels_):
            self.sentenceClusters[label].append(idx)

        # keep the order of the labels that the clusters should be used:
        self.sentenceClusterLabelsOrdered = labels[np.argsort(-labelCounts)]
        self.sentenceClusterIndexLast = -1

        # concatenate sentences until the the word limit is up:
        finalSummaryTxtList, finalSummaryIds, numWordsInSummary = self._getNextGeneralSentences(desiredWordCount)

        if len(finalSummaryTxtList) == 0:
            finalSummaryTxtList = ['NO INFORMATION TO SHOW.']
            finalSummaryIds = []

        return finalSummaryTxtList, finalSummaryIds, numWordsInSummary

    def _getNextGeneralSentences(self, desiredWordCount):
        # concatenate sentences until the the word limit is up:
        numWordsInSummary = 0
        finalSummaryTxtList = []
        finalSummaryIds = []
        while numWordsInSummary < desiredWordCount and not self._noMoreSentences():
            # get the next index to use in the sentenceClusterLabelsOrdered list (loop back to the beginning):
            self.sentenceClusterIndexLast = (self.sentenceClusterIndexLast + 1) % len(self.sentenceClusterLabelsOrdered)
            # get the index of the cluster to use now:
            curClusterLabel = self.sentenceClusterLabelsOrdered[self.sentenceClusterIndexLast]
            # get the best sentence in that cluster:
            bestSentenceInCluster = self._getBestSentence(self.allSentencesForPotentialSummaries,
                                                          self.sentenceClusters[curClusterLabel], self.corpus)
            # append the chosen sentence to the summary:
            if bestSentenceInCluster != None:
                finalSummaryTxtList.append(bestSentenceInCluster.text)
                finalSummaryIds.append(bestSentenceInCluster.sentId)
                numWordsInSummary += len(bestSentenceInCluster)
                self.usedSentences[bestSentenceInCluster.sentId] = bestSentenceInCluster
                self.usedSentencesText[bestSentenceInCluster.textCompressed] = bestSentenceInCluster.sentId

        return finalSummaryTxtList, finalSummaryIds, numWordsInSummary

    def _getBestSentence(self, allSentencesList, possibleIndicesOfSentences, corpus):
        # gets the highest scoring sentence in the possible sentences in reference to the corpus given
        bestSentence = None
        bestSentScore = -1
        for idx in possibleIndicesOfSentences:
            sentence = allSentencesList[idx]
            if sentence.sentId not in self.usedSentences and sentence.textCompressed not in self.usedSentencesText:  # skip sentences that were already used
                sentScore = self._getSentenceScore(sentence, self.corpus.wordCounter)
                if sentScore > bestSentScore:
                    bestSentence = sentence
                    bestSentScore = sentScore
        return bestSentence

    def _getSentenceScore(self, sentence, corpusWordCounter):
        # the score is the average word weight in the sentence
        # where word weight is the number of times the word appears in the corpus
        sentenceWordWeightTotal = 0
        for token in sentence.tokens:
            sentenceWordWeightTotal += corpusWordCounter[token.lower()]
        sentenceWordWeightAvg = float(sentenceWordWeightTotal) / len(sentence)
        return sentenceWordWeightAvg

        ##numEntities = len(sentence.spacyDoc.ents)
        #numSignificantWords = float(sentence.spacyDoc._.num_significant_words)
        #sentLen = float(len(sentence.spacyDoc))
        #return (numSignificantWords / sentLen) * log(sentLen)


    def _getQuerySummaryText(self, query, numSentencesNeeded, sentences):
        # The algorithm here is:
        #   Spacy-vectorize the query
        #   Get the similarity of the query to each of the potential sentences in the corpus
        #   Take the most similar sentences to the query as long as it isn't redundant to the sentences already added
        #       (and not sentences in previous summaries)

        if self._noMoreSentences():
            return ["NO MORE INFORMATION."], [], 0

        if query == '':
            finalSummaryTxtList, finalSummaryIds, numWordsInSummary = self._getNextGeneralSentences(numSentencesNeeded * 20)
            return finalSummaryTxtList, finalSummaryIds, numWordsInSummary


        # make a sentence object for the query:
        queryAsSentence = Sentence(QUERY_DOC_ALIAS, len(self.queries), query, self.corpus.representationStyle)

        # get an ordered list of sentences by similarity to the query:
        similaritiesToQuery = [(sentence, queryAsSentence.similarity(sentence))
                               for sentence in self.allSentencesForPotentialSummaries]
        similaritiesToQuery.sort(key=operator.itemgetter(1), reverse=True)

        # keep taking most query-similar, non-redundant sentences until we have enough:
        sentencesUsing = []
        for sentence, _ in similaritiesToQuery:
            if sentence.sentId not in self.usedSentences and sentence.textCompressed not in self.usedSentencesText and not self._isRedundant(sentence, sentencesUsing):
                sentencesUsing.append(sentence)
                self.usedSentences[sentence.sentId] = sentence
                self.usedSentencesText[sentence.textCompressed] = sentence.sentId
                if len(sentencesUsing) == numSentencesNeeded:
                    break

        # return also the length in words of the returned summary:
        summaryLength = sum(len(sent) for sent in sentencesUsing)

        return [sent.text for sent in sentencesUsing], [sent.sentId for sent in sentencesUsing], summaryLength

    def _isRedundant(self, sentence, otherSentences):
        # check if the sentence is too similar to the other sentences:
        for otherSentence in otherSentences:
            # see if we know the similarities already from before:
            if not sentence.sentId in self.sentencesSimilarities or not otherSentence.sentId in self.sentencesSimilarities[sentence.sentId]:
                sim = sentence.similarity(otherSentence)
                self.sentencesSimilarities[sentence.sentId][otherSentence.sentId] = sim
                self.sentencesSimilarities[otherSentence.sentId][sentence.sentId] = sim

            if self.sentencesSimilarities[sentence.sentId][otherSentence.sentId] > REDUNDANCY_THRESHOLD:
                return True

        return False

    def _isPotentialSentence(self, sentence):
        return isPotentialSentence(sentence)

    def _noMoreSentences(self):
        return len(self.usedSentences) == len(self.allSentencesForPotentialSummaries)