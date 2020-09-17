import sys
sys.path.append('..')
from QFSE.Utilities import loadSpacy
from data.Config import CORPORA_IDS_TO_NAMES, CORPORA_LOCATIONS, CORPUS_REFSUMMS_RELATIVE_PATH, CORPUS_QUESTIONNAIRE_RELATIVE_PATH
loadSpacy()
from QFSE.SuggestedQueriesNgramCount import SuggestedQueriesNgramCount
from QFSE.Corpus import Corpus
import os
import json

keyphrasesPerTopic = {}
for topicId, topicName in CORPORA_IDS_TO_NAMES.items():
    referenceSummariesFolder = os.path.join('..', CORPORA_LOCATIONS[topicName], CORPUS_REFSUMMS_RELATIVE_PATH)
    questionnaireFilepath = os.path.join('..', CORPORA_LOCATIONS[topicName], CORPUS_QUESTIONNAIRE_RELATIVE_PATH)
    corpusLocation = os.path.join('..', CORPORA_LOCATIONS[topicName])
    corpus = Corpus(corpusLocation, referenceSummariesFolder, questionnaireFilepath)
    suggestedQueriesGenerator = SuggestedQueriesNgramCount(corpus)
    keyphrasesPerTopic[topicId] = suggestedQueriesGenerator.getNextTopSuggestions(20)
    print('Finished: {}'.format(topicId))
    
with open('keyphrasesSuggestedQueriesNgramCount.json', 'w') as fp:
    json.dump(keyphrasesPerTopic, fp, indent=4)