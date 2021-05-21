# set the sys path to three directories up so that imports are relative to the qfse directory:
import sys
import os
from collections import defaultdict
from typing import List

from QFSE.Sentence import Sentence
from QFSE.consts import COREF_TYPE_EVENTS, COREF_TYPE_PROPOSITIONS
from QFSE.models import SummarySent, Summary
from QFSE.propositions.utils import get_proposition_clusters

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import json
import tornado.httpserver
import tornado.ioloop
import tornado.web
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s') # must be placed here due to import ordering
import traceback
import ssl
import WebApp.server.params as params

from QFSE.Utilities import loadSpacy, loadBert, get_item
from QFSE.Utilities import REPRESENTATION_STYLE_SPACY, REPRESENTATION_STYLE_BERT

# The SpaCy and BERT objects must be loaded before anything else, so that classes using them get the initialized objects.
# The SpaCy and BERT objects are initialized only when needed since these init processes take a long time.
REPRESENTATION_STYLE = REPRESENTATION_STYLE_SPACY #REPRESENTATION_STYLE_W2V REPRESENTATION_STYLE_BERT
get_item("spacy")
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

from QFSE.coref.utils import convert_corpus_to_coref_input_format, get_coref_clusters

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
TYPE_REQUEST_COREF_CLUSTER = 9
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
                elif requestType == TYPE_REQUEST_COREF_CLUSTER:
                    returnJson = self.get_coref_cluster(clientJson)
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
        elif 'request_coref_cluster' in clientJson:
            requestType = TYPE_REQUEST_COREF_CLUSTER
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

        formatted_topics = convert_corpus_to_coref_input_format(corpus, topicId)
        get_coref_clusters(formatted_topics, corpus)
        get_proposition_clusters(None, corpus)

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

        corpus_sents = self._summary_sents_to_corpus_sents(corpus, summary)
        response_sents = self._corpus_sents_to_response_sents(corpus_sents)

        reply = {
            "reply_get_initial_summary": {
                "summary": response_sents,
                "keyPhraseList": keyPhraseList,
                "topicName": topicName,
                "topicId": topicId,
                "documentsMetas": {x.id: {"id": x.id, "num_sents": len(x.sentences)} for x in corpus.documents},
                "corefClustersMetas": {cluster_idx: {"cluster_idx": cluster_idx, "display_name": mentions[0]['token']} for cluster_idx, mentions in corpus.coref_clusters.items()},
                "propositionClustersMetas": {cluster_idx: {"cluster_idx": cluster_idx, "display_name": mentions[0]['token']} for cluster_idx, mentions in corpus.proposition_clusters.items()},
                "numDocuments": str(len(corpus.documents)),
                "questionnaire": list(questionnaireList),
                "timeAllowed": str(timeAllowed),
                "textLength": str(summary.length_in_words)
            }
        }
        return json.dumps(reply)

    def _summary_sents_to_corpus_sents(self, corpus, summary: Summary) -> List[Sentence]:
        sentences_used = []
        document_by_id = {doc.id: doc for doc in corpus.documents}
        for summary_sent in summary.summary_sents:
            doc = document_by_id[summary_sent.doc_id]
            sent = doc.sentences[summary_sent.sent_idx]
            sentences_used.append(sent)
        return sentences_used

    def _corpus_sents_to_response_sents(self, corpus_sents: List[Sentence]) -> List[dict]:
        return [{
            "text": corpus_sent.text,
            "idx": corpus_sent.sentIndex,
            "id": corpus_sent.sentId,
            "doc_id": corpus_sent.docId,
            "coref_clusters": corpus_sent.coref_clusters,
            "proposition_clusters": corpus_sent.proposition_clusters,
            "coref_tokens": self._split_sent_text_to_tokens(corpus_sent)
        } for corpus_sent in corpus_sents]

    def _split_sent_text_to_tokens(self, sent: Sentence):
        tokens = sent.tokens
        token_to_mention = defaultdict(list)

        # Coref
        hotfix_wrong_indices = True
        if hotfix_wrong_indices:
            first_token_idx = sent.first_token_idx

        for mentions in sent.coref_clusters:
            mention_start = mentions['start']
            mention_end = mentions['end']
            if hotfix_wrong_indices:
                mention_start -= first_token_idx
                mention_end -= first_token_idx
            for token_idx in range(mention_start, mention_end + 1):
                token_to_mention[token_idx].append(mentions)

        # Propositions
        for mentions in sent.proposition_clusters:
            mention_start = mentions['start']
            mention_end = mentions['end']
            for token_idx in range(mention_start, mention_end + 1):
                token_to_mention[token_idx].append(mentions)

        # Split

        def flush_open_mentions(tokens_groups, open_mentions, open_mentions_to_flush):
            while any(open_mentions_to_flush):
                last_open_mention_id = list(open_mentions_to_flush.keys())[-1]
                last_open_mention = open_mentions_to_flush.pop(last_open_mention_id)
                if last_open_mention_id in open_mentions:
                    open_mentions.pop(last_open_mention_id)
                token_group = {
                    "tokens": last_open_mention['tokens'],
                    "group_id": last_open_mention['cluster_idx'],
                    "cluster_type": last_open_mention['cluster_type']
                }

                # Prepend to next open mention instead
                if any(open_mentions):
                    penultimate_open_mention = open_mentions[list(open_mentions.keys())[-1]]
                    penultimate_open_mention['tokens'].append(token_group)
                else:
                    tokens_groups.append(token_group)

        tokens_groups = []
        open_mentions_by_ids = {}
        for token_idx, token in enumerate(tokens):
            if token_idx in token_to_mention:
                mentions = token_to_mention[token_idx]
                open_mentions_to_flush = {}
                for open_mention_id, open_mention in open_mentions_by_ids.items():
                    open_mention_included = any(curr_mention for curr_mention in mentions if open_mention_id == curr_mention['cluster_idx'])
                    if not open_mention_included:
                        open_mentions_to_flush[open_mention_id] = open_mention
                flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_to_flush)

                for mention in mentions:
                    cluster_idx = mention['cluster_idx']
                    if not any(open_mentions_by_ids) or cluster_idx not in open_mentions_by_ids:
                        open_mentions_by_ids[cluster_idx] = {"tokens": [], "cluster_idx": cluster_idx, "cluster_type": mention['cluster_type']}

                if any(open_mentions_by_ids):
                    last_open_mention = list(open_mentions_by_ids.values())[-1]
                    last_open_mention['tokens'].append([token])
            else:
                flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_by_ids)
                tokens_groups.append([token])

        while any(open_mentions_by_ids):
            flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_by_ids)

        return tokens_groups

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

        corpus = m_infoManager.getSummarizer(clientId).corpus
        summary = m_infoManager.getSummarizer(clientId).summarizeByQuery(query, numSentences, queryType)
        for x in summary.summary_sents:
            formatted_sent = x.sent.replace('"', '\\"').replace('\n', ' ')
            x.sent = formatted_sent

        corpus_sents = self._summary_sents_to_corpus_sents(corpus, summary)
        response_sents = self._corpus_sents_to_response_sents(corpus_sents)

        reply = {
            "reply_query": {
                "summary": response_sents,
                "textLength": summary.length_in_words
            }
        }

        return json.dumps(reply)

    def get_document(self, client_json):
        client_id = client_json['clientId']
        doc_id = client_json['request_document']['docId']

        doc = self.get_doc_by_id(m_infoManager.getSummarizer(client_id).corpus, doc_id)

        reply = {
            "reply_document": {
                "doc": {
                    "id": doc_id,
                    "sentences": self._corpus_sents_to_response_sents(doc.sentences)
                }
            }
        }

        return json.dumps(reply)

    def get_doc_by_id(self, corpus, doc_id):
        found_docs = [x for x in corpus.documents if doc_id in x.id]
        if any(found_docs):
            doc = found_docs[0]
        else:
            raise ValueError(f"Doc not found ; doc_id {doc_id}")

        return doc

    def get_sent_by_id(self, doc, sent_idx):
        found_sents = [x for x in doc.sentences if x.sentIndex == sent_idx]
        if any(found_sents):
            sent = found_sents[0]
        else:
            raise ValueError(f"Sentence not found ; sent_idx {sent_idx}")

        return sent

    def get_coref_cluster(self, client_json):
        client_id = client_json['clientId']
        coref_cluster_id = int(client_json['request_coref_cluster']['corefClusterId'])
        coref_cluster_type = client_json['request_coref_cluster']['corefClusterType']

        corpus = m_infoManager.getSummarizer(client_id).corpus
        if coref_cluster_type == COREF_TYPE_PROPOSITIONS:
            clusters = corpus.proposition_clusters
        else:
            clusters = corpus.coref_clusters
        found_clusters = [mentions for key, mentions in clusters.items() if key == coref_cluster_id]
        if any(found_clusters):
            mentions = found_clusters[0]
        else:
            raise ValueError(f"Cluster not found ; coref_cluster_id {coref_cluster_id}")

        sentences = []
        for mention in mentions:
            doc = self.get_doc_by_id(corpus, mention['doc_id'])
            found_sent = self.get_sent_by_id(doc, mention['sent_idx'])
            if found_sent not in sentences:
                sentences.append(found_sent)

        reply = {
            "reply_coref_cluster": {
                "doc": {
                    "id": coref_cluster_id,
                    "corefType": coref_cluster_type,
                    "sentences": self._corpus_sents_to_response_sents(sentences)
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