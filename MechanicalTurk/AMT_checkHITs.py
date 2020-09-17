import boto3
import AMT_Parameters as config

create_hits_in_live = True #True # false means sandbox

HIT_IDS = {
    'name' : ['list of hitIDs']
}

if create_hits_in_live:
    mturk_endpoint = "https://mturk-requester.us-east-1.amazonaws.com"
else:
    mturk_endpoint = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"

# create a client with which to work on MTurk:
mturkClient = boto3.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_endpoint,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)

# Test that you can connect to the API by checking your account balance
# In Sandbox this always returns $10,000. In live, it will be your acutal balance.
user_balance = mturkClient.get_account_balance()
print('Your account balance is {}'.format(user_balance['AvailableBalance']))

# check if the HITs are alive or not:
print('hitId, status, numMaxAssignmentsPending, numPending, numAvailable, numCompleted, expiration')
for groupName, groupHitIdsList in HIT_IDS.items():
    print('Group: {}'.format(groupName))
    for hitId in groupHitIdsList:
        hitInfo = mturkClient.get_hit(HITId=hitId)
        status = hitInfo['HIT']['HITStatus']
        numMaxAssignmentsPending = hitInfo['HIT']['MaxAssignments']
        numPending = hitInfo['HIT']['NumberOfAssignmentsPending']
        numAvailable = hitInfo['HIT']['NumberOfAssignmentsAvailable']
        numCompleted = hitInfo['HIT']['NumberOfAssignmentsCompleted']
        expiration = hitInfo['HIT']['Expiration']
        print('\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(hitId, status, numMaxAssignmentsPending, numPending, numAvailable, numCompleted, expiration))