document.addEventListener('DOMContentLoaded', function () {

    let game_data = {game_state: ""}

    const joinForm = document.querySelector('form[action="/join"]');
    if (joinForm) {
        joinForm.addEventListener('submit', function (e) {
            const playerName = joinForm.querySelector('input[name="player_name"]').value.trim();
            console.log(playerName);
            const gameCode = joinForm.querySelector('input[name="game_code"]').value.trim();
            console.log(gameCode);
            if (playerName === '' || gameCode === '') {
                e.preventDefault();
                alert('Please enter both your name and the game code.');
            }
        });
        game_data["game_state"] = "login";
    }

    const header = document.getElementsByTagName("h1")[0]
    if(header && header.innerText === 'WAITING FOR PLAYERS TO JOIN') {
        game_data["game_state"] = "waiting_for_players";
    }

     const questionFormButton = document.getElementById('submit-question-btn');
    if (questionFormButton) {
        let submittingQuestion = false;
        questionFormButton.addEventListener('click', function () {
            if (submittingQuestion) return;            // guard


            const questionInput = document.getElementById('question-input').value.trim();
            const urlParams = new URLSearchParams(window.location.search);
            const game_code = urlParams.get('game_code');
            const player_name = urlParams.get('player');

            if (questionInput === '') {
                alert('Please enter a question before submitting.');
                return;
            }
            submittingQuestion = true;
            questionFormButton.disabled = true;

            // Send question to server using Fetch API
            fetch(`/submit_question?game_code=${game_code}&player=${player_name}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: questionInput })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('waiting-message').style.display = 'block';
                    questionFormButton.style.display = 'none'; // Hide the button after submission
                } else {
                    alert('Error: ' + data.message);
                    submittingQuestion = false; questionFormButton.disabled = false;
                }
            })
            .catch(function(error) {
                console.error('Error:', error)
                submittingQuestion = false; questionFormButton.disabled = false;
            });
        });
        game_data["game_state"] = "awaiting_question";
    }

    const responseForm = document.querySelector('form[action="/submit_response"]');
    if (responseForm) {
        let submittingResponse = false;
        responseForm.addEventListener('submit', function (e) {
            if (submittingResponse) { e.preventDefault(); return; }
            const response = responseForm.querySelector('textarea[name="response"]').value.trim();

            const questionSelect = responseForm.querySelector('select[name="question_id"]').value;
            //console.log("Question ID:", questionSelect);

            const responseType = "human"; // Always set to "human"
            //console.log("Response Type:", responseType);

            const intendedAuthor = responseForm.querySelector('select[name="intended_author"]').value;
            //console.log("Intended Author:", intendedAuthor);

            if (response === '' || questionSelect === '' || responseType === '' || intendedAuthor === '') {
                e.preventDefault();
                alert('Please fill out all fields before submitting your response.');
                return
            }
            const btn = responseForm.querySelector('[type="submit"]');
            submittingResponse = true;
            if (btn) btn.disabled = true;
        });
        //console.log("setting client state to awaiting_human_response")
        game_data["game_state"] = "awaiting_human_response"
    }

    /*// Handle guesses submission
    const submitGuessesButton = document.getElementById('submit-guesses');
    if (submitGuessesButton) {
        submitGuessesButton.addEventListener('click', function () {
            const guesses = [];
            document.querySelectorAll('.guess-response').forEach(function (guessField) {
                const responseId = parseInt(guessField.dataset.responseId);
                const guessedValue = guessField.value.split('_'); // Split value into type and intended author
                if (guessedValue.length !== 2) {
                    alert("Please make a guess for each response.");
                    return;
                }

                const guessedType = guessedValue[0];
                const guessedIntendedAuthor = guessedValue[1];

                guesses.push({
                    'response_id': responseId,
                    'guessed_type': guessedType,
                    'guessed_intended_author': guessedIntendedAuthor
                });
            });

            // Send guesses to the server
            fetch('/guess', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ guesses: guesses })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('You guessed ' + data.correct_count + ' correctly!');
                    window.location.href = '/results';
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => console.error('Error:', error));
        });
        //console.log("setting client state to guessing")
        game_data["game_state"] = "guessing"
    }*/

    // Function to check game state
    function checkGameState() {
        const urlParams = new URLSearchParams(window.location.search);
        const game_code = urlParams.get('game_code');
        const player_name = urlParams.get('player');

        fetch(`/check_game_state?game_code=${game_code}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentGameState = data.game_state;

                    // Update the page based on the current game state
                    handleGameStateChange(currentGameState, game_code, player_name);
                } else {
                    console.error('Error checking game state:', data.message);
                }
            })
            .catch(error => console.error('Error fetching game state:', error));
    }

// Function to check the number of players
function checkNumberOfPlayers() {
    console.log("checking num players");
    const urlParams = new URLSearchParams(window.location.search);
    const game_code = urlParams.get('game_code');

    // Make a request to the server to check the number of players
    fetch(`/check_number_of_players?game_code=${game_code}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const playerNames = data.player_names;
                console.log(playerNames)
                const htmlStr = playerNames.map(name => `<li>${name}</li>`).join("");
                const list = document.getElementsByTagName("ul")[0];

                // Update the list of players in the UI
                list.innerHTML = htmlStr;

                // Show the "Start Game" button if there are at least 3 players and the current user is the host
                //const button = document.getElementById('start_game_button');
                const jbutton = document.getElementById('j_start_game_button');
                if (data.number_of_players >= 3 && jbutton) {
                    //button.style.display = 'block'; // Show start game button
                    jbutton.style.display = 'block'; // Show start game button
                } else if (jbutton) {
                    jbutton.style.display = 'none'; // Hide start game button
                }
            } else {
                console.error('Error checking number of players:', data.message);
            }
        })
        .catch(error => console.error('Error:', error));
}
/*
    // Function to handle changes based on the new game state
    function handleGameStateChange(newState) {
        const stateMessageElement = document.getElementById('state-message');

        // Update the state message or instructions based on the new game state
        if (newState === 'awaiting_question') {
            stateMessageElement.innerText = "The game is now waiting for all players to write questions.";
            location.reload();
        } else if (newState === 'awaiting_human_response') {
            stateMessageElement.innerText = "The game is now waiting for all players to respond as humans.";
            location.reload();
        } else if (newState === 'awaiting_ai_response') {
            stateMessageElement.innerText = "The game is now waiting for all players to respond as AI.";
            location.reload();
        } else if (newState === 'guessing') {
            stateMessageElement.innerText = "It's time to guess the authors!";
            location.reload();
        } else if (newState === 'show_scores') {
            stateMessageElement.innerText = "Final scores are being calculated.";
        }

        // Optionally, show a notification to save input before the state change
       // alert('The game state has changed. Please save your response.');
    }*/

    // Function to handle changes in the game state
    function handleGameStateChange(newState, game_code, player_name) {
        if (newState === 'awaiting_question') {
            window.location.href = `/await_question?game_code=${game_code}&player=${player_name}`;
        } else if (newState === 'awaiting_responses') {
            window.location.href = `/await_responses?game_code=${game_code}&player=${player_name}`;
        } else if (newState.startsWith('guessing')) {
            window.location.href = `/guessing?game_code=${game_code}&player=${player_name}`;
        } else if (newState === 'show_scores') {
            window.location.href = `/final_scores?game_code=${game_code}&player=${player_name}`;
        }
    }


function initializeCountdown(deadline) {
    const countdownElement = document.getElementById('countdown-timer');
    const progressBar = document.getElementById('progress-bar');
    // Ensure deadline is correctly parsed as a UTC date
    const deadlineTime = new Date(deadline).getTime();  // Using the deadline string directly
    const interval = setInterval(function () {
        const now = new Date().getTime();
        const timeLeft = deadlineTime - now;

        // Calculate remaining time
        const secondsLeft = Math.max(Math.floor(timeLeft / 1000), 0);

        // Update countdown display
        if (countdownElement) {
            countdownElement.textContent = secondsLeft + ' seconds';
        }

        // Update progress bar width
        const totalDuration = 60; // Example: 60 seconds duration
        const percentage = Math.max((timeLeft / (totalDuration * 1000)) * 100, 0);
        if(progressBar) {
            progressBar.style.width = percentage + '%';
        }

        if (timeLeft <= 0) {
            clearInterval(interval); // Stop the countdown
            setTimeout(function () {
                const urlParams = new URLSearchParams(window.location.search);
                const game_code = urlParams.get('game_code');
                const player_name = urlParams.get('player');
                const page = window.location.pathname.split('/').pop();
                console.log("setting new page")
                console.log("game_code", game_code);
                console.log("page", page);
                let new_page = "await_question"
                if(page == "await_question") {
                    let new_page = "await_responses";
                } else if(page == "await_responses") {
                    new_page = "guessing"
                } else if(page == "guessing") {
                    new_page = "final_scores"
                }
                const url = "https://turingtest.pythonanywhere.com/"+new_page+"?game_code=" + game_code + "&player=" + player_name
                window.location.href= url;
            }, 1000);
        }
    }, 1000);
}

function fetchDeadline() {
    console.log("running fetchDeadline");
    const urlParams = new URLSearchParams(window.location.search);
    const game_code = urlParams.get('game_code');
    const player_name = urlParams.get('player');
    const page = window.location.pathname.split('/').pop();
    console.log("game_code", game_code);
    console.log("page", page);

    fetch(`/fetch_deadlines?game_code=${game_code}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log(data);
                const deadlines = data.deadlines;
                const currentDeadline = deadlines[page];

                if (currentDeadline) {
                    const deadlineTime = new Date(currentDeadline).getTime();
                    const now = new Date().getTime();

                    if (now > deadlineTime) {
                        console.log("wrong state for deadline")
                        // Redirect to the next page based on the game state
                        // NOTE: replace with client side logic
                        //window.location.href = `/game_state_check?game_code=${game_code}&player=${player_name}`;
                    } else {
                        initializeCountdown(currentDeadline);
                    }
                }
            }
        })
        .catch(error => console.error('Error fetching deadlines:', error));
}

console.log("calling fetchDeadline");
fetchDeadline();
console.log("XXXXX")
const urlParams = new URLSearchParams(window.location.search);
            const game_code = urlParams.get('game_code');
            const player_name = urlParams.get('player');
// Check if we are on the "Submit Your Responses" page
    if (window.location.pathname.includes('await_responses')) {
        console.log("in await_responses");
        // Fetch game data specifically for this page
        fetch('/fetch_game_data?game_code=' + game_code)
            .then(response => response.json())
            .then(data => {
                console.log(data);
                if (data.status === 'success') {
                    const game_data = data.game_data;
                    console.log('Fetched game data:', game_data);

                    // Call a function to create and update the DOM elements based on the fetched data
                    updateDOMWithGameData(game_data, player_name);
                } else {
                    console.error('Error fetching game data:', data.message);
                }
            })
            .catch(error => console.error('Error fetching game data:', error));



// Function to dynamically create DOM elements for questions and response fields
function updateDOMWithGameData(game_data, player_name) {
    const responseContainer = document.getElementById('response-container');
    responseContainer.innerHTML = ''; // Clear existing content

    // Loop through the questions and create elements for assigned responses
    game_data.questions.forEach(question => {
        if (Object.values(question.assigned_players).includes(player_name)) {
            let questionInstruction = ""
            if (question.assigned_players.human === player_name) {
                questionInstruction = "Respond as a Human: "
            }
            if (question.assigned_players.ai === player_name) {
                questionInstruction = "Respond pretending to be AI: "
            }
            const questionHeader = document.createElement('h3');
            questionHeader.textContent = `${questionInstruction} ${question.question}`;
            responseContainer.appendChild(questionHeader);

            if (question.assigned_players.human === player_name) {
                const textareaHuman = document.createElement('textarea');
                textareaHuman.setAttribute('id', `human-response-${question.id}`);
                textareaHuman.setAttribute('placeholder', 'Respond as a Human');
                textareaHuman.required = true;
                responseContainer.appendChild(textareaHuman);
            }

            if (question.assigned_players.ai === player_name) {
                const textareaAI = document.createElement('textarea');
                textareaAI.setAttribute('id', `ai-response-${question.id}`);
                textareaAI.setAttribute('placeholder', 'Respond as AI');
                textareaAI.required = true;
                responseContainer.appendChild(textareaAI);
            }
        }
    });
}

// Function to handle the submission of responses
function submitResponses(game_code, player_name) {
    const responseElements = document.querySelectorAll('textarea');
    console.log("running submitResponses")
    // Collect responses from the input fields
    const responses = [];
    responseElements.forEach(element => {
        const response = element.value.trim();
        console.log(response);
        if (response) {
            const responseType = element.id.includes('human') ? 'human' : 'ai';
            const questionId = parseInt(element.id.split('-').pop(), 10);
            responses.push({
                game_code: game_code,
                player: player_name,
                response: response,
                response_type: responseType,
                question_id: questionId
            });
        }
    });
    console.log(responses)
    // Send the responses to the server using Fetch API
    fetch('/submit_responses', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ responses: responses })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        if (data.status === 'success') {
            console.log('Responses submitted successfully.');
            // Hide the submit button and show the waiting message
            const submitButton = document.getElementById("submit-responses-btn");
            submitButton.style.display = 'none';
            const waitingMessage = document.createElement('p');
            waitingMessage.textContent = 'Waiting for other users...';
            document.body.appendChild(waitingMessage);
        } else {
            console.error('Error submitting responses:', data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

    }

    // Add event listener to the submit responses button
    const submitResponsesButton = document.getElementById('submit-responses-btn');
    if (submitResponsesButton) {
        let submittingResponses = false;
        submitResponsesButton.addEventListener('click', function () {
            if (submittingResponses) return;
            submittingResponses = true;
            submitResponsesButton.disabled = true;
            console.log("clicked")
            submitResponses(game_code, player_name);
        });
    }

    if (window.location.pathname.includes('guessing')) {
        const urlParams = new URLSearchParams(window.location.search);
        const game_code = urlParams.get('game_code');
        const player_name = urlParams.get('player');
        let currentQuestionIndex = 0; // Initialize the current question index
        let game_data = {};

    fetch('/fetch_game_data?game_code=' + game_code)
        .then(response => response.json())
        .then(data => {
            game_data = data.game_data;
            console.log(game_data); // Now the client has the game data fetched from the server

            // Start the countdown and display the first question
            const deadlines = game_data.deadlines;
            const currentDeadline = deadlines[`guessing_${currentQuestionIndex + 1}`];
            if (currentDeadline) {
                initializeCountdown(currentDeadline);
            }
            displayQuestion();
        });

    function displayQuestion() {
        function shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1)); // Random index from 0 to i
                [array[i], array[j]] = [array[j], array[i]];  // Swap elements
            }
        }

        const questionContainer = document.getElementById('question-container');
        const questions = game_data.questions;
        const responses = game_data.responses;

        if (currentQuestionIndex >= questions.length) {
            console.log("No more questions.");
            return;
        }

        const question = questions[currentQuestionIndex];
        const questionHtml = `<h3>Question: ${question.question}</h3><ul>`;

        shuffleArray(responses)

        let responseHtml = "";
        responses.forEach(response => {
            if (response.question_id === question.id) {
                responseHtml += `<li>${response.response}
                    <select class="guess-response" data-response-id="${response.id}">
                        <option value="">Select intended author</option>
                        <option value="human_human">Human answering honestly</option>
                        <option value="ai_ai">AI answering honestly</option>
                        <option value="human_ai">Human pretending to be AI</option>
                        <option value="ai_human">AI pretending to be human</option>
                    </select>
                </li>`;
            }
        });

        questionContainer.innerHTML = questionHtml + responseHtml + "</ul>";
        document.getElementById('submit-guesses').style.display = 'block'; // Show the submit button
        document.getElementById('waiting-message').style.display = 'none'; // Hide the waiting message
    }

    function initializeCountdown(deadline) {
        console.log("guessing specific intialize countdown");
        const countdownElement = document.getElementById('countdown-timer');
        const progressBar = document.getElementById('progress-bar');
        const deadlineTime = new Date(deadline).getTime();  // Using the deadline string directly
        const interval = setInterval(function () {
            const now = new Date().getTime();
            const timeLeft = deadlineTime - now;

            // Calculate remaining time
            const secondsLeft = Math.max(Math.floor(timeLeft / 1000), 0);

            // Update countdown display
            if (countdownElement) {
                countdownElement.textContent = secondsLeft + ' seconds';
            }

            // Update progress bar width
            const totalDuration = 60; // Example: 60 seconds duration
            const percentage = Math.max((timeLeft / (totalDuration * 1000)) * 100, 0);
            if(progressBar) {
                progressBar.style.width = percentage + '%';
            }

            if (timeLeft <= 0) {
                console.log("timeLeft is done")
                clearInterval(interval); // Stop the countdown
                setTimeout(function () {
                    currentQuestionIndex++;
                    const nextDeadline = game_data.deadlines[`guessing_${currentQuestionIndex + 1}`];
                    if (nextDeadline) {
                        initializeCountdown(nextDeadline);
                        console.log("displaying question")
                        displayQuestion();
                    } else {
                        const submitGuessesButton = document.getElementById('submit-guesses');
                        const buttonIsVisible = submitGuessesButton.style.display == "block";
                        if(buttonIsVisible) {
                            submitGuesses();  // If no more questions, submit guesses
                        }
                        console.log("no more deadlines")
                        new_page = "final_scores";
                        const url = "https://turingtest.pythonanywhere.com/" + new_page + "?game_code=" + game_code + "&player=" + player_name;
                        window.location.href = url;

                    }
                }, 1000);
            }
        }, 1000);
    }

    // Countdown initialization and redirection logic
/*function initializeCountdown(deadline) {
    const countdownElement = document.getElementById('countdown-timer');
    const progressBar = document.getElementById('progress-bar');
    const deadlineTime = new Date(deadline).getTime();  // Using the deadline string directly
    const interval = setInterval(function () {
        const now = new Date().getTime();
        const timeLeft = deadlineTime - now;

        // Calculate remaining time
        const secondsLeft = Math.max(Math.floor(timeLeft / 1000), 0);

        // Update countdown display
        if (countdownElement) {
            countdownElement.textContent = secondsLeft + ' seconds';
        }

        // Update progress bar width
        const totalDuration = 60; // Example: 60 seconds duration
        const percentage = Math.max((timeLeft / (totalDuration * 1000)) * 100, 0);
        if (progressBar) {
            progressBar.style.width = percentage + '%';
        }

        if (timeLeft <= 0) {
            clearInterval(interval); // Stop the countdown
            setTimeout(function () {
                const urlParams = new URLSearchParams(window.location.search);
                const game_code = urlParams.get('game_code');
                const player_name = urlParams.get('player');
                const page = window.location.pathname.split('/').pop();
                console.log("game_code", game_code);
                console.log("page", page);

                // Redirect logic based on the current page
                if (page === "await_question") {
                    new_page = "await_responses";
                } else if (page === "await_responses") {
                    new_page = "guessing";
                } else if (page === "guessing") {
                    new_page = "final_scores";  // Redirect to final_scores at the end of guessing
                }

                const url = "https://turingtest.pythonanywhere.com/" + new_page + "?game_code=" + game_code + "&player=" + player_name;
                window.location.href = url;
            }, 1000);
        }
    }, 1000);
}*/
    // Handle guesses submission
    const submitGuessesButton = document.getElementById('submit-guesses');
    if (submitGuessesButton) {
        submitGuessesButton.addEventListener('click', submitGuesses);
    }

// Function to handle guesses submission
function submitGuesses() {
    const guesses = [];
    document.querySelectorAll('.guess-response').forEach(function (guessField) {
        const responseId = parseInt(guessField.dataset.responseId);
        const guessedValue = guessField.value.split('_'); // Split value into type and intended author
        if (guessedValue.length !== 2) {
            alert("Please make a guess for each response.");
            return;
        }

        const guessedType = guessedValue[0];
        const guessedIntendedAuthor = guessedValue[1];

        guesses.push({
            'response_id': responseId,
            'guessed_type': guessedType,
            'guessed_intended_author': guessedIntendedAuthor
        });
    });

    // Retrieve game_code and player_name from the hidden input fields or URL
    const urlParams = new URLSearchParams(window.location.search);
    const game_code = urlParams.get('game_code');
    const player_name = urlParams.get('player');

    document.getElementById('submit-guesses').style.display = 'none'; // Hide the submit button
    document.getElementById('waiting-message').style.display = 'block'; // Show waiting message


    // Send guesses to the server
    fetch(`/guess?game_code=${game_code}&player=${player_name}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ guesses: guesses })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Guesses submitted successfully.');

            // Display feedback
            const feedback = data.feedback;
            feedback.forEach(item => {
                console.log(item)
                const guessField = document.querySelector(`.guess-response[data-response-id="${item.response_id}"]`);
                const feedbackElement = document.createElement('p');
                const authorStr = item.author === "AI" ? "" : " (by " + item.author + ")"
                if (item.is_correct) {
                    feedbackElement.textContent = "Correct" + authorStr;
                    feedbackElement.style.color = 'green';
                } else {
                    feedbackElement.textContent = `Incorrect. Correct Answer: ${item.correct_type} responding as ${item.correct_author} ${authorStr}`;
                    feedbackElement.style.color = 'red';
                }

                // Insert the feedback after the guess field
                guessField.parentNode.appendChild(feedbackElement);
            });

            // Hide submit button and show waiting message after feedback display

            // Wait 5 seconds before moving to the next question or stage
            /*setTimeout(() => {
                loadNewQuestion(); // Implement logic to load the next question here
            }, 5000);*/
        } else {
            console.error('Error submitting guesses:', data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}


// Function to load a new question for guessing
function loadNewQuestion(questionIndex) {
    // Logic to update the DOM with the new question and responses

    // Reset the visibility of submit button and waiting message
    document.getElementById('submit-guesses').style.display = 'block'; // Show the submit button
    document.getElementById('waiting-message').style.display = 'none'; // Hide the waiting message
}
    /*function submitGuesses() {
    const guesses = [];
    let missing_guess = false
    document.querySelectorAll('.guess-response').forEach(function (guessField) {
        const responseId = parseInt(guessField.dataset.responseId);
        const guessedValue = guessField.value.split('_'); // Split value into type and intended author
        if (guessedValue.length !== 1) {
            missing_guess = true;
            //alert("Please make a guess for each response.");
            return;
        }

        const guessedType = guessedValue[0];
        const guessedIntendedAuthor = guessedValue[1];

        guesses.push({
            'response_id': responseId,
            'guessed_type': guessedType,
            'guessed_intended_author': guessedIntendedAuthor
        });
    });

    if(missing_guess) {
        alert("Please make a guess for each response.");
    }

    // Retrieve game_code and player_name from the hidden input fields or URL
    const urlParams = new URLSearchParams(window.location.search);
    const game_code = urlParams.get('game_code');
    const player_name = urlParams.get('player');
    console.log(game_code)
    console.log(player_name);
    // Send guesses to the server
    url = `/guess?game_code=${game_code}&player=${player_name}`
    console.log(url)
    fetch(`/guess?game_code=${game_code}&player=${player_name}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ guesses: guesses })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Guesses submitted successfully.');
            submitGuessesButton.style.display = 'none'; // Hide the submit button
            document.getElementById('waiting-message').style.display = 'block'; // Show waiting message
        } else {
            console.error('Error submitting guesses:', data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}*/


    }

    if (window.location.pathname.includes('waiting_for_players')) {
        console.log("setting interval")
        // Set an interval to periodically check the number of players
        setInterval(checkNumberOfPlayers, 5000);
        setInterval(checkGameState, 5000);
        console.log("intervals set");

        // Add event listener to the start game button
        const startGameButton = document.getElementById('start_game_button');
        const jStartGameButton = document.getElementById('j_start_game_button');
        if(jStartGameButton) {
            let startingA = false;
            jStartGameButton.addEventListener('click', function () {
                if (startingA) return;
                startingA = true; jStartGameButton.disabled = true;
                const urlParams = new URLSearchParams(window.location.search);
                const game_code = urlParams.get('game_code');
                const player_name = urlParams.get('player');
                console.log(game_code)
                console.log(player_name);

                const url = "https://turingtest.pythonanywhere.com/await_question?game_code=" + game_code + "&player=" + player_name
                console.log(url)
                fetch(`/j_start_game?game_code=${game_code}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log(data)
                        if (data.status === 'success') {
                            window.location.href= url;
                        } else {
                            startingA = false;
                            jStartGameButton.disabled = false;
                        }
                    }).catch(() => { startingA = false; jStartGameButton.disabled = false; });
            })
        }

        if (startGameButton) {
            let startingB = false;
            startGameButton.addEventListener('click', function (event) {
                event.preventDefault();
                if (startingB) return;
                startingB = true; startGameButton.disabled = true;


                // Get game_code and player from URL parameters
                const urlParams = new URLSearchParams(window.location.search);
                const game_code = urlParams.get('game_code');
                const player_name = urlParams.get('player');

                // Make a POST request to start the game
                fetch(`/start_game?game_code=${game_code}&player=${player_name}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        game_code: game_code,
                        player_name: player_name
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Redirect to the question submission page
                        window.location.href = `/await_question?game_code=${game_code}&player=${player_name}`;
                    } else {
                        console.error('Error starting game:', data.message);
                        startingB = false; startGameButton.disabled = false;
                    }
                })
                .catch(function(error) {
                    console.error('Error:', error)
                    startingB = false; startGameButton.disabled = false;
                });
            });
        }
    }

});
