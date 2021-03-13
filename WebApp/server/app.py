# set the sys path to three directories up so that imports are relative to the qfse directory:
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import json
import tornado.httpserver
import tornado.ioloop
import tornado.web
import logging
logging.basicConfig(filename='intSumm.log', level=logging.DEBUG, format='%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s') # must be placed here due to import ordering
import traceback
import datetime
import ssl
import WebApp.server.params as params

from QFSE.Utilities import loadSpacy, loadBert
from QFSE.Utilities import REPRESENTATION_STYLE_W2V, REPRESENTATION_STYLE_SPACY, REPRESENTATION_STYLE_BERT

# The SpaCy and BERT objects must be loaded before anything else, so that classes using them get the initialized objects.
# The SpaCy and BERT objects are initialized only when needed since these init processes take a long time.
REPRESENTATION_STYLE = REPRESENTATION_STYLE_SPACY #REPRESENTATION_STYLE_W2V REPRESENTATION_STYLE_BERT
loadSpacy()
if REPRESENTATION_STYLE == REPRESENTATION_STYLE_BERT:
    loadBert()

import data.Config as config
from QFSE.SummarizerClustering import SummarizerClustering
from QFSE.SummarizerAddMore import SummarizerAddMore
from QFSE.SummarizerTextRankPlusLexical import SummarizerTextRankPlusLexical
from QFSE.Corpus import Corpus
from QFSE.SuggestedQueriesNgramCount import SuggestedQueriesNgramCount
from QFSE.SuggestedQueriesTextRank import SuggestedQueriesTextRank
from WebApp.server.InfoManager import InfoManager

# request types
TYPE_ERROR = -1
TYPE_GET_TOPICS = 0
TYPE_GET_INITIAL = 1
TYPE_QUERY = 2
TYPE_QUESTION_ANSWER = 3
TYPE_SUBMIT = 4
TYPE_SET_START_TIME = 5
TYPE_ITERATION_RATING = 6
TYPE_QUESTIONNAIRE_RATING = 7
TYPE_REQUEST_DOCUMENT = 8
# summary types
SUMMARY_TYPES = {'qfse_cluster':SummarizerClustering, 'increment_cluster':SummarizerAddMore, 'qfse_textrank':SummarizerTextRankPlusLexical}
SUGGESTED_QUERIES_TYPES = {'qfse_cluster':SuggestedQueriesNgramCount, 'increment_cluster':SuggestedQueriesNgramCount, 'qfse_textrank':SuggestedQueriesTextRank}
# number of suggested queries to show
NUM_SUGG_QUERIES_PRESENTED = {'qfse_cluster':10, 'increment_cluster':0, 'qfse_textrank':10}

m_infoManager = InfoManager()


class IntSummHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*")
        #self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def options(self):
        # no body
        logging.debug('Received OPTIONS request')
        self.set_status(204)

    def post(self):
        # Protocol implemented here based on the client messages.

        try:
            # load the json received from the client:
            clientJson = json.loads(self.request.body.decode('utf-8'))
            logging.debug('Got JSON data: ' + str(clientJson))
            requestType, clientId = self.getRequestTypeFromClientJson(clientJson)

            # if client sent an unknown json:
            if requestType == TYPE_ERROR:
                returnJson = self.getErrorJson('Undefined JSON received.')
            else:
                m_infoManager.createClient(clientId)

                if requestType == TYPE_GET_TOPICS:
                    returnJson = self.getTopicsJson(clientJson)
                elif requestType == TYPE_GET_INITIAL:
                    returnJson = self.getInitialSummaryJson(clientJson)
                elif requestType == TYPE_QUERY:
                    returnJson = self.getQuerySummaryJson(clientJson)
                elif requestType == TYPE_QUESTION_ANSWER:
                    returnJson = self.getQuestionAnswerJson(clientJson)
                elif requestType == TYPE_SUBMIT:
                    returnJson = self.getSubmitJson(clientJson)
                elif requestType == TYPE_SET_START_TIME:
                    returnJson = self.getStartTimeJson(clientJson)
                elif requestType == TYPE_ITERATION_RATING:
                    returnJson = self.getIterationRatingJson(clientJson)
                elif requestType == TYPE_QUESTIONNAIRE_RATING:
                    returnJson = self.getQuestionnaireRatingJson(clientJson)
                elif requestType == TYPE_REQUEST_DOCUMENT:
                    returnJson = self.get_document(clientJson)
                else:
                    returnJson = self.getErrorJson('Undefined JSON received.')

        except Exception as e:
            logging.error('Caught error from unknown location: ' + str(e))
            logging.error(traceback.format_exc())
            returnJson = self.getErrorJson('Please try again. General error: ' + str(e))

        logging.debug('Sending JSON data: ' + str(returnJson))

        self.write(returnJson) # send JSON to client

    def getRequestTypeFromClientJson(self, clientJson):
        if 'request_get_topics' in clientJson:
            requestType = TYPE_GET_TOPICS
        elif 'request_get_initial_summary' in clientJson:
            requestType = TYPE_GET_INITIAL
        elif 'request_query' in clientJson:
            requestType = TYPE_QUERY
        elif 'request_set_question_answer' in clientJson:
            requestType = TYPE_QUESTION_ANSWER
        elif 'request_submit' in clientJson:
            requestType = TYPE_SUBMIT
        elif 'request_set_start' in clientJson:
            requestType = TYPE_SET_START_TIME
        elif 'request_set_iteration_rating' in clientJson:
            requestType = TYPE_ITERATION_RATING
        elif 'request_set_questionnaire_rating' in clientJson:
            requestType = TYPE_QUESTIONNAIRE_RATING
        elif 'request_document' in clientJson:
            requestType = TYPE_REQUEST_DOCUMENT
        else:
            requestType = TYPE_ERROR

        if 'clientId' in clientJson:
            clientId = clientJson['clientId']
        else:
            requestType = TYPE_ERROR
            clientId = None

        return requestType, clientId

    def getTopicsJson(self, clientJson):
        topicsList = ', '.join('{{"topicId":"{}", "topicName":"{}"}}'.format(topicId, topicId) for topicId in config.CORPORA_LOCATIONS)
        jsonReply = \
            "{\"reply_get_topics\": {" + \
            "  \"topicsList\": [" + topicsList + "]" + \
            "}}"
        return jsonReply

    def getInitialSummaryJson(self, clientJson):
        clientId = clientJson['clientId']
        topicId = clientJson['request_get_initial_summary']['topicId']
        summaryType = clientJson['request_get_initial_summary']['summaryType']
        algorithm = clientJson['request_get_initial_summary']['algorithm']
        summaryWordLength = clientJson['request_get_initial_summary']['summaryWordLength']
        questionnaireBatchIndex = clientJson['request_get_initial_summary']['questionnaireBatchIndex']
        timeAllowed = clientJson['request_get_initial_summary']['timeAllowed']
        assignmentId = clientJson['request_get_initial_summary']['assignmentId']
        hitId = clientJson['request_get_initial_summary']['hitId']
        workerId = clientJson['request_get_initial_summary']['workerId']
        turkSubmitTo = clientJson['request_get_initial_summary']['turkSubmitTo']

        # make sure the topic ID is valid:
        if topicId in config.CORPORA_LOCATIONS:
            referenceSummsFolder = os.path.join(config.CORPORA_LOCATIONS[topicId], config.CORPUS_REFSUMMS_RELATIVE_PATH)
            questionnaireFilepath = os.path.join(config.CORPORA_LOCATIONS[topicId], config.CORPUS_QUESTIONNAIRE_RELATIVE_PATH)
            corpus = Corpus(config.CORPORA_LOCATIONS[topicId], referenceSummsFolder, questionnaireFilepath, representationStyle=REPRESENTATION_STYLE)
        else:
            return self.getErrorJson('Topic ID not supported: {}'.format(topicId))

        # make sure the summary type is valid:
        summaryAlgorithm = '{}_{}'.format(summaryType, algorithm)
        if summaryAlgorithm in SUMMARY_TYPES:
            summarizer = SUMMARY_TYPES[summaryAlgorithm](corpus, evaluateOnTheFly=False)
            if SUGGESTED_QUERIES_TYPES[summaryAlgorithm] == SuggestedQueriesTextRank:
                suggestedQueriesGenerator = SUGGESTED_QUERIES_TYPES[summaryAlgorithm](corpus, summarizer)
            else:
                suggestedQueriesGenerator = SUGGESTED_QUERIES_TYPES[summaryAlgorithm](corpus)
            m_infoManager.initClient(clientId, corpus, suggestedQueriesGenerator, NUM_SUGG_QUERIES_PRESENTED[summaryAlgorithm], summarizer, topicId,
                                     questionnaireBatchIndex, timeAllowed, assignmentId, hitId, workerId, turkSubmitTo)
        else:
            return self.getErrorJson('Summary type not supported: {}'.format(summaryAlgorithm))

        # generate the initial summary info:
        summary = m_infoManager.getSummarizer(clientId).summarizeGeneric(summaryWordLength)
        for x in summary.summary_sents:
            formatted_sent = x.sent.replace('"', '\\"').replace('\n', ' ')
            x.sent = formatted_sent
        keyPhraseList = suggestedQueriesGenerator.getSuggestionsFromToIndices(0, NUM_SUGG_QUERIES_PRESENTED[summaryAlgorithm] - 1)
        topicName = topicId

        questionnaireList = {{"id": qId,"str": qStr} for qId, qStr in m_infoManager.getQuestionnaire(clientId).items()}

        reply = {
            "reply_get_initial_summary": {
                "summary": [x.to_dict() for x in summary.summary_sents],
                "keyPhraseList": keyPhraseList,
                "topicName": topicName,
                "topicId": topicId,
                "documentsMetas": [{"id": x.id} for x in corpus.documents],
                "numDocuments": str(len(corpus.documents)),
                "questionnaire": list(questionnaireList),
                "timeAllowed": str(timeAllowed),
                "textLength": str(summary.length_in_words)
            }
        }
        return json.dumps(reply)

    def getQuerySummaryJson(self, clientJson):
        clientId = clientJson['clientId']
        topicId = clientJson['request_query']['topicId']
        query = clientJson['request_query']['query']
        numSentences = clientJson['request_query']['summarySentenceCount']
        queryType = clientJson['request_query']['type']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        if topicId != m_infoManager.getTopicId(clientId):
            return self.getErrorJson('Topic ID not yet initialized by client: {}'.format(topicId))

        summary = m_infoManager.getSummarizer(clientId).summarizeByQuery(query, numSentences, queryType)
        for x in summary.summary_sents:
            formatted_sent = x.sent.replace('"', '\\"').replace('\n', ' ')
            x.sent = formatted_sent

        reply = {
            "reply_query": {
                "summary": [x.to_dict() for x in summary.summary_sents],
                "textLength": summary.length_in_words
            }
        }

        return json.dumps(reply)

    def get_document(self, client_json):
        client_id = client_json['clientId']
        doc_id = client_json['request_document']['docId']

        found_docs = [x for x in m_infoManager.getSummarizer(client_id).corpus.documents if x.id == doc_id]
        if any(found_docs):
            doc = found_docs[0]
        else:
            raise ValueError(f"Doc not found ; doc_id {doc_id}")

        reply = {
            "reply_document": {
                "doc": {
                    "text": doc.text.split('   ')
                }
            }
        }

        return json.dumps(reply)

    def getQuestionAnswerJson(self, clientJson):
        clientId = clientJson['clientId']
        questionId = clientJson['request_set_question_answer']['qId']
        answer = clientJson['request_set_question_answer']['answer']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        self.setQuestionAnswer(clientId, questionId, answer)

        jsonReply = \
            "{\"reply_set_question_answer\": {" + \
            "}}"
        return jsonReply

    def setQuestionAnswer(self, clientId, qId, answer):
        m_infoManager.setQuestionnaireAnswers(clientId, {qId: answer})

    def getSubmitJson(self, clientJson):
        clientId = clientJson['clientId']
        questionAnswersDict = clientJson['request_submit']['answers']
        timeUsedForExploration = clientJson['request_submit']['timeUsed']
        commentsFromUser = clientJson['request_submit']['comments']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        success = self.setSubmitInfo(clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser)
        if success:
            m_infoManager.setEndTime(clientId)

        jsonReply = \
            "{\"reply_submit\": {" + \
            "  \"success\": " + ("true" if success else "false") + \
            "}}"
        return jsonReply

    def setSubmitInfo(self, clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser):
        isSuccess, msg = m_infoManager.setSubmitInfo(clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser)
        return isSuccess

    def getStartTimeJson(self, clientJson):
        clientId = clientJson['clientId']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        m_infoManager.setStartTimeOfInteraction(clientId)

        jsonReply = \
            "{\"reply_set_start\": {" + \
            "}}"
        return jsonReply

    def getIterationRatingJson(self, clientJson):
        clientId = clientJson['clientId']
        iterationIdx = int(clientJson['request_set_iteration_rating']['iterationIdx'])
        rating = float(clientJson['request_set_iteration_rating']['rating'])

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        self.setIterationRating(clientId, iterationIdx, rating)

        jsonReply = \
            "{\"reply_set_iteration_rating\": {" + \
            "}}"
        return jsonReply

    def setIterationRating(self, clientId, iterationIdx, rating):
        m_infoManager.setIterationRatings(clientId, {iterationIdx: rating})

    def getQuestionnaireRatingJson(self, clientJson):
        clientId = clientJson['clientId']
        questionId = clientJson['request_set_questionnaire_rating']['questionId']
        questionText = clientJson['request_set_questionnaire_rating']['questionText']
        rating = float(clientJson['request_set_questionnaire_rating']['rating'])

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        self.setQuestionnaireRating(clientId, questionId, questionText, rating)

        jsonReply = \
            "{\"reply_set_questionnaire_rating\": {" + \
            "}}"
        return jsonReply

    def setQuestionnaireRating(self, clientId, questionId, questionText, rating):
        m_infoManager.setQuestionnaireRatings(clientId, {questionId: {'text':questionText, 'rating': rating}})

    def getErrorJson(self, msg):
        reply = {"error": msg}
        logging.info("Sending Error JSON: " + msg)
        return json.dumps(reply)


if __name__ == '__main__':
    app = tornado.web.Application([tornado.web.url(r'/', IntSummHandler)])
    if params.is_https:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(params.https_certificate_file, params.https_key_file)
        http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
    else:
        http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(params.http_server_port)
    logging.info('Starting server on port ' + str(params.http_server_port))
    print('Starting server on port ' + str(params.http_server_port))
    tornado.ioloop.IOLoop.instance().start()