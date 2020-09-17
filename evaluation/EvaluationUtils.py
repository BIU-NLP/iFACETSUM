import matplotlib.pyplot as plt
from sklearn.metrics import auc
import numpy as np

def computeAUCofScoresCurve(allScores):
    # input: a list of dictionaries: {'results':{'R1': {'recall':<>,'precision':<>,'f1':<>}, 'R2': {...}, 'RL': {...}}, 'summary_len':<int>}
    # returns: a list of dictionaries: {'len': <summary_len>, 'R1': {'recall':<>,'precision':<>,'f1':<>}, 'R2': {...}, 'RL': {...}}
    # The returned list is one shorter than the input list length, and holds the AUC scores from the beginning until each X value.
    # The last item in this list holds the AUC value for the whole curve.
    
    X = []
    Y_R1_Recall = []
    Y_R2_Recall = []
    Y_RL_Recall = []
    Y_RSU_Recall = []
    Y_LitePyramid_Recall = []
    Y_R1_Prec = []
    Y_R2_Prec = []
    Y_RL_Prec = []
    Y_RSU_Prec = []
    Y_R1_F1 = []
    Y_R2_F1 = []
    Y_RL_F1 = []
    Y_RSU_F1 = []
    # The AUC scores from the beginning until each X value (length of the list one less than the number of X values).
    # The last item in this list holds the AUC value for the whole curve.
    aucScores = [] # list of {'len': numWords, 'R1': {'recall':<>,'precision':<>,'f1':<>}, 'R2': {...}, 'RL': {...}}
    for scoreInfo in allScores:
        results = scoreInfo['results']
        numWords = scoreInfo['summary_len']

        X.append(numWords)
        Y_R1_Recall.append(results['R1']['recall'])
        Y_R2_Recall.append(results['R2']['recall'])
        Y_RL_Recall.append(results['RL']['recall'])
        Y_RSU_Recall.append(results['RSU']['recall'])
        Y_R1_Prec.append(results['R1']['precision'])
        Y_R2_Prec.append(results['R2']['precision'])
        Y_RL_Prec.append(results['RL']['precision'])
        Y_RSU_Prec.append(results['RSU']['precision'])
        Y_R1_F1.append(results['R1']['f1'])
        Y_R2_F1.append(results['R2']['f1'])
        Y_RL_F1.append(results['RL']['f1'])
        Y_RSU_F1.append(results['RSU']['f1'])
        if 'litepyramid' in results:
            Y_LitePyramid_Recall.append(results['litepyramid']['recall'])
        else:
            Y_LitePyramid_Recall.append(-1.0)

        if len(X) > 1:
            aucScores.append({'len': numWords, 'R1': {}, 'R2': {}, 'RL': {}, 'RSU': {}, 'litepyramid': {}})
            aucScores[-1]['R1']['recall'] = auc(X, Y_R1_Recall)
            aucScores[-1]['R2']['recall'] = auc(X, Y_R2_Recall)
            aucScores[-1]['RL']['recall'] = auc(X, Y_RL_Recall)
            aucScores[-1]['RSU']['recall'] = auc(X, Y_RSU_Recall)
            aucScores[-1]['R1']['precision'] = auc(X, Y_R1_Prec)
            aucScores[-1]['R2']['precision'] = auc(X, Y_R2_Prec)
            aucScores[-1]['RL']['precision'] = auc(X, Y_RL_Prec)
            aucScores[-1]['RSU']['precision'] = auc(X, Y_RSU_Prec)
            aucScores[-1]['R1']['f1'] = auc(X, Y_R1_F1)
            aucScores[-1]['R2']['f1'] = auc(X, Y_R2_F1)
            aucScores[-1]['RL']['f1'] = auc(X, Y_RL_F1)
            aucScores[-1]['RSU']['f1'] = auc(X, Y_RSU_F1)
            aucScores[-1]['litepyramid']['recall'] = auc(X, Y_LitePyramid_Recall)

    return aucScores
    
def plotScoresCurve(allScores, curveAucScore, saveFigureFilepath):
    # input:
    #   - a list of dictionaries: {'results':{'R1': {'recall':<>,'precision':<>,'f1':<>}, 'R2': {...}, 'RL': {...}}, 'summary_len':<int>}
    #   - dictionary: {'len': <summary_len>, 'R1': {'recall':<aucScore>,'precision':<aucScore>,'f1':<aucScore>}, 'R2': {...}, 'RL': {...}}
    #   - filepath to save the figure

    X = []
    Y_R1_Recall = []
    Y_R2_Recall = []
    Y_RL_Recall = []
    Y_RSU_Recall = []
    Y_LitePyramid_Recall = []
    Y_R1_Prec = []
    Y_R2_Prec = []
    Y_RL_Prec = []
    Y_RSU_Prec = []
    Y_R1_F1 = []
    Y_R2_F1 = []
    Y_RL_F1 = []
    Y_RSU_F1 = []
    for scoreInfo in allScores:
        results = scoreInfo['results']
        numWords = scoreInfo['summary_len']

        X.append(numWords)
        Y_R1_Recall.append(results['R1']['recall'])
        Y_R2_Recall.append(results['R2']['recall'])
        Y_RL_Recall.append(results['RL']['recall'])
        Y_RSU_Recall.append(results['RSU']['recall'])
        Y_R1_Prec.append(results['R1']['precision'])
        Y_R2_Prec.append(results['R2']['precision'])
        Y_RL_Prec.append(results['RL']['precision'])
        Y_RSU_Prec.append(results['RSU']['precision'])
        Y_R1_F1.append(results['R1']['f1'])
        Y_R2_F1.append(results['R2']['f1'])
        Y_RL_F1.append(results['RL']['f1'])
        Y_RSU_F1.append(results['RSU']['f1'])
        if 'litepyramid' in results:
            Y_LitePyramid_Recall.append(results['litepyramid']['recall'])
        else:
            Y_LitePyramid_Recall.append(-1.0)

    # output a plot for the ROUGE and AUC:
    fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, sharex=True)
    ax1.set(title='Incremental Gain per Operation')
    ax1.set(ylabel='ROUGE-1')
    ax2.set(ylabel='ROUGE-2')
    ax3.set(ylabel='ROUGE-L')
    ax4.set(ylabel='ROUGE-SU')
    ax5.set(ylabel='Lite-Pyramid')
    ax5.set(xlabel='Word Count')

    ax1.plot(X, Y_R1_Recall, '-b', marker='x', label='R1_rec')
    for i, j in zip(X, Y_R1_Recall):
        ax1.annotate(str(j), xy=(i, j), xytext=(-10, 10), textcoords='offset points')
    ax1.text(np.mean(X), np.mean(Y_R1_Recall) / 2, 'AUC: {:.2f}'.format(curveAucScore['R1']['recall']))
    ax1.fill_between(X, 0, Y_R1_Recall, facecolor='blue', alpha=0.4)

    ax2.plot(X, Y_R2_Recall, '-g', marker='x', label='R2_rec')
    for i, j in zip(X, Y_R2_Recall):
        ax2.annotate(str(j), xy=(i, j), xytext=(-10, 10), textcoords='offset points')
    ax2.text(np.mean(X), np.mean(Y_R2_Recall) / 2, 'AUC: {:.2f}'.format(curveAucScore['R2']['recall']))
    ax2.fill_between(X, 0, Y_R2_Recall, facecolor='blue', alpha=0.4)

    ax3.plot(X, Y_RL_Recall, '-r', marker='x', label='RL_rec')
    for i, j in zip(X, Y_RL_Recall):
        ax3.annotate(str(j), xy=(i, j), xytext=(-10, 10), textcoords='offset points')
    ax3.text(np.mean(X), np.mean(Y_RL_Recall) / 2, 'AUC: {:.2f}'.format(curveAucScore['RL']['recall']))
    ax3.fill_between(X, 0, Y_RL_Recall, facecolor='blue', alpha=0.4)

    ax4.plot(X, Y_RSU_Recall, '-r', marker='x', label='RSU_rec')
    for i, j in zip(X, Y_RSU_Recall):
        ax4.annotate(str(j), xy=(i, j), xytext=(-10, 10), textcoords='offset points')
    ax4.text(np.mean(X), np.mean(Y_RSU_Recall) / 2, 'AUC: {:.2f}'.format(curveAucScore['RSU']['recall']))
    ax4.fill_between(X, 0, Y_RSU_Recall, facecolor='blue', alpha=0.4)

    ax5.plot(X, Y_LitePyramid_Recall, '-y', marker='x', label='LP_rec')
    for i, j in zip(X, Y_LitePyramid_Recall):
        ax5.annotate(str(j), xy=(i, j), xytext=(-10, 10), textcoords='offset points')
    ax5.text(np.mean(X), np.mean(Y_LitePyramid_Recall) / 2, 'AUC: {:.2f}'.format(curveAucScore['litepyramid']['recall']))
    ax5.fill_between(X, 0, Y_LitePyramid_Recall, facecolor='blue', alpha=0.4)

    ax1.legend()
    ax1.grid()
    ax2.legend()
    ax2.grid()
    ax3.legend()
    ax3.grid()
    ax4.legend()
    ax4.grid()
    ax5.legend()
    ax5.grid()

    #plt.show()
    plt.savefig(saveFigureFilepath)
    

def getLengthAtRouge(scores, rouge1Thres=-1., rouge2Thres=-1., rougeLThres=-1., rougeSUThres=-1., metricType='recall'):
    # input:
    #   - a list of dictionaries: {'results':{'R1': {'recall':<>,'precision':<>,'f1':<>}, 'R2': {...}, 'RL': {...}}, 'summary_len':<int>}
    
    
    rougeTlen = {
        'R1':{'threshold':rouge1Thres, 'summLen':-1},
        'R2':{'threshold':rouge2Thres, 'summLen':-1},
        'RL':{'threshold':rougeLThres, 'summLen':-1},
        'RSU':{'threshold': rougeSUThres, 'summLen': -1}
    }
    for scoreInfo in scores:
        summScore = scoreInfo['results']
        summLen = scoreInfo['summary_len']
        if rougeTlen['R1']['summLen'] < 0 and rouge1Thres > 0 and summScore['R1'][metricType] >= rouge1Thres:
            rougeTlen['R1']['summLen'] = summLen
        if rougeTlen['R2']['summLen'] < 0 and rouge2Thres > 0 and summScore['R2'][metricType] >= rouge2Thres:
            rougeTlen['R2']['summLen'] = summLen
        if rougeTlen['RL']['summLen'] < 0 and rougeLThres > 0 and summScore['RL'][metricType] >= rougeLThres:
            rougeTlen['RL']['summLen'] = summLen
        if rougeTlen['RSU']['summLen'] < 0 and rougeSUThres > 0 and summScore['RSU'][metricType] >= rougeSUThres:
            rougeTlen['RSU']['summLen'] = summLen

    return rougeTlen