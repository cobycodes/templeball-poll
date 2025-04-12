from flask import Flask, request, jsonify, render_template
import json
import os

app = Flask(
    __name__,
    static_folder='static',      # This points to myproject/static/
    template_folder='templates'  # This points to myproject/templates/
)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

def read_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
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

    # Example: store lastAvailable timestamp if "available"
    # (uncomment if you want that feature)
    # if new_availability == "available":
    #     from datetime import datetime
    #     person['lastAvailable'] = datetime.now().isoformat()

    write_data(data)
    return jsonify(person)

if __name__ == '__main__':
    # Start the Flask dev server
    # By default it listens on http://127.0.0.1:5000
    app.run(host='0.0.0.0', debug=True, port=3001)
