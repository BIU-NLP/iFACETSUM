import webServerParameters as config
import boto3
from xml.dom.minidom import parseString

hits_in_live = True # false means sandbox
environments = {
        "live": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview",
            "manage": "https://requester.mturk.com/mturk/manageHITs",
            "reward": str(config.payment_per_assignment)
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview",
            "manage": "https://requestersandbox.mturk.com/mturk/manageHITs",
            "reward": "1.23"
        },
}
mturk_environment = environments["live"] if hits_in_live else environments["sandbox"]
    
mturkClient = boto3.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)

assignments = {
    'assignmentID': {'workerId':'', 'bonusAmount':'', 'bonusMsg':'', 'msgGeneral':'', 'block':False, 'hitId':''},
}
rejections = {
    'assignmentID': {'msg':''},
}



for assignment_id in assignments:
    worker_id = assignments[assignment_id]['workerId']
    
    if assignment_id not in rejections:
        try:
            mturkClient.approve_assignment(
                AssignmentId = assignment_id,
                RequesterFeedback = assignments[assignment_id]['msgGeneral'],
                OverrideRejection=False
            )
            print('Assignment approved: ' + assignment_id)
        except Exception as e:
            print('Assignment not approved: ' + assignment_id + ':\n\t' + str(e))

    try:
        if assignments[assignment_id]['bonusAmount'] != '':
            response = mturkClient.send_bonus(
                WorkerId = worker_id,
                BonusAmount = assignments[assignment_id]['bonusAmount'],
                AssignmentId = assignment_id,
                Reason = assignments[assignment_id]['bonusMsg'],
                UniqueRequestToken = assignment_id
            )
            print('Bonus given for assignment ' + assignment_id + ' amount $' + assignments[assignment_id]['bonusAmount'])
    except Exception as e:
        print('Bonus not given for assignment ' + assignment_id + ':\n\t' + str(e))
        
        
    try:
        if assignments[assignment_id]['block']:
            mturkClient.create_worker_block(
                WorkerId=worker_id,
                Reason=assignments[assignment_id]['msgGeneral']
            )
            print('Worker blocked: ' + worker_id)
    except Exception as e:
        print('Block failed: ' + worker_id + ':\n\t' + str(e))

for assignment_id in rejections:
    try:
        response = mturkClient.reject_assignment(
            AssignmentId=assignment_id,
            RequesterFeedback=rejections[assignment_id]['msg']
        )
        print('Assignment rejected: ' + assignment_id)
    except Exception as e:
        print('Reject failed: ' + assignment_id + ':\n\t' + str(e))