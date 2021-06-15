import os
import csv
from QFSE.Document import Document
from collections import Counter, defaultdict
from nltk import bigrams
from nltk import trigrams
from QFSE.Utilities import REPRESENTATION_STYLE_W2V, STOP_WORDS
from QFSE.Utilities import nlp
import string
#from collections import defaultdict
#from math import log
#from nltk.corpus import wordnet
#from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
#import operator
#import editdistance
#from nltk.util import ngrams

FULL_QUESTIONNAIRE_IND = 999
QUESTIONNAIRE_IND_16_0 = 0 # first batch of 16 from the lite-pyramid 32
QUESTIONNAIRE_IND_16_1 = 1 # second batch of 16 from the lite-pyramid 32
QUESTIONNAIRE_IND_10 = 2 # 10 random from the lite-pyramid 32
QUESTIONNAIRE_IND_10PN = 3 # 5 random from the lite-pyramid 32 + 1 repeated + 2 ferom other topics (negative) + 2 empty for dynamic placement of sentences from the session text (positive)
QUESTIONNAIRE_ID_TO_NAME = {
    QUESTIONNAIRE_IND_16_0: 'batch1.csv',
    QUESTIONNAIRE_IND_16_1: 'batch2.csv',
    QUESTIONNAIRE_IND_10: 'batch10.csv',
    QUESTIONNAIRE_IND_10PN: 'batch10pn.csv'
}

class Corpus():
    def __init__(self, topic_id: str, directoryPath, referenceSummariesDirectory, questionnaireDirpath, representationStyle=REPRESENTATION_STYLE_W2V):
        self.topic_id = topic_id
        self.dirPath = directoryPath
        self.representationStyle = representationStyle
        #self.tfidfList = [] # list of all tf-idf scores over all documents, ordered by score (highest first)
        #self.countList = [] # list of all counts over all documents, ordered by count (highest first)
        self.documents = []
        # a list of all sentences in this corpus that may be used for summarization:
        self.allSentences = []
        # a dictionary of sentence string to sentence ID, to assist in quickly finding a sentence's ID by its string:
        self._allSentencesFinder = {}
        self._sentIdToSentence = {}
        # a Counter object of all the words, bigrams and trigrams in the corpus:
        self.wordCounter = None
        #self._bigramCounter = None
        #self._trigramCounter = None
        self.ngramCounter = None
        # load the corpus and intialize the above objects
        self._loadDocuments()
        # keep the directory of the reference summaries
        self.referenceSummariesDirectory = referenceSummariesDirectory
        # create the list of questions (and answers not filled) for this corpus (for the lite-pyramid style evaluation):
        # the first is a dict of dictionaries of {questionnairId -> {qId->qStr}}
        # the second is a dict of dictionaries of {questionnairId -> {qId->qStr}} (for True/False answer options)
        self.questionnaireDict, self.questionnaireAnswersReported = self._loadQuestionnaire(
            questionnaireDirpath)  # dict of dictionaries of qId->qStr
        self.coref_clusters = defaultdict(dict)


    def _loadDocuments(self):
        # load all files in the directory, and initialize its document objects:
        fileIndex = 0
        documentsText = []
        for root, subdirs, files in os.walk(self.dirPath):
            for filename in sorted(files):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r') as f:
                    fContent = f.read().replace('\n', ' ')
                    # fId = '{}_{}'.format(fileIndex, filename)
                    self.documents.append(Document(filename, fContent, filepath, self.representationStyle))
                    documentsText.append(fContent)
                    fileIndex += 1

        ## get all the Spacy docs at once, this is more efficient than doing do one by one:
        #for docIdx, spacyDoc in enumerate(nlp.pipe(documentsText, batch_size=100)):
        #    self.documents[docIdx].initDoc(documentsText[docIdx], spacyDoc, loadBert)

        self.allSentences = [sentence for doc in self.documents for sentence in doc.sentences]
        for sentence in self.allSentences:
            self._allSentencesFinder[sentence.text] = sentence.sentId
            self._sentIdToSentence[sentence.sentId] = sentence

        self._countAllWords()

        ## calculate the corpus IDF values:
        #self.idfDict = self._getIdfDict([file['doc'] for file in self.files])
        ## initialize the phrase counters of the corpus:
        #self._initPhraseCounters()

    def getAllText(self):
        return ' '.join(doc.text for doc in self.documents)

    def getSentenceIdByText(self, sentenceText):
        # if this sentence is not found, return the given sentence text as the key:
        if sentenceText in self._allSentencesFinder:
            return self._allSentencesFinder[sentenceText]
        # allow a 5 character difference, and look for the sentence anyway:
        sF = sentenceText.strip()
        for t in self._allSentencesFinder:
            sT = t.strip()
            if len(sT) - len(sF) < 5 and sF in sT:
                return self._allSentencesFinder[t]
            elif len(sF) - len(sT) < 5 and sT in sF:
                return self._allSentencesFinder[t]
        return None

    def getSentenceById(self, sentId):
        if sentId in self._sentIdToSentence:
            return self._sentIdToSentence[sentId]
        return None

    def _countAllWords(self):
        allTokensLower = [token.lower() for doc in self.documents for token in doc.tokens]
        allWords = [token for token in allTokensLower if
                    token.strip() not in STOP_WORDS and (token == '&' or token not in string.punctuation)]
        self.wordCounter = Counter(allWords)
        allBigrams = ['{} {}'.format(word1, word2) for word1, word2 in bigrams(allWords) if word1 != '&' and word2 != '&']
        allTrigrams = ['{} {} {}'.format(word1, word2, word3) for word1, word2, word3 in trigrams(allWords) if word1 != '&' and word3 != '&']
        #self._bigramCounter = ngrams(allWords, 2)
        bigramCounter = Counter(allBigrams)
        trigramCounter = Counter(allTrigrams)
        self.ngramCounter = bigramCounter | trigramCounter
        for bigram, bCount in bigramCounter.items():
            if bCount > 2:
                for trigram, tCount in trigramCounter.items():
                    if tCount > 2:
                        if bCount == tCount and bigram in trigram:
                            del self.ngramCounter[bigram]

    def _loadQuestionnaire(self, questionnaireDirpath):
        allQuestionBatches = {}
        allAnswersBatchesEmpty = {} # a default valued (False answer) list of dictionaries for the answers
        if os.path.exists(questionnaireDirpath):
            for questionBatchFilename in os.listdir(questionnaireDirpath):
                questionBatchFilepath = os.path.join(questionnaireDirpath, questionBatchFilename)
                questionsDict = {}
                with open(questionBatchFilepath, 'r') as inF:
                    csvReader = csv.DictReader(inF, delimiter=',', quotechar='"')
                    for row in csvReader:
                        if row['forUse'] == '1':
                            questionsDict[row['questionId']] = row['questionText']
                for questionnaireId, questionnaireFilename in QUESTIONNAIRE_ID_TO_NAME.items():
                    if questionBatchFilename == questionnaireFilename:
                        allQuestionBatches[questionnaireId] = questionsDict
                        allAnswersBatchesEmpty[questionnaireId] = {qId:False for qId in questionsDict}
        #allQuestionBatchesDict = [allQuestionBatches[i] for i in range(len(QUESTIONNAIRE_ID_TO_NAME))]

        return allQuestionBatches, allAnswersBatchesEmpty

    def getQuestionnaire(self, questionnaireId):
        if questionnaireId in self.questionnaireDict:
            return self.questionnaireDict[questionnaireId]
        elif questionnaireId == FULL_QUESTIONNAIRE_IND: # need to return combination of all 32 questions
            fullQuestionnaire = {}
            fullQuestionnaire.update(self.questionnaireDict[QUESTIONNAIRE_IND_16_0])
            fullQuestionnaire.update(self.questionnaireDict[QUESTIONNAIRE_IND_16_1])
            #for questionnaire in self.questionnaireList:
            #    fullQuestionnaire.update(questionnaire)
            return fullQuestionnaire
        else:
            return {}

    def setQuestionnaireAnswers(self, questionnaireId, answers):
        '''
        Set the answers for the questions in this corpus's questionnaire.
        :param batchNum: The questionnaire index (999 for any questionaire)
        :param answers: Dictionary of qId -> answer
        :return:
        '''
        if questionnaireId in self.questionnaireAnswersReported:
            for qId in answers:
                if qId in self.questionnaireAnswersReported[questionnaireId]:
                    self.questionnaireAnswersReported[questionnaireId][qId] = answers[qId]
        elif questionnaireId == FULL_QUESTIONNAIRE_IND: # need to set answers in all questionnaires
            for qId in answers:
                for questionnaireAnswers in self.questionnaireAnswersReported.values():
                    if qId in questionnaireAnswers:
                        questionnaireAnswers[qId] = answers[qId]


    def getQuestionnaireAnswers(self, questionnaireId):
        if questionnaireId in self.questionnaireAnswersReported:
            return self.questionnaireAnswersReported[questionnaireId]
        elif questionnaireId == FULL_QUESTIONNAIRE_IND: # need to return combination of all questionnaire answers
            fullQuestionnaireAnswers = {}
            for questionnaireAnswers in self.questionnaireAnswersReported.values():
                fullQuestionnaireAnswers.update(questionnaireAnswers)
            return fullQuestionnaireAnswers
        else:
            return {}