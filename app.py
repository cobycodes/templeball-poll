import os
import json
from functools import wraps
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import (
    Flask, request, jsonify, render_template,
    session, redirect, url_for, flash
)

load_dotenv()  # loads SECRET_KEY and other vars from .env

app = Flask(
    __name__,
    static_folder='static',      # points to myproject/static/
    template_folder='templates'  # points to myproject/templates/
)
app.secret_key = os.urandom(24)

# Session timeout: 10 minutes of inactivity
app.permanent_session_lifetime = timedelta(minutes=10)

# Data file paths
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
POLL_DATA_FILE    = os.path.join(DATA_DIR, 'player_poll.json')
RATINGS_DATA_FILE = os.path.join(DATA_DIR, 'player_ratings.json')

# Read/write helpers
def read_poll_data():
    with open(POLL_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_poll_data(data):
    with open(POLL_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def read_ratings_data():
    with open(RATINGS_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_ratings_data(data):
    with open(RATINGS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# Refresh session on each request to reset timeout
@app.before_request
def refresh_session():
    session.permanent = True
    session.modified = True

# Auth decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_type') != 'admin':
            flash("Admin access required", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# Login / Logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        data = read_ratings_data()
        user = None

        # dynamic username: first initial + last name
        for p in data.get('people', []):
            fn = p['playerInfo']['firstName']
            ln = p['playerInfo']['lastName']
            dyn_user = (fn[0] + ln).lower()
            if dyn_user == username and p.get('password') == password:
                user = p
                break

        if user:
            session['user_id']   = user['id']
            session['user_type'] = user['userType']
            session.permanent = True
            flash(f"Welcome, {username}!", "success")
            return redirect(request.args.get('next') or url_for('index'))

        flash("Invalid credentials", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# Voting pages (requires login)
@app.route('/')
@login_required
def index():
    # Read poll data as before
    # But also read the ratings data for the current user’s profile
    ratings = read_ratings_data()
    user_id   = session['user_id']
    user_type = session['user_type']

    # Find the player record for this user
    current_player = next(
        (p for p in ratings.get('people', []) if p['id'] == user_id),
        None
    )

    return render_template(
        'index.html',
        current_user_id=user_id,
        current_user_type=user_type,
        current_player=current_player
    )

@app.route('/data', methods=['GET'])
@login_required
def get_data():
    return jsonify(read_poll_data())

@app.route('/people/<int:person_id>', methods=['PUT'])
@login_required
def update_availability(person_id):
    data = read_poll_data()
    people = data.get('people', [])
    person = next((p for p in people if p['id'] == person_id), None)
    if not person:
        return jsonify({'error': 'Person not found'}), 404

    new_availability = request.json.get('availability')
    person['availability'] = new_availability
    if new_availability == "available":
        person['lastAvailable'] = datetime.now().isoformat()

    write_poll_data(data)
    return jsonify(person)

# Admin pages (requires admin)
@app.route('/admin')
@login_required
@admin_required
def admin_page():
    data = read_poll_data()
    poll_date = data.get("pollDate", "N/A")
    available_lines = []
    for person in data.get("people", []):
        if person.get("availability") == "available":
            name = person.get("name", "Unknown")
            in_time = person.get("inTime", person.get("lastAvailable", "N/A"))
            available_lines.append(f"{name} (InTime: {in_time})")
    available_string = "\n".join(available_lines)

    player_ratings = read_ratings_data()
    return render_template(
        'admin.html',
        poll_date=poll_date,
        available_string=available_string,
        player_ratings=player_ratings
    )

@app.route('/admin/ratings')
@login_required
@admin_required
def admin_ratings_list():
    ratings = read_ratings_data()
    return render_template('admin_ratings_list.html', ratings=ratings)

@app.route('/admin/ratings/add', methods=['GET'])
@login_required
@admin_required
def admin_add_player_form():
    return render_template('admin_add_player.html')

@app.route('/admin/ratings', methods=['POST'])
@login_required
@admin_required
def admin_add_player():
    data = read_ratings_data()
    players = data.setdefault('people', [])
    max_id = max((p.get('id', 0) for p in players), default=0)
    new_id = max_id + 1

    form = request.form.to_dict(flat=True)
    new_player = {'id': new_id}
    for full_key, val in form.items():
        cat, fld = full_key.split('.', 1)
        new_player.setdefault(cat, {})[fld] = val

    new_player['userType'] = form.get('userType', 'user')
    new_player['password'] = form.get('password', '')
    players.append(new_player)

    write_ratings_data(data)
    return redirect(url_for('admin_ratings_list'))

@app.route('/admin/ratings/<int:player_id>')
@login_required
@admin_required
def admin_player(player_id):
    data = read_ratings_data()
    player = next((p for p in data.get('people', []) if p.get('id') == player_id), None)
    if not player:
        return "Player not found", 404
    return render_template('admin_player.html', player=player)

@app.route('/admin/ratings/<int:player_id>', methods=['PUT'])
@login_required
@admin_required
def update_player_ratings(player_id):
    data = read_ratings_data()
    players = data.get('people', [])
    player = next((p for p in players if p.get('id') == player_id), None)
    if not player:
        return jsonify({"error": "Player not found"}), 404

    update_data = request.json
    for key, val in update_data.items():
        if isinstance(val, dict):
            player.setdefault(key, {}).update(val)
        else:
            player[key] = val

    write_ratings_data(data)
    return jsonify(player)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)
