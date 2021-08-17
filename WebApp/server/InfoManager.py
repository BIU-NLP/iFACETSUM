import threading
import logging
import traceback
import time
import WebApp.server.params as Params
from shutil import copyfile
from operator import itemgetter
import json
import os
from datetime import datetime

from QFSE.models import UIAction
from data import Config

class InfoManager:
    def __init__(self):
        self.m_clientsInfo = {}
        # create a lock for the tables, for possible concurrent editting:
        self.lockTables = threading.Lock()
        # the ds that holds the serializations of all the clients (dictionary of clientId -> saveDataDict)
        # this is so that only clients that need resaving are reserialized.
        self.savedInfo = {}
        # the ds that holds all the sentences used so far by all clients saved until now (dict of sentId -> sentText)
        self.sentencesUsed = {}
        # run a thread that saves the data once in a while:
        threadSaveDataToDatabase = threading.Thread(target=self.saveDataBackgroundFunc, args=())
        threadSaveDataToDatabase.start()

    def createClientFunc(self, clientId):
        if clientId not in self.m_clientsInfo:
            self.m_clientsInfo[clientId] = {}

    def createClient(self, clientId):
        return self.handleRequest(clientId, self.createClientFunc, [clientId], 'Failed to create client {}'.format(clientId))

    def clientInitialized(self, clientId):
        return clientId in self.m_clientsInfo and 'summarizer' in self.m_clientsInfo[clientId]

    def initClientFunc(self, clientId, corpus, suggQuerGen, numSuggQueries, summarizer, topicId, questionnaireBatchIndex, timeAllowed, assignmentId,
                       hitId, workerId, turkSubmitTo, query_results_analyzer):
        self.m_clientsInfo[clientId]['corpus'] = corpus
        self.m_clientsInfo[clientId]['suggQuerGen'] = suggQuerGen
        self.m_clientsInfo[clientId]['summarizer'] = summarizer
        self.m_clientsInfo[clientId]['topicId'] = topicId
        self.m_clientsInfo[clientId]['questionnaireBatchIndex'] = questionnaireBatchIndex
        self.m_clientsInfo[clientId]['timeAllowed'] = timeAllowed
        self.m_clientsInfo[clientId]['assignmentId'] = assignmentId
        self.m_clientsInfo[clientId]['hitId'] = hitId
        self.m_clientsInfo[clientId]['workerId'] = workerId
        self.m_clientsInfo[clientId]['turkSubmitTo'] = turkSubmitTo
        self.m_clientsInfo[clientId]['startTime'] = time.time()
        self.m_clientsInfo[clientId]['haveChanges'] = True
        self.m_clientsInfo[clientId]['endTime'] = -1
        self.m_clientsInfo[clientId]['exploreTime'] = -1
        self.m_clientsInfo[clientId]['comments'] = ''
        self.m_clientsInfo[clientId]['questionnaireRatings'] = {}
        self.m_clientsInfo[clientId]['query_results_analyzer'] = query_results_analyzer
        self.m_clientsInfo[clientId]['ui_actions'] = []
        # self.m_clientsInfo[clientId]['suggestedQueries'] = suggQuerGen.getSuggestionsFromToIndices(0, numSuggQueries-1)
        logging.info('Client initialized: {}'.format(clientId))

    def initClient(self, clientId, corpus, suggQuerGen, numSuggQueries, summarizer, topicId, questionnaireBatchIndex, timeAllowed, assignmentId,
                   hitId, workerId, turkSubmitTo, query_results_analyzer):
        return self.handleRequest(clientId, self.initClientFunc,
                                  [clientId, corpus, suggQuerGen, numSuggQueries, summarizer, topicId, questionnaireBatchIndex, timeAllowed,
                                   assignmentId, hitId, workerId, turkSubmitTo, query_results_analyzer],
                                  'Failed to initialize client {}'.format(clientId))

    def setStartTimeOfInteractionFunc(self, clientId):
        self.m_clientsInfo[clientId]['startTime'] = time.time()

    def setStartTimeOfInteraction(self, clientId):
        return self.handleRequest(clientId, self.setStartTimeOfInteractionFunc, [clientId],
                                  'Failed to set start time for client {}'.format(clientId))

    def getQuestionnaire(self, clientId):
        return self.m_clientsInfo[clientId]['corpus'].getQuestionnaire(
            self.m_clientsInfo[clientId]['questionnaireBatchIndex'])

    def getTopicId(self, clientId):
        return self.m_clientsInfo[clientId]['topicId']

    def getCorpus(self, clientId):
        return self.m_clientsInfo[clientId]['corpus']

    def getSummarizer(self, clientId):
        # When the summarizer is requested, it most likely means that a summary is generated, meaning there is a
        # change in the data. We don't generate the summary in this class because it may take a long time and
        # hold up other requests. The web server handler is per request in different threads, so we let it
        # take care of generated the summary.
        self.m_clientsInfo[clientId]['haveChanges'] = True
        return self.m_clientsInfo[clientId]['summarizer']

    def get_query_results_analyzer(self, clientId):
        return self.m_clientsInfo[clientId]['query_results_analyzer']

    def setSubmitInfoFunc(self, clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser):
        self.setQuestionnaireAnswersFunc(clientId, questionAnswersDict)
        self.m_clientsInfo[clientId]['exploreTime'] = timeUsedForExploration
        self.m_clientsInfo[clientId]['comments'] = commentsFromUser

    def setSubmitInfo(self, clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser):
        return self.handleRequest(clientId, self.setSubmitInfoFunc,
                                  [clientId, questionAnswersDict, timeUsedForExploration, commentsFromUser],
                                  'Failed to set submit info for client {}'.format(clientId))

    def setQuestionnaireAnswersFunc(self, clientId, questionAnswersDict):
        self.m_clientsInfo[clientId]['corpus'].setQuestionnaireAnswers(
            self.m_clientsInfo[clientId]['questionnaireBatchIndex'], questionAnswersDict)

    def setQuestionnaireAnswers(self, clientId, questionAnswersDict):
        return self.handleRequest(clientId, self.setQuestionnaireAnswersFunc, [clientId, questionAnswersDict],
                                  'Failed to set questionnaire answers for client {}'.format(clientId))

    def setIterationRatingsFunc(self, clientId, iterationRatingsDict):
        self.m_clientsInfo[clientId]['summarizer'].setIterationRatings(iterationRatingsDict)

    def setIterationRatings(self, clientId, iterationRatingsDict):
        return self.handleRequest(clientId, self.setIterationRatingsFunc, [clientId, iterationRatingsDict],
                                  'Failed to set star ratings for client {}'.format(clientId))

    def setQuestionnaireRatingsFunc(self, clientId, questionnaireRatingsDict):
        # dictionary of {questionId -> {'text': questionText, 'rating': rating}}
        for questionId, qInfo in questionnaireRatingsDict.items():
            self.m_clientsInfo[clientId]['questionnaireRatings'][questionId] = qInfo

    def setQuestionnaireRatings(self, clientId, questionnaireRatingsDict):
        return self.handleRequest(clientId, self.setQuestionnaireRatingsFunc, [clientId, questionnaireRatingsDict],
                                  'Failed to set questionnaire ratings for client {}'.format(clientId))

    def setEndTimeFunc(self, clientId):
        self.m_clientsInfo[clientId]['endTime'] = time.time()

    def setEndTime(self, clientId):
        return self.handleRequest(clientId, self.setEndTimeFunc, [clientId],
                                  'Failed to set end time for client {}'.format(clientId))

    def add_ui_action_log(self, clientId, ui_action: UIAction):
        self.m_clientsInfo[clientId]['ui_actions'].append(ui_action)

    def saveDataBackgroundFunc(self):
        while True:
            time.sleep(Params.time_to_sleep_between_background_save)

            self.lockTables.acquire()

            if self.haveAnyChanges():
                logging.info('Saving data in background.')
                if self.saveDataToDB():
                    logging.info('Saved in background successfully.')
                else:
                    logging.error('Save in background failed.')

            self.lockTables.release()

    def haveAnyChanges(self):
        for clientId in self.m_clientsInfo:
            if self.clientHasChanges(clientId):
                return True
        return False

    def clientHasChanges(self, clientId):
        return 'haveChanges' in self.m_clientsInfo[clientId] and self.m_clientsInfo[clientId]['haveChanges']

    def clientIsReal(self, clientId):
        '''
        Checks whether the client is of a real session or a simulation/preview (such as for AMT previewing)
        :param clientId:
        :return:
        '''
        if 'assignmentId' in self.m_clientsInfo[clientId] and \
                self.m_clientsInfo[clientId]['assignmentId'] != 'ASSIGNMENT_ID_NOT_AVAILABLE':
            return True
        else:
            # mark this client that it shouldn't be saved:
            if 'haveChanges' in self.m_clientsInfo[clientId]:
                self.m_clientsInfo[clientId]['haveChanges'] = False
            return False

    def saveDataToDB(self):
        try:
            logging.info('Making backup copy of db.')
            # make a backup of the existing db files before updating them:
            # self.backupFile(params.table_summaries_path)
            # self.backupFile(params.table_questions_path)
            self.backupFile(Params.table_results_path)

            # put the dataframes back to the csv files:
            logging.info('Saving updated tables to db.')

            # reassemble the save info for the clients that made changes:
            failedClients = []
            for clientId in self.m_clientsInfo:
                try:
                    if self.clientHasChanges(clientId):# and self.clientIsReal(clientId):
                        saveDict = {}
                        saveDict['clientId'] = clientId
                        saveDict['topicId'] = self.m_clientsInfo[clientId]['topicId']
                        # saveDict['timeAllowed'] = self.m_clientsInfo[clientId]['timeAllowed']
                        # #saveDict['startTime'] = self.m_clientsInfo[clientId]['startTime']
                        # saveDict['startTime'] = datetime.fromtimestamp(self.m_clientsInfo[clientId]['startTime']).strftime("%Y/%m/%d %H:%M:%S")
                        # saveDict['endTime'] = self.m_clientsInfo[clientId]['endTime']
                        # saveDict['totalTime'] = self.m_clientsInfo[clientId]['endTime'] - self.m_clientsInfo[clientId]['startTime']
                        # saveDict['exploreTime'] = self.m_clientsInfo[clientId]['exploreTime']
                        saveDict['previous_results'] = [x.to_dict() for x in self.m_clientsInfo[clientId]['query_results_analyzer']._previous_results]
                        saveDict['ui_actions'] = [x.to_dict() for x in self.m_clientsInfo[clientId]['ui_actions']]
                        self.savedInfo[clientId] = saveDict
                        self.m_clientsInfo[clientId]['haveChanges'] = False
                except Exception as e:
                    logging.error('Error saving client: ' + str(e))
                    logging.error(traceback.format_exc())
                    failedClients.append(clientId)
                    if 'haveChanges' in self.m_clientsInfo[clientId]:
                        self.m_clientsInfo[clientId]['haveChanges'] = False # don't try to save again

            # put together the list of information:
            saveList = [saveDict for saveDict in self.savedInfo.values()]
            # sort the list by start time:
            saveList = sorted(saveList, key=itemgetter('startTime'))
            dictForJson = {"info":saveList, "sentences":self.sentencesUsed ,"corpora":Config.CORPORA_IDS}
            # save the dictionary to the file as a json:
            with open(Params.table_results_path, 'w') as fp:
                json.dump(dictForJson, fp, indent=1)

            # if any of the clients failed to serialize for some reason, warn about it:
            if len(failedClients) > 0:
                logging.warning('Some clients were not saved: ' + str(failedClients))
                for clientId in failedClients:
                    if clientId in self.m_clientsInfo:
                        logging.warning('\t{}: {}'.format(clientId, str(self.m_clientsInfo[clientId])))

            return True

        except Exception as e:
            logging.error('Error saving to database: ' + str(e))
            logging.error(traceback.format_exc())
            return False

    def backupFile(self, filepath):
        # make a backup of the file in case the rewrite fails:
        backupPath = filepath + '.bkp'
        try:
            if os.path.exists(filepath):
                logging.info('Making backup copy of "' + filepath + '" to "' + backupPath)
                copyfile(filepath, backupPath)
            else:
                logging.info('No file to back up: ' + filepath)
        except Exception as e:
            logging.error('Failed to make a backup copy of "' + filepath + '" to "' + backupPath + ': ' + str(e))
            logging.error(traceback.format_exc())

    def handleException(self, message, exception):
        logging.error('{}: {}'.format(message, exception))
        logging.error(traceback.format_exc())
        return (False, message)

    def handleRequest(self, clientId, funcToExecute, argsForFunc, failMessage):
        self.lockTables.acquire()
        retVal = (True, '')
        try:
            funcToExecute(*argsForFunc)
        except Exception as e:
            retVal = (False, failMessage)
            logging.error('{}: {}'.format(failMessage, e))
            logging.error(traceback.format_exc())
        if clientId in self.m_clientsInfo:
            self.m_clientsInfo[clientId]['haveChanges'] = True
        self.lockTables.release()
        return retVal