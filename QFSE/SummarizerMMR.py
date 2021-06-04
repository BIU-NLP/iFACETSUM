from QFSE.Sentence import Sentence
from collections import defaultdict
import operator
from sklearn import cluster
import numpy as np
from sklearn.decomposition import PCA
from QFSE.SummarizerBase import SummarizerBase
from QFSE.Utilities import isPotentialSentence

import math

QUERY_DOC_ALIAS = '_QUERY_'
REDUNDANCY_THRESHOLD = 0.95

#import ipdb



## MMR implementation following https://github.com/vishnu45/NLP-Extractive-NEWS-summarization-using-MMR/blob/master/mmr_summarizer.py


def _TFs(sentences):
    """ Function to find the TF score of the words in the document cluster
    Inputs:
        sentences: sentences of the document cluster
    Outputs:
        tfWords: dictionary of words, TF score
    """
    tfWords = {}
    for sent in sentences:
        for word in sent.tokens:
            word = word.lower()
            tfWords[word] = tfWords.get(word, 0) + 1

    return tfWords



def _IDFs(corpus):
    """ Function to find the IDF score of the words in the document cluster
    Inputs:
        sentences: sentences of the document cluster
    Outputs:
        idfWords: dictionary of words, IDF score
    """
    N = len(corpus.documents)
    idfWords = {}

    all_words = []
    for doc in corpus.documents:
        all_words.extend(doc.tfs.keys())

    for word in all_words:
        n = 0
        for doc in corpus.documents:
            n += doc.tfs.get(word,0)
        try:
            idf = math.log10(float(N)/n)
        except ZeroDivisionError:
            idf = 0
        idfWords[word] = idf


    return idfWords



def _TFIDFs(sentences):
    """ Function to find the TF-IDF score of the words in the document cluster
    Inputs:
        sentences: sentences of the document cluster
    Outputs:
        tfidfWords: dictionary of words, TF-IDF score
    """
    tfWords = _TFs(sentences)
    idfWords = _IDFs(sentences)
    tfidfWords = {}

    for word in tfs:
        tfidfScore = tfWords[word] * idfWords[word]

        if tfidfWords.get(tfidfScore, None) == None:
            tfidfWords[tfidfScore] = [word]
        else:
            tfidfWords[tfidfScore].append(word)

    return tfidfWords


def MMRScore(sentence, query, summary, lambta=0.5):
    """ Function to calculate the MMR score given a sentence, the query, 
    and the current best set of sentences
    Inputs:
        sentence: sentence for which MMR score has to be calculated
        query: query sentence for the document cluster
        summary: list of sentences in the current summary
        lambta: MMR score hyperparameter
    Outputs:
        score: MMR score for the given sentence
        sim1: similarity score between sentene and query
        sim2: best similarity score w.r.t. summary so far
    """
    sim1 = sentence.similarity(query)
    l_expr = lambta * sim1
    value = [float("-inf")]

    for sent in summary:
        sim2 = sentence.similarity(sent)
        value.append(sim2)

    sim2 = max(value)

    r_expr = (1-lambta) * sim2
    score = l_expr - r_expr	

    return score, sim1, sim2


class SummarizerMMR(SummarizerBase):
 
    def __init__(self, corpus, evaluateOnTheFly=False):
        super().__init__(corpus, evaluateOnTheFly=evaluateOnTheFly)

        # A dictionary of pairs of Sentence IDs (symettrical) with the similarity score between them,
        # this is to save time computing it when needed again.
        self.sentencesSimilarities = defaultdict(lambda: {})
        # the following will be initialized in the _getGenericSummaryText call
        self.sentenceClusters = {} # dict { clusterLabel -> [listOfSentencesInCluster] }
        self.sentenceClusterLabelsOrdered = [] # order list of clusters to use
        self.sentenceClusterIndexLast = -1 # the last index used in sentenceClusterLabelsOrdered
        self.isGenericClustering = False

    def _getGenericSummaryText(self, desiredWordCount):
                
        if self.isGenericClustering:
            self.sentenceClusters, self.sentenceClusterLabelsOrdered = self._prepareForClustering()
            self.sentenceClusterIndexLast = -1

        else:
            self._prepareForMMR()


        # concatenate sentences until the the word limit is up:
        finalSummaryTxtList, finalSummaryIds, numWordsInSummary = self._getNextGeneralSentences(desiredWordCount)

        if len(finalSummaryTxtList) == 0:
            finalSummaryTxtList = ['NO INFORMATION TO SHOW.']
            finalSummaryIds = []

        return finalSummaryTxtList, finalSummaryIds, numWordsInSummary

    
    def _prepareForMMR(self):
        # this code prepare for MMR by calculating the tfs, tf-idfs for each document words
        # there by calculating the tf-idfs. This is usefuly to build the initial query
        
        ## add tfs for each document
        for doc in self.corpus.documents:
            tfs = _TFs(doc.sentences)
            doc.tfs = tfs

        ## get idfs of each word:
        idfs = _IDFs(self.corpus)

        ## get tf-idf for each word in a document:
        tfidfs = {}
        for doc in self.corpus.documents:
            for word,value in doc.tfs.items():
                tfidfs[word] = value * idfs[word]
            doc.tfidfs = tfidfs


    def _prepareForClustering(self):
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
        sentenceClusters = defaultdict(lambda : []) # { labelOfCluster -> [list of sentence indices] }
        for idx, label in enumerate(k_means.labels_):
            sentenceClusters[label].append(idx)

        # keep the order of the labels that the clusters should be used:
        sentenceClusterLabelsOrdered = labels[np.argsort(-labelCounts)]

        return sentenceClusters, sentenceClusterLabelsOrdered


    def _getNextGeneralSentences(self, desiredWordCount):
        # concatenate sentences until the the word limit is up:
        numWordsInSummary = 0
        finalSummaryTxtList = []
        finalSummaryIds = []
        if self.isGenericClustering:
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

        else:
            # now create MMR-based generic summary
            topWords = self._findTopWords()
            queryAsSentence = Sentence(QUERY_DOC_ALIAS, len(self.queries), " ".join(topWords), self.corpus.representationStyle)

            # get an ordered list of sentences based on its MMR score:
            lambta = 0.5
            usedSentencesList = []
            sentenceMMRScores = [(sentence,) + MMRScore(sentence, queryAsSentence, usedSentencesList, lambta)  # [(sent, mmrscore, sim1, sim2)]
                                    for sentence in self.allSentencesForPotentialSummaries] 
            sentencesUsing = []
            while numWordsInSummary < desiredWordCount and not self._noMoreSentences():
                if len(sentencesUsing)>0:
                    ## take the last added sentence and update the mmr score for the rest of the sentenes
                    for index, sentMMR in enumerate(sentenceMMRScores):
                        newSim2 = sentMMR[0].similarity(sentencesUsing[-1])
                        if newSim2 > sentMMR[3]:
                            mmrScore = lambta*sentMMR[2] - (1-lambta)*newSim2
                            sentenceMMRScores[index] = (sentMMR[0], mmrScore, sentMMR[2], newSim2)
                    
                sentenceMMRScores.sort(key=operator.itemgetter(1), reverse=True)
                # keep taking most query-similar, non-redundant sentences until we have enough:
                for index, (sentence,_,_,_) in enumerate(sentenceMMRScores):
                    if sentence.sentId not in self.usedSentences and sentence.textCompressed not in self.usedSentencesText:
                        sentencesUsing.append(sentence)
                        finalSummaryTxtList.append(sentence.text)
                        finalSummaryIds.append(sentence.sentId)
                        numWordsInSummary += len(sentence)
                        self.usedSentences[sentence.sentId] = sentence
                        self.usedSentencesText[sentence.textCompressed] = sentence.sentId
                        sentenceMMRScores.pop(index)
                        break

        return finalSummaryTxtList, finalSummaryIds, numWordsInSummary


    def _findTopWords(self, max_num=20):
        ## give a list of top frequent words based on tf-idf scores
        top_k_words = []
        for doc in self.corpus.documents:
            top_k_words.extend([(word, doc.tfidfs[word]) for word in sorted(doc.tfidfs, key=doc.tfidfs.__getitem__, reverse=True)[:max_num]])

        unique_ranked_words = []
        top_k_words = sorted(top_k_words, key=lambda x:x[1], reverse=True)
        for word,score in top_k_words:
            if word in unique_ranked_words:
                continue
            else:
                unique_ranked_words.append(word)

        return unique_ranked_words[:max_num]

        
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

        # get an ordered list of sentences based on its MMR score:
        lambta = 0.5
        usedSentencesList = [v for k,v in self.usedSentences.items()]
        sentenceMMRScores = [(sentence,) + MMRScore(sentence, queryAsSentence, usedSentencesList, lambta)  # [(sent, mmrscore, sim1, sim2)]
                                for sentence in self.allSentencesForPotentialSummaries] 
        sentencesUsing = []
        while(len(sentencesUsing)<=numSentencesNeeded):
            if len(sentencesUsing)>0:
                ## take the last added sentence and update the mmr score for the rest of the sentenes
                for index, sentMMR in enumerate(sentenceMMRScores):
                    newSim2 = sentMMR[0].similarity(sentencesUsing[-1])
                    if newSim2 > sentMMR[3]:
                        mmrScore = lambta*sentMMR[2] - (1-lambta)*newSim2
                        sentenceMMRScores[index] = (sentMMR[0], mmrScore, sentMMR[2], newSim2)
                
            sentenceMMRScores.sort(key=operator.itemgetter(1), reverse=True)
            # keep taking most query-similar, non-redundant sentences until we have enough:
            for index, (sentence,_,_,_) in enumerate(sentenceMMRScores):
                if sentence.sentId not in self.usedSentences and sentence.textCompressed not in self.usedSentencesText:
                    sentencesUsing.append(sentence)
                    self.usedSentences[sentence.sentId] = sentence
                    self.usedSentencesText[sentence.textCompressed] = sentence.sentId
                    sentenceMMRScores.pop(index)
                    break

        # return also the length in words of the returned summary:
        summaryLength = sum(len(sent) for sent in sentencesUsing)

        return [sent.text for sent in sentencesUsing], [sent.sentId for sent in sentencesUsing], summaryLength


    def _isRedundant(self, sentence, otherSentences):
        # check if the sentence is too similar to the other sentences:
        for otherSentence in otherSentences:
            # see if we know the similarities already from before:
            if not sentence.sentId in self.sentencesSimilarities or not otherSentence.sentId in self.sentencesSimilarities[sentence.sentId] and not self._isRedundant(sentence, sentencesUsing):
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
