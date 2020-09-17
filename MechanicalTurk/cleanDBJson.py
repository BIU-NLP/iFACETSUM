import json
from nltk.tokenize import word_tokenize
import os
import numpy as np

'''
Run this standalone from a cmd.
Creates a JSON file like the DB JSON file, but only with real MTURK sessions.
Also adds fields for the topicID and the number of summaries in each session.
'''


DB_FILE = 'SessionsCollected/controlled/results_table.json'
IS_MTURK = True

def readDbFile(dbFilepath):
    with open(dbFilepath, 'r') as jsonFile:
        dbDict = json.load(jsonFile)
        allSessionsList = dbDict['info']
        allSentencesUsedIdToText = dbDict['sentences']
        allCorporaNameToId = dbDict['corpora']
    
    print('Found {} sessions total'.format(len(allSessionsList)))
    
    return allSessionsList, allSentencesUsedIdToText, allCorporaNameToId

def selectSessionsToKeep(allSessionsList, allCorporaNameToId):
    sessionsByTopicIdToKeep = {} # summarizer -> topicId -> [sessionInfo]
    numPreviewsFound = 0
    numUnfinishedSessions = 0
    numSessionsKept = 0
    for session in allSessionsList:
        
        # skip over sessions that were just a preview:
        if session['assignmentId'] == 'ASSIGNMENT_ID_NOT_AVAILABLE':
            numPreviewsFound += 1
            continue
        # skip over sessions that were not finished:
        if session['endTime'] == -1:
            numUnfinishedSessions += 1
            continue
        # this is not a sandbox or test assignment:
        if IS_MTURK and 'www.mturk.com/mturk/externalSubmit' not in session['turkSubmitTo']:
            continue
        
        topicId = allCorporaNameToId[session['topicId']]
        summType = session['summType'].split('.')[2][:-2] # e.g. <class 'QFSE.SummarizerClustering.SummarizerClustering'> -> SummarizerClustering
        sessionsByTopicIdToKeep.setdefault(summType, {}).setdefault(topicId, []).append(session)
        numSessionsKept += 1

    print('Num preview sessions: {}'.format(numPreviewsFound))
    print('Num unfinished sessions: {}'.format(numUnfinishedSessions))
    print('Num sessions kept: {}'.format(numSessionsKept))
    for summType in sessionsByTopicIdToKeep:
        print('\t' + summType)
        for topicId in sessionsByTopicIdToKeep[summType]:
            print('\t\t{}: {}'.format(topicId, len(sessionsByTopicIdToKeep[summType][topicId])))
    
    return sessionsByTopicIdToKeep
    
def outputToJson(sessionsToKeep, allSentencesIdToText, allCorporaNameToId, inputFilepath):
    outputDict = {"info":[], "sentences":allSentencesIdToText, "corpora":allCorporaNameToId}
    exploreTimes = []
    nonExploreTimes = []
    numExploreTimeExcluded = 0
    for summarizer in sessionsToKeep:
        for topicId in sessionsToKeep[summarizer]:
            for i in range(len(sessionsToKeep[summarizer][topicId])):
                sessionsToKeep[summarizer][topicId][i]['topicName'] = sessionsToKeep[summarizer][topicId][i]['topicId']
                sessionsToKeep[summarizer][topicId][i]['topicId'] = topicId
                sessionsToKeep[summarizer][topicId][i]['numSummaries'] = len(sessionsToKeep[summarizer][topicId][i]['summaries'])

                if sessionsToKeep[summarizer][topicId][i]['exploreTime'] < 420:
                    exploreTimes.append(sessionsToKeep[summarizer][topicId][i]['exploreTime'])
                    nonExploreTimes.append(sessionsToKeep[summarizer][topicId][i]['totalTime'] - sessionsToKeep[summarizer][topicId][i]['exploreTime'])
                else:
                    numExploreTimeExcluded += 1

            outputDict["info"].extend(sessionsToKeep[summarizer][topicId])
            
    print('Avg Explore Time: ' + str(np.mean(exploreTimes)))
    print('Avg Non-explore Time: ' + str(np.mean(nonExploreTimes)))
    print('Num times excluded: {} of {}'.format(numExploreTimeExcluded, len(exploreTimes)+numExploreTimeExcluded))
    
    outputFilepath = '{}_clean.json'.format(inputFilepath[:-5])
    with open(outputFilepath, 'w') as fp:
        json.dump(outputDict, fp, indent=1)#, sort_keys=True)
            
    

def main(dbFilepath):
    # get the data from the DB_FILE for the actual sessions:
    allSessionsList, allSentencesUsedIdToText, allCorporaNameToId = readDbFile(dbFilepath)
    
    # there will be several sessions per algo/interface/topic/questionnaireBatch
    # try to find the best of the sessions according to different heuristics:
    sessionsByTopicIdToKeep = selectSessionsToKeep(allSessionsList, allCorporaNameToId)
    
    # output the score, and summary info to a JSON (like simulations):
    outputToJson(sessionsByTopicIdToKeep, allSentencesUsedIdToText, allCorporaNameToId, dbFilepath)
    
    
if __name__ == '__main__':
    main(DB_FILE)