import csv
import numpy as np

INPUT_CSV_FILEPATH = '1_Batch_4013008_batch_results.csv'
#INPUT_CSV_FILEPATH = '2_Batch_4013675_batch_results.csv'

workerResults = {} # workerId -> topicId -> qNum -> score
workerTimes = {} # workerId -> topicId -> timeInSeconds
workerAssignments = {} # workerId -> [assignmentIds]
with open(INPUT_CSV_FILEPATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # only use submitted work:
        if row['AssignmentStatus'] != 'Submitted':
            continue
            
        topicId = row['Input.TopicId']
        workerId = row['WorkerId']
        assignmentId = row['AssignmentId']
        workTime = int(row['WorkTimeInSeconds'])
            
        workerAssignments.setdefault(workerId, []).append(assignmentId)
        
        if workerId not in workerResults:
            workerResults[workerId] = {}
            workerTimes[workerId] = {}
        if topicId not in workerResults[workerId]:
            workerResults[workerId][topicId] = {}
        workerTimes[workerId][topicId] = workTime
        
        for columnName, columnVal in row.items():
            # first two questions:
            if columnName.startswith('Answer.') and '::Q' in columnName:
                qId = columnName.split('::')[-2] # ex. 'Answer.D0701A::Q1_1.D0701A::Q1_1::-1' -> 'Q1_1'
                qNum, qOpt = qId.split('_') # ex. 'Answer.D0701A::Q1_1.D0701A::Q1_1::-1' -> 'Q1', '1'
                qAnsScore = int(columnName.split('::')[-1]) # ex. 'Answer.D0701A::Q1_1.D0701A::Q1_1::-1' -> -1
                
                # if the value is 'true' then this is the radio button chosen by the user:
                isWorkerChoice = columnVal
                if isWorkerChoice == 'true' or isWorkerChoice == 'TRUE':
                    workerResults[workerId][topicId][qNum] = qAnsScore
            if columnName == 'Answer.third_query':
                workerResults[workerId][topicId]['Q3'] = columnVal
                    
print(workerResults)
print()
# print the results for each of the workers:
print('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format('workerId', 'avgWorkTime', 'numHitsCompleted', 'avgScore', 'num1s', 'num0s', 'numNeg1s', 'numQ3Filled'))
workersQualified = []
badWorkers = {}
for workerId in workerResults:
    workerScore = 0
    q1AnswerCounter = {-1:[], 0:[], 1:[]} # keeps the topicIds of each answer type
    q2AnswerCounter = {-1:[], 0:[], 1:[]} # keeps the topicIds of each answer type
    q3Filled = [] # keeps (topicId, answer) tuples of the q3s filled
    numHitsCompleted = len(workerResults[workerId])
    
    for topicId in workerResults[workerId]:
        # check whether this user did this topic
        if 'Q1' not in workerResults[workerId][topicId] or 'Q2' not in workerResults[workerId][topicId]:
            badWorkers[workerId] = badWorkers.setdefault(workerId, 0) + 1
            continue
        
        workerScore += (workerResults[workerId][topicId]['Q1'] + workerResults[workerId][topicId]['Q2'])
        q1AnswerCounter[workerResults[workerId][topicId]['Q1']].append(topicId)
        q2AnswerCounter[workerResults[workerId][topicId]['Q2']].append(topicId)
        if len(workerResults[workerId][topicId]['Q3']) > 0: # len of q3 is > 0 chars
            q3Filled.append((topicId, workerResults[workerId][topicId]['Q3']))
        
    if len(q1AnswerCounter[-1])+len(q2AnswerCounter[-1]) == 0 \
        and numHitsCompleted - len(q3Filled) == 0 \
        and len(q1AnswerCounter[0])+len(q2AnswerCounter[0]) == 0 \
        and len(workerResults[workerId]) == 1:
        
        workersQualified.append(workerId)
    
        print('{}\t{:.2f} min\t{}\t{}\t{}\t{}\t{}\t{}'.format(
            workerId, np.mean(list(workerTimes[workerId].values()))/60, 
            numHitsCompleted, float(workerScore)/numHitsCompleted, 
            len(q1AnswerCounter[1])+len(q2AnswerCounter[1]),
            len(q1AnswerCounter[0])+len(q2AnswerCounter[0]),
            len(q1AnswerCounter[-1])+len(q2AnswerCounter[-1]), len(q3Filled)))
        print('\tq1  1s\t{}'.format(q1AnswerCounter[1]))
        print('\t    0s\t{}'.format(q1AnswerCounter[0]))
        print('\t   -1s\t{}'.format(q1AnswerCounter[-1]))
        print('\tq2  1s\t{}'.format(q2AnswerCounter[1]))
        print('\t    0s\t{}'.format(q2AnswerCounter[0]))
        print('\t   -1s\t{}'.format(q2AnswerCounter[-1]))
        print('\tq3')
        for ans in q3Filled:
            print('\t\t{}\t{}'.format(ans[0], ans[1]))
        print('\t\t{} missing'.format(numHitsCompleted - len(q3Filled)))
        print()
    
print('Num workers total: ' + str(len(workerResults)))
print(list(workerResults.keys()))
print('Num workers qualified: ' + str(len(workersQualified)))
print(workersQualified)
qualifiedAssignments = [aId for workerId in workersQualified for aId in workerAssignments[workerId]]
print('Num qualified assignments: ' + str(len(qualifiedAssignments)))
print(qualifiedAssignments)
print('Num bad workers: ' + str(len(badWorkers)))
print(badWorkers)