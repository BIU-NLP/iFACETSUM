# Interactive Expansion-Based Summarization

The InterExp project code and data. Includes the evaluation framework for session collection and measurement, the QFSE baseline systems (server and web application), data files, and crowdsourcing resources.

Resources for the paper: [Evaluating Interactive Summarization: an Expansion-Based Framework](https://arxiv.org/abs/2009.08380)

## General Info
Purpose of Interactive Expansion-Based Summarization:

- Explore a topic interactively, instead of reading a static summary and looking for missing information in the source documents.
- An InterExp system provides an initial summary, and then expands on it according to queries submitted by the user.
- We hypothesize that a semi-automatic summarizer, one that generates a summary together with a human, provides better results than when fully automatically generating a summary of the same length.
- See the demo system [here](http://u.cs.biu.ac.il/~shapiro1/qfse/).

Evaluation:

- A main challenge in InterExp is how to evaluate an interactive session. Here we provide a framework that looks at the accumulating information in an interactive session and computes the ROUGE scores against reference summaries.
- See an example task [here](http://u.cs.biu.ac.il/~shapiro1/qfse/qfse.html?topicId=Steroid%20Use&algorithm=cluster&timeAllowed=-5&questionnaireInd=3&allowNavigate=0&summWordlen=75&assignmentId=1&isPractice=0), which is used to collect a session and provides some motivation with a questionnaire.


## Code and Folders in the Project

### QFSE
The interactive summarization logic, and testing it out:

- *Corpus, Document and Sentence*: Parse the input corpus, including the source documents, reference summaries, and questionnaire files. Initialized when loading a new topic, preparing the sentence representations needed.
- *SummarizerBase*: The base class with which to create the summarizer. The main needed to implement from here are _getGenericSummaryText and _getQuerySummaryText. This class is also responsible for calculating ROUGE scores, if needed, against reference summaries.
- *SummarizerClustering*: Inheriting from SummarizerBase, this is the logic for a summarizer that uses a clustering method for generating the summary, using similarity of sentence embeddings. When querying, the summarizer looks for the most similar sentences to the query (based on embeddings similarity), and takes those that are different enough from already presented sentences.
- *SummarizerTextRankPlusLexical.py*: Inheriting from SummarizerBase, this is the logic for a summarizer that uses TextRank for generating the summary. When querying, the summarizer looks for the most similar sentences to the query (product of ROUGE precision metrics and word2vex similarity), and takes those that are different enough from already presented sentences.
- *SummarizerAddOne*: Inheriting from SummarizerClustering, does the same for the initial summary, but when querying gives the next cluster's representing sentence (queries are empty strings).
- *SuggestedQueriesBase*: A base class to implement a "suggest queries" list.
- *SuggestedQueriesNgramCount*: Inheriting from SuggestedQueriesBase, gives the most common ngrams list from the corpus.
- *SuggestedQueriesTextRank*: Inheriting from SuggestedQueriesBase, gives the phrases from the TextRank graph.
- *Main*: A class that enables running the summarizing system interactively over console. To run:
	- Change the SUMMARIZER_CLASS variable to your class name
	- Change the SUGGESTED_QUERIES_CLASS variable to your class name
	- To try out different sentence embeddings, can change the REPRESENTATION_STYLE variable to REPRESENTATION_STYLE_BERT which will load the Sentence-BERT module, and prepare (on-the-fly) BERT sentence embeddings in the Corpus class. This takes some time though when starting up the system (45 to 60 seconds on CPU laptop). If you keep it on REPRESENTATION_STYLE_SPACY, loading takes about 10 seconds.
	- DEFAULT_FIRST_SUMMARY_LENGTH is the length of the initial summary
	- EVALUATE_ON_THE_FLY is whether ROUGE should be calculated after each interaction
	- Pass in a topic name, like "Native American Challenges" to the program. (See the topic names in data/Config.py)
	- The output will be the initial summary, and then it will iteratively expect a query and generate the response.
	- Note: You may need to uncomment the first two lines (import sys; sys.path.append('..');) Run this script from the main folder.

### WebApp
- Server
	- *QFSEWebServer*: The tornado web server class, which is the backend of the web application. Works with JSON rest API. Writes logs to intSumm.log in the main folder. Keeps new interactions in data/db json file every minute (if anything is new).
	- *InfoManager*: A class that manages all the sessions on the server. Does this thread-safely so that the dictionaries are updated one operation at a time (the server may handle several sessions at a time over the web).
- Client
	- *general.js*: General functionality used on the site. Make sure to change the **requestUrl** to the correct backend URL when on a hosting server. Locally use http://127.0.0.1:1389.

### Data
- *DUC2006Clean*: The DUC 2006 corpus cleaned for quick use. Includes the documents, reference summaries and questionnaires.
	- Note about the questionnaires:
		- batch1 and batch2 each have 16 questions from the Lite-Pyramid.
		- batch10 has 10 random questions from batch1 and batch2
		- batch10pn has 5 random questions, 1 repeated, 2 negative questions (from other topics), and 2 place holders for positive questions (filled in the functionalityQuestionnaire.js client side file, to put two short sentences from the session). This is the batch to use in the mechanical turk tasks to assist in pinpointing insencere work.
	- *db*: Holds the session information from the web sessions in JSON files. Each time the system is rebooted, a new JSON is formed.

### Evaluation
- *RougeEvaluator*: A class that evaluates the ROUGE score between given texts and reference summaries.
- *evaluateSummarizer*: Runs ROUGE on a single static summary against the reference summaries
- *simulations*: Simulation files and code to run the different variations of the system on pre-prepared query lists.
	- CreateSimulationQueriesOracle.ipynb - run standalone. Creates the oracle simulation JSONs by using the real pyramid SCUs. The output has a list of queries to query the systems (simulationQueriesOracle.json).
	- *simulationEvaluation* - run from pyCharm within project. Runs the queries from a simulation JSON file on a specified summarizer and outputs the results and graphs to a local folder.
- *evaluateSummarizer* - run from pyCharm project; not updated. Runs the summarizer just to get a static summary at 250 words, and outputs the ROUGE scores to a file under data/DUC2006Clean
- *RougeEvaluator* - run from pyCharm project. By importing this file, enables calculating rouge with the function getRougeScores.
- *CompareSessionResults* - run standalone. Compares different session JSONs and outputs graphs and a CSV file that compares them (e.g. in simulations/resultsCompared folder). Includes intersecting AUCs and X at limit and Y at limit (ROUGE scores at 250 words, and word lengths at given ROUGE scores) calculations. This is the main script for evaluation!*
- *ShowSessionsStats* - run standalone. Shows statistics on sessions.
- *Corellations* - run standalone. Shows correlations between many different ratings, scores and aspects on the sessions.
- *FixRougeScoresInResultsFile* - fixes the scores of some ROUGE results, which may not be consistently correct likely due to some bug in the ROUGE computation during session collection. This notebook goes over all sessions and recalulates the scores if needed.


## Adding a New Summarizer

Generally, inherit from SummarizerBase and overload functions _getGenericSummaryText and _getQuerySummaryText.

## Evaluating a Summarizer

### Simulations

One artificial way of evaluating against other summarizers is by running a sequence of identical queries on the compared summarizers.
This is artificial because the queries are dependent on the information previously presented by the summarizer. Also each user might behave somewhat differently.
On the other hand, this is an easy way of getting a high level idea of how well a summarizer does when compared to other summarizers.
To do this:

- In the evaluation/simulation/CreateSimulationQueries.ipynb notebook, there are several boxes, each which makes a different json simulation of queries: "oracle" (top 10 real pyramid SCUs), "keyphrases" (indicates to take the top 10 suggextsed queries), and "highlights" (indicates to take the first 5 tokens of the last summary, or firt named entity or firsy noun phrase or first k characters).
- In evaluation/simulation/simulationEvaluation.py, change the SIMILARITY_STYLE and the SESSIONS_TO_RUN list (with simulation JSON path (from last bullet), output_folder, summarizer_class and suggested_queries_class according to your requirments), and the LITE_PYRAMID_MAP_FILEPATH with the mapping json filepath.
	- simulationQueriesOracleLite.json - a sequence of 10 random SCUs from the [lite-pyramid](https://github.com/OriShapira/LitePyramids) data
	- simulationQueriesOracle.json - a sequence of 10 highly weighted SCUs from the real pyramid data
	- simulationQueriesKeyphrases.json - a sequence of 10 top suggested queries from the suggested_queries_class requested
	- simulationQueriesHighlightsNP.json - indicates to take the first noun phrase from the last summary in the sequence
	- simulationQueriesHighlightsNE.json - indicates to take the first named entity from the last summary in the sequence
	- simulationQueriesHighlights5t.json - indicates to take the first five tokens from the last summary in the sequence
	- instead of putting a simulations json, you can put a '\*random_n_k\*' string, meaning run n sessions with k random queries (fully executed within this script)
		- a random query can be either the first noun phrase highlight from the last summary or a random (index 0 to 9) suggested query
- The output will include the curves of the simulations on all topics, as well as a results.json file with the ROUGE scores and other information.
- If there are several sessions per topic in the results json (like when using the \*random_n_k\* option), you can run the getAverageSimulationSessionJson.py script to get a results_avg JSON, averaging the sessions per topic via interpolation. In the script, change the SIMULATION_RESULTS_FILEPATH (relevant results.json from last step) and OUTPUT_JSON_FOLDER.
- In the evaluation/CompareSessionResults.ipynb notebook, change the inputFiles list (with the results.json files of the compared simulations) and the outputFolder. Then run the box. This will output the comaprative curves on all topics, as well as a comparison.csv file containing:
	- "auc_results*" columns with the AUC of Rouge 1, 2 and L and litepyramids of the compared methods
	- "limit_wordCount*" columns with what word-lengths the "score_limit" was reached
	- "limit_F1score*" columns with the ROUGE-F1 score and litepyramid-Recall score at "wordcount_limit" words of the session

### Collected Sessions

- Similar to the above explanation, the collected sessions (via crowdsourcing or user studies) can be compared per topic (instead of comparing systems per topic, compare workers per topic).
- We can then find the average and variance of the workers per topic at interpolated X values (word length) to get a curve that represents the system per topic. This will then allow us to compare different systems over many sessions.
- To get curves and statistics:
	- In MechanicalTurk/cleanDBJson.py, change the DB_FILE variable to the database JSON file of the sessions to analyze (make sure the DB includes only the sessions you need) and the IS_MTURK variable (True for mturk or False for controlled sessions). The output is a JSON file with the same name but with a "_clean" suffix. This now includes on sessions that are actual finished sessions from the input db file (i.e. removes example assignments).
	- In MechanicalTurk/generateResultsJson.py change the DB_FILE variable (the JSON output of the last script), the OUTPUT_JSON_FOLDER variable and the IS_MTURK variable (True for mturk or False for controlled sessions), and the LITE_PYRAMID_MAP_FILEPATH mapping json filepath. This script creates two JSON files in the output folder specified:
		- A json of all sessions in the format for evaluation/CompareSessionResults.ipynb to ingest
		- A json of the average of sessions per topic also in the above format
	- Run the evaluation/CompareSessionResults.ipynb notebook on the needed results json(s) to get curve figures and the comparison.csv file with the ROUGE scores and user ratings (if present).
	- Run the evaluation/ShowSessionsStats.ipynb notebook on the results json to get stats on the sessions there. It outputs on the topicID level and on the full data. (Output is within the notebook for now.)
	
#### MechanicalTurk
- Scripts for creating and viewing HITs, approving assignemnts, send messages to workers, blocking/bonusing workers, and other functionalities on Amazon Mechanical Turk. Make sure to set whether you're working in the sandbox or for real (hits_in_live variable within scripts). Put the relevent MTurk credentials in the AMT_Parameters.py file (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).

- Processing the collected sessions
	- The sessions collected with crowdsourcing need some parsing/fixing before being analyzed.
	- This includes recomputing some ROUGE scores, which may be wrong for some reason when computed during session collection. (step 6)
		- Since this fix takes time, steps 1 to 5 explain how to recompute scores only for the newly added sessions.
	- Also the sessions are converted to somewhat of a different format to be consistent with the simulations format and for easier (manual) reading. (step 7)
Finally, the parsed sessions are analyzed in steps 8, 9 and 10.
	- Steps:
		1. From the server, copy the new sessions and the added sentences in the db file to RealSessions/results_table.json
		2. Run MechanicalTurk\results\cleanDBJson.py with DB_FILE = '../RealSessions/results_table.json'
		3. Change the name of RealSessions/results_table_clean.json to RealSessions/results_table_clean_bad.json
		4. Change the name of RealSessions/results_table_clean_fixed.json to RealSessions/results_table_clean_fixed_.json
		5. Copy the new session(s) from RealSessions/results_table_clean_bad.json to RealSessions/results_table_clean_fixed_.json
		6. Run FixRougeScoresInResultsFile.ipynb with
			resultsFilePath = '../MechanicalTurk/RealSessions/results_table_clean_fixed_.json'
			resultsFixedFilePath = '../MechanicalTurk/RealSessions/results_table_clean_fixed.json'
			ONLY_TOPICS = [<newly added sessions topic ids>]
			ONLY_WORKERS = [<newly added sessions worker ids>]
		7. Run MechanicalTurk/results/generateResultsJson.py with
			DB_FILE = '../RealSessions/results_table_clean_fixed.json'
			OUTPUT_JSON_FOLDER = '../RealSessions'
			NUM_MISTAKES_ALLOWED_IN_QUESTIONNAIRE = 4
			SESSION_INTERSECTION_MIN_COUNT = -1
		8. Run evaluation/CompareSessionResults.ipynb with
			inputFiles = \[
			    '../MechanicalTurk/RealSessions/results_SummarizerClustering_avg.json',
			    '../MechanicalTurk/RealSessions/results_SummarizerTextRankPlusLexical_avg.json', ...\]
		9. Run evaluation/Corellations.ipynb for correlations between different metrics
		10. Run evaluation/ShowSessionsStats.ipynb for statistics on the sessions file

- Controlled crowdsourcing
	- TrapTask - includes the AMT html for the task, with the input CSV for the HITs we released, and the script for analyzing the results.
	- Practice tasks - This is released in AMT with the script AMT_createHITs.py, with relevant variable changes within the script an in AMT_Parameters.py. The GUI of the QFSE is chabged with the isPractice=1 CGI argument in the URL.
	- Real session collection - This is released in AMT with the script AMT_createHITs.py, with relevant variable changes within the script an in AMT_Parameters.py.
	- In the SessionCollected folder, the "controlled" folder includes the collected data with some corresponding resulting outputs.
