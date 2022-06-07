var allQuestionsCheckboxes = [];
var commentBoxEle = null;
var questionnaireStarRatingsDone = {};

function initQuestionnaire(questionList, allTextsInSession) {
    allQuestionsCheckboxes = [];
    var questionnaireBody = document.getElementById('questionnaireModalBody');
    var usedSentencesForQuestions = []; // sentences used already for empty question slots
    for (var qInd = 0; qInd < questionList.length; qInd++) {
        questionId = questionList[qInd]["id"];
        questionTxt = questionList[qInd]["str"];

        // if no question is given, then we need to put a short sentence from the session text as the question:
        if (questionTxt == '') {
            // find the shortest unused sentence from the session's text:
            shortestSent = null;
            shortestSentLen = 99999;
            for (var sentIdx = 0; sentIdx < allTextsInSession.length; sentIdx++) {
                sent = allTextsInSession[sentIdx]['sent'];
                // try it out only if it wasn't used yet for a previous open-slot question:
                if (usedSentencesForQuestions.indexOf(sent) == -1) {
                    sentLen = sent.length;
                    if (sentLen < shortestSentLen) {
                        shortestSentLen = sentLen;
                        shortestSent = sent;
                    }
                }
            }
            questionTxt = shortestSent;
            usedSentencesForQuestions.push(shortestSent);
        }
        
        var qEle = document.createElement("div");
        qEle.style.float = "left";
        qEle.style.marginBottom = "8px";
        var checkboxEle = document.createElement("input");
        checkboxEle.type = "checkbox";
        checkboxEle.value = questionId;
        qEle.appendChild(checkboxEle);
        qEle.appendChild(document.createTextNode(" " + questionTxt));
        
        // bind the event to the keyword list item (we use bind because of the loop - see: https://stackoverflow.com/questions/19586137/addeventlistener-using-for-loop-and-passing-values )
        checkboxEle.addEventListener("change", checkboxChanged.bind(this, checkboxEle), false);
        
        questionnaireBody.appendChild(qEle);
        questionnaireBody.appendChild(document.createElement("br"));
        allQuestionsCheckboxes.push(checkboxEle);
    }

    // add the rating widgets for the three usability survey questions:
    var usageQuestionTitle = document.createElement("span");
    usageQuestionTitle.style.float = "left";
    usageQuestionTitle.style.marginTop = "20";
    usageQuestionTitle.style.color = "#002b33";
    usageQuestionTitle.style.fontStyle = "italic";
    usageQuestionTitle.style.fontWeight = "bold";
    usageQuestionTitle.innerHTML = "Thanks! What do you think of the system?"
    questionnaireBody.appendChild(usageQuestionTitle);
    var usageQuestion = document.createElement("span");
    usageQuestion.style.float = "left";
    usageQuestion.style.marginTop = "2";
    usageQuestion.style.marginLeft = "10";
    usageQuestion.style.color = "#faebd7";
    usageQuestion.innerHTML = "As a system for exploring information on a topic,"
    questionnaireBody.appendChild(usageQuestion);
    var questionId1 = 'r1';
    //usageRatingEle1 = getStarRatingQuestionnaireElement(questionId1, 1, "its capabilities meet my requirments", 5, "");
    usageRatingEle1 = getStarRatingQuestionnaireElement(questionId1, 1, "its capabilities meet the need to efficiently collect useful information for a journalistic overview", 5, "");
    usageRatingEle1.style.float = "left";
    usageRatingEle1.style.margin = "20 0 0 20";
    questionnaireBody.appendChild(document.createElement("br"));
    questionnaireBody.appendChild(usageRatingEle1);
    questionnaireStarRatingsDone[questionId1] = false;
    var questionId2 = 'r2';
    usageRatingEle2 = getStarRatingQuestionnaireElement(questionId2, 2, "it is easy to use", 5, "");
    usageRatingEle2.style.float = "left";
    usageRatingEle2.style.margin = "-25 20 0 20";
    questionnaireBody.appendChild(document.createElement("br"));
    questionnaireBody.appendChild(usageRatingEle2);
    questionnaireStarRatingsDone[questionId2] = false;
    var responsivenessQuestion = document.createElement("span");
    responsivenessQuestion.style.float = "left";
    responsivenessQuestion.style.marginTop = "-7px";
    responsivenessQuestion.style.marginLeft = "10px";
    responsivenessQuestion.innerHTML = "During the interactive stage, how well did the responses respond to your queries?"
    responsivenessQuestion.style.color = "#faebd7";
    questionnaireBody.appendChild(responsivenessQuestion);
    var questionId3 = 'r3';
    usageRatingEle3 = getStarRatingQuestionnaireElement(questionId3, 3, "During the interactive stage, how well did the responses respond to your queries?", 5, "");
    usageRatingEle3.style.float = "left";
    usageRatingEle3.style.margin = "-30px 50px 0px 212px";
    questionnaireBody.appendChild(document.createElement("br"));
    questionnaireBody.appendChild(usageRatingEle3);
    questionnaireStarRatingsDone[questionId3] = false;
    
    questionnaireBody.appendChild(document.createElement("br"));

    // add a comments box for the user to write any comments:
    commentBoxEle = document.createElement("textarea");
    commentBoxEle.placeholder = "comments (optional)";
    commentBoxEle.rows = 3;
    //commentBoxEle.cols = 50;
    commentBoxEle.style.width = "300px";
    commentBoxEle.style.marginTop = "10px";
    questionnaireBody.appendChild(commentBoxEle);
    
    // add a submit button at the bottom of the questionnaire:
    var submitButtonEle = document.createElement("div");
    submitButtonEle.classList.add("submitButton");
    questionnaireBody.appendChild(submitButtonEle);
    
    if (document.getElementById('assignmentId').value == 'ASSIGNMENT_ID_NOT_AVAILABLE') {
        submitButtonEle.style.cursor = "not-allowed";
        submitButtonEle.appendChild(document.createTextNode("Preview: cannot submit"));
    }
    else {
        submitButtonEle.addEventListener("click", submitQuestionnaire);
        submitButtonEle.appendChild(document.createTextNode("Submit"));
    }
}

function checkboxChanged(checkboxEle) {
    sendRequest({"clientId": clientId, "request_set_question_answer": {"qId": checkboxEle.value, "answer": checkboxEle.checked}});
}

function submitQuestionnaire() {
    //if (needIterationStarRating && !lastIterationRated) {
    if (iterationStarRatingType != 0 && !lastIterationRated) {
        alert("Please rate the last summary before submitting.");
    }
    else if (!allQuestionnaireRatingsFilled()) {
        alert("Please rate the " + Object.keys(questionnaireStarRatingsDone).length.toString() + " survey questions before submitting.");
    }
    else {
        practiceTaskMessage("Thank you!<br>Once you've finished the two practice tasks, we will check your work.<br>If you qualify, there will be <b>more of these tasks</b>, <u>without the guidance messages</u>.<br><br>Your sincere work can assist us in understanding how to build better systems for knowledge acquisition. <span style='font-size:30px;'>&#x1F680;</span><br><br><b>Thanks for your help!</b> <span style='font-size:30px;'>&#x1F60A;", function() {
            allAnswers = {};
            for (var i = 0; i < allQuestionsCheckboxes.length; i++) {
                allAnswers[allQuestionsCheckboxes[i].value] = allQuestionsCheckboxes[i].checked;
            }
            sendRequest({"clientId": clientId, "request_submit": {"answers": allAnswers, 'timeUsed': stopwatch, 'comments': commentBoxEle.value}});
            // response goes to submitFinal in general.js
        });
    }
}

function getStarRatingQuestionnaireElement(questionId, questionIdx, questionText, numStarsInRating, helpMessage) {
    // create a star rating widget for:
    var starRatingElement = document.createElement("div");
    starRatingElement.classList.add("rating");
    starRatingElement.style.padding = "15px 0px";
	starRatingElement.style.marginTop = "-15px";
	starRatingElement.style.marginRight = "-10px";

    // put 5 stars in the widget:
    for (var i = numStarsInRating; i >= 1; i--) { // since the stars are shown in opposite order, we mark them 5 to 1 (5 is best)
        // Enclosed within a function so that the addEventListener is within its own scope, otherwise the last
        // value passed (within this loop) to the listener is kept for all eventListeners in the loop.
        // (see: https://stackoverflow.com/questions/19586137/addeventlistener-using-for-loop-and-passing-values)
        (function () {
            // (star rating based on https://codepen.io/rachel_web/pen/dYrrvY)
            var starId = "star_" + i.toString() + "_" + questionId; // e.g. star_3_1 == 3 stars for question 1
            // the radio button enables choosing a star (but it is hidden in the style):
            var radioStar = document.createElement("input");
            radioStar.type = "radio";
            radioStar.id = starId;
            radioStar.name = "rating_" + questionId;
            radioStar.value = i.toString();
            radioStar.addEventListener('click', function(){onQuestionnaireRatingStarClicked(radioStar.id, questionText, numStarsInRating);}, false);
            starRatingElement.appendChild(radioStar);
            // the label is a star character (in the style):
            var labelStar = document.createElement("label");
            labelStar.htmlFor = starId;
            labelStar.setAttribute('label-before-content', String.fromCharCode(0x2605));
            starRatingElement.appendChild(labelStar);
        }());
    }

    // put an instructions label for the rating; since the widget above is placed opposite,
    // we put the instructions after in the code, though it appears before:
    if (questionIdx != 3) { // TODO: this is hardcoded for the third question, and should not be, but doing it for fast coding
        var instructionsSpan = document.createElement("span");
        instructionsSpan.id = "ratingInstructions_" + questionId;
        instructionsSpan.classList.add('ratingInstructions');
        instructionsSpan.style.position = "relative";
        instructionsSpan.style.float = "right";
        //instructionsSpan.classList.add('ratingInstructionsGlow'); // to be removed after first time clicked
        //instructionsSpan.style.textShadow = "0 0 10px #f7ff00";
        instructionsSpan.style.fontSize = "medium";
        if (questionIdx == 1) {
            instructionsSpan.style.margin = "-54 5 0 0";
        }
        else if (questionIdx == 2) {
            instructionsSpan.style.margin = "-7 5 0 0";
        }
        //instructionsSpan.innerHTML = questionIdx.toString() + ")  " + questionText + ":";
        instructionsSpan.innerHTML = String.fromCharCode(0x2022) + " " + questionText + ":";
        if (helpMessage != '') {
            instructionsSpan.title = helpMessage;
            instructionsSpan.style.cursor = 'help';
        }

        starRatingElement.appendChild(instructionsSpan);
    }

    // the "tooltip" to explain each rating star
    var explanationSpan = document.createElement("div");
    // change the location to be above the rating widget (NOTE: hardcoded for now):
    if (questionIdx == 1) { // TODO: this should be 10 pixels to the right of the width of hardcoded instructionsSpan
        explanationSpan.classList.add('explainLabelAboveUMUX');
        explanationSpan.style.marginLeft = 364; // 317;
    }
    if (questionIdx == 2) {
        explanationSpan.classList.add('explainLabelAboveUMUX');
        explanationSpan.style.marginLeft = 143; //152;
    }
    if (questionIdx == 3) {
        explanationSpan.classList.add('explainLabelAboveResponsiveness');
        explanationSpan.style.marginLeft = 0;
    }
    starRatingElement.appendChild(explanationSpan);

    return starRatingElement;
}

function onQuestionnaireRatingStarClicked(starId, questionText, numStarsInRating) {
    var idParts = starId.split('_');
    var rating = idParts[1] / numStarsInRating; // sent as a 0-to-1 float since number of stars may change sometime
    var questionId = idParts[2];
    // remove the glowing effect now that the star rating has been selected:
    instructionsSpan = document.getElementById("ratingInstructions_" + questionId.toString());
    if (instructionsSpan != null) {
        instructionsSpan.classList.remove('ratingInstructionsGlow');
    }
    // send the server the rating:
    sendRequest({"clientId": clientId, "request_set_questionnaire_rating": {"questionId": questionId, "questionText": questionText, "rating": rating}});
    questionnaireStarRatingsDone[questionId] = true;
}

function allQuestionnaireRatingsFilled() {
    for (var qId in questionnaireStarRatingsDone) {
        var wasAnswered = questionnaireStarRatingsDone[qId];
        if (!wasAnswered) {
            return false;
        }
    }
    return true;
}