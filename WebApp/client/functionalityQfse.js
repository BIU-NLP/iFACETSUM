const e = React.createElement;
var enterQueryButton = document.getElementById("enterQueryButton");
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
var repeatQueryButton = document.getElementById("repeatQueryButton");
//var moreInfoButton = document.getElementById("addMoreButton");
var queryInputBox = document.getElementById("userInput");
var exploreList = document.getElementById("explorationPane");
var keywordList = document.getElementById("keywordsList");
var keywordsArea = document.getElementById("keywordsArea");
var topicsDropdown = document.getElementById("topicsDropdownContent");
var stopExploringButton = document.getElementById('stopExploringButton');
var curTopicId = null;
var curLoadingInicatorElement = null;
var isWaitingForResponse = false;
var isWaitingForInitial = false;
var questionnaireBatchInd = -1;
var totalTextLength = 0;
let globalDocumentsMetas = null;
let globalCorefClustersMetas = null;
let globalPropositionClustersMetas = null;
var pageBaseUrl = "qfse.html";
var summaryType = "qfse";
var timeAllowed = -1;
var lastQueryType = '';
var lastQueryStr = '';
var iterationNum = 0; // keeps track of how many iterations there are (0 is the initial summary)
var iterationStarRatingType = 0; // 0=none , 1=rating , 2=newInfo
var lastIterationRated = false; // each iteration's summary must be rated before continuing to the next iteration
var numSentencesInQueryResponse = 2; // the number of sentences requested as a response to a query
var allTextsInSession = [];
var questionnaireList = [];
var assignmentId = '';
var hitId = '';
var workerId = '';
var turkSubmitTo = '';
var clientId = uuidv4(); // generate a random clientID for this summarization session
let showCoref = true;

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
    //queryInputBox.style.display = "none";
    //enterQueryButton.style.display = "none";
    queryInputBox.setAttribute("disabled", "");
}

/* Resets the keyphrases list and the the exploration pane. */
function resetPage() {
    while (exploreList.firstChild) {
        exploreList.removeChild(exploreList.firstChild);
    }
    while (keywordList.firstChild) {
        keywordList.removeChild(keywordList.firstChild);
    }
    curLoadingInicatorElement = null;
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
    globalCorefClustersMetas = topicInfo['corefClustersMetas'];
    const propositionClustersMetas = topicInfo['propositionClustersMetas'];
    globalPropositionClustersMetas = topicInfo['propositionClustersMetas'];
    //var timeAllowed = topicInfo['timeAllowed'];
    var textLength = topicInfo['textLength'];
    questionnaireList = topicInfo['questionnaire'];

    resetPage();
    curTopicId = topicId;
    // set the event name and keyphrases of the event:
    document.getElementById("topicNameHeader").innerHTML = name;
    document.getElementById("numDocumentsHeader").classList.add("myTooltip");
    document.getElementById("numDocumentsHeader").style.cursor = "help";
    document.getElementById("numDocumentsHeader").innerHTML = '' +
        'Summary of <span>' + numDocuments + ' articles</span>' +
        '<div class="bottomTooltip" style="width: 350px;">' +
        'Article sources: New York Times, Associated Press and Xinhua News Agency (years 1995-2000)' +
        '<i></i>' +
        '</div>' +
        ' on';

    createKeywordListElement(keyPhrasesList);
    createDocumentsListElement(documentsMetas);
    createMentionsListElement(corefClustersMetas);
    createPropositionsListElement(propositionClustersMetas);
    insertSummaryItemInExplorationPane(initialSummaryList, documentsMetas);

    // keep the text length so far:
    totalTextLength = textLength;

    // show the keywords area and search box in case they were hidden:
    keywordsArea.style.display = "block";
    queryInputBox.removeAttribute("disabled");

    // put focus on the query box:
    queryInputBox.focus();

    // set that the request has been responded to:
    isWaitingForInitial = false;

    // make the page visible to the annotator and show relevant functionalities:
    showPageToAnnotator();
}

function queryInputLength(){
	return queryInputBox.value.length;
}

/* Initializes the list of keyphrases. */
function createKeywordListElement(keyPhrasesList) {
    // add the keyphrases
    for (var i = 0; i < keyPhrasesList.length; i++) {
        // create the keyphrase list item and add it to the keywordList div:
        var liId = "li_keyword_"+i
        var li = document.createElement("li");
        li.setAttribute("id", liId);
        li.appendChild(document.createTextNode(keyPhrasesList[i]));
        li.classList.add("keywordItem");
        keywordList.appendChild(li);

        // create the event when the keyword is clicked:
        function keywordChosen(keywordLi) {
            // if it was not already used, search this keyphrase:
            //if (!isWaitingForResponse && !keywordLi.classList.contains("keywordUsed")) {

            if (canSendRequest()) {
                var text = keywordLi.innerText;
                if (text != "") {
                    text = text.trim();
                }
                keywordLi.classList.add("keywordUsed"); // put the keyword in "used" state
                lastQueryType = 'keyword';
                query(text);
                queryInputBox.focus();
            }
        }
        // bind the event to the keyword list item (we use bind because of the loop - see: https://stackoverflow.com/questions/19586137/addeventlistener-using-for-loop-and-passing-values )
        li.addEventListener("click", keywordChosen.bind(this, li), false);
    }
}

class PaneNavListItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {};
    }

    render() {
        const listItemIdx = this.props.i;
        const text = this.props.text;
        const itemId = this.props.itemId;
        const listType = this.props.listType;

        return e(
            "li",
            {
                "id": `li_${listType}_${listItemIdx}`,
                "className": "keywordItem",
                "data-cluster-idx": itemId
            },
            text
       );
    }
}

function createDocumentsListElement(documentsMetas) {
    for (const [i, documentMeta] of Object.values(documentsMetas).entries()) {
       var listElementResult = document.createElement("div");

        const liReact = e(
            PaneNavListItem,
            {
                "i": i,
                "text": documentMeta['id'],
                "itemId": documentMeta['id'],
                "listType": "document"
            }
        );

        ReactDOM.render(liReact, listElementResult);
        $documentsList.append(listElementResult);

        function documentChosen(documentLi) {

            if (canSendRequest()) {
                let itemText = documentLi.innerText;
                if (itemText != "") {
                    itemText = itemText.trim();
                }
                $innerLi = $(documentLi).find('li');
                const itemId = $innerLi.attr('data-cluster-idx');
                $innerLi[0].classList.add("keywordUsed"); // put the keyword in "used" state
                lastQueryType = 'keyword';
                fetchDocument(itemId, itemText);
            }
        }

        listElementResult.addEventListener("click", documentChosen.bind(this, listElementResult), false);
    }

}

function createMentionsListElement(corefClustersMetas) {
    for (const [i, corefClusterMeta] of Object.values(corefClustersMetas).entries()) {
       var listElementResult = document.createElement("div");

        const liReact = e(
            PaneNavListItem,
            {
                "i": i,
                "text": corefClusterMeta['display_name'],
                "itemId": corefClusterMeta['cluster_idx'],
                "listType": "mention"
            }
        );

        ReactDOM.render(liReact, listElementResult);
        $mentionsList.append(listElementResult);

        function corefClusterChosen(corefClusterLi) {

            if (canSendRequest()) {
                const itemText = corefClusterLi.innerText;
                $innerLi = $(corefClusterLi).find('li');
                const itemId = $innerLi.attr('data-cluster-idx');
                $innerLi[0].classList.add("keywordUsed"); // put the keyword in "used" state
                lastQueryType = 'keyword';
                fetchCorefCluster(itemId);
            }
        }

        listElementResult.addEventListener("click", corefClusterChosen.bind(this, listElementResult), false);
    }
}

function createPropositionsListElement(propositionClustersMetas) {
    for (const [i, propositionClusterMeta] of Object.values(propositionClustersMetas).entries()) {
       var listElementResult = document.createElement("div");

        const liReact = e(
            PaneNavListItem,
            {
                "i": i,
                "text": propositionClusterMeta['display_name'],
                "itemId": propositionClusterMeta['cluster_idx'],
                "listType": "mention"
            }
        );

        ReactDOM.render(liReact, listElementResult);
        $propositionsList.append(listElementResult);

        function propositionClusterChosen(propositionClusterLi) {

            if (canSendRequest()) {
                const itemText = propositionClusterLi.innerText;
                $innerLi = $(propositionClusterLi).find('li');
                const itemId = $innerLi.attr('data-cluster-idx');
                $innerLi[0].classList.add("keywordUsed"); // put the keyword in "used" state
                lastQueryType = 'keyword';
                fetchPropositionCluster(itemId);
            }
        }

        listElementResult.addEventListener("click", propositionClusterChosen.bind(this, listElementResult), false);
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

function insertSummaryItemInExplorationPane(txtList, documentsMetas) {
    // a div is used to align the li item right:
    var listElementResult = document.createElement("div");
    listElementResult.classList.add("floatright");

    const liReact = e(
        ListItem,
        {
            "txtList": txtList,
            "numSentToShow": 3,
            "showCoref": showCoref
        }
    );

    ReactDOM.render(liReact, listElementResult);

    exploreList.appendChild(listElementResult); //add to exploration list


//        var textNode = document.createTextNode(txtList[i]['sent']);

//    // if needed, put the star rating widget within the summary item:
//    //if (needIterationStarRating) {
//    if (iterationStarRatingType != 0) {
//        var instructionsTxt = RATING_PARAMS[iterationStarRatingType]['instructionsRest'];
//        var instructionsExplanation = RATING_PARAMS[iterationStarRatingType]['explanationRest'];
//        var instructionsExplanationStarLabelClass = RATING_PARAMS[iterationStarRatingType]['starLabelClassRest'];
//        if (iterationNum == 0) { // for the initial summary
//            instructionsTxt = RATING_PARAMS[iterationStarRatingType]['instructionsInitial'];
//            instructionsExplanation = RATING_PARAMS[iterationStarRatingType]['explanationInitial'];
//            instructionsExplanationStarLabelClass = RATING_PARAMS[iterationStarRatingType]['starLabelClassInitial'];
//        }
//        addStarRatingWidget(li, RATING_PARAMS[iterationStarRatingType]['numStars'], iterationNum, RATING_PARAMS[iterationStarRatingType]['signCharacter'], instructionsTxt, instructionsExplanation, instructionsExplanationStarLabelClass)
//    }

    // extend the list of all texts:
    Array.prototype.push.apply(allTextsInSession, txtList);

    // iteration done
    iterationNum++;
}

function openDocument(e) {
    const docId = e.target.textContent;
    $('#navigationDocumentsButton').click();
    fetchDocument(docId, docId);

}
$(document).on('click', '.open-document', openDocument);

function openCorefCluster(e) {
    const corefId = $(e.target).attr('data-coref-cluster-idx');
    const text = e.target.textContent;
    $('#navigationMentionsButton').click();
    fetchCorefCluster(corefId);

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
        const groupId = this.props.group_id;
        const clusterType = this.props.cluster_type;

        const innerHtml = [];

        let className = "";
        let onMouseEnterFunc;
        let onMouseLeaveFunc;
        if (groupId !== undefined) {
            const groupColor = group_id_to_color[groupId % GROUPS_COLORS.length];
            className = "highlight-" + groupColor;
            onMouseEnterFunc = () => this.props.startHighlightCluster(groupId);
            onMouseLeaveFunc = () => this.props.stopHighlightCluster(groupId);

            if (this.props.highlightedClusters.includes(groupId)) {
                className += " highlight-hover";
            } else {
                className += " highlight-no-hover";
            }


            const groupIcon = e(
                "span",
                {
                    "className": "highlight-hover highlight-icon highlight-" + groupColor
                },
                groupId
            );
//            innerHtml.push(groupIcon);
        }

        for (const tokensGroup of groups) {
            let innerTokensGroup;

            if (tokensGroup['group_id'] !== undefined) {
                innerTokensGroup = e(
                  TokensGroup,
                  {
                    "groups": tokensGroup['tokens'],
                    "group_id": tokensGroup['group_id'],
                    "cluster_type": tokensGroup['cluster_type'],
                    "highlightedClusters": this.props.highlightedClusters,
                    "startHighlightCluster": this.props.startHighlightCluster,
                    "stopHighlightCluster": this.props.stopHighlightCluster,
                    "showPopover": this.props.showPopover
                  }
                );
                innerHtml.push(innerTokensGroup);
            } else {
                let groupClass = "";

                for (const token of tokensGroup) {
                    innerTokensGroup = e(
                         "span",
                         {
                            "className": groupClass
                         },
                         token + " "
                    );
                    innerHtml.push(innerTokensGroup);
                }
            }
        }

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

class ListItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            minimized: true,
            highlightedClusters: [],
            showCoref: props.showCoref
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
                return x !== clusterIdx
            })
        });
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

    initializePopOver = () => {
        const $this = $(ReactDOM.findDOMNode(this));
        const $popoverElements = $this.find('[data-toggle=popover]');
        $popoverElements.on('shown.bs.popover', function(event) {
            const $target = $(event.target);
            const clusterId = $target.attr('data-coref-cluster-idx');
            const clusterType = $target.attr('data-coref-cluster-type');
            const sentIdx = $target.closest('[data-sent-idx]').attr('data-sent-idx');

            let clustersMeta = globalCorefClustersMetas;
            if (clusterType === "propositions") {
                clustersMeta = globalPropositionClustersMetas;
            }

            if (clustersMeta[clusterId].sentences === undefined) {
                sendRequest({
                    "clientId": clientId,
                    "request_coref_cluster": {
                        "corefClusterId": clusterId,
                        "corefClusterType": clusterType
                    }
                });
            } else {
                let sentences = clustersMeta[clusterId]['sentences'];
                sentences = sentences.filter(x => x['idx'] != sentIdx);

                let liReact;
                if (sentences.length > 0){
                    liReact = e(
                        ListItem,
                        {
                            "txtList": sentences,
                            "numSentToShow": 999,
                            "showCoref": showCoref,
                            "showPopover": false  // Don't show a popover inside a popover
                        }
                    );
                } else {
                    liReact = e(
                        "span",
                        {},
                        "This is the only sentence"
                    );
                }

                const $popoverDataContent = $('#popover-loading');
                ReactDOM.render(liReact, $popoverDataContent[0]);
            }
        });
        $popoverElements.popover();
    }

    componentDidMount = () => {
        // allows overriding a component outside of react
        globalListItemCallbacks.push((data) => {
            this.setState(data);
        });

        this.initializePopOver()
    }

    componentDidUpdate = () => {
        // handles when clicking "read more"
        this.initializePopOver()
    }

    render() {
        const txtList = this.props.txtList;
        const numSentToShow = this.props.numSentToShow || 1;
        const sentences = [];

        // put the list of sentences separately line by line with a small margin in between:
        for (var i = 0; i < txtList.length; i++) {
            if (i < numSentToShow || !this.state.minimized) {
                const sentenceText = txtList[i]['text'];
                const docId = txtList[i]['doc_id'];
                const sentIdx = txtList[i]['idx'];

                const sentencePar = e(
                    'p',
                    {
                       "className": "sentence-paragraph",
                       "data-sent-idx": sentIdx
                    },
                    e(
                      TokensGroup,
                      {
                        "groups": this.state.showCoref ? txtList[i]['coref_tokens'] : txtList[i]['proposition_tokens'],
                        "startHighlightCluster": this.startHighlightCluster,
                        "stopHighlightCluster": this.stopHighlightCluster,
                        "highlightedClusters": this.state.highlightedClusters,
                        "showPopover": this.props.showPopover !== undefined ? this.props.showPopover : true
                      }
                    )
                  );
                  sentences.push(sentencePar);
            }
        }

        if (numSentToShow < txtList.length) {
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
                    "Read more (" + txtList.length + " sentences)"
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

function insertDocInPane(doc, $pane) {

    // a div is used to align the li item right:
    var listElementResult = document.createElement("div");
    listElementResult.classList.add("floatright");

    const documentsMetas = globalDocumentsMetas;

    const liReact = e(
        ListItem,
        {
            "txtList": doc.sentences,
            "numSentToShow": 2,
            "showCoref": showCoref
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
    repeatQueryButton.style.display = "none";
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


//function onTextMouseUp() {
//    // get the currently selected text on the page:
//    var text = "";
//    if (window.getSelection) {
//        text = window.getSelection().toString();
//    } else if (document.selection && document.selection.type != "Control") {
//        text = document.selection.createRange().text;
//    }
//
//    // add a space at the end of the highlighted text if there isn't one:
//    if (text != "") {
//        text = text.trim();
//        text += ' ';
//    }
//    // if there's no space before the newly added text, add one:
//    if (queryInputBox.value != "" && !queryInputBox.value.endsWith(' ')) {
//        text = ' ' + text;
//    }
//
//    // put the selected text in the query box, and focus on the query box:
//    queryInputBox.value += text; // set the search query to the highlighted text (append text)
//    lastQueryType = 'highlight'
//    queryInputBox.focus();
//}

/* Handle a query string. */
function query(queryStr) {

    // create the query list item in the exploration pane:
    insertQueryItemInExplorationPane(queryStr, exploreList);

    // put a loading ellipsis:
    insertLoadingIndicatorInExplorationPane(exploreList);

    // scroll to bottom:
    exploreList.scrollTop = exploreList.scrollHeight;

    // if no query type was set until now ('freetext' or 'highlight' or 'keyword'), then it must be that some text was copy-pasted into the query box:
    if (lastQueryType == '') {
        lastQueryType = 'copypaste';
    }

    // if the new query is not a "more info" query, then keep remember it:
    if (queryStr != '') {
        lastQueryStr = queryStr;
    }

    // get query response info from the server:
    sendRequest({"clientId": clientId, "request_query": {"topicId": curTopicId, "query": queryStr, "summarySentenceCount":numSentencesInQueryResponse, "type":lastQueryType}});
    // the response will be sent to function setQueryResponse asynchronously
}

function fetchDocument(documentId, documentName) {
    insertQueryItemInExplorationPane(documentName, $documentsPane[0]);

    insertLoadingIndicatorInExplorationPane($documentsPane[0]);

    // scroll to bottom:
    $documentsPane[0].scrollTop = $documentsPane[0].scrollHeight;

    sendRequest({
        "clientId": clientId,
        "request_document": {
            "docId": documentId
        }
    });
}
function fetchCorefCluster(corefClusterId) {
    const corefClusterText = globalCorefClustersMetas[corefClusterId]['display_name'];
    insertQueryItemInExplorationPane(corefClusterText, $mentionsPane[0]);

    insertLoadingIndicatorInExplorationPane($mentionsPane[0]);

    // scroll to bottom:
    $mentionsPane[0].scrollTop = $mentionsPane[0].scrollHeight;

    sendRequest({
        "clientId": clientId,
        "request_coref_cluster": {
            "corefClusterId": corefClusterId,
            "corefClusterType": "events"
        }
    });
}

function fetchPropositionCluster(propositionClusterId) {
    const propositionClusterText = globalPropositionClustersMetas[propositionClusterId]['display_name'];
    insertQueryItemInExplorationPane(propositionClusterText, $propositionsPane[0]);

    insertLoadingIndicatorInExplorationPane($propositionsPane[0]);

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

function queryOnButtonClick(){
	if (queryInputLength() > 0 && canSendRequest()) { //makes sure that an empty queryInputBox field doesn't create a li
        query(queryInputBox.value); //makes text from queryInputBox field the li text
        queryInputBox.value = ""; //Reset text queryInputBox field
	}
}

function queryOnKeyUp(event) {
    if (queryInputLength() > 0) {
        if (event.which == 13 && canSendRequest()) { //this now looks to see if you hit "enter"/"return"
            //the 13 is the enter key's keycode, this could also be display by event.keyCode === 13
            query(queryInputBox.value); //makes text from queryInputBox field the li text
            queryInputBox.value = ""; //Reset text queryInputBox field
        }
        else if (event.which != 13) {
            if (queryInputLength() == 1 || lastQueryType != 'highlight') {
                // if the last query type was not a highlight, then this is free text
                // if it is highlight, then we consider the query type a highlight even if some text is written in
                // if the length is 1 now, then this is the first character of a query, so it must be free text
                lastQueryType = 'freetext';
            }
        }
	}
    else {
        lastQueryType = '';
    }
}

function queryRepeatOnButtonClick() {
    if (lastQueryStr == '') {
        alert("No query to repeat.")
    }
    // if a query was run before, rerun it:
    else if (canSendRequest()) {
        lastQueryType = 'repeat';
        query(lastQueryStr); // run the last query
    }
}

function moreInfoOnButtonClick() {
    if (canSendRequest()) {
        lastQueryType = 'moreinfo';
        query(''); // run the query
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

function changeGroup(event) {
    const $targetClicked = $(event.currentTarget);

    if ($targetClicked.find('input').attr('id') == "togglePropositionsButton") {
        showCoref = false;
    }

    if ($targetClicked.find('input').attr('id') == "toggleMentionsButton") {
        showCoref = true;
    }

    for (globalListItemCallback of globalListItemCallbacks) {
        globalListItemCallback({"showCoref": showCoref});
    }
}

enterQueryButton.addEventListener("click",queryOnButtonClick);
queryInputBox.addEventListener("keyup", queryOnKeyUp);
repeatQueryButton.addEventListener("click", queryRepeatOnButtonClick);
//moreInfoButton.addEventListener("click", moreInfoOnButtonClick);
stopExploringButton.addEventListener("click", stopExploringButtonOnClick);
for (toolbarNavigationItem of $toolbarNavigationItems) {
    toolbarNavigationItem.addEventListener("click", changeScreen);
}

const $groupToggleButtons = $('#groups-toggle label');
for (groupToggleButton of $groupToggleButtons) {
    groupToggleButton.addEventListener("click", changeGroup);
}


window.onload = onInitFunc;