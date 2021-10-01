import os
import re
#from collections import defaultdict
#from math import log, sqrt
from QFSE.abstractive_summarizer import HuggingFaceSummarizer

nlp = None
bert_embedder = None


def sent_id_to_doc_id(sent_id):
    return sent_id.split("::")[0]


def sent_id_to_sent_idx(sent_id):
    return int(sent_id.split("::")[1])


registry = {}


def register(registry_key):
    def inner_register(func):
        registry[registry_key] = {
            "func": func,
            "value": None,
            "initialized": False
        }
    return inner_register


@register("spacy")
def loadSpacy():
    import pytextrank
    tr = pytextrank.TextRank()

    import spacy
    from spacy.tokens import Span
    # load spacy models:
    nlp = spacy.load('en_core_web_md')
    nlp.add_pipe(tr.PipelineComponent, name="textrank", last=True)
    # fix is_stop problem (https://github.com/explosion/spaCy/issues/922):
    nlp.vocab.add_flag(lambda s: s.lower() in spacy.lang.en.stop_words.STOP_WORDS, spacy.attrs.IS_STOP)
    # allow keeping the number of significant words in a span for quick access later:
    numSignificantWords_getter = lambda span: len([token for token in span if not token.is_stop and not token.is_punct])
    Span.set_extension("num_significant_words", getter=numSignificantWords_getter)
    return nlp


@register("abstract_summarizer")
def loadAbstractSummarizer():
    from transformers import BartTokenizer, BartForConditionalGeneration, BartConfig
    from transformers import LEDForConditionalGeneration, LEDTokenizer

    model_name = get_item("abstract_summarizer_model_name")

    MODEL_DIRECOTRY = f'./models/{model_name}/'

    use_bart = "bart" in model_name
    if os.path.exists(MODEL_DIRECOTRY):
        if use_bart:
            model = BartForConditionalGeneration.from_pretrained(MODEL_DIRECOTRY)
            tokenizer = BartTokenizer.from_pretrained(MODEL_DIRECOTRY)
        else:
            model = LEDForConditionalGeneration.from_pretrained(MODEL_DIRECOTRY, return_dict_in_generate=True)
            tokenizer = LEDTokenizer.from_pretrained(MODEL_DIRECOTRY)
    else:
        if use_bart:
            model = BartForConditionalGeneration.from_pretrained(model_name)
            tokenizer = BartTokenizer.from_pretrained(model_name)
        else:
            model = LEDForConditionalGeneration.from_pretrained(model_name, return_dict_in_generate=True)
            tokenizer = LEDTokenizer.from_pretrained(model_name)

        model.save_pretrained(MODEL_DIRECOTRY)
        tokenizer.save_pretrained(MODEL_DIRECOTRY)
    return model, tokenizer


@register("abstract_summarizer_model_name")
def get_abstract_summarizer_model_name():
    # return "allenai/led-large-16384"
    # return "allenai/led-large-16384-arxiv"
    return "facebook/bart-large-cnn"
    # return "facebook/bart-large"


@register("bart_summarizer")
def loadBartSummarizer():
    return HuggingFaceSummarizer(get_item("abstract_summarizer_model_name"))


@register("corpus_registry")
def corpus_registry():
    from QFSE.corpus_registry import CorpusRegistry
    return CorpusRegistry()


@register("query_registry")
def query_registry():
    from QFSE.query_registry import QueryRegistry
    return QueryRegistry()


def get_item(registry_key: str):
    if not registry[registry_key]['initialized']:
        registry[registry_key]['value'] = registry[registry_key]['func']()
        registry[registry_key]['initialized'] = True
    return registry[registry_key]['value']


def loadBert():
    global bert_embedder

    from sentence_transformers import SentenceTransformer
    # load the BERT embedder (https://github.com/UKPLab/sentence-transformers):
    bert_embedder = SentenceTransformer('roberta-base-nli-stsb-mean-tokens')


STOP_WORDS = {'a':1, 'able':1, 'about':1, 'above':1, 'abst':1, 'accordance':1, 'according':1, 'accordingly':1,
              'across':1, 'act':1, 'actually':1, 'added':1, 'adj':1, 'adopted':1, 'affected':1, 'affecting':1,
              'affects':1, 'after':1, 'afterwards':1, 'again':1, 'against':1, 'ah':1, 'all':1, 'almost':1, 'alone':1,
              'along':1, 'already':1, 'also':1, 'although':1, 'always':1, 'am':1, 'among':1, 'amongst':1, 'an':1,
              'and':1, 'announce':1, 'another':1, 'any':1, 'anybody':1, 'anyhow':1, 'anymore':1, 'anyone':1,
              'anything':1, 'anyway':1, 'anyways':1, 'anywhere':1, 'apparently':1, 'approximately':1, 'are':1,
              'aren':1, 'arent':1, 'arise':1, 'around':1, 'as':1, 'aside':1, 'ask':1, 'asking':1, 'at':1, 'auth':1,
              'available':1, 'away':1, 'awfully':1, 'b':1, 'back':1, 'be':1, 'became':1, 'because':1, 'become':1,
              'becomes':1, 'becoming':1, 'been':1, 'before':1, 'beforehand':1, 'begin':1, 'beginning':1, 'beginnings':1,
              'begins':1, 'behind':1, 'being':1, 'believe':1, 'below':1, 'beside':1, 'besides':1, 'between':1,
              'beyond':1, 'biol':1, 'both':1, 'brief':1, 'briefly':1, 'but':1, 'by':1, 'c':1, 'ca':1, 'came':1,
              'can':1, 'cannot':1, "can't":1, 'certain':1, 'certainly':1, 'co':1, 'com':1, 'come':1, 'comes':1,
              'contain':1, 'containing':1, 'contains':1, 'could':1, "couldn't":1, 'd':1, 'date':1, 'did':1, "didn't":1,
              'different':1, 'do':1, 'does':1, "doesn't":1, 'doing':1, 'done':1, "don't":1, 'down':1, 'downwards':1,
              'due':1, 'during':1, 'e':1, 'each':1, 'ed':1, 'edu':1, 'effect':1, 'eg':1, 'eight':1, 'eighty':1,
              'either':1, 'else':1, 'elsewhere':1, 'end':1, 'ending':1, 'enough':1, 'especially':1, 'et':1, 'et-al':1,
              'etc':1, 'even':1, 'ever':1, 'every':1, 'everybody':1, 'everyone':1, 'everything':1, 'everywhere':1,
              'ex':1, 'except':1, 'f':1, 'far':1, 'few':1, 'ff':1, 'fifth':1, 'first':1, 'five':1, 'fix':1,
              'followed':1, 'following':1, 'follows':1, 'for':1, 'former':1, 'formerly':1, 'forth':1, 'found':1,
              'four':1, 'from':1, 'further':1, 'furthermore':1, 'g':1, 'gave':1, 'get':1, 'gets':1, 'getting':1,
              'give':1, 'given':1, 'gives':1, 'giving':1, 'go':1, 'goes':1, 'gone':1, 'got':1, 'gotten':1, 'h':1,
              'had':1, 'happens':1, 'hardly':1, 'has':1, "hasn't":1, 'have':1, "haven't":1, 'having':1, 'he':1,
              'hed':1, 'hence':1, 'her':1, 'here':1, 'hereafter':1, 'hereby':1, 'herein':1, 'heres':1, 'hereupon':1,
              'hers':1, 'herself':1, 'hes':1, 'hi':1, 'hid':1, 'him':1, 'himself':1, 'his':1, 'hither':1, 'home':1,
              'how':1, 'howbeit':1, 'however':1, 'hundred':1, 'i':1, 'id':1, 'ie':1, 'if':1, "i'll":1, 'im':1,
              'immediate':1, 'immediately':1, 'importance':1, 'important':1, 'in':1, 'inc':1, 'indeed':1, 'index':1,
              'information':1, 'instead':1, 'into':1, 'invention':1, 'inward':1, 'is':1, "isn't":1, 'it':1, 'itd':1,
              "it'll":1, 'its':1, 'itself':1, "i've":1, 'j':1, 'just':1, 'k':1, 'keep':1, 'keeps':1, 'kept':1,
              'keys':1, 'kg':1, 'km':1, 'know':1, 'known':1, 'knows':1, 'l':1, 'largely':1, 'last':1, 'lately':1,
              'later':1, 'latter':1, 'latterly':1, 'least':1, 'less':1, 'lest':1, 'let':1, 'lets':1, 'like':1,
              'liked':1, 'likely':1, 'line':1, 'little':1, "'ll":1, 'look':1, 'looking':1, 'looks':1, 'ltd':1,
              'm':1, 'made':1, 'mainly':1, 'make':1, 'makes':1, 'many':1, 'may':1, 'maybe':1, 'me':1, 'mean':1,
              'means':1, 'meantime':1, 'meanwhile':1, 'merely':1, 'mg':1, 'might':1, 'million':1, 'miss':1, 'ml':1,
              'more':1, 'moreover':1, 'most':1, 'mostly':1, 'mr':1, 'mrs':1, 'much':1, 'mug':1, 'must':1, 'my':1,
              'myself':1, 'n':1, 'na':1, 'name':1, 'namely':1, 'nay':1, 'nd':1, 'near':1, 'nearly':1, 'necessarily':1,
              'necessary':1, 'need':1, 'needs':1, 'neither':1, 'never':1, 'nevertheless':1, 'new':1, 'next':1, 'nine':1,
              'ninety':1, 'no':1, 'nobody':1, 'non':1, 'none':1, 'nonetheless':1, 'noone':1, 'nor':1, 'normally':1,
              'nos':1, 'not':1, 'noted':1, 'nothing':1, 'now':1, 'nowhere':1, 'o':1, 'obtain':1, 'obtained':1,
              'obviously':1, 'of':1, 'off':1, 'often':1, 'oh':1, 'ok':1, 'okay':1, 'old':1, 'omitted':1, 'on':1,
              'once':1, 'one':1, 'ones':1, 'only':1, 'onto':1, 'or':1, 'ord':1, 'other':1, 'others':1, 'otherwise':1,
              'ought':1, 'our':1, 'ours':1, 'ourselves':1, 'out':1, 'outside':1, 'over':1, 'overall':1, 'owing':1,
              'own':1, 'p':1, 'page':1, 'pages':1, 'part':1, 'particular':1, 'particularly':1, 'past':1, 'per':1,
              'perhaps':1, 'placed':1, 'please':1, 'plus':1, 'poorly':1, 'possible':1, 'possibly':1, 'potentially':1,
              'pp':1, 'predominantly':1, 'present':1, 'previously':1, 'primarily':1, 'probably':1, 'promptly':1,
              'proud':1, 'provides':1, 'put':1, 'q':1, 'que':1, 'quickly':1, 'quite':1, 'qv':1, 'r':1, 'ran':1,
              'rather':1, 'rd':1, 're':1, 'readily':1, 'really':1, 'recent':1, 'recently':1, 'ref':1, 'refs':1,
              'regarding':1, 'regardless':1, 'regards':1, 'related':1, 'relatively':1, 'research':1, 'respectively':1,
              'resulted':1, 'resulting':1, 'results':1, 'right':1, 'run':1, 's':1, 'said':1, 'same':1, 'saw':1,
              'say':1, 'saying':1, 'says':1, 'sec':1, 'section':1, 'see':1, 'seeing':1, 'seem':1, 'seemed':1,
              'seeming':1, 'seems':1, 'seen':1, 'self':1, 'selves':1, 'sent':1, 'seven':1, 'several':1, 'shall':1,
              'she':1, 'shed':1, "she'll":1, 'shes':1, 'should':1, "shouldn't":1, 'show':1, 'showed':1, 'shown':1,
              'showns':1, 'shows':1, 'significant':1, 'significantly':1, 'similar':1, 'similarly':1, 'since':1,
              'six':1, 'slightly':1, 'so':1, 'some':1, 'somebody':1, 'somehow':1, 'someone':1, 'somethan':1,
              'something':1, 'sometime':1, 'sometimes':1, 'somewhat':1, 'somewhere':1, 'soon':1, 'sorry':1,
              'specifically':1, 'specified':1, 'specify':1, 'specifying':1, 'state':1, 'states':1, 'still':1, 'stop':1,
              'strongly':1, 'sub':1, 'substantially':1, 'successfully':1, 'such':1, 'sufficiently':1, 'suggest':1,
              'sup':1, 'sure':1, 't':1, 'take':1, 'taken':1, 'taking':1, 'tell':1, 'tends':1, 'th':1, 'than':1,
              'thank':1, 'thanks':1, 'thanx':1, 'that':1, "that'll":1, 'thats':1, "that've":1, 'the':1, 'their':1,
              'theirs':1, 'them':1, 'themselves':1, 'then':1, 'thence':1, 'there':1, 'thereafter':1, 'thereby':1,
              'thered':1, 'therefore':1, 'therein':1, "there'll":1, 'thereof':1, 'therere':1, 'theres':1, 'thereto':1,
              'thereupon':1, "there've":1, 'these':1, 'they':1, 'theyd':1, "they'll":1, 'theyre':1, "they've":1,
              'this':1, 'those':1, 'thou':1, 'though':1, 'thoughh':1, 'thousand':1, 'throug':1, 'through':1,
              'throughout':1, 'thru':1, 'thus':1, 'til':1, 'tip':1, 'to':1, 'together':1, 'too':1, 'took':1, 'toward':1,
              'towards':1, 'tried':1, 'tries':1, 'truly':1, 'try':1, 'trying':1, 'ts':1, 'twice':1, 'two':1, 'u':1,
              'un':1, 'under':1, 'unfortunately':1, 'unless':1, 'unlike':1, 'unlikely':1, 'until':1, 'unto':1, 'up':1,
              'upon':1, 'ups':1, 'us':1, 'use':1, 'used':1, 'useful':1, 'usefully':1, 'usefulness':1, 'uses':1,
              'using':1, 'usually':1, 'v':1, 'value':1, 'various':1, "'ve":1, 'very':1, 'via':1, 'viz':1, 'vol':1,
              'vols':1, 'vs':1, 'w':1, 'want':1, 'wants':1, 'was':1, "wasn't":1, 'way':1, 'we':1, 'wed':1, 'welcome':1,
              "we'll":1, 'went':1, 'were':1, "weren't":1, "we've":1, 'what':1, 'whatever':1, "what'll":1, 'whats':1,
              'when':1, 'whence':1, 'whenever':1, 'where':1, 'whereafter':1, 'whereas':1, 'whereby':1, 'wherein':1,
              'wheres':1, 'whereupon':1, 'wherever':1, 'whether':1, 'which':1, 'while':1, 'whim':1, 'whither':1,
              'who':1, 'whod':1, 'whoever':1, 'whole':1, "who'll":1, 'whom':1, 'whomever':1, 'whos':1, 'whose':1,
              'why':1, 'widely':1, 'willing':1, 'wish':1, 'with':1, 'within':1, 'without':1, "won't":1, 'words':1,
              'world':1, 'would':1, "wouldn't":1, 'www':1, 'x':1, 'y':1, 'yes':1, 'yet':1, 'you':1, 'youd':1,
              "you'll":1, 'your':1, 'youre':1, 'yours':1, 'yourself':1, 'yourselves':1, "you've":1, 'z':1, 'zero':1,
              '`':1, '``':1, "'":1, '(':1, ')':1, ',':1, '_':1, ';':1, ':':1, '~':1, '-':1, '--':1, '$':1, '^':1, '*':1,
              "'s":1, "'t":1, "'m":1, 'doesn':1, 'don':1, 'hasn':1, 'haven':1, 'isn':1, 'wasn':1,
              'won':1, 'weren':1, 'wouldn':1, 'didn':1, 'shouldn':1, 'couldn':1, '':1}

PUNCTUATION = {'!':1, '"':1, '#':1, '$':1, '%':1, '&':1, '\\':1, "'":1, '(':1, ')':1, '*':1, '+':1, ',':1, '-':1,
               '.':1, '/':1, ':':1, ';':1, '<':1, '=':1, '>':1, '?':1, '@':1, '[':1, ']':1, '^':1, '_':1,
               '`':1, '{':1, '|':1, '}':1, '~':1, "''":1, '``':1}

TRANSITION_WORDS = {'and':1, 'but':1, 'similarly':1, 'accordingly':1, 'also':1, 'furthermore':1, 'lastly':1,
                    'thereby':1, 'hence':1, 'likewise':1, 'therefore':1, 'thus':1, 'however':1}

REPRESENTATION_STYLE_BERT = 'bert'
REPRESENTATION_STYLE_W2V = 'w2v'
REPRESENTATION_STYLE_SPACY = 'spacy'


def isPotentialSentence(sentence):
    if sentence.text[0] in ['"', "'", '`', '(', '[', '_', '-'] \
            or sentence.text[-1] != '.' \
            or sentence.lengthInWords < 8 \
            or sentence.lengthInWords > 35 \
            or sentence.lengthInChars < 30:
        return False
    # is there a phone number in the sentence:
    r = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
    if len(r.findall(sentence.text)) > 0:
        return False
    # is there a URL in the sentence:
    r = re.compile(r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*')
    if len(r.findall(sentence.text)) > 0:
        return False
    # is there an email address in the sentence:
    r = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
    if len(r.findall(sentence.text)) > 0:
        return False
    # does the sentence start with a transition word:
    for transitionWord in TRANSITION_WORDS:
        if sentence.textCompressed.startswith(transitionWord):
            return False
    # or sentenceText[-1] in ['?', ':', '"', "'"]

    return True