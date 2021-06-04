from collections import defaultdict

from QFSE.Sentence import Sentence
from QFSE.Utilities import REPRESENTATION_STYLE_SPACY, get_item
from QFSE.Utilities import nlp
from nltk.tokenize import sent_tokenize, word_tokenize

NUMBER_OF_TOP_SENTENCES_KEPT = 3

class Document:
    def __init__(self, docId, text, filepath, representationStyle):
        self.id = docId
        self.filepath = filepath
        self.text = text
        self.representationStyle = representationStyle
        self.spacyDoc = None
        self.coref_clusters = defaultdict(dict)
        self._initDoc()

    def _initDoc(self):
        nlp = get_item("spacy")
        self.spacyDoc = nlp(self.text)
        self.tokens = [t.text for t in self.spacyDoc]
        self.topSentencesText = [sent.text for sent in self.spacyDoc._.textrank.summary(limit_phrases=20, limit_sentences=NUMBER_OF_TOP_SENTENCES_KEPT)]

        # sentence tokenization done with SpaCy - for consistency within all variants

        if self.representationStyle == REPRESENTATION_STYLE_SPACY:
            # since it is time consuming to compute Spacy objects per sentence, we pass in the sentence
            # vector representation per sentence:
            self.sentences = []
            for sentIdx, sentSpacyObj in enumerate(self.spacyDoc.sents):
                doNotInitRepresentation = True
                self.sentences.append(
                    Sentence(self.id, sentIdx, sentSpacyObj.text, self.representationStyle, doNotInitRepresentation=doNotInitRepresentation, spacy_rep=sentSpacyObj))
                if doNotInitRepresentation:
                    self.sentences[-1].setRepresentation(sentSpacyObj.vector)

        # in all other cases, and as it should be for correct code, the representations are computed
        # within the Sentence object:
        else:
            self.sentences = [Sentence(self.id, sentIdx, sentSpacyObj.text, self.representationStyle, spacy_rep=sentSpacyObj)
                              for sentIdx, sentSpacyObj in enumerate(self.spacyDoc.sents)]



    #def _setBertSentenceEmbeddings(self):
    #    # Since setting the BERT embedding is a little slower when done a sentence at a time, we do it at once here
    #    # get the sentence texts:
    #    sentencesList = [sentObj.text for sentObj in self.sentences]
    #    # get the BERT embeddings:
    #    embeddings = bert_embedder.encode(sentencesList)
    #    # set the embeddings for the sentences:
    #    for sentIdx, sentObj in enumerate(self.sentences):
    #        sentObj.bertEmbedding = embeddings[sentIdx]