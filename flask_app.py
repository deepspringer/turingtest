from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import openai
import threading
from datetime import datetime, timedelta, timezone
from random import sample
import sensitive_data


# Initialize a lock
game_data_lock = threading.Lock()
openai.api_key = sensitive_data.api_key

app = Flask(__name__)
app.secret_key = sensitive_data.flask_secret

GAME_DATA_PATH = '/home/turingtest/mysite/data/game_data.json'

# Add this global variable to store ongoing timers
timers = {}

@app.route('/test_setup', methods=['GET'])
def test_setup():
    # Get parameters from the request
    game_code = request.args.get('game_code')
    game_state = request.args.get('game_state')
    deadline_duration = request.args.get('deadline_duration', type=int)  # Duration in seconds

    # Validate the game code
    if not game_code:
        return "Game code is required", 400

    # Load game data
    game_data = load_game_data()

    # Check if game exists
    if game_code not in game_data:
        return f"Game with code {game_code} not found.", 404

    # Update the game state
    if game_state:
        game_data[game_code]['game_state'] = game_state

    # Update the deadline if a duration is provided
    if deadline_duration:
        new_deadline = datetime.now(timezone.utc) + timedelta(seconds=deadline_duration)
        game_data[game_code]['deadline'] = new_deadline.isoformat()

    # Save the updated game data
    save_game_data(game_data)

    # Update the session with the specified game code
    #session['game_code'] = game_code

    # Log the new state for debugging purposes
    #print(f"Game code {game_code} set to state {game_state} with deadline in {deadline_duration} seconds.")

    # Redirect to the game route to view the changes
    return redirect(url_for('game'))


def set_game_state_timer(game_code, state, duration_seconds):

    deadline = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)  # Use UTC

    # Save the deadline in the game data
    game_data = load_game_data()
    game_data[game_code]['deadline'] = deadline.isoformat()  # Save as string to JSON
    save_game_data(game_data)

    # Start a timer that will update the game state after the given duration
    timer = threading.Timer(duration_seconds, update_game_state, args=[game_code, state])
    timer.start()

    # Store the timer object so it can be managed later (if needed)
    timers[game_code] = timer

def update_game_state(game_code, new_state):
    game_data = load_game_data()

    # Ensure the game exists and update its state
    if game_code in game_data:
        game_data[game_code]['game_state'] = new_state
        #game_data[game_code].pop('deadline', None)  # Remove the deadline
        save_game_data(game_data)

    # Clean up the timer from the timers dictionary
    if game_code in timers:
        timers.pop(game_code)


@app.route('/j_start_game', methods=['GET'])
def j_start_game():
    # Log that the route has been accessed
    print("Entered /start_game route")
    RESPOND_SECS = 120  # ← give users 2 minutes to respond (pick your value)
    QUESTION_SECS = 80  # your existing base window
    GUESS_SECS = 80     # per-guessing round length (if you want to keep it)

    # Load game data
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    #player_name = request.args.get('player')  # Get the player's name from the URL parameters

    # Log the player name and game code
    #print("Starting game with player:", player_name)
    print("Game code:", game_code)

    # Check if the game code and player name are valid
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    # Change state to await questions and set a timer for the next state
    game_data[game_code]['game_state'] = 'awaiting_question'
    #print("Game state updated to 'awaiting_question' for game code:", game_code)
    length = 80
    deadlines = {
        "await_question": get_deadline_time(QUESTION_SECS),
        "await_responses": get_deadline_time(QUESTION_SECS + RESPOND_SECS),
    }
    current_game = game_data[game_code]
    #num_players = len(game_data[game_code]["players"])
    for i in range(1, len(current_game['players']) + 1):
    #for i in range(0, num_players):
        guessing_key = f'guessing_{i}'
        deadlines[guessing_key] = get_deadline_time(QUESTION_SECS + RESPOND_SECS + GUESS_SECS * i)

    game_data[game_code]['deadlines'] = deadlines
    save_game_data(game_data)

    set_game_state_timer(game_code, 'awaiting_responses', QUESTION_SECS)

    return jsonify({'status': 'success'})

def get_deadline_time(seconds):
    deadline = datetime.now(timezone.utc) + timedelta(seconds=seconds)  # Use UTC
    return deadline.isoformat()


@app.route('/start_game', methods=['POST'])
def start_game():
    # Log that the route has been accessed
    print("Entered /start_game route")

    # Load game data
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')  # Get the player's name from the URL parameters

    # Log the player name and game code
    print("Starting game with player:", player_name)
    print("Game code:", game_code)

    # Check if the game code and player name are valid
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    # Change state to await questions and set a timer for the next state
    game_data[game_code]['game_state'] = 'awaiting_question'
    print("Game state updated to 'awaiting_question' for game code:", game_code)
    save_game_data(game_data)

    # Set a timer to transition from 'awaiting_question' to 'awaiting_responses' in 60 seconds
    set_game_state_timer(game_code, 'awaiting_responses', 60)
    print("Timer set for 60 seconds to transition to 'awaiting_responses'")

    # Redirect to the submit_question route for the player
    print("Redirecting to await_question route for player:", player_name)
    return redirect(url_for('await_question', game_code=game_code, player=player_name))

@app.route('/await_question')
def await_question():
    # Log that the route has been accessed
    print("Entered /await_question route")

    # Retrieve parameters
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Log the player name and game code
    print("Awaiting question with player:", player_name)
    print("Game code:", game_code)

    # Load game data
    game_data = load_game_data()
    #print("Game data loaded:", game_data)

    # Validate game code and player name
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        print("Player not found in this game:", player_name)
        return "Player not found in this game.", 404

    # Log successful validation
    print("Valid game code and player name. Rendering template for submitting question.")

    # Render the template for submitting a question
    return render_template('submit_question.html', game_data=game_data[game_code], player_name=player_name)


@app.route('/await_responses')
def await_responses():
    # Log that the route has been accessed
    print("Entered /await_responses route")

    # Retrieve parameters
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Log the player name and game code
    print("Awaiting responses with player:", player_name)
    print("Game code:", game_code)

    # Load game data
    game_data = load_game_data()
    #print("Game data loaded:", game_data)

    # Validate game code and player name
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        print("Player not found in this game:", player_name)
        return "Player not found in this game.", 404

    # Log successful validation
    print("Valid game code and player name. Rendering template for submitting question.")

    # Render the template for submitting a question
    return render_template('responses.html', game_data=game_data[game_code], player_name=player_name)

@app.route('/guessing')
def guessing():
    # Retrieve parameters
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Log the player name and game code
    print("Guessing with player:", player_name)
    print("Game code:", game_code)

    # Load game data
    game_data = load_game_data()
    #print("Game data loaded:", game_data)

    # Validate game code and player name
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        print("Player not found in this game:", player_name)
        return "Player not found in this game.", 404

    # Log successful validation
    print("Valid game code and player name. Rendering template for submitting question.")

    # Render the template for submitting a question
    return render_template('guessing.html', game_data=game_data[game_code], player_name=player_name)


@app.route('/final_scores')
def final_scores():
    # Retrieve parameters
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Log the player name and game code
    print("Guessing with player:", player_name)
    print("Game code:", game_code)

    # Load game data
    game_data = load_game_data()

    # Validate game code and player name
    if not game_code or game_code not in game_data:
        print("Invalid game code, redirecting to index")
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        print("Player not found in this game:", player_name)
        return "Player not found in this game.", 404

    # Log successful validation
    print("Valid game code and player name. Rendering template for submitting question.")

    # Render the template for submitting a question
    return render_template('final_scores.html', game_data=game_data[game_code], player_name=player_name)


def load_game_data():
    try:
        with game_data_lock:  # Acquire lock
            with open(GAME_DATA_PATH, 'r') as file:
                return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        # If the file is empty or not found, return an empty dictionary
        return {}

def save_game_data(data):
    with game_data_lock:  # Acquire lock
        with open(GAME_DATA_PATH, 'w') as file:
            json.dump(data, file, indent=4)


def chat_completion(user_input, messages=[], temperature=0.7, model="gpt-4o"):
    messages.append({"role": "user", "content": user_input})
    openai_response = openai.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages
    )
    response_content = openai_response.choices[0].message.content
    try:
        result = json.loads(response_content)
    except json.JSONDecodeError:
        result = response_content
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/join', methods=['POST'])
def join():
    game_data = load_game_data()
    game_code = request.form['game_code']
    player_name = request.form['player_name']

    # Check if game code exists; if not, initialize the game data
    if game_code not in game_data:
        # Initialize game data for new game
        game_data[game_code] = {
            'players': {},
            'questions': [],
            'responses': [],
            'scores': {},
            'game_state': 'waiting_for_players'  # Initial state
        }

    # Add the player to the game
    game_data[game_code]['players'][player_name] = {'name': player_name, 'guessing_score': 0, 'writing_score': 0}

    # Save the updated game data
    save_game_data(game_data)

    # Redirect to the 'waiting_for_players' route with game code and player name as parameters
    return redirect(url_for('waiting_for_players', game_code=game_code, player=player_name))


@app.route('/fetch_deadlines', methods=['GET'])
def fetch_deadlines():
    game_code = request.args.get('game_code')
    print("running fetch_deadlines")
    print(game_code)
    game_data = load_game_data()
    if not game_code or game_code not in game_data:
        return jsonify({'status': 'error', 'message': 'Game not found'})

    deadlines = game_data[game_code].get('deadlines', {})
    print(deadlines)
    return jsonify({'status': 'success', 'deadlines': deadlines})

"""
@app.route('/fetch_deadline', methods=['GET'])
def fetch_deadline():

    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    if not game_code or game_code not in game_data:
        return jsonify({'status': 'error', 'message': 'Game not found'})

    # Get the deadline from the game data
    deadline = game_data[game_code].get('deadline', '')

    return jsonify({'status': 'success', 'deadline': deadline})
"""

@app.route('/waiting_for_players')
def waiting_for_players():
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Load game data
    game_data = load_game_data()

    # Validate the game code and player name
    if not game_code or game_code not in game_data:
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        return "Player not found in this game.", 404

    # Render the template for waiting for players
    return render_template('waiting_for_players.html', game_data=game_data[game_code], player_name=player_name)


@app.route('/game')
def game():
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    if not game_code or not player_name:
        return redirect(url_for('index'))

    current_game = game_data[game_code]

    game_state = current_game.get('game_state', 'waiting_for_players')

    # Pass the deadline to the template
    deadline = current_game.get('deadline', '')


    if game_state == 'waiting_for_players':
        return render_template('waiting_for_players.html', game_data=current_game, deadline=deadline)
    elif game_state == 'awaiting_question':
        return render_template('submit_question.html', game_data=current_game, deadline=deadline)
    elif game_state == 'awaiting_responses':
        return render_template('responses.html', game_data=current_game, deadline=deadline)
    elif game_state == 'guessing':
        return render_template('guessing.html', game_data=current_game, deadline=deadline)
    elif game_state == 'show_scores':
        return render_template('final_scores.html', game_data=current_game, deadline=deadline)

    # Default fallback if no game state matches
    return render_template('game.html', game_data=current_game, deadline=deadline)

@app.route('/submit_question', methods=['POST'])
def submit_question():
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    question = request.json.get('question')  # Adjust to get JSON data

    if game_code in game_data:
        question_id = len(game_data[game_code]['questions'])
        game_data[game_code]['questions'].append({'author': player_name, 'question': question, 'id': question_id})

        # Assign exactly two players to respond: one as human, one as AI
        player_names = list(game_data[game_code]['players'].keys())
        player_index = player_names.index(player_name)  # Find the index of the current player

        # Calculate the index for the AI responder and human responder
        ai_responder_index = (player_index + 1) % len(player_names)
        human_responder_index = (player_index + 2) % len(player_names)

        # Assign players
        assigned_player_roles = {
            'ai': player_names[ai_responder_index],
            'human': player_names[human_responder_index]
        }

        # Update the game data with the assigned players
        game_data[game_code]['questions'][-1]['assigned_players'] = assigned_player_roles

        save_game_data(game_data)

        # Generate AI responses for the question
        truthful_prompt = """
        Your job is to generate answers for a 'reverse turing test' game. You will be asked a question and must answer as an AI assistant.
        A human will be answering the same question, attempting to imitate the style of an AI. You will win if the audience correctly guesses that your response is the AI response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.
        """

        deceptive_prompt = """
        Your job is to generate answers for a 'turing test' game. You will be asked a question and must answer as if you were human. Your response should be light, spontaneous, somewhat humorous, and specific to the life of some particular human.
        A human will be answering the same question, attempting to sound as human as possible. You will win if the audience guesses that your response is the human response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.
        """

        ai_ai_response = chat_completion(question, [{"role": "system", "content": truthful_prompt}])
        ai_human_response = chat_completion(question, [{"role": "system", "content": deceptive_prompt}])
        game_data = load_game_data()

        response_id = len(game_data[game_code]['responses']) + 1

        game_data[game_code]['responses'].append({
            'id': response_id,
            'author': "AI",
            'response': ai_ai_response,
            'type': "ai",
            'intended_author': "ai",
            'question_id': question_id
        })
        game_data[game_code]['responses'].append({
            'id': response_id + 1,  # Increment the ID for the next response
            'author': "AI",
            'response': ai_human_response,
            'type': "ai",
            'intended_author': "human",
            'question_id': question_id
        })
        save_game_data(game_data)

        # Check if all players have submitted questions
        if len(game_data[game_code]['questions']) == len(game_data[game_code]['players']):
            #game_data[game_code]['game_state'] = 'awaiting_responses'
            #set_game_state_timer(game_code, 'awaiting_responses', 60)  # Adjust timer duration as needed
            save_game_data(game_data)

            # Return success message
            return jsonify({'status': 'success'})
        else:
            # Return success if not all players have submitted their questions
            return jsonify({'status': 'success'})

    # If game_code does not exist, return an error
    return jsonify({'status': 'error', 'message': 'Invalid game code or player.'}), 400
"""
@app.route('/submit_question', methods=['POST'])
def submit_question():
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    question = request.form['question']

    if game_code in game_data:
        question_id = len(game_data[game_code]['questions'])
        game_data[game_code]['questions'].append({'author': player_name, 'question': question, 'id': question_id})

        # Assign exactly two players to respond: one as human, one as AI
        player_names = list(game_data[game_code]['players'].keys())
        player_names.remove(player_name)  # Remove the author of the question from selection

        # Randomly assign one player to respond as a human and one as an AI
        assigned_players = sample(player_names, 2)
        assigned_player_roles = {'human': assigned_players[0], 'ai': assigned_players[1]}

        game_data[game_code]['questions'][-1]['assigned_players'] = assigned_player_roles

        save_game_data(game_data)

        # Generate AI responses for the question
        truthful_prompt =
        Your job is to generate answers for a 'reverse turing test' game. You will be asked a question and must answer as an AI assistant.
        A human will be answering the same question, attempting to imitate the style of an AI. You will win if the audience correctly guesses that your response is the AI response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.


        deceptive_prompt =
        Your job is to generate answers for a 'turing test' game. You will be asked a question and must answer as if you were human. Your response should be light, spontaneous, somewhat humorous, and specific to the life of some particular human.
        A human will be answering the same question, attempting to sound as human as possible. You will win if the audience guesses that your response is the human response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.


        ai_ai_response = chat_completion(question, [{"role": "system", "content": truthful_prompt}])
        ai_human_response = chat_completion(question, [{"role": "system", "content": deceptive_prompt}])
        game_data = load_game_data()

        response_id = len(game_data[game_code]['responses']) + 1

        game_data[game_code]['responses'].append({
            'id': response_id,
            'author': "AI",
            'response': ai_ai_response,
            'type': "ai",
            'intended_author': "ai",
            'question_id': question_id
        })
        game_data[game_code]['responses'].append({
            'id': response_id + 1,  # Increment the ID for the next response
            'author': "AI",
            'response': ai_human_response,
            'type': "ai",
            'intended_author': "human",
            'question_id': question_id
        })
        save_game_data(game_data)

        # Check if all players have submitted questions
        if len(game_data[game_code]['questions']) == len(game_data[game_code]['players']):
            # Move to the next game state and set timer for responses
            game_data[game_code]['game_state'] = 'awaiting_responses'
            set_game_state_timer(game_code, 'awaiting_responses', 60)  # Adjust timer duration as needed
            save_game_data(game_data)

            # Redirect to the response submission page
            return redirect(url_for('await_responses', game_code=game_code, player=player_name))

    # If not all players have submitted their questions, redirect back to the waiting page
    return redirect(url_for('await_question', game_code=game_code, player=player_name))
"""

"""
@app.route('/submit_question', methods=['POST'])
def submit_question():
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    question = request.form['question']

    if game_code in game_data:
        question_id = len(game_data[game_code]['questions'])
        game_data[game_code]['questions'].append({'author': player_name, 'question': question, 'id': question_id})

        # Assign exactly two players to respond: one as human, one as AI
        player_names = list(game_data[game_code]['players'].keys())
        player_names.remove(player_name)  # Remove the author of the question from selection

        # Randomly assign one player to respond as a human and one as an AI
        assigned_players = sample(player_names, 2)
        assigned_player_roles = {'human': assigned_players[0], 'ai': assigned_players[1]}

        game_data[game_code]['questions'][-1]['assigned_players'] = assigned_player_roles

        save_game_data(game_data)

        # Generate AI responses for the question
        truthful_prompt =
        Your job is to generate answers for a 'reverse turing test' game. You will be asked a question and must answer as an AI assistant.
        A human will be answering the same question, attempting to imitate the style of an AI. You will win if the audience correctly guesses that your response is the AI response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.


        deceptive_prompt =
        Your job is to generate answers for a 'turing test' game. You will be asked a question and must answer as if you were human. Your response should be light, spontaneous, somewhat humorous, and specific to the life of some particular human"
        A human will be answering the same question, attempting to sound as human as possible. You will win if the audience guesses that your response is the human response.
        Your response should be about 10 words long. Reply with only the response, no explanatory text.


        ai_ai_response = chat_completion(question, [{"role": "system", "content": truthful_prompt}])
        ai_human_response = chat_completion(question, [{"role": "system", "content": deceptive_prompt}])
        game_data = load_game_data()

        response_id = len(game_data[game_code]['responses']) + 1

        game_data[game_code]['responses'].append({
            'id': response_id,
            'author': "AI",
            'response': ai_ai_response,
            'type': "ai",
            'intended_author': "ai",
            'question_id': question_id
        })
        game_data[game_code]['responses'].append({
            'id': response_id + 1,  # Increment the ID for the next response
            'author': "AI",
            'response': ai_human_response,
            'type': "ai",
            'intended_author': "human",
            'question_id': question_id
        })
        save_game_data(game_data)

        # Check if all players have submitted questions
        if len(game_data[game_code]['questions']) == len(game_data[game_code]['players']):
            # Move to the next game state
            set_game_state_timer(game_code, 'awaiting_responses', 60)  # Adjust timer duration as needed

    return redirect(url_for('game'))
"""
@app.route('/game_state_check')
def game_state_check():
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    game_data = load_game_data()
    current_game = game_data.get(game_code, {})

    # Get all deadlines from the game data
    deadlines = current_game.get('deadlines', {})

    # Get the current time in UTC
    current_time = datetime.now(timezone.utc)

    # Determine the correct route based on deadlines
    if 'submit_question' in deadlines:
        question_deadline = datetime.fromisoformat(deadlines['submit_question'])
        if current_time < question_deadline:
            return redirect(url_for('submit_question', game_code=game_code, player=player_name))

    if 'responses' in deadlines:
        response_deadline = datetime.fromisoformat(deadlines['responses'])
        if current_time < response_deadline:
            return redirect(url_for('responses', game_code=game_code, player=player_name))

    # Check for guessing deadlines
    for i in range(1, len(current_game['players']) + 1):
        guessing_key = f'guessing_{i}'
        if guessing_key in deadlines:
            guessing_deadline = datetime.fromisoformat(deadlines[guessing_key])
            if current_time < guessing_deadline:
                return redirect(url_for('guessing', game_code=game_code, player=player_name, question_index=i))

    # If all deadlines are past, assume we are at the final scores stage
    return redirect(url_for('final_scores', game_code=game_code, player=player_name))


@app.route('/check_number_of_players')
def check_number_of_players():
    print("running check_number of players")
    game_code = request.args.get('game_code')

    game_data = load_game_data()

    if not game_code or game_code not in game_data:
        return jsonify({'status': 'error', 'message': 'Game not found'})

    players = game_data[game_code]['players']

    player_names = [player['name'] for player in players.values()]
    number_of_players = len(game_data[game_code]['players'])
    return jsonify({'status': 'success', 'number_of_players': number_of_players, 'player_names': player_names})

@app.route('/fetch_game_data', methods=['GET'])
def fetch_game_data():
    game_code = request.args.get('game_code')

    # Load game data from wherever it's stored (e.g., file, database)
    game_data = load_game_data()

    if not game_code or game_code not in game_data:
        return jsonify({'status': 'error', 'message': 'Game not found'})

    # Return the relevant game data as JSON
    return jsonify({'status': 'success', 'game_data': game_data[game_code]})


@app.route('/check_game_state')
def check_game_state():
    game_code = request.args.get('game_code')
    game_data = load_game_data()

    # Check if the game exists
    if not game_code or game_code not in game_data:
        return jsonify({'status': 'error', 'message': 'Game not found'})

    # Get the current game state
    game_state = game_data[game_code].get('game_state', 'waiting_for_players')

    # Return the current game state
    return jsonify({'status': 'success', 'game_state': game_state})


@app.route('/submit_responses', methods=['POST'])
def submit_responses():
    game_data = load_game_data()

    # Expect JSON data, so parse the request body as JSON
    data = request.get_json()

    if not data or 'responses' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400

    responses = data['responses']

    if not responses:
        return jsonify({'status': 'error', 'message': 'No responses found in the request'}), 400

    # Validate game code and player name from the first response (assuming they're the same for all)
    game_code = responses[0].get('game_code')
    player_name = responses[0].get('player')

    if not game_code or game_code not in game_data:
        print("Invalid game code")
        return jsonify({'status': 'error', 'message': 'Invalid game code'}), 400

    if not player_name:
        print("Invalid player name")
        return jsonify({'status': 'error', 'message': 'Invalid player name'}), 400

    # Retrieve the questions assigned to the player
    assigned_questions = [
        q for q in game_data[game_code]['questions']
        if player_name in q['assigned_players'].values()
    ]

    # Save each response in the game data
    for response in responses:
        question_id = response.get('question_id')
        response_text = response.get('response')
        response_type = response.get('response_type')

        if question_id is None or response_text is None:
            continue  # Skip if any required data is missing

        response_id = len(game_data[game_code]['responses']) + 1

        # Determine if it's a human or AI response
        if response_type == 'human':
            game_data[game_code]['responses'].append({
                'id': response_id,
                'author': player_name,
                'response': response_text,
                'type': "human",
                'intended_author': "human",
                'question_id': question_id
            })
        elif response_type == 'ai':
            game_data[game_code]['responses'].append({
                'id': response_id,
                'author': player_name,
                'response': response_text,
                'type': "human",  # Human pretending to be AI
                'intended_author': "ai",
                'question_id': question_id
            })

    save_game_data(game_data)

    # Check if all players have submitted their responses
    human_responses_received = [r for r in game_data[game_code]['responses'] if r['type'] == "human"]
    if len(human_responses_received) == len(game_data[game_code]['players']) * 2:  # Each player submits two responses
        # Move to the guessing phase
        game_data[game_code]['game_state'] = 'guessing'
        set_game_state_timer(game_code, 'show_scores', 60)
        save_game_data(game_data)

    return jsonify({'status': 'success'})

@app.route('/submit_response', methods=['POST'])
def submit_response():
    #print("submit_response called")

    # Load game data
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    # Check if game_code and player_name are valid
    if not game_code or not player_name:
        print("Invalid game session")
        return "Invalid session, please try again.", 400

    # Retrieve form data with error handling
    try:
        response = request.form['response']
        #print(f"Response: {response}")
        response_type = request.form['response_type']
        intended_author = request.form['intended_author']
        question_id = int(request.form['question_id'])
    except KeyError as e:
        print(f"Missing form data: {e}")
        return "Missing form data", 400
    except ValueError as e:
        print(f"Invalid form data: {e}")
        return "Invalid form data", 400

    # Validate that game code exists
    if game_code in game_data:
        # Generate a unique ID for the new response
        response_id = len(game_data[game_code]['responses']) + 1

        # Save the new response to game data
        game_data[game_code]['responses'].append({
            'id': response_id,
            'author': player_name,
            'response': response,
            'type': response_type,
            'intended_author': intended_author,
            'question_id': question_id
        })
        save_game_data(game_data)
        print("Response saved successfully")
    else:
        print("Game code not found in game data")
        return "Game not found", 404

    # Check if all players have submitted their responses
    responses_received = [r for r in game_data[game_code]['responses']
                          if r['type'] == "human" and r['intended_author'] == intended_author]


    if len(responses_received) == len(game_data[game_code]['players']):
        # All players have submitted responses
        #if game_data[game_code]['game_state'] == 'awaiting_ai_response':
        game_data[game_code]['game_state'] = 'guessing'
        set_game_state_timer(game_code, 'show_scores', 60)  # Timer for guessing phase
        #else:
        #    game_data[game_code]['game_state'] = 'guessing'
        #    set_game_state_timer(game_code, 'show_scores', 60)  # Timer to show final scores
        save_game_data(game_data)

    return redirect(url_for('game'))


@app.route('/results')
def results():
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')

    if game_code not in game_data:
        return redirect(url_for('index'))

    # Calculate scores and display results
    return render_template('results.html', game_data=game_data[game_code])

"""
@app.route('/guessing')
def guessing():
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    question_index = request.args.get('question_index', type=int)

    game_data = load_game_data()

    # Validate the game code, player name, and question index
    if not game_code or game_code not in game_data:
        return redirect(url_for('index'))

    if player_name not in game_data[game_code]['players']:
        return "Player not found in this game.", 404

    if question_index is None or question_index >= len(game_data[game_code]['questions']):
        return "Invalid question index.", 404

    # Render the template for the guessing page
"""
"""
@app.route('/guess', methods=['POST'])
def guess():
    print("running guess")
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    guessed_responses = request.json.get('guesses', [])
    print(game_code)
    print(player_name)
    if game_code not in game_data or not player_name:
        return jsonify({'status': 'error', 'message': 'Game or player not found'})

    # Initialize scores if they do not exist
    if 'guessing_score' not in game_data[game_code]['players'][player_name]:
        game_data[game_code]['players'][player_name]['guessing_score'] = 0

    # Process guesses
    correct_count = 0
    for guess in guessed_responses:
        print(guess)
        response_id = guess['response_id']
        guessed_type = guess['guessed_type']
        guessed_intended_author = guess['guessed_intended_author']

        for response in game_data[game_code]['responses']:
            if response['id'] == response_id:
                #print("found response_id: " + str(response_id))
                # Check if the guessed type matches
                if response['type'] == guessed_type and response['intended_author'] == guessed_intended_author:
                    print("correctly guessed type: " + guessed_type)
                    correct_count += 1
                    game_data[game_code]['players'][player_name]['guessing_score'] += 1
                    print("New guessing score for " + player_name + " is " + str(game_data[game_code]['players'][player_name]['guessing_score']))

                # Check if the guessed intended author matches
                if response['intended_author'] == guessed_intended_author:
                    print("correctly got someone to guess intended author: " + guessed_intended_author)
                    question_index = response['question_id']
                    # Get the author's name from the question
                    author_name = response['author']
                    if author_name != "AI":
                        if 'writing_score' not in game_data[game_code]['players'][author_name]:
                            game_data[game_code]['players'][author_name]['writing_score'] = 0
                        game_data[game_code]['players'][author_name]['writing_score'] += 1
                        print("New writing score for " + author_name + " is " + str(game_data[game_code]['players'][author_name]['writing_score']))
                break

    save_game_data(game_data)

    return jsonify({'status': 'success', 'correct_count': correct_count})
"""

@app.route('/guess', methods=['POST'])
def guess():
    print("running guess")
    game_data = load_game_data()
    game_code = request.args.get('game_code')
    player_name = request.args.get('player')
    guessed_responses = request.json.get('guesses', [])
    print(game_code)
    print(player_name)
    if game_code not in game_data or not player_name:
        return jsonify({'status': 'error', 'message': 'Game or player not found'})

    # Initialize scores if they do not exist
    if 'guessing_score' not in game_data[game_code]['players'][player_name]:
        game_data[game_code]['players'][player_name]['guessing_score'] = 0

    # Store feedback for the client
    feedback = []
    correct_count = 0

    for guess in guessed_responses:
        print(guess)
        response_id = guess['response_id']
        guessed_type = guess['guessed_type']
        guessed_intended_author = guess['guessed_intended_author']

        for response in game_data[game_code]['responses']:
            if response['id'] == response_id:
                is_correct = False
                if response['type'] == guessed_type and response['intended_author'] == guessed_intended_author:
                    print("correctly guessed type: " + guessed_type)
                    correct_count += 1
                    game_data[game_code]['players'][player_name]['guessing_score'] += 1
                    is_correct = True

                feedback.append({
                    'response_id': response_id,
                    'is_correct': is_correct,
                    'correct_type': response['type'],
                    'correct_author': response['intended_author'],
                    'author': response['author']
                })

                # Writing score logic for authors
                if response['intended_author'] == guessed_intended_author:
                    question_index = response['question_id']
                    author_name = response['author']
                    if author_name != "AI":
                        if 'writing_score' not in game_data[game_code]['players'][author_name]:
                            game_data[game_code]['players'][author_name]['writing_score'] = 0
                        game_data[game_code]['players'][author_name]['writing_score'] += 1

                break

    save_game_data(game_data)

    return jsonify({'status': 'success', 'correct_count': correct_count, 'feedback': feedback})


if __name__ == '__main__':
    app.run()
