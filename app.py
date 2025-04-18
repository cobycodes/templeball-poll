from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect, url_for
import json
import os

app = Flask(
    __name__,
    static_folder='static',      # This points to myproject/static/
    template_folder='templates'  # This points to myproject/templates/
)

# define the data directory relative to this file (root directory)
# this will be moved to config
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# define the player_poll and player_ratings files
# this will be moved to config
POLL_DATA_FILE = os.path.join(DATA_DIR, 'player_poll.json')
RATINGS_DATA_FILE = os.path.join(DATA_DIR, 'player_ratings.json')

# read and write to the poll data file
def read_poll_data():
    with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
def write_poll_data(data):
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# read and write to the ratings data file
def read_ratings_data():
    with open(RATINGS_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

#def write_ratings_data():
#    with open(RATINGS_DATA_FILE, 'w', encoding='utf-8') as f:
#        json.dump(data, f, indent=2)

@app.route('/')
def home():
    # Render templates/index.html
    return render_template('index.html')

@app.route('/data', methods=['GET'])
def get_data():
    # Return { "pollDate": "...", "people": [...] }
    data = read_poll_data()
    return jsonify(data)

@app.route('/people/<int:person_id>', methods=['PUT'])
def update_availability(person_id):
    data = read_poll_data()  # { pollDate, people }
    people = data['people']

    # find the matching person
    person = next((p for p in people if p['id'] == person_id), None)
    if not person:
        return jsonify({'error': 'Person not found'}), 404

    # get new availability from JSON body
    new_availability = request.json.get('availability')
    person['availability'] = new_availability

    # store lastAvailable timestamp if "available"
    if new_availability == "available":
        from datetime import datetime
        person['lastAvailable'] = datetime.now().isoformat()

    write_poll_data(data)
    return jsonify(person)

@app.route('/admin')
def admin_page():
    data = read_poll_data()  # This loads your poll data (for poll results)
    poll_date = data.get("pollDate", "N/A")
    available_lines = []
    for person in data.get("people", []):
        if person.get("availability") == "available":
            name = person.get("name", "Unknown")
            in_time = person.get("inTime", "N/A")
            available_lines.append(f"{name} (InTime: {in_time})")
    available_string = "\n".join(available_lines)
    
    # NEW: Read player ratings JSON file
    player_ratings_data = read_ratings_data()
    return render_template("admin.html", 
                           poll_date=poll_date,
                           available_string=available_string,
                           player_ratings=player_ratings_data)

@app.route('/admin/ratings')
def admin_ratings_list():
    # Read player ratings JSON (assumed to have a "people" key)
    ratings_data = read_ratings_data()  
    # Pass the entire ratings data (as a dict) to the new template.
    return render_template("admin_ratings_list.html", ratings=ratings_data)

@app.route('/admin/ratings/<int:player_id>')
def admin_player(player_id):
    ratings_data = read_ratings_data()
    # Find the player matching player_id in the "people" array.
    player = next((p for p in ratings_data.get("people", []) if p.get("id") == player_id), None)
    if not player:
        return "Player not found", 404
    return render_template("admin_player.html", player=player)

@app.route('/admin/ratings/<int:player_id>', methods=['PUT'])
def update_player_ratings(player_id):
    ratings_data = read_ratings_data()  # load ratings from RATINGS_DATA_FILE
    players = ratings_data.get("people", [])
    player = next((p for p in players if p.get("id") == player_id), None)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    update_data = request.json  # this is the dictionary sent from our form
    
    # For each key in the update data, update the player's record.
    # Here we assume a shallow merge for top-level keys and one level of nesting.
    for key, value in update_data.items():
        if isinstance(value, dict):
            if key not in player:
                player[key] = {}
            for sub_key, sub_value in value.items():
                player[key][sub_key] = sub_value
        else:
            player[key] = value
    
    # Write back the updated ratings file.
    with open(RATINGS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(ratings_data, f, indent=2)
    
    return jsonify(player)

@app.route('/admin/ratings/add', methods=['GET'])
def admin_add_player_form():
    # Render the form template we just created
    return render_template('admin_add_player.html')

@app.route('/admin/ratings', methods=['POST'])
def admin_add_player():
    # Read existing ratings
    data = read_ratings_data()
    players = data.setdefault('people', [])
    
    # Determine new ID
    max_id = max((p.get('id', 0) for p in players), default=0)
    new_id = max_id + 1

    # Build the new player dict from form data
    form = request.form.to_dict(flat=True)
    new_player = {'id': new_id}

    # Helper to nest keys on dots
    for full_key, value in form.items():
        category, field = full_key.split('.', 1)
        new_player.setdefault(category, {})[field] = (int(value) 
            if value.isdigit() else value)

    # Append and save
    players.append(new_player)
    with open(RATINGS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    # Redirect back to the list
    return redirect(url_for('admin_ratings_list'))

if __name__ == '__main__':
    # Start the Flask dev server
    # By default it listens on http://0.0.0.0:3001
    app.run(host='0.0.0.0', debug=True, port=3001)
