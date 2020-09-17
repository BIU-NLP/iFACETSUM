# based on: https://github.com/aws-samples/mturk-code-samples/blob/master/Python/CreateHitSample.py
# see for help: https://boto3.readthedocs.io/en/latest/reference/services/mturk.html
# see more examples in: https://blog.mturk.com/tutorial-a-beginners-guide-to-crowdsourcing-ml-training-data-with-python-and-mturk-d8df4bdf2977

import sys
import boto3
from boto.mturk.question import ExternalQuestion
import AMT_Parameters as config
import time
import datetime
import logging
logging.basicConfig(filename='logAMTqfse.log', level=logging.INFO, format='%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s')


LOG_INFO = 0
LOG_ERROR = -1
def writeMessage(msg, logType=LOG_INFO):
    if logType == LOG_INFO:
        #print('INFO: ' + msg)
        logging.info(msg)
    elif logType == LOG_ERROR:
        #print('ERROR: ' + msg)
        logging.error(msg)


# BASIC HIT PARAMETERS
create_hits_in_live = False #True # false means sandbox
is_practice_task = False # false means real sessions, true means practice sessions
if is_practice_task:
    hit_url_format = ""
    for interface in config.interface_info:
        config.interface_info[interface]['title'] += ''
else:
    hit_url_format = ""

# QUALIFICATION CONFIGURATION
# See: http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html#ApiReference_QualificationType-IDs
worker_requirements = [
    { # Worker_PercentAssignmentsApproved
        'QualificationTypeId': '000000000000000000L0',
        'Comparator': 'GreaterThanOrEqualTo',
        'IntegerValues': [99],
        'RequiredToPreview': True
    },
    { # Worker_NumberHITsApproved
        'QualificationTypeId': '00000000000000000040',
        'Comparator': 'GreaterThan',
        'IntegerValues': [500],
        'RequiredToPreview': True
    },
    #{ # Worker_Locale
    #    'QualificationTypeId': '00000000000000000071',
    #    'Comparator': 'In',
    #    'LocaleValues':[
    #        {'Country':"US"},
    #        {'Country':"AU"},
    #        {'Country':"GB"}
    #    ],
    #    'RequiredToPreview': True
    #}
]

# add the practice task qualification:
if is_practice_task:
    if create_hits_in_live: # real
        worker_requirements.append({'QualificationTypeId': '', 'Comparator': 'Exists', 'RequiredToPreview': True})
    else: # sandbox
        worker_requirements.append({'QualificationTypeId': '', 'Comparator': 'Exists', 'RequiredToPreview': True})

# add the real session task qualification, if these are real sessions (and not the practice task):
if not is_practice_task:
    if create_hits_in_live:  # real
        worker_requirements.append({'QualificationTypeId': '', 'Comparator': 'Exists', 'RequiredToPreview': True})
    else:  # sandbox
        worker_requirements.append({'QualificationTypeId': '', 'Comparator': 'Exists', 'RequiredToPreview': True})

frame_height = 800

environments = {
        "live": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview",
            "manage": "https://requester.mturk.com/mturk/manageHITs"
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview",
            "manage": "https://requestersandbox.mturk.com/mturk/manageHITs"
        },
}
mturk_environment = environments["live"] if create_hits_in_live else environments["sandbox"]

# create a client with which to work on MTurk:
mturkClient = boto3.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)

# Test that you can connect to the API by checking your account balance
user_balance = mturkClient.get_account_balance()

# In Sandbox this always returns $10,000. In live, it will be your acutal balance.
writeMessage('Your account balance is {}'.format(user_balance['AvailableBalance']))

# create the HITs for each eventID:
startTime = datetime.datetime.now()
writeMessage('Starting creation of HITs...')
hitIDsCreated = []


for algorithm in config.algorithms:
    for interface, topics in config.topics_by_interface.items():
        for topic in topics:
            # the URL to the HIT interface (setting the relevant CGI parameters):
            # "https://u.cs.biu.ac.il/~shapiro1/qfse/{}.html?topicId={}&topicName={}&algorithm={}&timeAllowed={}&questionnaireInd={}&allowNavigate=0"
            hit_url = hit_url_format.format(interface, topic, algorithm, -config.assignment_explorationTimeMinimum, config.questionnaire_index, config.initialSummaryWordLen)

            # create the AMT external question object XML for the HIT:
            questionform = ExternalQuestion(hit_url, frame_height).get_as_xml()

            # Create the HIT:
            newHit = mturkClient.create_hit(
                MaxAssignments=config.num_annotation_per_summary,
                LifetimeInSeconds=config.hit_lifetime,
                AssignmentDurationInSeconds=config.time_allowed_for_assignment,
                Reward=str(config.interface_info[interface]['reward']),
                Title=config.interface_info[interface]['title'],
                Keywords=','.join(config.interface_info[interface]['keywords']),
                Description=config.interface_info[interface]['description'],
                Question=questionform,
                QualificationRequirements=worker_requirements,
                AutoApprovalDelayInSeconds=config.auto_approval_delay,
                RequesterAnnotation=''
            )

            writeMessage('A new HIT has been created. You can preview it here: {}'.format(mturk_environment['preview'] + '?groupId=' + newHit['HIT']['HITGroupId']))
            writeMessage('HITID = ' + newHit['HIT']['HITId'] + ' (Use to Get Results)')
            #writeMessage('\tTime from start: {0:.2f} minutes'.format(((datetime.datetime.now() - startTime).seconds) / 60.0))

            # keep the HIT ID to track that it has finished:
            hitIDsCreated.append({'hitId':newHit['HIT']['HITId'], 'interface':interface, 'topic':topic, 'algorithm': algorithm, 'timeAllowed':config.time_allowed_for_assignment, 'questionnaireInd':config.questionnaire_index, 'reward':config.interface_info[interface]['reward']})


writeMessage('\nResults can be seen here: {}'.format(mturk_environment['manage']))
writeMessage('Finished creation of HITs:')
writeMessage('\n{}'.format('\n'.join('\t{}'.format(hitInfo) for hitInfo in hitIDsCreated)))
writeMessage('\tTime from start: {0:.2f} minutes'.format(((datetime.datetime.now() - startTime).seconds) / 60.0))

# wait for all assignments to finish:
writeMessage('\nWaiting for all assignments to finish...')
hitsComplete = {hitInfo['hitId']:False for hitInfo in hitIDsCreated}
while True:
    time.sleep(120) # wait in 2 minute intervals to check whether assignments have completed
    writeMessage('Waiting for finish: {:.2f} minutes'.format(((datetime.datetime.now() - startTime).seconds) / 60.0))
    for hitInfo in hitIDsCreated:
        hitId = hitInfo['hitId']
        # check on the hit if it has not completed yet:
        if not hitsComplete[hitId]:
            # get the hit assignments that were submitted for the HIT:
            worker_results = mturkClient.list_assignments_for_hit(HITId=hitId, AssignmentStatuses=['Submitted'])
            # if all assignments have completed, mark as done:
            if worker_results['NumResults'] >= config.num_annotation_per_summary:
                hitsComplete[hitId] = True
                writeMessage('\tHIT completed: {}'.format(hitId))
            else:
                writeMessage('\tHIT {} has completed {} assignments so far'.format(hitId, worker_results['NumResults']))
    # if all HITs have completed, break the loop:
    if all(hitsComplete[hitId] for hitId in hitsComplete):
        break

writeMessage('All HITS have been completed. DONE!')
writeMessage('\tTime from start: {0:.2f} minutes'.format(((datetime.datetime.now() - startTime).seconds) / 60.0))