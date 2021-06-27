# CorExplore

CorExplore is a demo application for exploring a document-set on a topic.
It provides information-seeking support by creating a faceted-navigation experience, using latest `CD Coreference Resolution`, `Proposition Alignment` and `Abstractive Summarization` technologies.


### How to run

1. git clone the project
2. Run `pip install -r requirements.txt`
2. Run `python WebApp/server/app.py`
3. Open in a web browser the file `WebApp/client/qfse.html`

### How to add your own data

1. Change `Config.py` to point to your data directory, including the text files and the cluster files (either json or conll format).

### How to create your own clusters

See CorExplore paper for more details (soon).
