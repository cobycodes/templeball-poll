from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
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
    # Convert to a pretty JSON string for display
    import json
    player_ratings_string = json.dumps(player_ratings_data, indent=2)
    
    return render_template("admin.html", 
                           poll_date=poll_date,
                           available_string=available_string,
                           player_ratings=player_ratings_string)


if __name__ == '__main__':
    # Start the Flask dev server
    # By default it listens on http://0.0.0.0:3001
    app.run(host='0.0.0.0', debug=True, port=3001)
