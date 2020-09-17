import sys
sys.path.append('.')


from QFSE.Utilities import REPRESENTATION_STYLE_BERT, REPRESENTATION_STYLE_SPACY, REPRESENTATION_STYLE_W2V
from QFSE.Utilities import loadSpacy, loadBert

SIMILARITY_STYLE = REPRESENTATION_STYLE_SPACY #REPRESENTATION_STYLE_BERT

loadSpacy()
if SIMILARITY_STYLE == REPRESENTATION_STYLE_BERT:
    loadBert()

from QFSE.SummarizerClustering import SummarizerClustering
from QFSE.SummarizerAddMore import SummarizerAddMore
from QFSE.SummarizerMMR import SummarizerMMR
from QFSE.SummarizerTextRankPlusLexical import SummarizerTextRankPlusLexical
from QFSE.SuggestedQueriesNgramCount import SuggestedQueriesNgramCount
from QFSE.SuggestedQueriesTextRank import SuggestedQueriesTextRank

from datetime import datetime as dt
import os
from evaluation.RougeEvaluator import getRougeScores
from evaluation.litepyramid.LitePyramidEvaluator import LitePyramidEvaluator
from evaluation.EvaluationUtils import computeAUCofScoresCurve, plotScoresCurve, getLengthAtRouge
import json
from nltk.tokenize import word_tokenize
import matplotlib.pyplot as plt
from sklearn.metrics import auc
import numpy as np
from QFSE.Corpus import Corpus
from data.Config import CORPORA_LOCATIONS, CORPUS_REFSUMMS_RELATIVE_PATH, CORPUS_QUESTIONNAIRE_RELATIVE_PATH, CORPORA_IDS_TO_NAMES
from QFSE.Utilities import nlp
import random

LITE_PYRAMID_MAP_FILEPATH = '' #'evaluation/litepyramid/sentence2scuMap.json' # if there isn't one, put a ''

SESSIONS_TO_RUN = [
    ('evaluation/simulations/simulationQueriesOracleLite.json', 'evaluation/simulations/resultsTROracleLite', SummarizerTextRankPlusLexical, SuggestedQueriesTextRank),
    ('evaluation/simulations/simulationQueriesOracleLite.json', 'evaluation/simulations/resultsClusteringSpacyOracleLite', SummarizerClustering, SuggestedQueriesNgramCount)
]

DUC_FOLDER = 'data/DUC2006Clean'
ROUGE1_THRESHOLD = 0.37
ROUGE2_THRESHOLD = 0.07
ROUGEL_THRESHOLD = 0.29
ROUGESU_THRESHOLD = 0.11



def evaluateSequenceOfSummaries(summaries, summariesSentIds, queriesInfo, topic, outputFolderForPlot, litePyramidEvaluator, isAccumulating=False, rouge1Thres=-1.0, rouge2Thres=-1.0, rougeLThres=-1.0, rougeSUThres=-1.0):
    topicPath = os.path.join(DUC_FOLDER, topic)
    if not os.path.isdir(topicPath):
        raise Exception('Error: Topic "{}" not found under "{}".'.format(topic, DUC_FOLDER))
    referenceSummariesFolder = os.path.join(topicPath, 'referenceSummaries')
    if not os.path.isdir(referenceSummariesFolder):
        raise Exception('Error: No reference summaries found for topic "{}" under "{}".'.format(topic, DUC_FOLDER))

    allScores = []
    summaryToCheck = ''
    summarySentIdsChecked = []
    for summary, summarySentIds, queryInfo in zip(summaries, summariesSentIds, queriesInfo):
        if not isAccumulating:
            # concatenate the summaries to each other:
            summaryToCheck += ' {}'.format(summary)
            summarySentIdsChecked.extend(summarySentIds)
        else:
            summaryToCheck = summary
            summarySentIdsChecked = summarySentIds
        results = getRougeScores(summaryToCheck, referenceSummariesFolder)
        litePyramidScore = litePyramidEvaluator.getLitePyramidScore(summarySentIdsChecked, topic)
        results.setdefault('litepyramid', {})['recall'] = litePyramidScore
        allScores.append({'query':queryInfo, 'results': results, 'sentenceIds': summarySentIdsChecked[:], 'summary': summaryToCheck, 'summary_len': len(word_tokenize(summaryToCheck))})

    # plot the ROUGE curves to a file, and get the AUC and length@threshold scores:
    figureOutputPath = os.path.join(outputFolderForPlot, topic)
    #aucScores = plotRougeCurvesAndAuc(allScores, figureOutputPath)
    aucScores = computeAUCofScoresCurve(allScores)
    plotScoresCurve(allScores, aucScores[-1], figureOutputPath)
    summLensAtThreshold = getLengthAtRouge(allScores, rouge1Thres=rouge1Thres, rouge2Thres=rouge2Thres, rougeLThres=rougeLThres, rougeSUThres=rougeSUThres)

    return allScores, aucScores, summLensAtThreshold

def getKeyphraseQuery(simulationQueryRequestStr, suggestedQueriesGenerator):
    neededIdx = int(simulationQueryRequestStr.split('[')[1].split(']')[0]) # e.g. '<[4]>' --> '4'
    suggestion = suggestedQueriesGenerator.getSuggestionAtIndex(neededIdx)
    return suggestion

def getHighlightQuery(simulationQueryRequestStr, lastSummaryTxt):
    requestStr = simulationQueryRequestStr.split('<')[1].split('>')[0] # e.g. '<tokens[1:3]>' --> 'tokens[1:3]'
    requestTypeStr = requestStr.split('[')[0] # e.g. 'tokens[1:3]> --> 'tokens'
    requestRangeStr = requestStr.split('[')[1].split(']')[0] # e.g. 'tokens[1:3]> --> '1:3'
    # options are '<tokens[i:j]>', '<chars[i:j]>', '<np[i]>', '<ne[i]>'
    if requestTypeStr == 'chars':
        startIdx, endIdx = map(int, requestRangeStr.split(':')) # e.g. '1:3' --> 1, 3
        highlight = lastSummaryTxt[startIdx:endIdx]
    elif requestTypeStr == 'tokens':
        startIdx, endIdx = map(int, requestRangeStr.split(':')) # e.g. '1:3' --> 1, 3
        highlight = ' '.join(word_tokenize(lastSummaryTxt)[startIdx:endIdx])
    elif requestTypeStr == 'np':
        idx = int(requestRangeStr) # e.g. '1' --> 1
        lastSummDoc = nlp(lastSummaryTxt)
        nounChunksList = list(lastSummDoc.noun_chunks)
        highlight = nounChunksList[idx].text
    elif requestTypeStr == 'ne':
        idx = int(requestRangeStr) # e.g. '1' --> 1
        lastSummDoc = nlp(lastSummaryTxt)
        namedEntitiesList = list(lastSummDoc.ents)
        if idx < len(namedEntitiesList):
            highlight = namedEntitiesList[idx].text
        else:
            nounChunksList = list(lastSummDoc.noun_chunks)
            if idx < len(nounChunksList):
                highlight = nounChunksList[idx].text

    else:
        print("Error: bad highlight request type: {}".format(simulationQueryRequestStr))
        highlight = ''

    return highlight

def getRandomQueriesDict(numQueries):
    # Generates a random list of queries with the specified number of queries in a list.
    # The first is the "initial" query, and the rest are random between
    # a random suggested keyphrase or a noun-phrase highlight.

    # start always with the initial query (initial generic summary):
    queriesDict = [{'type': 'initial', 'text':'', 'request_len':50}]
    # now fill the rest with random queries:
    for _ in range(numQueries-1):
        query = {'request_len':2}
        queryType = random.choice(['highlight', 'keyword'])
        query['type'] = queryType
        if queryType == 'highlight':
            query['text'] = '<np[0]>' # first noun phrase in last summary
        elif queryType == 'keyword':
            query['text'] = '<[{}]>'.format(random.choice(list(range(10)))) # one of the top-10 keyphrases
        queriesDict.append(query)

    return queriesDict


def getSimulationSummarySequence(summarySimulationJsonPath, SummarizerClass=SummarizerClustering, similarityStyle=REPRESENTATION_STYLE_W2V, SuggestedQueriesClass=SuggestedQueriesNgramCount):
    summarySequences = {} # topic -> list of lists of incremental summaries (each topic with one or more simulated sessions)
    summarySentenceIdsSequences = {} # topic -> list of lists of incremental summaries' sentence Ids lists (each topic with one or more simulated sessions)
    querySequences = {} # topic -> list of lists of query info ([query, queryType, -1]) (each topic with one or more simulated sessions)

    # check if we need to create a random queries dictionary:
    if summarySimulationJsonPath.startswith('*random_'):
        numSessions = int(summarySimulationJsonPath.split('_')[1])  # e.g. '*random_5_10*' --> 5
        numQueriesPerSession = int(summarySimulationJsonPath.split('_')[2].split('*')[0])  # e.g. '*random_5_10*' --> 10
        # create a list of random query lists per topic:
        queriesDict = {topicId:[getRandomQueriesDict(numQueriesPerSession) for _ in range(numSessions)]
                       for topicId in CORPORA_IDS_TO_NAMES}
    # otherwise take the queries dictionary from the pre-prepared JSON file:
    else:
        # get the queries for the simulation:
        with open(summarySimulationJsonPath) as jsonFile:
            queriesDict = json.load(jsonFile)
            # the JSON has a single list of queries per topic, so put it as a list of one list since it will repeat only once:
            queriesDict = {topicId:[queriesList] for topicId, queriesList in queriesDict.items()}

    # create the simulated sessions with a summarizer:
    for topic in queriesDict:
        # initialize topic:
        corpusName = CORPORA_IDS_TO_NAMES[topic]
        referenceSummariesFolder = os.path.join(CORPORA_LOCATIONS[corpusName], CORPUS_REFSUMMS_RELATIVE_PATH)
        questionnaireFilepath = os.path.join(CORPORA_LOCATIONS[corpusName], CORPUS_QUESTIONNAIRE_RELATIVE_PATH)
        corpus = Corpus(CORPORA_LOCATIONS[corpusName], referenceSummariesFolder, questionnaireFilepath, representationStyle=similarityStyle) # loadBert=(similarityStyle == REPRESENTATION_STYLE_BERT))

        summarySequences[topic] = []
        summarySentenceIdsSequences[topic] = []
        querySequences[topic] = []
        
        for queriesList in queriesDict[topic]:
            # initialize summarizer:
            summarizer = SummarizerClass(corpus)
            if SuggestedQueriesClass == SuggestedQueriesTextRank:
                suggestedQueriesGenerator = SuggestedQueriesClass(corpus, summarizer)
            else:
                suggestedQueriesGenerator = SuggestedQueriesClass(corpus)

            # check if the first request is an 'initial' request:
            if queriesList[0]['type'] != 'initial':
                print("Error: No initial request set for topic '{}' in file '{}'".format(topic, summarySimulationJsonPath))

            # get the initial summary, and then the query summaries:
            summarySequenceOfTopic = []
            summarySentenceIdsSequenceOfTopic = []
            querySequencesOfTopic = []
            summaryTxt, summaryLen = summarizer.summarizeGeneric(queriesList[0]['request_len'])
            if summaryLen > 0:
                summarySentenceIds = summarizer.summaries[-1] # get the last list of sentence IDs in the summary
                summarySequenceOfTopic.append(' '.join(summaryTxt))
                summarySentenceIdsSequenceOfTopic.append(summarySentenceIds)
                querySequencesOfTopic.append(['', 'initial', -1])
                lastSummaryTxt = ' '.join(summaryTxt)
            for requestIdx in range(1, len(queriesList)):
                # get the query text according to the query type:
                if queriesList[requestIdx]['type'] == 'freetext':
                    queryTxt = queriesList[requestIdx]['text']
                elif queriesList[requestIdx]['type'] == 'keyword':
                    queryTxt = getKeyphraseQuery(queriesList[requestIdx]['text'], suggestedQueriesGenerator)
                elif queriesList[requestIdx]['type'] == 'highlight':
                    queryTxt = getHighlightQuery(queriesList[requestIdx]['text'], lastSummaryTxt)
                else:
                    print("Error: query type is not supported ({}) in topic '{}' in file '{}'".format(queriesList[requestIdx]['type'], topic, summarySimulationJsonPath))
                    queryTxt = ''

                # get the expansion summary:
                summaryTxt, summaryLen = summarizer.summarizeByQuery(queryTxt,
                                                                     queriesList[requestIdx]['request_len'],
                                                                     queriesList[requestIdx]['type'])
                summarySentenceIds = summarizer.summaries[-1] # get the last list of sentence IDs in the summary
                
                summarySequenceOfTopic.append(' '.join(summaryTxt))
                summarySentenceIdsSequenceOfTopic.append(summarySentenceIds)
                lastSummaryTxt = ' '.join(summaryTxt)
                querySequencesOfTopic.append([queryTxt, queriesList[requestIdx]['type'], -1])

            summarySequences[topic].append(summarySequenceOfTopic)
            summarySentenceIdsSequences[topic].append(summarySentenceIdsSequenceOfTopic)
            querySequences[topic].append(querySequencesOfTopic)

    return summarySequences, summarySentenceIdsSequences, querySequences

def main():
    litePyramidEvaluator = LitePyramidEvaluator(LITE_PYRAMID_MAP_FILEPATH)
    for simulation_json_path, output_folder, summarizer_class, suggested_queries_class in SESSIONS_TO_RUN:
        # create the output directory, and fail if already exists:
        os.makedirs(output_folder)

        # get the summaries for all topics with the simulation and summarizer specified:
        allSessionsSummaries, allSessionsSummariesSentenceIds, allSessionsQueriesInfo = \
            getSimulationSummarySequence(simulation_json_path,
                                         SummarizerClass=summarizer_class,
                                         similarityStyle=SIMILARITY_STYLE,
                                         SuggestedQueriesClass=suggested_queries_class)

        # evaluate all the summaries, and get results (saves the curve plots in image files):
        allResults = {}
        for topic in allSessionsSummaries:
            allResults[topic] = []
            for sessionIdx, (sessionSummaries, sessionSummariesSentIds) in enumerate(zip(allSessionsSummaries[topic], allSessionsSummariesSentenceIds[topic])):
                allScoresInTopic, aucScoresInTopic, summLensAtThresholdInTopic = evaluateSequenceOfSummaries(
                    sessionSummaries, sessionSummariesSentIds, allSessionsQueriesInfo[topic][sessionIdx],
                    topic, output_folder, litePyramidEvaluator, isAccumulating=False,
                    rouge1Thres=ROUGE1_THRESHOLD, rouge2Thres=ROUGE2_THRESHOLD, rougeLThres=ROUGEL_THRESHOLD, rougeSUThres=ROUGESU_THRESHOLD)
                allResults[topic].append({'scores': allScoresInTopic, 'auc': aucScoresInTopic, 'lenAtThreshold': summLensAtThresholdInTopic, 'id': 'simulation_{}'.format(sessionIdx)})

            #print('AUC Scores: ' + str(aucScores))
            #print('Summary Lengths at thresholds: ' + str(summLensAtThreshold))

        # save the results to a JSON file:
        resultsFile = os.path.join(output_folder, 'results.json')
        with open(resultsFile, 'w') as fOut:
            json.dump(allResults, fOut, indent=4, sort_keys=True)



if __name__ == '__main__':
    main()