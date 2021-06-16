
CORPORA_LOCATIONS = {
                     'Native American Challenges': 'data/DUC2006Clean/D0601/documents',
                     # 'Wetlands': 'data/DUC2006Clean/D0603/documents',
                     # 'Osteoarthritis': 'data/DUC2006Clean/D0605/documents',
                     # "Automobile Safety": 'data/DUC2006Clean/D0608/documents',
                     # 'Quebec Separatist Movement': 'data/DUC2006Clean/D0614/documents',
                     # 'Evolution Teaching': 'data/DUC2006Clean/D0615/documents',
                     # 'Russia in Chechnya': 'data/DUC2006Clean/D0616/documents',
                     'EgyptAir Crash': 'data/DUC2006Clean/D0617/documents',
                     # 'School Safety': 'data/DUC2006Clean/D0620/documents',
                     # 'Stephen Lawrence Killing': 'data/DUC2006Clean/D0624/documents',
                     # 'Adoption': 'data/DUC2006Clean/D0627/documents',
                     # 'ADHD': 'data/DUC2006Clean/D0628/documents',
                     # 'Computer Viruses': 'data/DUC2006Clean/D0629/documents',
                     # 'Bookselling': 'data/DUC2006Clean/D0630/documents',
                     # 'Concorde Aircraft': 'data/DUC2006Clean/D0631/documents',
                     # 'Kursk Submarine': 'data/DUC2006Clean/D0640/documents',
                     # 'El Nino': 'data/DUC2006Clean/D0643/documents',
                     # 'US Affordable Housing': 'data/DUC2006Clean/D0645/documents',
                     # 'Elian Gonzales': 'data/DUC2006Clean/D0647/documents',
                     # 'Jimmy Carter International': 'data/DUC2006Clean/D0650/documents',
                     # 'Steroid Use': 'data/DUC2006Clean/D0602/documents',
                     # 'Global Warming': 'data/DUC2006Clean/D0606/documents'
                     # note this last topic is a sample for the AMT preview
}

CORPORA_IDS = {  'Native American Challenges': 'D0601',
                 'Wetlands': 'D0603',
                 'Osteoarthritis': 'D0605',
                 "Automobile Safety": 'D0608',
                 'Quebec Separatist Movement': 'D0614',
                 'Evolution Teaching': 'D0615',
                 'Russia in Chechnya': 'D0616',
                 'EgyptAir Crash': 'D0617',
                 'School Safety': 'D0620',
                 'Stephen Lawrence Killing': 'D0624',
                 'Adoption': 'D0627',
                 'ADHD': 'D0628',
                 'Computer Viruses': 'D0629',
                 'Bookselling': 'D0630',
                 'Concorde Aircraft': 'D0631',
                 'Kursk Submarine': 'D0640',
                 'El Nino': 'D0643',
                 'US Affordable Housing': 'D0645',
                 'Elian Gonzales': 'D0647',
                 'Jimmy Carter International': 'D0650',
                 'Steroid Use': 'D0602',
                 'Global Warming': 'D0606'}

CORPORA_IDS_TO_NAMES = {
				 'D0601': 'Native American Challenges',
                 'D0603': 'Wetlands',
                 'D0605': 'Osteoarthritis',
                 'D0608': "Automobile Safety",
                 'D0614': 'Quebec Separatist Movement',
                 'D0615': 'Evolution Teaching',
                 'D0616': 'Russia in Chechnya',
                 'D0617': 'EgyptAir Crash',
                 'D0620': 'School Safety',
                 'D0624': 'Stephen Lawrence Killing',
                 'D0627': 'Adoption',
                 'D0628': 'ADHD',
                 'D0629': 'Computer Viruses',
                 'D0630': 'Bookselling',
                 'D0631': 'Concorde Aircraft',
                 'D0640': 'Kursk Submarine',
                 'D0643': 'El Nino',
                 'D0645': 'US Affordable Housing',
                 'D0647': 'Elian Gonzales',
                 'D0650': 'Jimmy Carter International',
                 'D0602': 'Steroid Use',
                 'D0606': 'Global Warming'}

CORPUS_REFSUMMS_RELATIVE_PATH = '../referenceSummaries'
CORPUS_QUESTIONNAIRE_RELATIVE_PATH = '../questions'

COREF_LOCATIONS = {
    'Native American Challenges': {
        # "entities": "data/coref/native/duc_entities.conll",
        # "entities": "data/coref/native/spacy_wd_coref_duc.json",
        # "entities": "data/coref/native/duc_predictions_ments.json",
        "entities": "data/coref/native/wec_entities/wec_native_predicted_clusters.json",
        # "events":  "data/coref/native/events_average_0.3_model_5_topic_level.conll",
        # "events":  "data/coref/native/cdlm_events/CDLM_events.conll",
        # "events":  "data/coref/native/wec_events/wec_native_event_predictions_loose_fix.json",
        "events":  "data/coref/native/wec_events/wec_native_event_predictions_loose_fix2.json",
        # "events":  "data/coref/native/wec_events/wec_native_event_predictions_strict_fix.json",
        "propositions": "data/coref/native/propositions/devDUC2006_InDoc_D0601A_checkpoint-2000.csv"
    },
    "Automobile Safety": {

    },
    'EgyptAir Crash': {
        "entities": "data/coref/egypt/wec_entities/wec_egyptAir_predicted_clusters.json",
        "events": "data/coref/egypt/cdlm_events/dev_events_average_0.85_corpus_level.conll",
        "propositions": "data/coref/egypt/propositions/devDUC2006_InDoc_D0617_checkpoint-2000.csv"
    },
    'Computer Viruses': {},
    'Steroid Use': {},
    'Global Warming': {}
}
