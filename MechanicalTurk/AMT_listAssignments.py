import AMT_Parameters as config
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

hitIDs = []

for hit_id in hitIDs:
    hit = mturkClient.get_hit(HITId=hit_id)
    print('Hit {} status: {}'.format(hit_id, hit['HIT']['HITStatus']))
    response = mturkClient.list_assignments_for_hit(
        HITId=hit_id,
        AssignmentStatuses=['Submitted', 'Approved'],
        MaxResults=10,
    )

    assignments = response['Assignments']
    print('The number of submitted assignments is {}'.format(len(assignments)))
    for assignment in assignments:
        worker_id = assignment['WorkerId']
        assignment_id = assignment['AssignmentId']
        answer_xml = parseString(assignment['Answer'])

        # the answer is an xml document. we pull out the value of the first
        # //QuestionFormAnswers/Answer/FreeText
        answer = answer_xml.getElementsByTagName('FreeText')[0]
        # See https://stackoverflow.com/questions/317413
        only_answer = " ".join(t.nodeValue for t in answer.childNodes if t.nodeType == t.TEXT_NODE)

        print('The Worker with ID {} submitted assignment {} and gave the answer "{}"'.format(worker_id, assignment_id, only_answer))

        print(mturkClient.get_assignment(AssignmentId=assignment_id))
        
        '''
        # Approve the Assignment (if it hasn't already been approved)
        if assignment['AssignmentStatus'] == 'Submitted':
            print 'Approving Assignment {}'.format(assignment_id)
            mturkClient.approve_assignment(
                AssignmentId=assignment_id,
                RequesterFeedback='good',
                OverrideRejection=False,
            )
        '''