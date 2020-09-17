import sys
import json
from nltk.tokenize import word_tokenize
import os
sys.path.append('..')
from EvaluationUtils import computeAUCofScoresCurve, getLengthAtRouge
import numpy as np

'''
Run this standalone from a cmd.
Creates the results file for the different summarizers from a given DB JSON file. The script selects a single session per topic for each of the summarizers, and outputs it to a JSON similar to that of of a simulation JSON output file. This allows running the same CompareSimulaitionResults notebook on these outputs to eventually get a final results and comparison file.
'''


#SIMULATION_RESULTS_FILEPATH = 'results/resultsClusteringSpacyKeyphrases75_2/results.json'
#OUTPUT_JSON_FOLDER = 'results/resultsClusteringSpacyKeyphrases75_2'
#SIMULATION_RESULTS_FILEPATH = 'results/resultsTRKeyphrases75_2/results.json'
#OUTPUT_JSON_FOLDER = 'results/resultsTRKeyphrases75_2'
#SIMULATION_RESULTS_FILEPATH = 'results/resultsTROracleLite75/results.json'
#OUTPUT_JSON_FOLDER = 'results/resultsTROracleLite75'
SIMULATION_RESULTS_FILEPATH = 'results/resultsClusteringSpacyOracleLite75/results.json'
OUTPUT_JSON_FOLDER = 'results/resultsClusteringSpacyOracleLite75'
ROUGE1_THRESHOLD = 0.37
ROUGE2_THRESHOLD = 0.07
ROUGEL_THRESHOLD = 0.29
ROUGESU_THRESHOLD = 0.11
AVERAGE_SESSION_X_INCREMENT = 25
MIN_X_VAL_OF_AVERAGE = 105 # -1 means default (use overall min)
MAX_X_VAL_OF_AVERAGE = 333 # -1 means default (use overall max)

IGNORE_TOPIC_IDS = ['D0602']

def readSimulationResultsFile(simulationResultsFilepath):
    with open(simulationResultsFilepath, 'r') as jsonFile:
        allSessions = json.load(jsonFile)
    
    return allSessions # {topicId -> [{'auc':[{}],'id':<>,'lenAtThreshold':{},'scores':[{}]}]}

def outputToJson(allSessions, outputFolderpath):
    outputDictAvgPerTopic = {}
    for topicId in allSessions:
        if topicId not in IGNORE_TOPIC_IDS:
            # get the "average session" of the topic's list of sessions:
            averageSessionScoresList = getAvgStdOfSessionsList(allSessions[topicId])
            averageSessionDict = {}
            averageSessionDict['scores'] = averageSessionScoresList
            averageSessionDict['auc'] = computeAUCofScoresCurve(averageSessionScoresList)
            averageSessionDict['lenAtThreshold'] = getLengthAtRouge(averageSessionScoresList, rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD)
            averageSessionDict['id'] = 'average'
            averageSessionDict['numSessions'] = len(allSessions[topicId])
            outputDictAvgPerTopic[topicId] = [averageSessionDict]
            
    # get the average of the averaged topics (overall scores):
    sessionsListTopicsAvg = [outputDictAvgPerTopic[topicId][0] for topicId in outputDictAvgPerTopic]
    averageSessionScoresList = getAvgStdOfSessionsList(sessionsListTopicsAvg, minXval=MIN_X_VAL_OF_AVERAGE, maxXval=MAX_X_VAL_OF_AVERAGE)
    averageSessionDict = {}
    averageSessionDict['scores'] = averageSessionScoresList
    averageSessionDict['auc'] = computeAUCofScoresCurve(averageSessionScoresList)
    averageSessionDict['lenAtThreshold'] = getLengthAtRouge(averageSessionScoresList, rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD)
    averageSessionDict['id'] = 'averageOfTopics'
    averageSessionDict['numSessions'] = len(sessionsListTopicsAvg)
    outputDictAvgPerTopic['AVG'] = [averageSessionDict]
            
    outputFilepathAvg = os.path.join(outputFolderpath, 'results_avg.json')
    with open(outputFilepathAvg, 'w') as fp:
        json.dump(outputDictAvgPerTopic, fp, indent=4, sort_keys=True)
            
    
def getAvgStdOfSessionsList(sessions, minXval=-1, maxXval=-1):
    # Get values average and std of the sessions in this topic.
    # Loop through X values incrementing at 25 words, and get the interpolated values from each session. Then avg and std those values.
    
    # get min and max intersecting summary lengths in the list of sessions:
    if minXval == -1:
        minSummLen = max([session['scores'][0]['summary_len'] for session in sessions]) # maximum of first iterations of sessions (this is the minumum intersecting X)
    else:
        minSummLen = minXval
    if maxXval == -1:
        maxSummLen = min([session['scores'][-1]['summary_len'] for session in sessions]) # minimum of last iterations of sessions (this is the maximum intersecting X)
    else:
        maxSummLen = maxXval
        
    # list all the X vals (word lengths) we'll use:
    xVals = [minSummLen] + [x for x in range(0, maxSummLen+1, AVERAGE_SESSION_X_INCREMENT) if x > minSummLen] + [maxSummLen]
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



def main(simulationResultsFilepath, outputFolderpath):
    # get the data from the DB_FILE for the sessions:
    allSessions = readSimulationResultsFile(simulationResultsFilepath)
    
    # output the score, and average session info to a JSON:
    outputToJson(allSessions, outputFolderpath)
    
    
if __name__ == '__main__':
    main(SIMULATION_RESULTS_FILEPATH, OUTPUT_JSON_FOLDER)