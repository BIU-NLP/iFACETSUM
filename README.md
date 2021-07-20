# iFᴀᴄᴇᴛSᴜᴍ

iFᴀᴄᴇᴛSᴜᴍ is a demo application for exploring a document-set on a topic.
It provides information-seeking support by creating a faceted-navigation experience, using latest `CD Coreference Resolution`, `Proposition Alignment` and `Abstractive Summarization` technologies.


### How to run

1. git clone the project
2. Run `pip install -r requirements.txt`
2. Run `python WebApp/server/app.py`
3. Open in a web browser the file `WebApp/client/index.html`

### How to add your own data

1. Change `Config.py` to point to your data directory, including the text files and the cluster files (either json or conll format).

### How to create your own clusters

To support reproducibility efforts and adding custom document-sets, all models used were released and available online.

#### CD Event Co-reference Alignment

1. Create event mentions using the models and scripts in https://github.com/ariecattan/event_extractor.
2. Create pairwise mention scores and clusters using CDLM (link will be added soon).
3. Use agglomerative clustering to combine mentions into clusters.

#### CD Entities Co-reference Alignment

1. Create entities mentions using SpanBert, accessible from https://docs.allennlp.org/models/main/.
2. Use the WEC model to score each pairwise (link will be added soon).
3. Use agglomerative clustering to combine WD and CD mentions into clusters.

#### Proposition Alignment

1. Please refer to https://github.com/oriern/SuperPAL for instructions of extracting propositions using OIE and extracting pairwise scores.
2. iFᴀᴄᴇᴛSᴜᴍ's code takes care of converting the pairwise CSV from SuperPAL into clusters. 
