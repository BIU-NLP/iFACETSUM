# set the sys path to three directories up so that imports are relative to the qfse directory:
import sys
import os
from collections import defaultdict
from typing import List, Set, Dict, Union

from QFSE.Sentence import Sentence
from QFSE.consts import COREF_TYPE_EVENTS, COREF_TYPE_PROPOSITIONS, COREF_TYPE_ENTITIES
from QFSE.coref.coref_labels import create_cluster_obj
from QFSE.coref.models import Mention
from QFSE.models import SummarySent, Summary, Cluster, DocSent, ClusterQuery, QueryResult, QueryResultSentence, \
    TokensCluster
from QFSE.propositions.utils import get_proposition_clusters
from QFSE.query_results_analyzer import QueryResultsAnalyzer

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
        get_coref_clusters(formatted_topics, corpus, COREF_TYPE_EVENTS)
        get_coref_clusters(formatted_topics, corpus, COREF_TYPE_ENTITIES)
        get_proposition_clusters(formatted_topics, corpus)

        m_infoManager.initClient(clientId, corpus, None, 0, None, topicId,
                                 questionnaireBatchIndex, timeAllowed, assignmentId, hitId, workerId, turkSubmitTo,
                                 QueryResultsAnalyzer())
        topicName = topicId

        reply = {
            "reply_get_initial_summary": {
                "summary": [],
                "keyPhraseList": [],
                "topicName": topicName,
                "topicId": topicId,
                "documentsMetas": {x.id: {"id": x.id, "num_sents": len(x.sentences)} for x in corpus.documents},
                "corefClustersMetas": self._get_clusters_filtered(COREF_TYPE_ENTITIES, corpus),
                "eventsClustersMetas": self._get_clusters_filtered(COREF_TYPE_EVENTS, corpus),
                "propositionClustersMetas": self._get_clusters_filtered(COREF_TYPE_PROPOSITIONS, corpus),
                "numDocuments": str(len(corpus.documents)),
                "questionnaire": [],
                "timeAllowed": str(timeAllowed),
                "textLength": ""
            }
        }
        return json.dumps(reply)

    def _get_clusters_filtered(self, cluster_type, corpus, doc_sent_indices: Set[DocSent] = None):
        """
        Filters clusters based on a query (faceted search)
        """

        clusters_filtered = {}
        for cluster_idx, cluster in corpus.coref_clusters[cluster_type].items():
            # Return all if no query
            query_is_empty = doc_sent_indices is None
            cluster_sentences_shown_in_query = False
            if doc_sent_indices:
                cluster_sentences_shown_in_query = [mention for mention in cluster['mentions'] if DocSent(mention['doc_id'], mention['sent_idx']) in doc_sent_indices]

            should_return_cluster = query_is_empty or any(cluster_sentences_shown_in_query)

            if should_return_cluster:
                cluster['num_mentions_filtered'] = cluster['num_mentions'] if query_is_empty else len(cluster_sentences_shown_in_query)
                cluster['display_name_filtered'] = cluster['display_name'] if query_is_empty else create_cluster_obj(cluster_idx, cluster_type, [Mention.from_dict(mention) for mention in cluster_sentences_shown_in_query]).display_name
                clusters_filtered[cluster_idx] = cluster

        return clusters_filtered


    def _get_mention_labels_keyphrases(self, clusters):
        most_mentioned_clusters = sorted(clusters.values(), key=lambda cluster: len(cluster['mentions']), reverse=True)
        return [{"label": cluster['cluster_label'], "text": cluster['display_name'], "cluster_id": cluster['cluster_id'], "cluster_type": cluster['cluster_type']} for cluster in most_mentioned_clusters[:50]]


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
            "coref_clusters": corpus_sent.coref_clusters[COREF_TYPE_ENTITIES],
            "proposition_clusters": corpus_sent.coref_clusters[COREF_TYPE_PROPOSITIONS],
            "coref_tokens": self._split_sent_text_to_tokens(corpus_sent)
        } for corpus_sent in corpus_sents]

    def _split_sent_text_to_tokens(self, sent) -> List[Union[TokensCluster, List[str]]]:
        tokens = sent
        token_to_mention = defaultdict(list)

        # # Coref
        # hotfix_wrong_indices = True
        # if hotfix_wrong_indices:
        #     first_token_idx = sent.first_token_idx
        #
        # for mentions in sent.coref_clusters[COREF_TYPE_ENTITIES]:
        #     mention_start = mentions['start']
        #     mention_end = mentions['end']
        #     if hotfix_wrong_indices:
        #         mention_start -= first_token_idx
        #         mention_end -= first_token_idx
        #     for token_idx in range(mention_start, mention_end + 1):
        #         token_to_mention[token_idx].append(mentions)
        #
        # # Propositions
        # for mentions in sent.coref_clusters[COREF_TYPE_PROPOSITIONS]:
        #     mention_start = mentions['start']
        #     mention_end = mentions['end']
        #     for token_idx in range(mention_start, mention_end + 1):
        #         token_to_mention[token_idx].append(mentions)

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
            token = token.text_with_ws
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
        clusters_query = clientJson['request_query']['clusters_query'] if 'clusters_query' in clientJson['request_query'] else None
        clusters_query = [ClusterQuery.from_dict(cluster_query) for cluster_query in clusters_query] if clusters_query else clusters_query
        query = clientJson['request_query']['query']
        numSentences = clientJson['request_query']['summarySentenceCount']
        queryType = clientJson['request_query']['type']

        if not m_infoManager.clientInitialized(clientId):
            return self.getErrorJson('Unknown client. Please reload page.')

        if topicId != m_infoManager.getTopicId(clientId):
            return self.getErrorJson('Topic ID not yet initialized by client: {}'.format(topicId))

        corpus = m_infoManager.getCorpus(clientId)
        sentences = None
        doc_sent_indices_to_use = None
        if clusters_query:
            doc_sent_indices = []
            for cluster_query in clusters_query:
                cluster = self._get_clusters(corpus, cluster_query.cluster_id, cluster_query.cluster_type)
                doc_sent_indices.append({DocSent(mention['doc_id'], mention['sent_idx']) for mention in cluster['mentions']})
            if any(doc_sent_indices):
                doc_sent_indices_to_use = set.intersection(*doc_sent_indices)
                sentences = self._get_sentences_for_query(doc_sent_indices_to_use, corpus)

        length_in_words = 0
        query_result = QueryResult([], clusters_query)
        if sentences is not None:
            if len(sentences) > 1:
                summarizer = get_item("bart_summarizer")
                summary_sents = summarizer.summarize(sentences)
            else:
                # No need to summarize one sentence
                summary_sents = [sent.spacy_rep for sent in sentences]

            query_result.result_sentences = [QueryResultSentence(self._split_sent_text_to_tokens(sent)) for sent in summary_sents]

            # Save queries and mark similar sentences to those used
            query_results_analyzer = m_infoManager.get_query_results_analyzer(clientId)
            query_results_analyzer.analyze_repeating(query_result)
            query_results_analyzer.add_query_results(query_result)

            length_in_words = 0

        reply = {
            "reply_query": {
                "queryResult": query_result.to_dict(),
                "textLength": length_in_words,
                "corefClustersMetas": self._get_clusters_filtered(COREF_TYPE_ENTITIES, corpus, doc_sent_indices_to_use),
                "eventsClustersMetas": self._get_clusters_filtered(COREF_TYPE_EVENTS, corpus, doc_sent_indices_to_use),
                "propositionClustersMetas": self._get_clusters_filtered(COREF_TYPE_PROPOSITIONS, corpus, doc_sent_indices_to_use)
            }
        }

        return json.dumps(reply)

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