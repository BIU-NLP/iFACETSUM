from QFSE.Utilities import loadSpacy, loadBert
from QFSE.Utilities import REPRESENTATION_STYLE_W2V, REPRESENTATION_STYLE_SPACY, REPRESENTATION_STYLE_BERT

# The SpaCy and BERT objects must be loaded before anything else, so that classes using them get the initialized objects.
# The SpaCy and BERT objects are initialized only when needed since these init processes take a long time.
REPRESENTATION_STYLE = REPRESENTATION_STYLE_SPACY #REPRESENTATION_STYLE_W2V REPRESENTATION_STYLE_BERT
loadSpacy()
if REPRESENTATION_STYLE == REPRESENTATION_STYLE_BERT:
    loadBert()

from datetime import datetime as dt
import os
from QFSE.Corpus import Corpus
from QFSE.SummarizerClustering import SummarizerClustering
from QFSE.SummarizerMMR import SummarizerMMR
from evaluation.RougeEvaluator import getRougeScores
import json

# DUC 2006
DUC_FOLDER = 'C:/Users/user/Google Drive/School/Thesis/Summarization/ExtractiveSystems/qfse_shared/data/DUC2006Clean'
OUT_FILE = 'C:/Users/user/Google Drive/School/Thesis/Summarization/ExtractiveSystems/qfse_shared/data/DUC2006Clean/DUC06_results_Clustering.txt'
SUMMARY_WORD_LENGTH = 250
LIMIT_LENGTH_BYTES = -1
LIMIT_LENGTH_WORDS = 250
SUMMARIZER_CLASS = SummarizerClustering #SummarizerMMR

# Compare results on DUC 2004 in https://arxiv.org/pdf/1706.06681.pdf

def main():
    allScores = {}
    startTime = dt.now()
    for topicFolder in os.listdir(DUC_FOLDER):
        topicPath = os.path.join(DUC_FOLDER, topicFolder)
        if not os.path.isdir(topicPath):
            continue
        documentsFolder = os.path.join(topicPath, 'documents')
        referenceSummariesFolder = os.path.join(topicPath, 'referenceSummaries')
        corpus = Corpus(documentsFolder, referenceSummariesFolder, '', representationStyle=REPRESENTATION_STYLE)

        summarizer = SUMMARIZER_CLASS(corpus)
        summarySentenceList, summaryLengthInWords = summarizer.summarizeGeneric(SUMMARY_WORD_LENGTH)
        summary = '\n'.join(summarySentenceList)
        results = getRougeScores(summary, referenceSummariesFolder, limitLengthBytes=LIMIT_LENGTH_BYTES, limitLengthWords=LIMIT_LENGTH_WORDS)
        allScores[topicFolder] = {'results':results, 'summary':summarySentenceList}
        print('{}\tFinished topic {}'.format((dt.now()-startTime), topicFolder))

    avgR1, avgR2, avgRL, avgRSU, avgF1R1, avgF1R2, avgF1RL, avgF1RSU = getAverageRouges(allScores)
    allScores['avg_recall'] = {'R1':avgR1, 'R2':avgR2, 'RL':avgRL, 'RSU':avgRSU}
    allScores['avg_f1'] = {'R1': avgF1R1, 'R2': avgF1R2, 'RL': avgF1RL, 'RSU': avgF1RSU}

    with open(OUT_FILE, 'w') as fOut:
        json.dump(allScores, fOut, indent=4, sort_keys=True)


def getAverageRouges(allScores):
    totalR1 = 0
    totalR2 = 0
    totalRL = 0
    totalRSU = 0
    totalF1R1 = 0
    totalF1R2 = 0
    totalF1RL = 0
    totalF1RSU = 0
    for topic in allScores:
        # add in the ROUGE for the topic (if there are scores for the topic):
        if 'R1' in allScores[topic]['results']:
            totalR1 += allScores[topic]['results']['R1']['recall']
            totalR2 += allScores[topic]['results']['R2']['recall']
            totalRL += allScores[topic]['results']['RL']['recall']
            totalRSU += allScores[topic]['results']['RSU']['recall']
            totalF1R1 += allScores[topic]['results']['R1']['f1']
            totalF1R2 += allScores[topic]['results']['R2']['f1']
            totalF1RL += allScores[topic]['results']['RL']['f1']
            totalF1RSU += allScores[topic]['results']['RSU']['f1']
    totalR1 /= len(allScores)
    totalR2 /= len(allScores)
    totalRL /= len(allScores)
    totalRSU /= len(allScores)
    totalF1R1 /= len(allScores)
    totalF1R2 /= len(allScores)
    totalF1RL /= len(allScores)
    totalF1RSU /= len(allScores)

    return totalR1, totalR2, totalRL, totalRSU, totalF1R1, totalF1R2, totalF1RL, totalF1RSU

if __name__ == '__main__':
    main()