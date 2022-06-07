const e = React.createElement;
let globalQuery = [];
const $queryArea = $('#queryArea');
const $documentsListArea = $('#documentsListArea');
const $documentsList = $('#documentsList');
const $mentionsListArea = $('#mentionsListArea');
const $mentionsList = $('#mentionsList');
const $propositionsListArea = $('#propositionsListArea');
const $propositionsList = $('#propositionsList');
const $explorationPage = $('#explorationPage');
const $toolbarNavigationItems = $('.toolbar-navigation-item');
const $documentsPane = $('#documentsPane');
const $mentionsPane = $('#mentionsPane');
const $propositionsPane = $('#propositionsPane');
const globalListItemCallbacks = [];
//var moreInfoButton = document.getElementById("addMoreButton");
var keywordList = document.getElementById("keywordsList");
var keywordsArea = document.getElementById("keywordsArea");
var topicsDropdown = document.getElementById("topicsDropdownContent");
var stopExploringButton = document.getElementById('stopExploringButton');
var curTopicId = null;
var isWaitingForResponse = false;
var isWaitingForInitial = false;
var questionnaireBatchInd = -1;
var totalTextLength = 0;
let globalDocumentsMetas = null;
let globalQueriesResults = {};
const globalClustersMetas = {};
const globalState = {};
var pageBaseUrl = "index.html";
var summaryType = "qfse";
var timeAllowed = -1;
var lastQuery = null;
var iterationNum = 0; // keeps track of how many iterations there are (0 is the initial summary)
var iterationStarRatingType = 0; // 0=none , 1=rating , 2=newInfo
var lastIterationRated = false; // each iteration's summary must be rated before continuing to the next iteration
var allTextsInSession = [];
var questionnaireList = [];
var assignmentId = '';
var hitId = '';
var workerId = '';
var turkSubmitTo = '';
var clientId = uuidv4(); // generate a random clientID for this summarization session

const KEY_CONCEPTS_LABEL = "Concepts";
const KEY_STATEMENTS_LABEL = "Statements";
const PERSON_LABEL = "Person";
const ORGANIZATION_LABEL = "Organization";
const LOCATION_LABEL = "Location";
const NORP_LABEL = "Nationality, Religious, Political";
const DATE_LABEL = "Date";
const ENTITIES_LABEL = "Entities";
const MISC_LABEL = "Miscellaneous";

const FIELD_TO_SORT_CLUSTERS = "num_mentions_filtered";
//const FIELD_TO_SORT_CLUSTERS = "num_sents_filtered";


const CLUSTERS_FACETS_ORDER = [KEY_CONCEPTS_LABEL, ENTITIES_LABEL, KEY_STATEMENTS_LABEL, PERSON_LABEL, LOCATION_LABEL, ORGANIZATION_LABEL, NORP_LABEL, MISC_LABEL];

const CLUSTER_FACET_TO_TOOLTIP = {};
const default_tooltip = "co-occurring in the document set, press a cluster to get its summary and filtered navigation";
CLUSTER_FACET_TO_TOOLTIP[KEY_CONCEPTS_LABEL] = `Concepts ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[KEY_STATEMENTS_LABEL] = `Statements ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[ENTITIES_LABEL] = `Entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[PERSON_LABEL] = `Person entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[ORGANIZATION_LABEL] = `Organization entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[LOCATION_LABEL] = `Location entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[NORP_LABEL] = `${NORP_LABEL} entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[DATE_LABEL] = `${DATE_LABEL} entities ${default_tooltip}`;
CLUSTER_FACET_TO_TOOLTIP[MISC_LABEL] = `Uncategorized entities ${default_tooltip}`;

NUM_OF_SENTS_PER_FACET = {};
NUM_OF_SENTS_PER_FACET[KEY_STATEMENTS_LABEL] = 3;

LABELS_TO_FILTER = [DATE_LABEL];


//var CHAR_NUMBER = String.fromCharCode(0x2780); // see https://www.toptal.com/designers/htmlarrows/symbols/ for more
var RATING_PARAMS = {
    1 : {
        'numStars':5,
        'signCharacter': CHAR_STAR,
        'instructionsInitial':'Summary quality:',
        'explanationInitial':'How useful is this information regarding the main topic?',
        'instructionsRest':'Response satisfaction:',
        'explanationRest':'Relevant to the query, and informative for the topic.',
        'starLabelClassInitial' : 'explainLabelAboveType1',
        'starLabelClassRest' : 'explainLabelAboveType1'
    },
    2 : {
        'numStars':5, //10
        'signCharacter': CHAR_CHECKMARK,
        'instructionsInitial':"How useful is this for the journalist's generic overview of the topic?",
        'explanationInitial':"If it's way off topic, give a low score. If it's very useful for the journalist's generic overview, give a high score.",
        'instructionsRest':'How much useful info does this add to the journalist\'s overview (regardless of how well it matched your query)?',
        'explanationRest':"More new and useful information should yield a higher score.",
        'starLabelClassInitial' : 'explainLabelAboveType2Iteration1',
        'starLabelClassRest' : 'explainLabelAboveType2Iteration2'
    }
};


function setNoTopicChosen() {
    document.getElementById("topicNameHeader").innerHTML = "Choose a topic to explore.";
    document.getElementById("numDocumentsHeader").innerHTML = "";
    // hide the keywords area and the query box:
    keywordsArea.style.display = "none";
}

/* Resets the keyphrases list and the the exploration pane. */
function resetPage() {
//    while (keywordList.firstChild) {
//        keywordList.removeChild(keywordList.firstChild);
//    }

    $('#queriesModal').modal('hide');
}


function setTopic(topicInfo) {
    var keyPhrasesList = topicInfo['keyPhraseList'];
    var name = topicInfo['topicName'];
    var topicId = topicInfo['topicId'];
    var initialSummaryList = topicInfo['summary'];
    var numDocuments = topicInfo['numDocuments'];
    const documentsMetas = topicInfo['documentsMetas'];
    globalDocumentsMetas = documentsMetas;
    const corefClustersMetas = topicInfo['corefClustersMetas'];
    const eventsClustersMetas = topicInfo['eventsClustersMetas'];
    const propositionClustersMetas = topicInfo['propositionClustersMetas'];
    saveCorefClusters(corefClustersMetas, eventsClustersMetas, propositionClustersMetas);
    insertSummaryItemsInExplorationPane([], isLoading=false);


    //var timeAllowed = topicInfo['timeAllowed'];
    var textLength = topicInfo['textLength'];
    questionnaireList = topicInfo['questionnaire'];

//    resetPage();
    curTopicId = topicId;
    // set the event name and keyphrases of the event:
    document.getElementById("topicNameHeader").innerHTML = name;
    document.getElementById("numDocumentsHeader").classList.add("myTooltip");
    document.getElementById("numDocumentsHeader").style.cursor = "help";
//    document.getElementById("numDocumentsHeader").innerHTML = '' +
//        'Summary of <span>' + numDocuments + ' articles</span>' +
//        '<div class="bottomTooltip" style="width: 350px;">' +
//        'Article sources: New York Times, Associated Press and Xinhua News Agency (years 1995-2000)' +
//        '<i></i>' +
//        '</div>' +
//        ' on';

    createClustersIdsList();

    // keep the text length so far:
    totalTextLength = textLength;

    // show the keywords area and search box in case they were hidden:
    keywordsArea.style.display = "block";


    // set that the request has been responded to:
    isWaitingForInitial = false;

    // make the page visible to the annotator and show relevant functionalities:
    showPageToAnnotator();
}

function getFixedClustersBasedOnGlobalQueries(dataQueryIdx) {
    const queryResult = globalQueriesResults[dataQueryIdx];
    const origSentences = queryResult['orig_sentences'];

    const fixedClusters = [];
    for (const clusterQuery of queryResult['query']) {
        fixedClusters.push(parseInt(clusterQuery['cluster_id']));
    }

    return fixedClusters;
}

function initializeModal() {
    $('#origSentencesModal').on('show.bs.modal', function(event) {
        const dataQueryIdx = $(event.relatedTarget).attr('data-query-idx');
        const queryResult = globalQueriesResults[dataQueryIdx];
        const origSentences = queryResult['orig_sentences'];

        const fixedClusters = getFixedClustersBasedOnGlobalQueries(dataQueryIdx);

        const htmlElementToRenderInto = document.createElement("div");

        const reactToRender = e(
            ListItem,
            {
                "resultSentences": origSentences,
                "numSentToShow": 10,
                "showPopover": false, // Don't show a popover inside a modal
                "fixedClusters": fixedClusters, // Show only clusters that were used to query
                "isSummary": false
            }
        );


        ReactDOM.render(reactToRender, htmlElementToRenderInto);

        const $modalBody = $('#origSentencesModal .modal-body');
        $modalBody[0].replaceChildren(htmlElementToRenderInto); //add to exploration list

        logUIAction("orig_sentences_modal", {"query_idx": dataQueryIdx});

    });

    $('#historyModal').on('show.bs.modal', function(event) {
        const queryResults = Object.values(globalQueriesResults);

        const htmlElementToRenderInto = document.createElement("div");

        const reactToRender = e(
            SummaryList,
            {
                "queryResults": queryResults,
                "numSentToShow": 10,
                "showPopover": false, // Don't show a popover inside a modal
                "showHistoryBtn": false // Don't show history button inside history modal
            }
        );


        ReactDOM.render(reactToRender, htmlElementToRenderInto);

        const $modalBody = $('#historyModal .modal-body');
        $modalBody[0].replaceChildren(htmlElementToRenderInto); //add to exploration list

        logUIAction("historyModal", {});

    });

    $('#queriesModal').on('show.bs.modal', function(event) {
        const clusterFacet = $(event.relatedTarget).attr('data-cluster-facet');

        const allClusters = globalClustersMetas['all'];
        const labelClusters = allClusters[clusterFacet];
        const clustersQuery = globalQuery;

        const htmlElementToRenderInto = document.createElement("div");

        const multiFacetLabel = ENTITIES_LABEL;

        let reactToRender;
        if (clusterFacet !== multiFacetLabel) {
            reactToRender = e(
                LabelClustersItem,
                {
                    "labelClusters": labelClusters,
                    "clustersQuery": clustersQuery,
                    "minimized": false
                }
            );
        } else {
            const entitiesClusters = {};
            for (const cluster of globalClustersMetas["all"][ENTITIES_LABEL]) {
                const clusterLabel = cluster['cluster_label'];
                const currArray = entitiesClusters[clusterLabel] || [];
                entitiesClusters[clusterLabel] = currArray;
                currArray.push(cluster);
            }

            // Multiple sub facets
            reactToRender = e(
                ClustersIdsList,
                {
                    "allClusters": entitiesClusters,
                    "clustersQuery": globalQuery,
                    "useLabelAsFacet": true,
                    "minimized": false
                }
            );
        }

        ReactDOM.render(reactToRender, htmlElementToRenderInto);

        const $modalBody = $('#queriesModal .modal-body');
        $modalBody[0].replaceChildren(htmlElementToRenderInto); //add to exploration list

        logUIAction("queriesModal", {
            "clusterFacet": clusterFacet
        });
    });

    $('#documentModal').on('show.bs.modal', function(event) {
        const replyDocument = globalState['document'];
        const dataQueryIdx = globalState['lastQueryIdx'];
        const docId = replyDocument['doc']['doc_id'];

        const htmlElementToRenderInto = document.createElement("div");

        const lastQueryIdx = globalState['lastQueryIdx'];
        const docIdToSentences = createDocIdToSentences(globalQueriesResults[lastQueryIdx]['orig_sentences']);
        const fixedClusters = getFixedClustersBasedOnGlobalQueries(dataQueryIdx);

        const fixedSentsIds = [];
        for (const sent of docIdToSentences[docId]) {
            fixedSentsIds.push(sent['sent_idx']);
        }

        const reactToRender = e(
            ListItem,
            {
                "resultSentences": replyDocument['doc']['orig_sentences'],
                "numSentToShow": 999,
                "showPopover": false, // Don't show a popover inside a modal
                "fixedClusters": fixedClusters,
                "fixedSentsIndices": fixedSentsIds,
                "isSummary": false
            }
        );

        ReactDOM.render(reactToRender, htmlElementToRenderInto);

        const $modalBody = $('#documentModal .modal-body');
        $modalBody[0].replaceChildren(htmlElementToRenderInto); //add to exploration list

        logUIAction("documentModal", {
            "query_idx": dataQueryIdx,
            "doc_id": docId
        });
    });
}


function removeQueryItem(clusterQuery) {
    if (canSendRequest()) {
        globalQuery = globalQuery.filter(currClusterQuery => !compareClustersObjects(currClusterQuery, clusterQuery));
        query(null, null, null);
    }
}

function isClusterSelected(cluster) {
     const globalQueryFiltered = globalQuery.filter(currClusterQuery => compareClustersObjects(currClusterQuery, cluster));
     return globalQueryFiltered.length > 0 ? globalQueryFiltered[0] : null;
 }


class ClusterIdItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            "clusterSelected": isClusterSelected(this.props.cluster)
        };
    }

    query = () => {
        if (canSendRequest()) {
            const cluster = this.props.cluster;
            const text = cluster['display_name'];
            const clusterId = cluster['cluster_id'];
            const clusterType = cluster['cluster_type'];

            const clusterQuery = isClusterSelected(cluster);

            if (clusterQuery !== null) {
                this.setState({
                    "clusterSelected": false
                });
                removeQueryItem(clusterQuery);
            } else {
                this.setState({
                    "clusterSelected": true
                });
                query(text, clusterId, clusterType);
            }
        }
    }

    render() {

        const cluster = this.props.cluster;
        const useLabelAsFacet = this.props.useLabelAsFacet;

        const displayName = cluster['display_name'];
        const clusterLabel = cluster['cluster_label'];
        const clusterFacet = cluster['cluster_facet'];
        const clusterSelected = isClusterSelected(cluster);
        const clusterSelectedClassName = clusterSelected ? "selected" : "";

        const mentionCounter = {};
        for (const mention of cluster['mentions']) {
            const token = mention['token'];
            const mentionCount = mentionCounter[token] || 0;
            mentionCounter[token] = mentionCount + 1;
        }

        const mentionWithCount = Object.keys(mentionCounter).map(key => [key, mentionCounter[key]]);
        mentionWithCount.sort((first, second) => second[1] - first[1]);

        const allMentionsText = mentionWithCount.map(mentionWithCount => `${mentionWithCount[0]} (${mentionWithCount[1]})`).join("\n");

        let final_display_name = displayName;
        if (clusterLabel !== clusterFacet && clusterLabel !== MISC_LABEL && !useLabelAsFacet) {
            final_display_name = `${clusterLabel}: ${displayName}`;
        }

        return e(
            "div",
            {
                "className": `list-group-item d-flex justify-content-between align-items-center cluster-list-item ${clusterSelectedClassName}`,
                "data-cluster-id": cluster['cluster_id'],
                "data-cluster-type": cluster['cluster_type']
            },
            [
                e(
                    "div",
                    {
                        "className": "form-check",
                        onClick: this.query
                    },
                    [
                        e(
                            "input",
                            {
                                "className": "form-check-input",
                                "type": "checkbox",
                                "readOnly": "readOnly",
                                "checked": clusterSelectedClassName ? "checked" : false
                            }
                        ),
                        e(
                            "label",
                            {
                                "className": "form-check-label"
                            },
                            [
                                final_display_name
                            ]
                        )
                    ]
                ),
                e(
                    "span",
                    {
                        "className": "badge badge-primary badge-pill",
                        "data-toggle": "tooltip",
                        "title": allMentionsText
                    },
                    `${cluster[FIELD_TO_SORT_CLUSTERS]}`
                )
            ]
       );
    }
}

function compareClustersObjects(cluster1, cluster2) {
    return cluster1['cluster_id'] == cluster2['cluster_id'] && cluster1['cluster_type'] == cluster2['cluster_type'];
}

function saveCorefClusters(corefClustersMetas, eventsClustersMetas, propositionClustersMetas) {
    globalClustersMetas['entities'] = corefClustersMetas;
    globalClustersMetas['events'] = eventsClustersMetas;
    globalClustersMetas['propositions'] = propositionClustersMetas;

    const corefLabelsToClusters = categorizeClustersByLabels(Object.values(corefClustersMetas));
    const eventsLabelsToClusters = categorizeClustersByLabels(Object.values(eventsClustersMetas));
    const propositionLabelsToClusters = categorizeClustersByLabels(Object.values(propositionClustersMetas));

    const allClusters = Object.assign(eventsLabelsToClusters, propositionLabelsToClusters, corefLabelsToClusters)
    globalClustersMetas['all'] = allClusters;
}

class LabelClustersItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            minimized: this.props.minimized !== undefined ? this.props.minimized : true
        };
    }

    expand = () => {
        this.setState({
            "minimized": false
        });

        this.initializePopOver();
    }

    minimize = () => {
        this.setState({
            "minimized": true
        });
    }

    componentDidMount = () => {
        this.initializePopOver()
    }

    componentDidUpdate = () => {
        // handles when clicking "show more"
        this.initializePopOver()
    }

    initializePopOver = () => {
        const $this = $(ReactDOM.findDOMNode(this));
        const $popoverElements = $this.find('[data-toggle=popover]');
        $popoverElements.popover();

    }


    render() {
        const labelClusters = this.props.labelClusters;
        const amountOfFacets = this.props.amountOfFacets;
        const clusterLabel = labelClusters[0]['cluster_label'];
        const clusterFacet = labelClusters[0]['cluster_facet'];
        const clustersQuery = this.props.clustersQuery;
        const numSentToShow = this.props.numSentToShow || NUM_OF_SENTS_PER_FACET[clusterFacet] || 8;
        const maxSentsToShow = this.props.maxSentsToShow || 999;
        const useLabelAsFacet = this.props.useLabelAsFacet;
        const minimized = this.state.minimized;

        const labelToUse = useLabelAsFacet ? clusterLabel : clusterFacet;

        const clustersItems = [];
        clustersItems.push(
            e(
                "div",
                {
                    "className": "card-header clean-card-header clusters-label",
                    "data-toggle": "tooltip",
                    "title": CLUSTER_FACET_TO_TOOLTIP[labelToUse]
                },
                labelToUse
            )
        );
        for (let i = 0; i < labelClusters.length; i++) {
            if (i < numSentToShow || (!minimized && i < maxSentsToShow)) {

                const cluster = labelClusters[i];

                const clusterIdItemReact = e(
                    ClusterIdItem,
                    {
                        "cluster": cluster,
                        "useLabelAsFacet": useLabelAsFacet
                    }
                )

                clustersItems.push(clusterIdItemReact)
            }
        }

        let cardFooter;
        if (clustersItems.length < labelClusters.length && clustersItems.length < maxSentsToShow) {
            if (minimized) {
                cardFooter = e(
                    "div",
                    {
                        "className": "show-more-btn"
                    },
                    e(
                        'button',
                        {
                            style: {
                                "marginTop": "10px",
                                "marginBottom": "10px",
                                "cursor": "pointer"
                            },
                            "data-toggle": "modal",
                            "data-target": "#queriesModal",
                            "data-cluster-facet": clusterFacet
                        },
                        [
                            "Show all"
                        ]
                    )
                );
            }
         }

        const minimizedClass = minimized ? " minimized" : "";

        let numColumnsInGrid = Math.floor(12 / amountOfFacets);
        if (numColumnsInGrid > 4) {
            numColumnsInGrid = 4;
        }

        const colClass = `col-md-${numColumnsInGrid}`;

        let facetsValuesListClasses = "facets-values-list ";
        if (!minimized) {
            facetsValuesListClasses += colClass;
        }

        let facetsValuesList = e(
            "div",
            {"className": facetsValuesListClasses},
            clustersItems
        );

        if (minimized) {
            facetsValuesList = e(
                "div",
                {
                    "className": `list-group-item label-list-group-item list-group accordion label-clusters-item card ${colClass}`
                },
                [
                    facetsValuesList,
                    cardFooter
                ]
           );
        }

        return facetsValuesList
    }
}


class ClustersIdsList extends React.Component {
    render() {
        const allClusters = this.props.allClusters;
        const clustersQuery = this.props.clustersQuery;
        const useLabelAsFacet = this.props.useLabelAsFacet;  // In multi facets, when opening show more we want the label to show as the facet
        const minimized = this.props.minimized;

        const facetsToUse = [];
        for (const clusterFacet of CLUSTERS_FACETS_ORDER) {
            if (Object.keys(allClusters).includes(clusterFacet)) {
                facetsToUse.push(clusterFacet);
            }
        }

        const labelClustersItems = [];
        for (const clusterFacet of facetsToUse) {
            const labelClusters = allClusters[clusterFacet];

            const labelClustersItem = e(
                LabelClustersItem,
                {
                    "labelClusters": labelClusters,
                    "clustersQuery": clustersQuery,
                    "useLabelAsFacet": useLabelAsFacet,
                    "amountOfFacets": facetsToUse.length,
                    "minimized": minimized
                }
            )

            labelClustersItems.push(labelClustersItem);
        }

        return e(
            "div",
            {
                "className": "list-group card"
            },
            [
//                e(
//                    "div",
//                    {
//                        "id": "navigation-header",
//                        "className": "card-header"
//                    },
//                    "Navigation"
//                ),
                e(
                    "div",
                    {
                        "id": "navigation-card",
                        "className": "card-body"
                    },
                    e(
                        "div",
                        {
                            "className": "row"
                        },
                        labelClustersItems
                    )
                )
            ]
       );
    }
}

function createClustersIdsList(corefClustersMetas, eventsClustersMetas, propositionClustersMetas) {

    const htmlElementToRenderInto = document.createElement("div");

    const reactToRender = e(
        ClustersIdsList,
        {
            "allClusters": globalClustersMetas['all'],
            "clustersQuery": globalQuery
        }
    );


    ReactDOM.render(reactToRender, htmlElementToRenderInto);

    const $clustersIdsListContainer = $('#clustersIdsListContainer');
    $clustersIdsListContainer[0].replaceChildren(htmlElementToRenderInto);
}

function getClusterFromGlobalByQuery(clusterQuery) {
    return globalClustersMetas[clusterQuery['cluster_type']][clusterQuery['cluster_id']];
}

function categorizeClustersByLabels(clusters) {
    // Convert list of clusters to labels clusters
    const labelsClusters = {};
    clusters = clusters.sort((a,b) => b[FIELD_TO_SORT_CLUSTERS] - a[FIELD_TO_SORT_CLUSTERS]);
    for (const cluster of clusters) {
        const clusterFacet = cluster['cluster_facet'];
        const clusterLabel = cluster['cluster_label'];
        if (!LABELS_TO_FILTER.includes(clusterLabel)) {
            cluster['cluster_facet'] = clusterFacet;
            const labelClusters = labelsClusters[clusterFacet] || [];
            labelsClusters[clusterFacet] = labelClusters;
            labelClusters.push(cluster);
        }
    }

    return labelsClusters;
}

class QueryBadgeItem extends React.Component {

    removeClicked = () => {
        const clusterQuery = this.props.clusterQuery;
        const clusterId = clusterQuery['cluster_id'];
        const clusterType = clusterQuery['cluster_type'];
        // Use the checkbox button to make the checkbox click
        $(`[data-cluster-id=${clusterId}][data-cluster-type=${clusterType}] .form-check-input`).click();
    }

    render() {
        const clusterQuery = this.props.clusterQuery;
        const showHistoryBtn = this.props.showHistoryBtn;

        let textItems = [
            e(
                "span",
                {
                    "className": "query-badge-item-text"
                },
                `${clusterQuery['token']}`,
            ),
            e(
                "span",
                {
                    "className": "query-badge-remove"
                },
                " x"
            )
        ];
        let properties = {
             "className": "badge badge-pill badge-secondary query-badge-item",
             onClick: this.removeClicked
         };

         // If we are not inside the history modal
         if (showHistoryBtn) {
            properties['className'] += ' clickable';
         } else {
            textItems.pop(textItems[textItems.length-1])
            delete properties["onClick"];
         }

        return e(
            "span",
            properties,
            textItems
        )
    }
}

class QueryBadgesList extends React.Component {
    render() {
        const globalQuery = this.props.globalQuery;
        const showHistoryBtn = this.props.showHistoryBtn;

        const queryItems = [];
        if (globalQuery.length > 0) {
            let text = "Query: "
            if (showHistoryBtn) {
                text = "";
            }

            queryItems.push(e(
                "span",
                {},
                text
            ));
        }
        for (const clusterQuery of globalQuery) {
            queryItems.push(e(
                "span",
                {
                    "className": "query-badge-wrapper"
                },
                e(
                    QueryBadgeItem,
                    {
                        "clusterQuery": clusterQuery,
                        "showHistoryBtn": showHistoryBtn
                    }
                )
            ))
        }

        return e(
            "div",
            {
                "className": "queryBadgesPane"
            },
            queryItems
        );
    }
}

function insertQueryItemInExplorationPane(txt, paneItem) {
    // a div is used to align the li item left:
    var listElementQuery = document.createElement("div");
    listElementQuery.classList.add("floatleft");
    // the li item that holds the query string:
    var li = document.createElement("li"); // create an li element
    li.classList.add("exploreItem");
    li.classList.add("userItem");
    if (txt == '') {
        txt = '+';
    }
    li.appendChild(document.createTextNode("> " + txt));
    listElementQuery.appendChild(li);
    paneItem.appendChild(listElementQuery); //add to exploration list
}

function insertSummaryItemsInExplorationPane(queryResults, isLoading) {
    const listElementResult = document.createElement("div");

    const liReact = e(
        ExplorationPage,
        {
            "queryResults": queryResults,
            "isLoading": isLoading
        }
    );

    ReactDOM.render(liReact, listElementResult);

    $('#explorationPage')[0].replaceChildren(listElementResult);
}

function insertQueryItems() {
    const listElementResult = document.createElement("div");

    if (globalQuery.length > 0) {
        const liReact = e(
            QueryBadgesList,
            {
                "globalQuery": globalQuery,
                "showHistoryBtn": true
            }
        );

        ReactDOM.render(liReact, listElementResult);
    }

    $('#queryContainer')[0].replaceChildren(listElementResult);
}

function openDocument(e) {
    const docId = $(e.target).attr('data-doc-id');
    fetchDocument(docId, docId);
}

function openCorefCluster(e) {
    const corefId = $(e.target).attr('data-coref-cluster-idx');
    const text = e.target.textContent;
    $('#navigationMentionsButton').click();
    fetchCorefCluster(corefId, corefClusterType);

}
$(document).on('click', '.open-coref-cluster', openPropositionCluster);

function openPropositionCluster(e) {
    const propositionId = $(e.target).attr('data-proposition-cluster-idx');
    const text = e.target.textContent;
    $('#navigationPropositionsButton').click();
    fetchPropositionCluster(propositionId);

}
$(document).on('click', '.open-proposition-cluster', openPropositionCluster);



// const GROUPS_COLORS = ["blue", "pink", "orange", "red"];
const GROUPS_COLORS = ["blue"];
const group_id_to_color = {};
for (const [i, color] of GROUPS_COLORS.entries()) {
    group_id_to_color[i] = color;
}

class TokensGroup extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        const groups = this.props.groups;
        const groupId = this.props.cluster_id;
        const clusterType = this.props.cluster_type;

        const innerHtml = [];

        let className = "";
        let onMouseEnterFunc;
        let onMouseLeaveFunc;

        let showHighlight = groupId !== undefined;
        if (groupId !== undefined) {

            // Don't highlight if requested fixed clusters
            if (this.props.fixedClusters && !this.props.fixedClusters.includes(groupId)) {
                showHighlight = false;
            }

            if (showHighlight) {
                const groupColor = group_id_to_color[groupId % GROUPS_COLORS.length];
                className = `highlight-${groupColor}`;
                className += " highlight-hover";
                onMouseEnterFunc = () => this.props.startHighlightCluster(groupId);
                onMouseLeaveFunc = () => this.props.stopHighlightCluster(groupId);

                const groupIcon = e(
                    "span",
                    {
                        "className": "highlight-hover highlight-icon highlight-" + groupColor
                    },
                    groupId
                );
//              innerHtml.push(groupIcon);

            } else {
                className += " highlight-not-fixed";
            }
        }

        let runningText = {
            "tokens": []
        };

        function flushRunningText(innerHtml, runningText) {
            if (runningText['tokens'].length > 0) {
                innerHtml.push(e(
                    "span",
                    {},
                    runningText['tokens']
                ));
                runningText['tokens'] = [];
            }
        }

        for (const tokensGroup of groups) {
            let currGroupId = tokensGroup['cluster_id'];
            const isCluster = currGroupId !== undefined;

            const noFixedClusters = this.props.fixedClusters === undefined;
            const isInFixedClusters = this.props.fixedClusters && this.props.fixedClusters.includes(currGroupId);
            const showCluster = isCluster && (isInFixedClusters || noFixedClusters);


            if (showCluster) {
                const innerTokensGroup = e(
                  TokensGroup,
                  {
                    "groups": tokensGroup['tokens'],
                    "cluster_id": tokensGroup['cluster_id'],
                    "cluster_type": tokensGroup['cluster_type'],
                    "highlightedClusters": this.props.highlightedClusters,
                    "startHighlightCluster": this.props.startHighlightCluster,
                    "stopHighlightCluster": this.props.stopHighlightCluster,
                    "showPopover": this.props.showPopover,
                    "fixedClusters": this.props.fixedClusters
                  }
                );
                flushRunningText(innerHtml, runningText);
                innerHtml.push(innerTokensGroup);
            } else {
                extractTokens(tokensGroup);

                function extractTokens(token) {
                    if (token.hasOwnProperty('tokens')) {
                        recursiveExtractTokens(token['tokens']);
                    } else {
                        runningText['tokens'].push(token);
                    }
                }

                function recursiveExtractTokens(tokens) {
                    for (const token of tokens) {
                        extractTokens(token);
                    }
                }
            }
        }

        flushRunningText(innerHtml, runningText);

        let elementParams = {
            "className": "sentence-span " + className,
            "onMouseEnter": onMouseEnterFunc,
            "onMouseLeave": onMouseLeaveFunc
        };

        // Add popover if not inside a popover
        if (groupId !== undefined && this.props.showPopover) {
            let dataContent = '<div id="popover-loading">Loading...</div>';

            elementParams = Object.assign({}, elementParams, {
                "data-toggle": "popover",
                "data-trigger": "focus",
                "tabindex": "-1",
                "data-placement": "right",
                "data-html": true,
                "data-coref-cluster-idx": groupId,
                "data-coref-cluster-type": clusterType,
                "data-content": "<span>" +
                dataContent +
                "</span>"
            })
        }

        return e(
            "span",
            elementParams,
            innerHtml
        )
    }
}

function createDocIdToSentences(sentences) {
    let docIdToSentences = {};

    // Build docIdToSentences
    for (const sentence of sentences) {
        const docId = sentence['doc_id'];
        const docIdSentences = docIdToSentences[docId] || [];
        docIdToSentences[docId] = docIdSentences;
        docIdSentences.push(sentence);
    }

    return docIdToSentences;
}

function createSortedSentences(sentences) {
    const docIdToSentences = createDocIdToSentences(sentences);

    // Sort sentences by sent_idx
    for (const docId of Object.keys(docIdToSentences)) {
        const docSentences = docIdToSentences[docId];
        docSentences.sort((first, second) => first['sent_idx'] - second['sent_idx']);
    }

    // Sort documents by number of sentences
    const docIdsWithCounts = Object.keys(docIdToSentences).map(key => [key, docIdToSentences[key].length]);
    docIdsWithCounts.sort((first, second) => second[1] - first[1]);

    return docIdsWithCounts.map(docIdWithCount => docIdToSentences[docIdWithCount[0]]);
}


class ListItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            minimized: true,
            highlightedClusters: props.fixedClusters || []
        };
    }

    startHighlightCluster = (clusterIdx) => {
        this.setState({
            "highlightedClusters": this.state.highlightedClusters.concat(clusterIdx)
        });
    }

    stopHighlightCluster = (clusterIdx) => {
        this.setState({
            "highlightedClusters": this.state.highlightedClusters.filter(function(x) {
                // Don't remove clusters received in props (should stay fixed)
                if (this.props.fixedClusters && this.props.fixedClusters.includes(clusterIdx)) {
                    return true;
                }

                return x !== clusterIdx;
            }.bind(this))
        });
    }


    expand = () => {
        this.setState({
            "minimized": false
        });

//        this.initializePopOver();
    }

    minimize = () => {
        this.setState({
            "minimized": true
        });
    }

    initializePopOver = () => {
//        const $this = $(ReactDOM.findDOMNode(this));
//        const $popoverElements = $this.find('[data-toggle=popover]');
//        $popoverElements.on('shown.bs.popover', function(event) {
//            const $target = $(event.target);
//            const clusterId = $target.attr('data-coref-cluster-idx');
//            const clusterType = $target.attr('data-coref-cluster-type');
//            const sentIdx = $target.closest('[data-sent-idx]').attr('data-sent-idx');
//
//            let clustersMeta = globalCorefClustersMetas;
//            if (clusterType === "propositions") {
//                clustersMeta = globalPropositionClustersMetas;
//            }
//
//            if (clustersMeta[clusterId].sentences === undefined) {
//                sendRequest({
//                    "clientId": clientId,
//                    "request_coref_cluster": {
//                        "corefClusterId": clusterId,
//                        "corefClusterType": clusterType
//                    }
//                });
//            } else {
//                let sentences = clustersMeta[clusterId]['sentences'];
//                sentences = sentences.filter(x => x['idx'] != sentIdx);
//
//                let liReact;
//                if (sentences.length > 0){
//                    liReact = e(
//                        ListItem,
//                        {
//                            "resultSentences": sentences,
//                            "numSentToShow": 999,
//                            "showPopover": false,  // Don't show a popover inside a popover
//                            "fixedClusters": [parseInt(clusterId)]
//                        }
//                    );
//                } else {
//                    liReact = e(
//                        "span",
//                        {},
//                        "This is the only sentence"
//                    );
//                }
//
//                const $popoverDataContent = $('#popover-loading');
//                ReactDOM.render(liReact, $popoverDataContent[0]);
//            }
//
//            // avoid more popups showing if mention inside mention
//            event.preventDefault();
//        });
//        $popoverElements.popover();
    }

    componentDidMount = () => {
        // allows overriding a component outside of react
        globalListItemCallbacks.push((data) => {
            this.setState(data);
        });

//        this.initializePopOver()
    }

    componentDidUpdate = () => {
        // handles when clicking "read more"
//        this.initializePopOver()
    }

    shouldShowMore = (numSentencesShown, numSentToShow) => {
        return numSentencesShown < numSentToShow || !this.state.minimized
    }

    render() {
        const queryIdx = this.props.queryIdx;
        const resultSentences = this.props.resultSentences;
        const fixedSentsIndices = this.props.fixedSentsIndices || [];
        const origSentences = this.props.origSentences;
        const numSentToShow = this.props.numSentToShow || 1;
        const isSummary = this.props.isSummary !== undefined ? this.props.isSummary : true;
        const sentences = [];

        // put the list of sentences separately line by line with a small margin in between:
        const sortedSentences = createSortedSentences(resultSentences);
        let numSentencesShown = 0;
        const showSentIdx = !isSummary;

        for (const docSentences of sortedSentences) {
            if (this.shouldShowMore(numSentencesShown, numSentToShow)) {
                const docId = docSentences[0]['doc_id']

                let documentSentencesElements = [];

                for (var i = 0; i < docSentences.length; i++) {
                    numSentencesShown += 1;
                    if (this.shouldShowMore(numSentencesShown, numSentToShow)) {
                        const sentIdx = docSentences[i]['sent_idx'];
                        const isFirstTimeSeen = docSentences[i]['is_first_time_seen'];
                        let sentenceSeenClass = "";
                        if (isFirstTimeSeen === false) {
                            sentenceSeenClass = "sentence-seen";
                        }

                        const sentItems = [];
                        let colClass = "col-12";

                        if (showSentIdx) {
                            let sentIndexClasses = "sentence-index col-1";

                            if (fixedSentsIndices.includes(sentIdx)) {
                                sentIndexClasses += " fixed-sent-idx";
                            }

                            sentItems.push(e(
                                "span",
                                {
                                    "className": sentIndexClasses,
                                    "data-toggle": "tooltip",
                                    "title": "Sentence index"
                                },
                                `#${sentIdx}`
                           ));

                           colClass = "col-11";
                        }

                        sentItems.push(e(
                            "div",
                            {
                                "className": colClass,
                            },
                            e(
                                TokensGroup,
                                {
                                    "groups": docSentences[i]['tokens'],
                                    "startHighlightCluster": this.startHighlightCluster,
                                    "stopHighlightCluster": this.stopHighlightCluster,
                                    "highlightedClusters": this.state.highlightedClusters,
                                    "showPopover": this.props.showPopover !== undefined ? this.props.showPopover : true,
                                    "fixedClusters": this.props.fixedClusters
                                }
                            )
                        ));

                        const sentencePar = e(
                            'div',
                            {
                               "className": `sentence-paragraph ${sentenceSeenClass} no-gutters row`,
                               "data-sent-idx": sentIdx
                            },
                            sentItems
                          );
                          documentSentencesElements.push(sentencePar);
                    }
                }

                let documentElement = documentSentencesElements;


                if (!isSummary) {
                    documentElement = e(
                        "div",
                        {
                            "className": "card clean-card"
                        },
                        [
                            e(
                                "div",
                                {
                                    "className": "card-header clean-card-header doc-id-header",
                                    "data-doc-id": docId,
                                    "onClick": openDocument
                                },
                                `Document: ${docId}`
                            ),
                            e(
                                "div",
                                {"className": "card-body"},
                                documentSentencesElements
                            )
                        ]
                    );
               }

                sentences.push(documentElement);
            }
        }

        if (numSentToShow < resultSentences.length) {
            if (this.state.minimized) {
                const readMoreBtn = e(
                    'button',
                    {
                        style: {
                            "marginTop": "10px",
                            "marginBottom": "10px",
                            "cursor": "pointer"
                        },
                        onClick: this.expand
                    },
                    "Read more (" + resultSentences.length + " sentences)"
                );
                sentences.push(readMoreBtn);
            } else {
                const readLessBtn = e(
                    'button',
                    {
                        style: {
                            "marginTop": "10px",
                            "marginBottom": "10px",
                            "cursor": "pointer"
                        },
                        onClick: this.minimize
                    },
                    "Read less"
                );
                sentences.push(readLessBtn);
            }
        }

        const minimizedClass = this.state.minimized ? " minimized" : "";

        return e(
           "li",
           {
               "className": "exploreItem" + minimizedClass
           },
           sentences
       );
    }
}

class SummaryList extends React.Component {
    render() {
        const queryResults = this.props.queryResults;
        const showPopover = this.props.showPopover;
        const numSentToShow = this.props.numSentToShow;
        const showHistoryBtn = this.props.showHistoryBtn === undefined ? true : this.props.showHistoryBtn;
        const showQuery = !showHistoryBtn;

        const queryResultItems = [];

        for (const queryResult of queryResults) {
            const queryIdx = queryResult['query_idx'];
            const resultSentences = queryResult['result_sentences'];
            const origSentences = queryResult['orig_sentences'];

            if (showQuery) {
                const queryBadgeItem = e(
                    QueryBadgesList,
                    {
                        "globalQuery": queryResult['query'],
                        "showHistoryBtn": showHistoryBtn
                    }
                );

                queryResultItems.push(queryBadgeItem)
            }

            if (resultSentences.length > 0) {
                const fixedClusters = [];
                for (const clusterQuery of queryResult['query']) {
                    fixedClusters.push(parseInt(clusterQuery['cluster_id']));
                }

                const queryResultItem = e(
                    ListItem,
                    {
                        "queryIdx": queryIdx,
                        "resultSentences": resultSentences,
                        "origSentences": origSentences,
                        "numSentToShow": numSentToShow || 3,
                        "fixedClusters": fixedClusters,
                        "showPopover": showPopover,
                        "showHistoryBtn": showHistoryBtn
                    }
                );

                queryResultItems.push(queryResultItem);
            }
        }

        return e(
            "ul",
            {},
            queryResultItems
        )
    }
}

class LoadingSpinner extends React.Component {
    render() {
        return e(
            "div",
            {},
            e(
                "div",
                {
                    "className": "spinner-border text-primary",
                    "role": "status"
                },
                e(
                    "span",
                    {"className": "sr-only"},
                    "Loading..."
                )
            )
        );
    }
}

class ExplorationPageHeader extends React.Component {
    render() {
        const queryResults = this.props.queryResults;
        const anyHistory = this.props.anyHistory;

        const headerButtons = [];

        if (anyHistory) {
            const historyBtn = e(
                'button',
                {
                    "className": "history-button",
                    "data-toggle": "modal",
                    "data-target": "#historyModal"
                },
                `History`
            );

            headerButtons.push(historyBtn);
        }

        // Can show original sentences only if there is one query on screen
        if (queryResults && queryResults.length == 1) {
            const query = queryResults[0];

            const originalSentencesButton = e(
                'button',
                {
                    "id": "original-sentences-button",
                    "data-toggle": "modal",
                    "data-target": "#origSentencesModal",
                    "data-query-idx": query['query_idx'],
                    "data-query-id": this.props.queryId
                },
                `Original sentences`
            );

            headerButtons.push(originalSentencesButton);
        }

        return e(
            "div",
            {
                "id": "summaryHeader",
                "className": "card-header"
            },
            [
                e(
                    "div",
                    {
                        "className": "main-component-title"
                    },
                    "Summary"
                ),
                headerButtons
            ]
        )
    }
}

class ExplorationPage extends React.Component {
    render() {
        const queryResults = this.props.queryResults;
        const isLoading = this.props.isLoading;

        const exploreItems = [];

        if (queryResults.length == 0) {
            if (isLoading) {
                exploreItems.push(e(
                    LoadingSpinner
                ));
            } else {
                const introMsg = "Query the document set using the navigation. A summary will be produced for your query and the navigation will be filtered based on co-occurrence with your query.";
                exploreItems.push(
                    e(
                        "li",
                        {
                            "className": "exploreItem"
                        },
                        introMsg
                    )
                );
            }
        } else {
            exploreItems.push(e(
                SummaryList,
                {
                    "queryResults": queryResults
                }
            ));
        }

        return e(
            "div",
            {
                "className": "card"
            },
            [
                e(
                    ExplorationPageHeader,
                    {
                        "queryResults": queryResults,
                        "anyHistory": Object.keys(globalQueriesResults).length > 0
                    }
                ),
                e(
                    "div",
                    {
                        "id": "explorationCard",
                        "className": "card-body"
                    },
                    e(
                        "div",
                        {
                            "id": "explorationPane",
                            "className": "pane listItems card"
                        },
                        exploreItems
                    )
                )
            ]
        );
    }
}

function insertDocInPane(doc, $pane) {

    // a div is used to align the li item right:
    var listElementResult = document.createElement("div");
    listElementResult.classList.add("floatright");

    const documentsMetas = globalDocumentsMetas;

    const liReact = e(
        ListItem,
        {
            "resultSentences": doc.sentences,
            "numSentToShow": 2
        }
    );

    ReactDOM.render(liReact, listElementResult);

    $pane.append(listElementResult); //add to exploration list

    // scroll to more or less the headline of the document:
    $pane[0].scrollTop = $pane[0].scrollTop + $pane[0].offsetHeight - 200;
}

function setGlobalResponse(docResult) {
    const doc = docResult['doc'];
    const groupId = doc.id;
    const corefType = doc['corefType'];
    let clustersMeta = globalCorefClustersMetas;
    if (corefType === "propositions") {
        clustersMeta = globalPropositionClustersMetas;
    }
    clustersMeta[groupId]['sentences'] = doc.sentences;
}

function addStarRatingWidget(parentElement, numStarsInRating, iterationNum, displayCharacter, instructionsTxt, instructionsExplanation, starLabelClass) {
    // create a star rating widget for this summary/summary-expansion after the text:
    var starRatingElement = document.createElement("div");
    starRatingElement.classList.add("rating");
    // put 5 stars in the widget:
    for (var i = numStarsInRating; i >= 1; i--) { // since the stars are shown in opposite order, we mark them 5 to 1 (5 is best)
        // Enclosed within a function so that the addEventListener is within its own scope, otherwise the last
        // value passed (within this loop) to the listener is kept for all eventListeners in the loop.
        // (see: https://stackoverflow.com/questions/19586137/addeventlistener-using-for-loop-and-passing-values)
        (function () {
            // (star rating based on https://codepen.io/rachel_web/pen/dYrrvY)
            var starId = "star_" + i.toString() + "_" + iterationNum.toString(); // e.g. star_3_2 == 3 stars for iteration 2
            // the radio button enables choosing a star (but it is hiddem in the style):
            var radioStar = document.createElement("input");
            radioStar.type = "radio";
            radioStar.id = starId;
            radioStar.name = "rating_" + iterationNum.toString();
            radioStar.value = i.toString();
            radioStar.addEventListener('click', function(){onRatingStarClicked(radioStar.id);}, false);
            starRatingElement.appendChild(radioStar);
            // the label is a star character (in the style):
            var labelStar = document.createElement("label");
            labelStar.htmlFor = starId;
            labelStar.setAttribute('label-before-content', displayCharacter);
            labelStar.style.paddingTop = "16px";
            starRatingElement.appendChild(labelStar);
        }());
    }
    // put an instructions label for the rating; since the widget above is placed opposite,
    // we put the instructions after in the code, though it appears before:
    var instructionsSpan = document.createElement("span");
    instructionsSpan.id = "ratingInstructions_" + iterationNum.toString();
    instructionsSpan.classList.add('ratingInstructions');
    instructionsSpan.classList.add('ratingInstructionsGlow'); // to be removed after first time clicked
    instructionsSpan.style.cursor = 'help';

    instructionsSpan.innerHTML = instructionsTxt;
    instructionsSpan.title = instructionsExplanation;

    starRatingElement.appendChild(instructionsSpan);

    // the "tooltip" to explain each rating star
    var explanationSpan = document.createElement("div");
    explanationSpan.classList.add(starLabelClass);
    starRatingElement.appendChild(explanationSpan);

    lastIterationRated = false;
    parentElement.append(starRatingElement);
}

function onRatingStarClicked(starId) {
    var idParts = starId.split('_');
    var rating = idParts[1] / RATING_PARAMS[iterationStarRatingType]['numStars']; //numStarsInRating; // sent as a 0-to-1 float since number of stars may change sometime
    var iterationIdx = idParts[2];
    // remove the glowing effect now that the star rating has been selected:
    instructionsSpan = document.getElementById("ratingInstructions_" + iterationIdx.toString());
    instructionsSpan.classList.remove('ratingInstructionsGlow');
    // send the server the rating:
    sendRequest({"clientId": clientId, "request_set_iteration_rating": {"iterationIdx": iterationIdx, "rating": rating}});
    lastIterationRated = true;

    if (document.getElementById("questionnaireArea").style.display == "none") { // only show guiding messages if not in the questionnaire by now
        //if (iterationIdx == 0) {
        // print the message if the rating marked is of the current iteration (the user may have re-rated some earlier iteration):
        // notice that the iteration number here starts from 1, while the iterationIdx starts from 0
        if (iterationNum == 1 && iterationIdx == 0) {
            practiceTaskMessage("Nice <span style='font-size:30px;'>&#x1F604;</span><br><br><u><b>Query</b></u><br>Now think of a query <span style='font-size:25px;'>&#x2753;</span> that might get you <u>additional generally interesting information</u> about \"" + m_topicId + "\". <span style='font-size:30px;'>&#x1F4F0;</span><br>Based on what you've already read, what important information is <i>missing</i>, or what would be good to <i>expand</i> on?<br>You may write something in the query box, highlight something from the text, or click one of the suggested queries.<br><br><u>Remember</u>: your goal is to get the <b>most valuable additional information</b> on the topic for a journalist's general overview on the topic. <span style='font-size:30px;'>&#x1F4F0;</span>", function(){}); //<br><br>Notice the time <span style='font-size:30px;'>&#x23F2;</span> on the bottom, though feel free to explore as much as you'd like.", function(){});
        }
        else if (iterationNum == 2 && iterationIdx == 1) {
            practiceTaskMessage("Great <span style='font-size:30px;'>&#128513;</span><br>Query again. <span style='font-size:25px;'>&#x2753;</span> If you think the system didn't give you good information on your last query, you might want to repeat the query, or rephrase it a bit.<br><br><b>Remember your goal:</b> acquire <u>generally interesting information</u> on \"" + m_topicId + "\". <span style='font-size:30px;'>&#x1F4F0;</span>", function(){});
        }
        else if (iterationNum == 3 && iterationIdx == 2) {
            practiceTaskMessage("Fantastic <span style='font-size:30px;'>&#x1F60E;</span><br>You know what to do. Remember your goal... <span style='font-size:30px;'>&#x1F4F0;</span><br><br>And once you think you've covered the interesting points of the topic and the time is up, you can move on to the questionnaire at the bottom right <span style='font-size:30px;'>&#x2198;</span> .", function(){});
        }
    }
}

function showQuestionnaire() {
    // initialize the questionnaire:
    if (questionnaireBatchInd > -1 && questionnaireList.length > 0) {
        initQuestionnaire(questionnaireList, allTextsInSession); // in functionailityQuestionnaire.js
    }

    queryArea = document.getElementById("queryArea");
    questionnaireArea = document.getElementById("questionnaireArea");
    rightSide = document.getElementById("rightSide");
    leftSide = document.getElementById("leftSide");

    // hide the query area
    queryArea.style.display = "none";
    //moreInfoButton.style.display = "none";

    // the right and left sides were unbalanced until now to give more room for the summary area
    // now we split the two sides in half:
    rightSide.style.width = "50%";
    leftSide.style.width = "50%";

    // change the cursor of the text areas in the exploration pane to the auto text cursor instead of the highlighter:
    var textAreas = document.getElementsByClassName("highlighterCursor");
    for (var i = 0; i < textAreas.length ; i++) {
        textAreas[i].style.cursor = "auto";
    }

    // hide the highlighting tip message div:
    document.getElementById("highlightTipMessage").style.display = "none";

    // show the questionnaire area:
    questionnaireArea.style.display = "inline-table";

    // hide the "stop exploring" button in case it's showing
    stopExploringButton.style.display = "none";

    setTimeout(function () {
        //practiceTaskMessage("Thanks! <span style='font-size:30px;'>&#x1F642;</span><br>This part is self explanatory.<br>It's OK if not all statements are found, but please try to be as accurate as possible.", function(){});
        practiceTaskMessage("Thanks! <span style='font-size:30px;'>&#x1F642;</span><br>Now mark the statements whose information is covered in the presented text (up to minor details).<br>It's OK if not all statements are found, but please try to be as accurate as possible.", function(){});
    }, 500);
}

/* Handle a query string. */
function query(queryStr, clusterId, clusterType) {
    resetPage();

    if (clusterType) {
        globalQuery.push({
            "cluster_id": clusterId,
            "cluster_type": clusterType,
            "token": queryStr
        });
    }
    insertSummaryItemsInExplorationPane([], isLoading=true);

    createClustersIdsList();

    /* Even if the query is empty we want to refresh the view */
    insertQueryItems();

    queryStr = "";
    for (const clusterQuery of globalQuery) {
        const cluster = getClusterFromGlobalByQuery(clusterQuery);
        queryStr += ` ${cluster['display_name']}`;
    }

    // if the new query is not a "more info" query, then keep remember it:
    if (queryStr != '') {
        lastQuery = [queryStr, clusterId, clusterType];
    }

    // get query response info from the server:
    clustersQuery = globalQuery;
    sendRequest({"clientId": clientId, "request_query": {"topicId": curTopicId, "clusters_query": clustersQuery, "query": queryStr}});
    // the response will be sent to function setQueryResponse asynchronously
}

function fetchDocument(documentId, documentName) {
    sendRequest({
        "clientId": clientId,
        "request_document": {
            "docId": documentId
        }
    });
}

function fetchCorefCluster(corefClusterId, corefClusterType) {
    const corefClusterText = globalCorefClustersMetas[corefClusterId]['display_name'];
    insertQueryItemInExplorationPane(corefClusterText, $mentionsPane[0]);

    // scroll to bottom:
    $mentionsPane[0].scrollTop = $mentionsPane[0].scrollHeight;

    sendRequest({
        "clientId": clientId,
        "request_coref_cluster": {
            "corefClusterId": corefClusterId,
            "corefClusterType": corefClusterType
        }
    });
}

function fetchPropositionCluster(propositionClusterId) {
    const propositionClusterText = globalPropositionClustersMetas[propositionClusterId]['display_name'];
//    insertQueryItemInExplorationPane(propositionClusterText, $propositionsPane[0]);

    // scroll to bottom:
    $propositionsPane[0].scrollTop = $propositionsPane[0].scrollHeight;

    sendRequest({
        "clientId": clientId,
        "request_coref_cluster": {
            "corefClusterId": propositionClusterId,
            "corefClusterType": "propositions"
        }
    });
}

function logUIAction(action, actionDetails) {
    if (canSendRequest()) {
        sendRequest({
                "clientId": clientId,
                "request_log_ui_action": {
                    "action": action,
                    "actionDetails": actionDetails
                }
            });;
    }
}

function canSendRequest() {
    // check if the user needs to rate the last summary:
    //if (needIterationStarRating && !lastIterationRated) {
    if (iterationStarRatingType != 0 && !lastIterationRated) {
        alert("Please rate the last summary.");
        return false;
    }
    return !isWaitingForResponse && curTopicId != null;
}

function changeScreen(event) {
    const $targetClicked = $(event.currentTarget);
    for (toolbarNavigationItem of $toolbarNavigationItems) {
        $(toolbarNavigationItem).removeClass('active');
    }
    $targetClicked.addClass('active');
    if ($targetClicked.attr('id') === "navigationSummaryButton") {
        $explorationPage.removeClass('hidden');
        $queryArea.removeClass('hidden');
    } else {
        $explorationPage.addClass('hidden');
        $queryArea.addClass('hidden');
    }

    if ($targetClicked.attr('id') === "navigationDocumentsButton") {
        $documentsPane.removeClass('hidden');
        $documentsListArea.removeClass('hidden');
    } else {
        $documentsPane.addClass('hidden');
        $documentsListArea.addClass('hidden');
    }

    if ($targetClicked.attr('id') === "navigationMentionsButton") {
        $mentionsPane.removeClass('hidden');
        $mentionsListArea.removeClass('hidden');
    } else {
        $mentionsPane.addClass('hidden');
        $mentionsListArea.addClass('hidden');
    }

    if ($targetClicked.attr('id') === "navigationPropositionsButton") {
        $propositionsPane.removeClass('hidden');
        $propositionsListArea.removeClass('hidden');
    } else {
        $propositionsPane.addClass('hidden');
        $propositionsListArea.addClass('hidden');
    }

}


function showDebug() {
    const $toolbarContent = $('#toolbarContent');
    const $mainContent = $('#mainContent');
    $toolbarContent.attr('style', '');
    $toolbarContent.attr('class', 'col-2')
    $mainContent.attr('class', 'col-7');
}


const debugMode = window.location.href.indexOf("debug") > -1;
if (debugMode) {
    showDebug();
}

//moreInfoButton.addEventListener("click", moreInfoOnButtonClick);
stopExploringButton.addEventListener("click", stopExploringButtonOnClick);
for (toolbarNavigationItem of $toolbarNavigationItems) {
    toolbarNavigationItem.addEventListener("click", changeScreen);
}

initializeModal();

window.onload = onInitFunc;