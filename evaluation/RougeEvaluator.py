from pyrouge import Rouge155
import logging
import traceback
from collections import defaultdict
import tempfile
import os

# A parameter whether to remove the stopwords from the summaries.
REMOVE_STOP_WORDS = True
LEAVE_STOP_WORDS = False

# The rouge types. Keys are internal IDs for this code, and the values
# are the strings used in the dictioanry returned by the Rouge155 module.
ROUGE_TYPES = {
    'R1':'rouge_1',
    'R2':'rouge_2',
    'R3':'rouge_3',
    'R4':'rouge_4',
    'RSU':'rouge_su*',
    'RL':'rouge_l',
    'RW':'rouge_w_1.2',
    'RS':'rouge_s*'}

# The format in which the input summaries are. SEE is the DUC html format which ROUGE uses.
# Regular text format can also be used, where each sentence is on a separate line (has time and space overhead).
FORMAT_SEE = 'SEE'
FORMAT_TEXT = 'text'

def getRougeScores(systemSummaryText, referenceSummariesFolderpath, inputFormat=FORMAT_TEXT, limitLengthBytes=-1, limitLengthWords=-1):
    # initialize the ROUGE object:
    #if stopWordsRemoval == REMOVE_STOP_WORDS:
    #    rougeCalculator = Rouge155(rouge_args='-s')
    #else:
    rougeCalculator = Rouge155()

    ## write the system summary to a temporary file (close the file later):
    #tmpFD, tmpPath = tempfile.mkstemp()
    #with os.fdopen(tmpFD, 'w') as tmp:
    #sysSummFolder = os.path.dirname(tmpPath)
    #sysSummFilename = os.path.basename(tmpPath)

    sysSummFolder = tempfile.mkdtemp()
    if not os.path.exists(sysSummFolder):
        os.makedirs(sysSummFolder)
    sysSummFilename = "systemSummary.txt"
    tempFilePath = os.path.join(sysSummFolder, sysSummFilename)

    with open(tempFilePath, 'w') as tmp:
        # do stuff with temp file
        tmp.write(systemSummaryText)

    # set the properties for the ROUGE object:
    rougeCalculator.system_dir = sysSummFolder
    rougeCalculator.model_dir = referenceSummariesFolderpath
    rougeCalculator.system_filename_pattern = '(.*)' #sysSummFilename
    rougeCalculator.model_filename_pattern = '.*'

    if limitLengthBytes > 0:
        rougeCalculator.add_rouge_args_to_default(['-b', str(limitLengthBytes)])
    if limitLengthWords > 0:
        rougeCalculator.add_rouge_args_to_default(['-l', str(limitLengthWords)])

    ## add the ROUGE flag to truncate the system summaries according to their defined length:
    #rougeAdditionalParams = ['-l', int(summLen)]
    # possibly add the ROUGE flag to remove stop words:
    #rougeAdditionalParams = []
    #if stopWordsRemoval == REMOVE_STOP_WORDS:
    #    rougeAdditionalParams.append('-s')
    #rougeCalculator.args.add_rouge_args_to_default(rougeAdditionalParams)

    results = defaultdict(lambda: {})
    try:
        # When using plain text format, run convert_and_evaluate.
        # For SEE format, use just evaluate(), since convert is for text->SEE conversion.
        if inputFormat == FORMAT_SEE:
            output = rougeCalculator.evaluate()
        elif inputFormat == FORMAT_TEXT:
            output = rougeCalculator.convert_and_evaluate()
        else:
            output = rougeCalculator.convert_and_evaluate()

        # get the ROUGE results:
        output_dict = rougeCalculator.output_to_dict(output)
        for rougeType, rougeDataStr in ROUGE_TYPES.items():
            results[rougeType]['recall'] = output_dict[rougeDataStr + '_recall']
            results[rougeType]['precision'] = output_dict[rougeDataStr + '_precision']
            results[rougeType]['f1'] = output_dict[rougeDataStr + '_f_score']
    except Exception as e:
        logging.error('Failed to compute ROUGE: {}'.format(e))
        logging.error(traceback.format_exc())

    #os.remove(tmpPath)

    return results