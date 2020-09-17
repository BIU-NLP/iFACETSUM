import boto3
import AMT_Parameters as config

create_hits_in_live = True # false means sandbox
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

"""
Get a list of workers with the specified qualification
"""
def workers_with_qualType(qualTypeId, mturkClient):
    response = mturkClient.list_workers_with_qualification_type(
        QualificationTypeId=qualTypeId,
        MaxResults=20
    )
    return [q['WorkerId'] for q in response['Qualifications'] if q['Status']=='Granted']

"""
Function for associating a qualification to a group of workers.
"""
def associate_workers_with_qualification(workers, qualificationId, mturkClient, notify=False):
    for worker in workers:
        response = mturkClient.associate_qualification_with_worker(
            QualificationTypeId=qualificationId,
            WorkerId=worker,
            IntegerValue=1,
            SendNotification=notify
        )
        response = response['ResponseMetadata']
        if response['HTTPStatusCode']==200:
            print(f"worker {worker}: success.")
        else:
            print(f"worker {worker}: fail; ", response)

"""
Function for disassociating a qualification to a group of workers.
"""
def disassociate_workers_from_qualification(workers, qualificationId, mturkClient, reason):
    for worker in workers:
        response = mturkClient.disassociate_qualification_from_worker(
            QualificationTypeId=qualificationId,
            WorkerId=worker,
            Reason=reason
        )
        response = response['ResponseMetadata']
        if response['HTTPStatusCode']==200:
            print("worker {}: success.".format(worker))
        else:
            print("worker {}: fail.".format(worker), response)

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
print('Your account balance is {}'.format(user_balance['AvailableBalance']))


WORKERS = []
QUALIFICATION_ID = ''

print('Before association:')
print(workers_with_qualType(QUALIFICATION_ID, mturkClient))
associate_workers_with_qualification(WORKERS, QUALIFICATION_ID, mturkClient, True)
print('After association:')
print(workers_with_qualType(QUALIFICATION_ID, mturkClient))
#disassociate_workers_from_qualification(WORKERS, QUALIFICATION_ID, mturkClient, "Testing disassociation.")
#print('After disassociation:')
#print(workers_with_qualType(QUALIFICATION_ID, mturkClient))