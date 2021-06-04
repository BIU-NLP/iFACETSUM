from typing import List

import matplotlib.pyplot as plt
import logging
import time
import threading

from QFSE.Utilities import sent_id_to_doc_id, sent_id_to_sent_idx
from QFSE.models import Summary, SummarySent


class SummarizerBase:

    def __init__(self, corpus, evaluateOnTheFly=False):
        self.corpus = corpus
        # keep a list of the sentences to potentially use (i.e. filter out unwanted sentences):
        self.allSentencesForPotentialSummaries = [sentence for sentence in corpus.allSentences if
                                                  self._isPotentialSentence(sentence)]
        # the query strings used until now
        self.queries = []
        # The sentences we already used until any given moment. The key is the Sentence ID, and the value is the Sentence
        self.usedSentences = {}
        self.usedSentencesText = {} # lowercase compressed version of the used sentences
        # the summaries returned, kept as lists of Sentence IDs (the first is the initial summary, and the rest are per query):
        self.summaries = [] # list of lists of sentenceIds
        self.summariesRating = [] # list of ratings per summary (0 to 1) -- if -1, then unset
        # keep track of the rouge scores after each operation:
        self.rougeScores = []  # list of tuples (wordLength, rougeScores)
        # should the ROUGE be calculated at each summary generation
        self.evaluateOnTheFly = evaluateOnTheFly

        self.haveChanges = False

    def _isPotentialSentence(self, sentence):
        # this should be overridden by the inheriting classes
        return False

    def summarizeGeneric(self, desiredWordCount) -> Summary:
        summaryTextList, summarySentenceIdsList, summaryLengthInWords = self._getGenericSummaryText(desiredWordCount)
        if len(summarySentenceIdsList) > 0:
            self.summaries.append(summarySentenceIdsList)
            self.summariesRating.append(-1)

        if self.evaluateOnTheFly:
            # run a thread that calculates the ROUGE of the accumulated summary until now:
            threadCalculateRouge = threading.Thread(target=self._keepRougeCurrent, args=())
            threadCalculateRouge.start()
        self.haveChanges = True
        summary_sents = [SummarySent(sent_id_to_doc_id(sent_id), sent_id, sent_id_to_sent_idx(sent_id), sent) for (sent_id, sent) in zip(summarySentenceIdsList, summaryTextList)]
        return Summary(summary_sents, summaryLengthInWords)

    def _getGenericSummaryText(self, desiredWordCount):
        # this should be overridden by the inheriting classes
        return '', [], 0

    def summarizeByQuery(self, query, numSentencesNeeded, queryType, sentences=None) -> Summary:
        summaryTextList, summarySentenceIdsList, summaryLengthInWords = self._getQuerySummaryText(query, numSentencesNeeded, sentences)
        #if len(summarySentenceIdsList) > 0:
        # even if the summary is empty, keep it (otherwise there is a sync bug between the iteration and the summaries):
        self.summaries.append(summarySentenceIdsList)
        self.summariesRating.append(-1)

        self.queries.append((query, queryType, time.time()))

        if self.evaluateOnTheFly:
            # run a thread that calculates the ROUGE of the accumulated summary until now:
            threadCalculateRouge = threading.Thread(target=self._keepRougeCurrent, args=())
            threadCalculateRouge.start()
        self.haveChanges = True
        summary_sents = [SummarySent(sent_id_to_doc_id(sent_id), sent_id, sent_id_to_sent_idx(sent_id), sent) for (sent_id, sent) in zip(summarySentenceIdsList, summaryTextList)]
        return Summary(summary_sents, summaryLengthInWords)

    def _getQuerySummaryText(self, query, numSentencesNeeded, sentences):
        # this should be overridden by the inheriting classes
        return '', [], 0

    def _keepRougeCurrent(self):
        logging.info('Computing ROUGE...')
        allTextSoFar = '\n'.join(sentence.text for sentence in self.usedSentences.values())
        allTextNumWords = sum([len(sentence) for sentence in self.usedSentences.values()])
        results = evaluation.RougeEvaluator.getRougeScores(allTextSoFar, self.corpus.referenceSummariesDirectory)
        self.rougeScores.append((allTextNumWords, results))
        self.haveChanges = True


    def _keepRougeAll(self):
        textSoFar = ''
        numWordsSoFar = 0
        for summaryIdx, summary in enumerate(self.summaries):
            textSoFar += '\n'.join(self.usedSentences[sentId].text for sentId in summary)
            numWordsSoFar += sum([len(self.usedSentences[sentId]) for sentId in summary])
            # only calcualte ROUGE for the accumulated summaries not yet evaluated:
            if len(self.rougeScores) <= summaryIdx:
                results = evaluation.RougeEvaluator.getRougeScores(textSoFar, self.corpus.referenceSummariesDirectory)
                self.rougeScores.append((numWordsSoFar, results))
        self.haveChanges = True


    def plotRougeCurves(self):
        if not self.evaluateOnTheFly:
            self._keepRougeAll()

        fig = plt.figure()
        ax = plt.axes()
        ax.set(ylim=(0, 1),
               xlabel='Word Count', ylabel='ROUGE Score',
               title='Incremental Gain per Operation')

        X = []
        Y_R1_Recall = []
        Y_R2_Recall = []
        Y_RL_Recall = []
        Y_R1_Prec = []
        Y_R2_Prec = []
        Y_RL_Prec = []
        Y_R1_F1 = []
        Y_R2_F1 = []
        Y_RL_F1 = []
        for numWords, results in self.rougeScores:
            X.append(numWords)
            Y_R1_Recall.append(results['R1']['recall'])
            Y_R2_Recall.append(results['R2']['recall'])
            Y_RL_Recall.append(results['RL']['recall'])
            Y_R1_Prec.append(results['R1']['precision'])
            Y_R2_Prec.append(results['R2']['precision'])
            Y_RL_Prec.append(results['RL']['precision'])
            Y_R1_F1.append(results['R1']['f1'])
            Y_R2_F1.append(results['R2']['f1'])
            Y_RL_F1.append(results['RL']['f1'])

        plt.plot(X, Y_R1_Recall, '-b', label='R1_rec')
        plt.plot(X, Y_R2_Recall, '-g', label='R2_rec')
        plt.plot(X, Y_RL_Recall, '-r', label='RL_rec')
        plt.plot(X, Y_R1_Prec, '--b', label='R1_prec')
        plt.plot(X, Y_R2_Prec, '--g', label='R2_prec')
        plt.plot(X, Y_RL_Prec, '--r', label='RL_prec')
        plt.plot(X, Y_R1_F1, ':b', linestyle=':', label='R1_f1')
        plt.plot(X, Y_R2_F1, ':g', linestyle=':', label='R2_f1')
        plt.plot(X, Y_RL_F1, ':r', linestyle=':', label='RL_f1')
        plt.legend()
        plt.grid()

        plt.show()

    def getInfoForJson(self, timePointOfReference):
        '''
        Gets a list of dictionaries for information about the summaries stored here.
        [
            {   'summary':[<sentenceIds>],
                'query':(<query_text>, <query_type>, <when_query_requested>),
                'rouge':(<total_word_length>, {resultsDict})
            }
        ]
        :param timePointOfReference: the time.time() for which to subtract for the query times.
        :return:
        '''
        ## make sure we have the rouge scores evaluated already:
        #if not self.evaluateOnTheFly:
        #    self._keepRougeAll()

        info = []
        for i in range(len(self.summaries)):
            summInfo = {}
            summInfo['summary'] = self.summaries[i] # list of sentence IDs
            summInfo['query'] = self.getQueryRepresentation(self.queries[i - 1], timePointOfReference) if i > 0 \
                else ('', 'initial', 0)  # tuple (<query_text>, <query_type>, <when_query_requested>)
            summInfo['rating'] = round(self.summariesRating[i], 3)
            summInfo['rouge'] = self.rougeScores[i] if i < len(self.rougeScores) else () # tuple of (<total_word_length>, {resultsDict})
            info.append(summInfo)
        return info

    def getQueryRepresentation(self, queryTuple, timePointOfReference):
        return (queryTuple[0], queryTuple[1], queryTuple[2] - timePointOfReference)

    def setIterationRatings(self, iterationRatingsDict):
        if len(iterationRatingsDict) > 0:
            for iterationIdx, rating in iterationRatingsDict.items():
                self.summariesRating[iterationIdx] = rating
            self.haveChanges = True