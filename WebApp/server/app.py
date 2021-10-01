# set the sys path to three directories up so that imports are relative to the qfse directory:
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Set, Dict, Union, Optional

from nltk import word_tokenize

from QFSE import Corpus
from QFSE.Sentence import Sentence
from QFSE.abstractive_coref.mentions_finder import MentionsFinder
from QFSE.consts import COREF_TYPE_EVENTS, COREF_TYPE_PROPOSITIONS, COREF_TYPE_ENTITIES
from QFSE.corpus_registry import CorpusRegistry, get_clusters_filtered
from QFSE.models import Summary, DocSent, ClusterQuery, QueryResult, QueryResultSentence, \
    TokensCluster, DocumentResult, UIAction, QueryResultUserWrapper
from QFSE.query_registry import QueryRegistry
from QFSE.query_results_analyzer import QueryResultsAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

import json
import tornado.httpserver
import tornado.ioloop
import tornado.web
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s')  # must be placed here due to import ordering
import traceback
import ssl
import WebApp.server.params as params

from QFSE.Utilities import loadBert, get_item

import data.Config as config
from QFSE.SummarizerClustering import SummarizerClustering
from QFSE.SummarizerAddMore import SummarizerAddMore
from QFSE.SummarizerTextRankPlusLexical import SummarizerTextRankPlusLexical
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
TYPE_REQUEST_COREF_CLUSTER = 9
TYPE_LOG_UI_ACTION = 10
# summary types
SUMMARY_TYPES = {'qfse_cluster': SummarizerClustering, 'increment_cluster': SummarizerAddMore,
                 'qfse_textrank': SummarizerTextRankPlusLexical}
SUGGESTED_QUERIES_TYPES = {'qfse_cluster': SuggestedQueriesNgramCount, 'increment_cluster': SuggestedQueriesNgramCount,
                           'qfse_textrank': SuggestedQueriesTextRank}
# number of suggested queries to show
NUM_SUGG_QUERIES_PRESENTED = {'qfse_cluster': 10, 'increment_cluster': 0, 'qfse_textrank': 10}

m_infoManager = InfoManager()


class IntSummHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*")
        # self.set_header("Access-Control-Allow-Headers", "x-requested-with")
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
                elif requestType == TYPE_LOG_UI_ACTION:
                    returnJson = self.log_ui_action(clientJson)
                else:
                    returnJson = self.getErrorJson('Undefined JSON received.')

        except Exception as e:
            logging.error('Caught error from unknown location: ' + str(e))
            logging.error(traceback.format_exc())
            returnJson = self.getErrorJson('Please try again. General error: ' + str(e))

        logging.debug('Sending JSON data: ' + str(returnJson))

        self.write(returnJson)  # send JSON to client

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
        elif 'request_log_ui_action' in clientJson:
            requestType = TYPE_LOG_UI_ACTION
        else:
            requestType = TYPE_ERROR

        if 'clientId' in clientJson:
            clientId = clientJson['clientId']
        else:
            requestType = TYPE_ERROR
            clientId = None

        return requestType, clientId

    def getTopicsJson(self, clientJson):
        topicsList = ', '.join(
            '{{"topicId":"{}", "topicName":"{}"}}'.format(topicId, topicId) for topicId in config.CORPORA_LOCATIONS)
        jsonReply = \
            "{\"reply_get_topics\": {" + \
            "  \"topicsList\": [" + topicsList + "]" + \
            "}}"
        return jsonReply

    def getInitialSummaryJson(self, clientJson):
        clientId = clientJson['clientId']
        topicId = clientJson['request_get_initial_summary']['topicId']
        questionnaireBatchIndex = clientJson['request_get_initial_summary']['questionnaireBatchIndex']
        timeAllowed = clientJson['request_get_initial_summary']['timeAllowed']
        assignmentId = clientJson['request_get_initial_summary']['assignmentId']
        hitId = clientJson['request_get_initial_summary']['hitId']
        workerId = clientJson['request_get_initial_summary']['workerId']
        turkSubmitTo = clientJson['request_get_initial_summary']['turkSubmitTo']

        corpus_registry: CorpusRegistry = get_item("corpus_registry")
        corpus = corpus_registry.get_corpus(topicId)
        if corpus is None:
            return self.getErrorJson('Topic ID not supported: {}'.format(topicId))

        m_infoManager.initClient(clientId, corpus, None, 0, None, topicId,
                                 questionnaireBatchIndex, timeAllowed, assignmentId, hitId, workerId, turkSubmitTo,
                                 QueryResultsAnalyzer())
        topicName = topicId

        m_infoManager.add_ui_action_log(clientId, UIAction("initial", {
            "topic_id": topicId
        }, datetime.utcnow().isoformat()))

        reply = {
            "reply_get_initial_summary": {
                "summary": [],
                "keyPhraseList": [],
                "topicName": topicName,
                "topicId": topicId,
                "documentsMetas": {x.id: {"id": x.id, "num_sents": len(x.sentences)} for x in corpus.documents},
                "corefClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_ENTITIES]),
                "eventsClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_EVENTS]),
                "propositionClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_PROPOSITIONS]),
                "numDocuments": str(len(corpus.documents)),
                "questionnaire": [],
                "timeAllowed": str(timeAllowed),
                "textLength": ""
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

    def _split_sent_text_to_tokens(self, sent, is_original_sentences: bool, skip_mentions=False,
                                   original_sentences=None) -> List[
        Union[TokensCluster, List[str]]]:
        tokens = sent
        if is_original_sentences:
            tokens = word_tokenize(sent.text)

        token_to_mention = {}
        if not skip_mentions:
            token_to_mention = self._get_token_to_mention(sent, is_original_sentences, original_sentences)

        # Split

        def flush_open_mentions(tokens_groups, open_mentions, open_mentions_to_flush):
            while any(open_mentions_to_flush):
                last_open_mention_id = list(open_mentions_to_flush.keys())[-1]
                last_open_mention = open_mentions_to_flush.pop(last_open_mention_id)
                if last_open_mention_id in open_mentions:
                    open_mentions.pop(last_open_mention_id)
                token_group = TokensCluster(
                    tokens=last_open_mention['tokens'],
                    cluster_id=last_open_mention['cluster_idx'],
                    cluster_type=last_open_mention['cluster_type']
                )

                # Prepend to next open mention instead
                if any(open_mentions):
                    penultimate_open_mention = open_mentions[list(open_mentions.keys())[-1]]
                    penultimate_open_mention['tokens'].append(token_group)
                else:
                    tokens_groups.append(token_group)

        tokens_groups: List[Union[TokensCluster, List[str]]] = []
        open_mentions_by_ids = {}
        for token_idx, token in enumerate(tokens):
            if isinstance(token, str):
                # we used word_tokenize, can't reconstruct
                token = token + " "
            else:
                token = token.text_with_ws
            if token_idx in token_to_mention:
                mentions = token_to_mention[token_idx]
                open_mentions_to_flush = {}
                for open_mention_id, open_mention in open_mentions_by_ids.items():
                    open_mention_included = any(curr_mention for curr_mention in mentions if
                                                open_mention_id == self._get_mention_id(curr_mention))
                    if not open_mention_included:
                        open_mentions_to_flush[open_mention_id] = open_mention
                flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_to_flush)

                for mention in mentions:
                    cluster_idx = self._get_mention_id(mention)
                    if not any(open_mentions_by_ids) or cluster_idx not in open_mentions_by_ids:
                        open_mentions_by_ids[cluster_idx] = {"tokens": [], "cluster_idx": mention['cluster_idx'],
                                                             "cluster_type": mention['cluster_type']}

                # add the token only to one open mention
                if any(open_mentions_by_ids):
                    chosen_open_mention = self._choose_open_mention(list(open_mentions_by_ids.values()))
                    chosen_open_mention['tokens'].append([token])
            else:
                flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_by_ids)
                tokens_groups.append([token])

        while any(open_mentions_by_ids):
            flush_open_mentions(tokens_groups, open_mentions_by_ids, open_mentions_by_ids)

        return tokens_groups

    def _choose_open_mention(self, open_mentions) -> dict:
        """
        Assuming propositions is longest, we want to add the token to others first
        """

        CLUSTERS_ORDER = {
            COREF_TYPE_PROPOSITIONS: 1,
            COREF_TYPE_EVENTS: 2,
            COREF_TYPE_ENTITIES: 3
        }

        sorted_open_mentions = sorted(open_mentions, key=lambda x: CLUSTERS_ORDER[x['cluster_type']], reverse=True)

        return sorted_open_mentions[0]

    def _get_mention_id(self, mention):
        return f"{mention['cluster_idx']}_{mention['cluster_type']}"

    def _get_token_to_mention(self, sent, is_original_sentences: bool, original_sentences):
        if not is_original_sentences:
            token_to_mention = MentionsFinder().find_mentions(sent, original_sentences)
        else:
            token_to_mention = defaultdict(list)

            # Coref - if not running CD LM
            hotfix_wrong_indices = True
            first_token_idx = 0
            if hotfix_wrong_indices:
                first_token_idx = sent.first_token_idx

            # Entities
            for mentions in sent.coref_clusters[COREF_TYPE_ENTITIES]:
                mention_start = mentions['start']
                mention_end = mentions['end']
                if hotfix_wrong_indices:
                    mention_start -= first_token_idx
                    mention_end -= first_token_idx
                for token_idx in range(mention_start, mention_end + 1):
                    token_to_mention[token_idx].append(mentions)

            # Events
            for mentions in sent.coref_clusters[COREF_TYPE_EVENTS]:
                mention_start = mentions['start']
                mention_end = mentions['end']
                # if hotfix_wrong_indices:
                #     mention_start -= first_token_idx
                #     mention_end -= first_token_idx
                for token_idx in range(mention_start, mention_end + 1):
                    token_to_mention[token_idx].append(mentions)

            # Propositions
            for mentions in sent.coref_clusters[COREF_TYPE_PROPOSITIONS]:
                mention_start = mentions['start']
                mention_end = mentions['end']
                for token_idx in range(mention_start, mention_end + 1):
                    token_to_mention[token_idx].append(mentions)

        return token_to_mention

    def getQuerySummaryJson(self, clientJson):
        clientId = clientJson['clientId']
        topicId = clientJson['request_query']['topicId']
        clusters_query = self._get_clusters_query_from_request(clientJson['request_query'])
        query = clientJson['request_query']['query']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        if topicId != m_infoManager.getTopicId(clientId):
            return self.getErrorJson('Topic ID not yet initialized by client: {}'.format(topicId))

        reply_query = {}

        corpus_registry: CorpusRegistry = get_item("corpus_registry")
        corpus: Corpus = corpus_registry.get_corpus(topicId)
        doc_sent_indices: Optional[Set[DocSent]] = None

        query_result = None

        if clusters_query:
            query_registry: QueryRegistry = get_item("query_registry")
            query_result = query_registry.get_query(clusters_query)
            query_results_analyzer = m_infoManager.get_query_results_analyzer(clientId)

            if query_result is None:
                sentences = []
                doc_sent_indices = self._clusters_query_to_doc_sent_indices(clusters_query, corpus)
                if any(doc_sent_indices):
                    doc_sent_indices_to_use = set.intersection(*doc_sent_indices)
                    sentences = self._get_sentences_for_query(doc_sent_indices_to_use, corpus)

                query_result = QueryResult([], clusters_query, [
                    QueryResultSentence(self._split_sent_text_to_tokens(sent, is_original_sentences=True), sent.docId,
                                        sent.sentIndex) for sent in sentences], datetime.utcnow().isoformat())
                if any(sentences):
                    if len(sentences) > 1:
                        summarizer = get_item("bart_summarizer")
                        summary_sents = summarizer.summarize(sentences)
                    else:
                        # No need to summarize one sentence
                        summary_sents = [sent.spacy_rep for sent in sentences]

                    query_result.result_sentences = [QueryResultSentence(
                        self._split_sent_text_to_tokens(sent, is_original_sentences=False,
                                                        original_sentences=sentences)) for sent in summary_sents]

                query_registry.save_query(query_result)

            # Save queries and mark similar sentences to those used
            # query_results_analyzer.analyze_repeating(query_result)
            query_idx = query_results_analyzer.add_query_results(query_result)
            query_result_wrapper = QueryResultUserWrapper(query_result, query_idx)

            reply_query = {
                "queryResult": query_result_wrapper.custom_to_dict(),
                "textLength": 0,
            }

            doc_sent_indices = query_result.get_doc_sent_indices()

        m_infoManager.add_ui_action_log(clientId, UIAction("query", {
            "query_idx": query_result_wrapper.query_idx if query_result_wrapper is not None else None
        }, datetime.utcnow().isoformat()))

        # Always return the clusters even if query is none
        reply_query = {
            **reply_query,
            **{
                "corefClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_ENTITIES],
                                                            doc_sent_indices),
                "eventsClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_EVENTS],
                                                             doc_sent_indices),
                "propositionClustersMetas": get_clusters_filtered(corpus.coref_clusters[COREF_TYPE_PROPOSITIONS],
                                                                        doc_sent_indices)
            }
        }

        return json.dumps({
            "reply_query": reply_query
        })

    def _get_clusters_query_from_request(self, request):
        clusters_query = request['clusters_query'] if 'clusters_query' in request else None
        clusters_query = [ClusterQuery.from_dict(cluster_query) for cluster_query in
                          clusters_query] if clusters_query else clusters_query

        return clusters_query

    def _clusters_query_to_doc_sent_indices(self, clusters_query, corpus) -> List[Set[DocSent]]:
        doc_sent_indices = []
        for cluster_query in clusters_query:
            cluster = self._get_clusters(corpus, cluster_query.cluster_id, cluster_query.cluster_type)
            doc_sent_indices.append(
                {DocSent(mention['doc_id'], mention['sent_idx']) for mention in cluster['mentions']})

        return doc_sent_indices

    def _get_sentences_for_query(self, doc_sent_indices: Set[DocSent], corpus):
        sentences = []
        for doc_sent in doc_sent_indices:
            for document in corpus.documents:
                # Using in instead of == because of proposition clusters missing the document_id
                if doc_sent.doc_id in document.id:
                    sentences.append(document.sentences[doc_sent.sent_idx])
                    break

        return sentences

    def get_document(self, client_json):
        client_id = client_json['clientId']
        doc_id = client_json['request_document']['docId']

        corpus = m_infoManager.getCorpus(client_id)
        doc = self.get_doc_by_id(corpus, doc_id)

        doc_result = DocumentResult(doc_id, [
            QueryResultSentence(self._split_sent_text_to_tokens(sent, is_original_sentences=True), sent.docId,
                                sent.sentIndex) for sent in doc.sentences])

        m_infoManager.add_ui_action_log(client_id, UIAction("open_original_doc", {
            "doc_id": doc_id
        }, datetime.utcnow().isoformat()))

        reply = {
            "reply_document": {
                "doc": doc_result.to_dict()
            }
        }

        return json.dumps(reply)

    def _is_sent_in_doc_sent_indices(self, doc_sent_indices, sent) -> bool:
        return DocSent(sent.docId, sent.sentIndex) in doc_sent_indices

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
        coref_cluster_id = client_json['request_coref_cluster']['corefClusterId']
        coref_cluster_type = client_json['request_coref_cluster']['corefClusterType']

        corpus = m_infoManager.getSummarizer(client_id).corpus

        mentions = self._get_clusters(corpus, coref_cluster_id, coref_cluster_type)

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

    def _get_clusters(self, corpus, cluster_id, cluster_type) -> Dict:
        clusters = {cluster_id: cluster for cluster_id, cluster in corpus.coref_clusters[cluster_type].items()}
        found_clusters = [cluster for key, cluster in clusters.items() if key == cluster_id]
        if any(found_clusters):
            cluster = found_clusters[0]
        else:
            raise ValueError(f"Cluster not found ; coref_cluster_id {cluster_id}")
        return cluster

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
        isSuccess, msg = m_infoManager.setSubmitInfo(clientId, questionAnswersDict, timeUsedForExploration,
                                                     commentsFromUser)
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
        m_infoManager.setQuestionnaireRatings(clientId, {questionId: {'text': questionText, 'rating': rating}})

    def getErrorJson(self, msg):
        reply = {"error": msg}
        logging.info("Sending Error JSON: " + msg)
        return json.dumps(reply)

    def log_ui_action(self, client_json):
        client_id = client_json['clientId']
        action = client_json['request_log_ui_action']['action']
        action_details = client_json['request_log_ui_action']['actionDetails']

        m_infoManager.add_ui_action_log(client_id, UIAction(action, action_details, datetime.utcnow().isoformat()))

        return json.dumps({
            "reply_log_ui_action": {
                "status": "success"
            }
        })


if __name__ == '__main__':
    settings = {
        "static_path": "WebApp/client",
        "static_url_prefix": "/client/",
    }
    app = tornado.web.Application([tornado.web.url(r'/', IntSummHandler)], **settings)
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
