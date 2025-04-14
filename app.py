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
def read_data():
    with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def write_data(data):
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def home():
    # Render templates/index.html
    return render_template('index.html')

@app.route('/data', methods=['GET'])
def get_data():
    # Return { "pollDate": "...", "people": [...] }
    data = read_data()
    return jsonify(data)

@app.route('/people/<int:person_id>', methods=['PUT'])
def update_availability(person_id):
    data = read_data()  # { pollDate, people }
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

    write_data(data)
    return jsonify(person)

@app.route("/admin")
def admin_page():
    data = read_data()  # read_data() loads your data.json
    poll_date = data.get("pollDate", "N/A")

    # Build a list of "Name (lastAvailable: ...)" lines for users who are "available"
    available_lines = []
    for person in data["people"]:
        if person.get("availability") == "available":
            name = person.get("name", "Unknown")
            last_available = person.get("lastAvailable", "N/A") 
            available_lines.append(f"{name} (Vote Time: {last_available})")

    # Convert that list into a single string with newlines
    available_string = "\n".join(available_lines)

    # render admin.html
    return render_template("admin.html",
                           poll_date=poll_date,
                           available_string=available_string)

if __name__ == '__main__':
    # Start the Flask dev server
    # By default it listens on http://0.0.0.0:3001
    app.run(host='0.0.0.0', debug=True, port=3001)
