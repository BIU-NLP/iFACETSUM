var addMoreButton = document.getElementById("addMoreButton");
var exploreList = document.getElementById("explorationPane");
var topicsDropdown = document.getElementById("topicsDropdownContent");
var stopExploringButton = document.getElementById('stopExploringButton');
var curTopicId = null;
var curLoadingInicatorElement = null;
var isWaitingForInitial = false;
var isWaitingForResponse = false;
var questionnaireBatchInd = -1;
var totalTextLength = 0;
var pageBaseUrl = "increment.html";
var summaryType = "increment";
var timeAllowed = -1;
var iterationNum = 0; // keeps track of how many iterations there are (0 is the initial summary)
var needIterationStarRating = false; // we do need the user to rate each summary
var allTextsInSession = [];
var questionnaireList = [];
var assignmentId = '';
var hitId = '';
var workerId = '';
var turkSubmitTo = '';
var clientId = uuidv4(); // generate a random clientID for this summarization session


function setNoTopicChosen() {
    document.getElementById("topicNameHeader").innerHTML = "Choose a topic to explore.";
    document.getElementById("numDocumentsHeader").innerHTML = "";
}

/* Resets the keyphrases list and the the exploration pane. */
function resetPage() {
    while (exploreList.firstChild) {
        exploreList.removeChild(exploreList.firstChild);
    }
    curLoadingInicatorElement = null;
}

function setTopic(topicInfo) {
    var name = topicInfo['topicName'];
    var topicId = topicInfo['topicId'];
    var initialSummaryList = topicInfo['summary'];
    var numDocuments = topicInfo['numDocuments'];
    //var timeAllowed = topicInfo['timeAllowed'];
    var textLength = topicInfo['textLength'];
    questionnaireList = topicInfo['questionnaire'];
    
    resetPage();
    curTopicId = topicId;
    // set the event name and keyphrases of the event:
    document.getElementById("topicNameHeader").innerHTML = name;
    //document.getElementById("numDocumentsHeader").innerHTML = "Summary of " + numDocuments + " articles on";
    document.getElementById("numDocumentsHeader").classList.add("myTooltip");
    document.getElementById("numDocumentsHeader").style.cursor = "help";
    document.getElementById("numDocumentsHeader").innerHTML = '' +
        'Summary of <span>' + numDocuments + ' articles</span>' +
        '<div class="bottomTooltip" style="width: 350px;">' +
        'Article sources: New York Times, Associated Press and Xinhua News Agency (years 1995-2000)' +
        '<i></i>' +
        '</div>' +
        ' on';
    //document.getElementById("sourceHeader").innerHTML = "Article sources: New York Times, Associated Press and Xinhua News Agency";
    insertSummaryItemInExplorationPane(initialSummaryList);
    
    // keep the text length so far:
    totalTextLength = textLength;
    
    // set that the request has been responded to:
    isWaitingForInitial = false;
    
    // make the page visible to the annotator and show relevant functionalities:
    showPageToAnnotator();
}



function insertSummaryItemInExplorationPane(txtList) {
    // a div is used to align the li item right:
    var listElementResult = document.createElement("div");
    var li = document.createElement("li"); // create an li element
    li.classList.add("exploreItem");
    li.style.maxWidth = "fit-content";
    
    // put the list of sentences sepatately line by line with a small margin in between:
    for (var i = 0; i < txtList.length; i++) {
        var sentencePar = document.createElement("p");
        sentencePar.style.marginTop = "10px";
        sentencePar.style.marginBottom = "10px";
        sentencePar.appendChild(document.createTextNode(txtList[i]));
        li.appendChild(sentencePar);
    }
    
	listElementResult.appendChild(li);
    exploreList.appendChild(listElementResult); //add to exploration list

    // extend the list of all texts:
    Array.prototype.push.apply(allTextsInSession, txtList);

    // iteration done
    iterationNum++;
}

function showQuestionnaire() {
    // initialize the questionnaire:
    if (questionnaireBatchInd > -1 && questionnaireList.length > 0) {
        initQuestionnaire(questionnaireList, allTextsInSession); // in functionailityQuestionnaire.js
    }

    questionnaireArea = document.getElementById("questionnaireArea");
    rightSide = document.getElementById("rightSide");
    leftSide = document.getElementById("leftSide");
    
    // hide the query area
    add1MoreButton.style.display = "none";
    add2MoreButton.style.display = "none";
    add3MoreButton.style.display = "none";
    add4MoreButton.style.display = "none";
    add5MoreButton.style.display = "none";
    
    // the right and left sides were unbalanced until now to give more room for the summary area
    // now we split the two sides in half:
    rightSide.style.width = "50%";
    leftSide.style.width = "50%";
    leftSide.style.left = "0px";
    
    // show the questionnaire area:
    questionnaireArea.style.display = "inline-table";
    
    // hide the "stop exploring" button in case it's showing
    stopExploringButton.style.display = "none";
    
}


/* Handle a query string. */
function addMoreInfo(numSentences) {
    if (canSendRequest()) {
        // put a loading ellipsis:
        insertLoadingIndicatorInExplorationPane();
        
        // scroll to bottom:
        exploreList.scrollTop = exploreList.scrollHeight;
        
        // get query response info from the server:
        sendRequest({"clientId": clientId, "request_query": {"topicId": curTopicId, "query": "", "summarySentenceCount":numSentences, "type":"addmore_"+numSentences}});
        // the response will be sent to function setQueryResponse asynchronously
    }
}

function canSendRequest() {
    return !isWaitingForResponse && curTopicId != null;
}

add1MoreButton.addEventListener("click", function(){addMoreInfo(1);});
add2MoreButton.addEventListener("click", function(){addMoreInfo(2);});
add3MoreButton.addEventListener("click", function(){addMoreInfo(3);});
add4MoreButton.addEventListener("click", function(){addMoreInfo(4);});
add5MoreButton.addEventListener("click", function(){addMoreInfo(5);});
stopExploringButton.addEventListener("click", stopExploringButtonOnClick);

window.onload = onInitFunc;