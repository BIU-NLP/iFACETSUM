# the number of annotations (by different workers) that each summary should get:
num_annotation_per_summary = 6
# the amount of time (in seconds) that the user is allowed to do the assignment:
# even if the user is in the middle of the assignment, it can timeout.
time_allowed_for_assignment = 60*60
# the payment per assignment:
payment_per_assignment = 0.70
# the amount of time in seconds that the HIT appears in MTURK:
hit_lifetime = 7*24*60*60
# the delay until which the assignment is automatically approved in case it wansn't accepted/rejected:
auto_approval_delay = 2*24*60*60 #300

# the AWS keys to create the hit as a requester on Amazon Mechanical Turk:
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

# AMT assignment ID for preview:
amt_preview_assignment_id = 'ASSIGNMENT_ID_NOT_AVAILABLE'

topics_by_interface = {
    ## Practice Tasks:
    #'qfse': ['Steroid Use', 'Global Warming'],
    # Real Batch 1
    'qfse': ['Native American Challenges', 'Wetlands', 'Osteoarthritis', 'Automobile Safety', 'Quebec Separatist Movement', 'Evolution Teaching', 'Russia in Chechnya', 'EgyptAir Crash', 'School Safety', 'Stephen Lawrence Killing'],
    ## Real Batch 2
    #'qfse': ['Adoption', 'ADHD', 'Computer Viruses', 'Bookselling', 'Concorde Aircraft', 'Kursk Submarine', 'El Nino', 'US Affordable Housing', 'Elian Gonzales', 'Jimmy Carter International'],

}

algorithms = ['cluster'] #, 'textrank']

assignment_explorationTimeMinimum = 150
questionnaire_index = 3
initialSummaryWordLen = 75
interface_info = {
    'qfse': {
        'title': 'Explore a topic interactively and mark what facts are in the text',
        'description': 'Read and learn about a topic in an interactive interface by inputting queries. When you are done, mark whether 10 presented statements are found in the full text of your exploration session. [IMPORTANT: Task is not suitable for smartphones. Requires Chrome browser.]',
        'keywords': ["Interactive Exploration", "Summarization", "Question Answering", "Reading Comprehension", "Textual Content Evaluation"],
        'reward': payment_per_assignment
        },
}