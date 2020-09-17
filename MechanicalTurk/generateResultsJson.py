import sys
import json
from nltk.tokenize import word_tokenize
import os
sys.path.append('../evaluation')
from EvaluationUtils import computeAUCofScoresCurve, getLengthAtRouge
#from LitePyramidEvaluator import LitePyramidEvaluator
import numpy as np

'''
Run this standalone from a cmd.
Creates the results file for the different summarizers from a given DB JSON file. The script removes sessions with a specified amount of mistakes in the quality control questionaire. This allows running the same CompareSimulaitionResults notebook on these outputs to eventually get a final results and comparison file.
'''


DB_FILE = '../RealSessions/results_table_clean_fixed.json'
OUTPUT_JSON_FOLDER = '../RealSessions'
LITE_PYRAMID_MAP_FILEPATH = ''
IS_MTURK = True
ROUGE1_THRESHOLD = 0.37
ROUGE2_THRESHOLD = 0.075
ROUGEL_THRESHOLD = 0.31
ROUGESU_THRESHOLD = 0.14
AVERAGE_SESSION_X_INCREMENT = 25
SESSION_INTERSECTION_MIN_COUNT = -1 # minimum number sessions needed to average at the non-fully-intersecting x-value intervals (4 for Wild, -1 for controlled)
NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE = 4 # 4 for controlled sessions, 1 for wild sessions
# A suffix for the filename. If not needed, put an empty string:
OUTPUT_FILE_OPTIONAL_SUFFIX = ''
#OUTPUT_FILE_OPTIONAL_SUFFIX = 'FORCED'

# An optional dictionary of {topicId -> [workerId]} that forces only these sessions to be saved in the output file, even if they are shown to be filtered or failed. If not needed, set as None:
SESSIONS_TO_FORCE_KEEP = None


def readDbFile(dbFilepath):
    with open(dbFilepath, 'r') as jsonFile:
        dbDict = json.load(jsonFile)
        allSessionsList = dbDict['info']
        allSentencesUsedIdToText = dbDict['sentences']
        allCorporaNameToId = dbDict['corpora']
    
    print('Found {} sessions total'.format(len(allSessionsList)))
    print('Num different workers: {}'.format(len(set([session['workerId'] for session in allSessionsList]))))
    
    return allSessionsList, allSentencesUsedIdToText, allCorporaNameToId


def selectSessionsToKeep(allSessionsList, allCorporaNameToId, sessionsToForceKeep=None):
    
    sessionsByTopicIdToKeep = {} # summarizer -> topicId -> [sessionInfo]
    filteredSessions = []
    failedSessions = []
    
    for session in allSessionsList:
        
        if IS_MTURK:
            
            # skip over sessions that have less than 3 iterations:
            if len(session['summaries']) < 3:
                filteredSessions.append((session, 'Less than 3 iterations'))
                continue
                
            # check the answers of the questionnaire:
            numMistakes = 0
            repeatedQuestionAnswers = {}
            for qId, answer in session['questionnaire'].items():
                # user answered True on a definite False statement:
                if qId.startswith('neg_') and answer == True:
                    numMistakes += 1
                # user answered False on a definite True statement:
                elif qId.startswith('pos_') and answer == False:
                    numMistakes += 1
                else:
                    # collect the answer of repeated questions
                    qIdParts = qId.split('_')
                    if len(qIdParts) == 2: # such question IDs look like "261_1"
                        repeatedQuestionAnswers[qId] = answer
            # if there is more than one answer for the repeated questions, it's a mistake:
            if len(set(repeatedQuestionAnswers.values())) > 1:
                numMistakes += 1
            # if the number of definite questionnaire mistakes is more than NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE, then this is likely insencere work:
            if NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE > 0 and numMistakes <= NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE:
                print('Not filtering: {} mistake in questionnaire found (Assignment {} Worker {})'.format(NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE, session['assignmentId'], session['workerId']))
            if numMistakes > NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE:
                filteredSessions.append((session, 'More than {} definite questionnaire mistakes ({})'.format(NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE, numMistakes)))
                failedSessions.append(session)
                continue
            
        # get the topic ID -- the topicId field might be the ID or it might be the name:
        topicId = getTopidId(session, allCorporaNameToId)
        summType = getSummaryType(session) # e.g. SummarizerClustering
        sessionsByTopicIdToKeep.setdefault(summType, {}).setdefault(topicId, []).append(session)
        

    print('Number of unused sessions: ' + str(len(filteredSessions)))
    print('Sessions kept:')
    for summType in sessionsByTopicIdToKeep:
        print('\t' + summType)
        for topicId in sessionsByTopicIdToKeep[summType]:
            print('\t\t{}: {}'.format(topicId, len(sessionsByTopicIdToKeep[summType][topicId])))
    
    return sessionsByTopicIdToKeep, filteredSessions, failedSessions
    

def getStats(sessionsToKeep):
    for summarizer in sessionsToKeep:
        for topicId in sessionsToKeep[summarizer]:
            initialRatingsInTopic = []
            queryRatingsInTopic = []
            for session in sessionsToKeep[summarizer][topicId]:
                for summInfoIdx, summInfo in enumerate(session['summaries']):
                    if summInfoIdx == 0:
                        initialRatingsInTopic.append(summInfo['rating'])
                    else:
                        queryRatingsInTopic.append(summInfo['rating'])

def outputToJson(sessionsToKeep, allSentencesIdToText, outputFolderpath): #, litePyramidEvaluator):
    for summarizer in sessionsToKeep:
        outputDict = {}
        outputDictAvgPerTopic = {}
        for topicId in sessionsToKeep[summarizer]:
            ## for now use the session with the most iterations
            #sessionInfo = max(sessionsToKeep[summarizer][topicId], key=lambda s:len(s['summaries']))
            
            outputDict[topicId] = []
            for sessionInfo in sessionsToKeep[summarizer][topicId]:
            
                sessionDict = { 'scores': [], 'auc': [], 'id': sessionInfo['workerId'], 
                                'lenAtThreshold': {}, 'questionnaireRatings':{}, 'totalTime':-1, 'exploreTime':-1, 'questionnaireTime':-1}
                summaryTextAccumulated = ''
                summaryTextLenAccumulated = 0
                summarySentenceIdsAccumulated = []
                for summInfo in sessionInfo['summaries']:
                    summInfoDict = {}
                    summInfoDict['results'] = summInfo['rouge'][1]
                    summarySentenceIdsAccumulated.extend(summInfo['summary'])
                    #litePyrRecallScore = litePyramidEvaluator.getLitePyramidScore(summarySentenceIdsAccumulated, topicId)
                    #summInfoDict['results'].setdefault('litepyramid', {})['recall'] = litePyrRecallScore
                    summarySentenceIds = summInfo['summary']
                    iterationSummaryText = ' '.join(allSentencesIdToText[sentId] for sentId in summarySentenceIds)
                    summaryTextAccumulated += iterationSummaryText + ' '
                    summaryTextLenAccumulated += len(word_tokenize(iterationSummaryText))
                    summInfoDict['summary'] = summaryTextAccumulated
                    summInfoDict['summary_len'] = summaryTextLenAccumulated
                    summInfoDict['sentenceIds'] = summInfo['summary']
                    summInfoDict['rating'] = summInfo['rating']
                    summInfoDict['query'] = summInfo['query']
                    
                    sessionDict['scores'].append(summInfoDict)
                
                sessionDict['auc'] = computeAUCofScoresCurve(sessionDict['scores'])
                sessionDict['lenAtThreshold'] = getLengthAtRouge(sessionDict['scores'], rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD, metricType='f1')
                if 'questionnaireRatings' in sessionInfo:
                    sessionDict['questionnaireRatings'] = sessionInfo['questionnaireRatings']
                sessionDict['exploreTime'] = sessionInfo['exploreTime']
                sessionDict['totalTime'] = sessionInfo['totalTime']
                sessionDict['questionnaireTime'] = sessionInfo['totalTime'] - sessionInfo['exploreTime']
                
                outputDict[topicId].append(sessionDict)
                
            # get the "average session" of the topic's list of sessions:
            averageSessionScoresList = getAvgStdOfSessionsList(outputDict[topicId])
            averageSessionDict = {}
            averageSessionDict['scores'] = averageSessionScoresList
            averageSessionDict['auc'] = computeAUCofScoresCurve(averageSessionScoresList)
            averageSessionDict['lenAtThreshold'] = getLengthAtRouge(averageSessionScoresList, rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD, metricType='f1')
            averageSessionDict['id'] = 'average'
            averageSessionDict['numSessions'] = len(outputDict[topicId])
            if 'questionnaireRatings' in sessionInfo:
                averageSessionDict['questionnaireRatings'] = getAvgStdOfQuestionaireRatings([sessionInfo['questionnaireRatings'] for sessionInfo in sessionsToKeep[summarizer][topicId]])
            averageSessionDict['exploreTime'] = np.mean([sessionDict['exploreTime'] for sessionDict in outputDict[topicId]])
            averageSessionDict['totalTime'] = np.mean([sessionDict['totalTime'] for sessionDict in outputDict[topicId]])
            averageSessionDict['questionnaireTime'] = np.mean([sessionDict['questionnaireTime'] for sessionDict in outputDict[topicId]])
            outputDictAvgPerTopic[topicId] = [averageSessionDict]
                
        
        # get the average of the averaged topics (overall scores):
        sessionsListTopicsAvg = [outputDictAvgPerTopic[topicId][0] for topicId in outputDictAvgPerTopic]
        averageSessionScoresList = getAvgStdOfSessionsList(sessionsListTopicsAvg)
        averageSessionDict = {}
        averageSessionDict['scores'] = averageSessionScoresList
        averageSessionDict['auc'] = computeAUCofScoresCurve(averageSessionScoresList)
        averageSessionDict['lenAtThreshold'] = getLengthAtRouge(averageSessionScoresList, rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD, metricType='f1')
        averageSessionDict['id'] = 'averageOfAverageOfTopics'
        averageSessionDict['numSessions'] = len(sessionsListTopicsAvg)
        if 'questionnaireRatings' in sessionsListTopicsAvg[0]:
            averageSessionDict['questionnaireRatings'] = getAvgStdOfQuestionaireRatings([sessionInfo['questionnaireRatings'] for sessionInfo in sessionsListTopicsAvg])
        averageSessionDict['exploreTime'] = np.mean([sessionDict['exploreTime'] for sessionDict in sessionsListTopicsAvg])
        averageSessionDict['totalTime'] = np.mean([sessionDict['totalTime'] for sessionDict in sessionsListTopicsAvg])
        averageSessionDict['questionnaireTime'] = np.mean([sessionDict['questionnaireTime'] for sessionDict in sessionsListTopicsAvg])
        outputDictAvgPerTopic['AVG'] = [averageSessionDict]
        
        
        outputFilepath = os.path.join(outputFolderpath, 'results_{}{}.json'.format(summarizer, OUTPUT_FILE_OPTIONAL_SUFFIX))
        with open(outputFilepath, 'w') as fp:
            json.dump(outputDict, fp, indent=4, sort_keys=True)
            
        outputFilepathAvg = os.path.join(outputFolderpath, 'results_{}{}_avg.json'.format(summarizer, OUTPUT_FILE_OPTIONAL_SUFFIX))
        with open(outputFilepathAvg, 'w') as fp:
            json.dump(outputDictAvgPerTopic, fp, indent=4, sort_keys=True)
            
    
def getAvgStdOfQuestionaireRatings(listOfDicts):
    dictOfLists = {}
    for results in listOfDicts:
        for qId, qInfo in results.items():
            if qId in dictOfLists:
                if qInfo['text'] == dictOfLists[qId]['text']:
                    dictOfLists[qId]['rating'].append(qInfo['rating'])
            else:
                dictOfLists[qId] = {'text':qInfo['text'], 'rating':[qInfo['rating']]}
    
    dictOverall = {}
    for qId, qInfo in dictOfLists.items():
        dictOverall[qId] = {'text':qInfo['text'], 'rating':np.mean(qInfo['rating']), 'ratingStd':np.std(qInfo['rating'])}
        
    return dictOverall
    

def getAvgStdOfSessionsList(sessions):
    # Get values average and std of the sessions in this topic.
    # Loop through X values incrementing at 25 words, and get the interpolated values from each session. Then avg and std those values.
    
    # get min and max intersecting summary lengths in the list of sessions:
    minSummLen, maxSummLen = getMinMaxXvalsInSessions(sessions, minNumberOfIntersectingSessions=SESSION_INTERSECTION_MIN_COUNT)
    # list all the X vals (word lengths) we'll use:
    xVals = [minSummLen] + [x for x in range(0, maxSummLen, AVERAGE_SESSION_X_INCREMENT) if x > minSummLen] + [maxSummLen]
    # get the Y vals (ROUGE dictionaries) for the needed X vals:
    allSessionsYs = {xVal:[] for xVal in xVals}
    for session in sessions:
        for xVal in xVals:
            yValRougeDict = getInterpolatedRougeDict(xVal, session['scores'])
            if yValRougeDict != None:
                allSessionsYs[xVal].append(yValRougeDict)
    
    # get the average and StDs for the list of Ys:
    avgSessionInfo = []
    for xVal in xVals:
        avgRougeDict, stdRougeDict = getAvgStdRougeDict(allSessionsYs[xVal])
        newIteration = {}
        newIteration['results'] = avgRougeDict
        newIteration['results_std'] = stdRougeDict
        newIteration['summary_len'] = xVal
        avgSessionInfo.append(newIteration)
    
    return avgSessionInfo
    
def getMinMaxXvalsInSessions(sessions, minNumberOfIntersectingSessions=-1):
    # Finds the min and max x-vals for which to calculate averages of the given sessions.
    # Returns the value at which there is atleast minNumberOfIntersectingSessions sessions with values there.
    # If -1 is passed (default), then there has to be fill intersection (all sessions have values there).
    # If a number higher than the number of sessions is passed, then also requires full intersection.
    
    # the start x-val that is k-lowest is the one that has k sessions starting at that or a higher x-val:
    allStartIndices = [session['scores'][0]['summary_len'] for session in sessions]
    allStartIndices.sort()
    if minNumberOfIntersectingSessions > -1 and minNumberOfIntersectingSessions < len(allStartIndices):
        minSummLen = allStartIndices[minNumberOfIntersectingSessions-1]
    else:
        minSummLen = allStartIndices[-1]
    
    # the end x-val that is k-highest is the one that has k sessions ending at that or a lower x-val:
    allEndIndices = [session['scores'][-1]['summary_len'] for session in sessions]
    allEndIndices.sort()
    if minNumberOfIntersectingSessions > -1 and minNumberOfIntersectingSessions < len(allStartIndices):
        maxSummLen = allEndIndices[-minNumberOfIntersectingSessions]
    else:
        maxSummLen = allEndIndices[0]
    
    ## maximum of first iterations of sessions (this is the minumum intersecting X)
    #minSummLen = max([session['scores'][0]['summary_len'] for session in sessions])
    ## minimum of last iterations of sessions (this is the maximum intersecting X)
    #maxSummLen = min([session['scores'][-1]['summary_len'] for session in sessions])
    
    return minSummLen, maxSummLen
    
        
def getInterpolatedRougeDict(wordCount, session):
    minSummLen = session[0]['summary_len']
    maxSummLen = session[-1]['summary_len']
    if wordCount < minSummLen or wordCount > maxSummLen:
        return None
        
    for iterationIdx, iteration in enumerate(session):
        iterationSummLen = iteration['summary_len']
        if iterationSummLen == wordCount:
            return iteration['results'].copy()
        
        nextIteration = session[iterationIdx + 1]
        nextIterationSummLen = nextIteration['summary_len']
        if iterationSummLen < wordCount and wordCount < nextIterationSummLen:
            iterationScores = {}
            for rougeMetric in iteration['results']:
                for metric in iteration['results'][rougeMetric]:
                    iterationScores.setdefault(rougeMetric, {})[metric] = getInterpolatedYval(
                        [iterationSummLen, nextIterationSummLen],
                        [iteration['results'][rougeMetric][metric], nextIteration['results'][rougeMetric][metric]],
                        0,
                        wordCount)
            return iterationScores

    
def getInterpolatedYval(xList, yList, idxStart, neededXval):
    # gets the y value at the neededXval, between idxStart and idxStart+1:
    return np.interp(neededXval, xList[idxStart:idxStart+2], yList[idxStart:idxStart+2])


def getAvgStdRougeDict(allSessionsYs):
    avgScoresDict = {}
    stdScoresDict = {}
    for rougeMetric in allSessionsYs[0]:
        for metric in allSessionsYs[0][rougeMetric]:
            curMetricScoreList = [session[rougeMetric][metric] for session in allSessionsYs]
            avgScoresDict.setdefault(rougeMetric, {})[metric] = np.mean(curMetricScoreList)
            stdScoresDict.setdefault(rougeMetric, {})[metric] = np.std(curMetricScoreList)
    return avgScoresDict, stdScoresDict


def forceKeepSpecificSessions(sessionsToForceKeep, sessionsToKeep, filteredSessions, allCorporaNameToId):
    # sessionsToForceKeep: topicId -> listOfWorkerIds
    # Goes through the sessions in all of sessionsToKeep, filteredSessions and keeps sessions specified in sessionsToForceKeep
    
    sessionsToKeepFinal = {}
    
    # look for sessions to force keep in the sessionsByTopicIdToKeep:
    for summarizer in sessionsToKeep:
        for topicId in sessionsToKeep[summarizer]:
            for sessionInfo in sessionsToKeep[summarizer][topicId]:
                workerId = sessionInfo['workerId']
                if topicId in sessionsToForceKeep and workerId in sessionsToForceKeep[topicId]:
                    sessionsToKeepFinal.setdefault(summarizer, {}).setdefault(topicId, []).append(sessionInfo)
                    
    # look for sessions to force keep in the filtered sessions:
    for sessionInfo, filterReason in filteredSessions:
        topicId = getTopidId(sessionInfo, allCorporaNameToId)
        workerId = sessionInfo['workerId']
        if topicId in sessionsToForceKeep and workerId in sessionsToForceKeep[topicId]:
            summaryType = getSummaryType(sessionInfo)
            sessionsToKeepFinal.setdefault(summaryType, {}).setdefault(topicId, []).append(sessionInfo)
            print('Force kept a filtered session ({}):'.format(filterReason))
            print('\tTopic ID: {}'.format(topicId))
            print('\tWorker ID: {}'.format(sessionInfo['workerId']))
            print('\tHIT ID: {}'.format(sessionInfo['hitId']))
            print('\tAssignment ID: {}'.format(sessionInfo['assignmentId']))
            print('----------------')
    
    return sessionsToKeepFinal
            
    
def getSummaryType(session):
    return session['summType'].split('.')[2][:-2] # e.g. <class 'QFSE.SummarizerClustering.SummarizerClustering'> -> SummarizerClustering
    
def getTopidId(session, allCorporaNameToId):
    # get the topic ID -- the topicId field might be the ID or it might be the name:
    topicName = session['topicId']
    if topicName in allCorporaNameToId.values():
        topicId = topicName
    else:
        topicId = allCorporaNameToId[session['topicId']]
    return topicId
        

def main(dbFilepath, outputFolderpath, litePyramidMapFilepath, sessionsToForceKeep):
    # get the data from the DB_FILE for the actual sessions:
    allSessionsList, allSentencesUsedIdToText, allCorporaNameToId = readDbFile(dbFilepath)
    
    # there will be several sessions per algo/interface/topic/questionnaireBatch
    # try to find the best of the sessions according to different heuristics:
    sessionsByTopicIdToKeep, filteredSessions, failedSessions = selectSessionsToKeep(allSessionsList, allCorporaNameToId)
    
    print('\n--- Filtered ---')
    for filteredSession in filteredSessions:
        print(filteredSession[1])
        print('\tHIT ID: {}'.format(filteredSession[0]['hitId']))
        print('\tAssignment ID: {}'.format(filteredSession[0]['assignmentId']))
        print('\tWorker ID: {}'.format(filteredSession[0]['workerId']))
    print('----------------\n')
    print('\n--- Failed ---')
    failedAssignmentIds = []
    for failedSession in failedSessions:
        print('Assignment ID: {}'.format(failedSession['assignmentId']))
        print('\tWorker ID: {}'.format(failedSession['workerId']))
        print('\tHIT ID: {}'.format(failedSession['hitId']))
        failedAssignmentIds.append(failedSession['assignmentId'])
    print('----------------\n')
    print('\n--- Passed ---')
    for session in allSessionsList:
        if session['assignmentId'] not in failedAssignmentIds:
            print('Assignment ID: {}'.format(session['assignmentId']))
            print('\tWorker ID: {}'.format(session['workerId']))
            print('\tHIT ID: {}'.format(session['hitId']))
    print('----------------\n')
    
    # if we force to keep specific sessions, then extract those from all the previous filtering we did:
    if sessionsToForceKeep != None:
        sessionsByTopicIdToKeep = forceKeepSpecificSessions(sessionsToForceKeep, sessionsByTopicIdToKeep, filteredSessions, allCorporaNameToId)
    
    #litePyramidEvaluator = LitePyramidEvaluator(litePyramidMapFilepath)
    
    # output the score, and summary info to a JSON (like simulations):
    outputToJson(sessionsByTopicIdToKeep, allSentencesUsedIdToText, outputFolderpath)#, litePyramidEvaluator=litePyramidEvaluator)
    
    
if __name__ == '__main__':
    main(DB_FILE, OUTPUT_JSON_FOLDER, LITE_PYRAMID_MAP_FILEPATH, SESSIONS_TO_FORCE_KEEP)