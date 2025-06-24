from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from pyrebase import pyrebase
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'supersecretkey'

# Initialize Firebase Admin
cred = credentials.Certificate("shopperspy-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Pyrebase config
firebase_config = {
    "apiKey": "AIzaSyATlfn28N-zL2iW4v84zow3PRb-cPnQ3IM",
    "authDomain": "speak-ease-a221a.firebaseapp.com",
    "databaseURL": "https://speak-ease-a221a-default-rtdb.firebaseio.com",
    "projectId": "speak-ease-a221a",
    "storageBucket": "speak-ease-a221a.firebasestorage.app",
    "messagingSenderId": "814624711121",
    "appId": "1:814624711121:web:9ef1d07a10e121888dc0f0",
    "measurementId": "G-VRG9W5GSP9"
}

firebase = pyrebase.initialize_app(firebase_config)
auth_client = firebase.auth()
realtime_db = firebase.database()

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            user_data = authenticate_user(email)
            
            session['user'] = {
                'id': user_data['id'],
                'email': email,
                'name': user_data.get('name', email.split('@')[0])
            }
            
            return redirect(url_for('chat'))
            
        except Exception as e:
            return render_template('login.html', error=str(e))
    
    return render_template('login.html')

def authenticate_user(email):
    users_ref = db.collection('users')
    users = list(users_ref.stream())  # Convert to list to reuse

    for user in users:
        user_data = user.to_dict()
        print(f"User ID: {user.id}")
        print(f"Checking user: {user_data.get('email', 'No email')}")
        
        if user_data.get('email') == email:
            # Return both the document ID and user data
            return {
                'id': user.id,
                **user_data
            }

    return None

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user']['id']
    current_user_doc = db.collection('users').document(current_user_id).get()
    current_user_data = current_user_doc.to_dict()

    user_learning_languages = set(current_user_data.get('learn_languages', []))
    tutor_languages = set(current_user_data.get('tutor', []))
    user_tutor_languages = set(current_user_data.get('tutor', []))

    users = []
    added_user_ids = set()

    all_users = db.collection('users').stream()

    for doc in all_users:
        user_id = doc.id
        if user_id == current_user_id:
            continue

        user_data = doc.to_dict()
        name = user_data.get('name', user_id)

        # Case 1: Current user is a student (has learn_languages)
        other_tutor_languages = set(user_data.get('tutor', []))
        matched_as_student = user_learning_languages & other_tutor_languages

        if matched_as_student and user_id not in added_user_ids:
            description = format_language_description(matched_as_student, role="Tutor")
            users.append({
                'id': user_id,
                'name': name,
                'description': description
            })
            added_user_ids.add(user_id)
            continue  # If matched already, don't double check below

        # Case 2: Current user is a tutor (has tutor)
        other_learn_languages = set(user_data.get('learn_languages', []))
        matched_as_tutor = user_tutor_languages & other_learn_languages

        if matched_as_tutor and user_id not in added_user_ids:
            description = format_language_description(matched_as_tutor, role="Student")
            users.append({
                'id': user_id,
                'name': name,
                'description': description
            })
            added_user_ids.add(user_id)

    # Forums user is part of
    forums = []
    forum_lang = tutor_languages.union(user_learning_languages)
    for lang in forum_lang:
        forum_doc = db.collection('forums').document(lang).get()
        if forum_doc.exists:
            forum_data = forum_doc.to_dict()
            if session['user']['email'] in forum_data.get('peoples', []):
                forums.append({
                    'id': lang,
                    'name': forum_data.get('name', lang),
                    'description': forum_data.get('description', '')
                })

    return render_template('chat.html',
                           user=session['user'],
                           users=users,
                           forums=forums,
                           firebase_config=firebase_config)


def format_language_description(languages, role):
    langs = [lang.capitalize() for lang in languages]
    if len(langs) == 1:
        return f"{langs[0]} {role}"
    else:
        return f"{' and '.join(langs)} {role}"


@app.route('/get_messages/<recipient_id>')
def get_messages(recipient_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sender_id = session['user']['id']
    chat_id = '-'.join(sorted([sender_id, recipient_id]))
    
    messages = realtime_db.child("chats").child(chat_id).get().val()
    
    if not messages:
        return jsonify({'messages': []})
    
    messages_list = [msg for msg in messages.values()]
    messages_list.sort(key=lambda x: x['timestamp'])
    
    return jsonify({'messages': messages_list})

@app.route('/get_forum_messages/<forum_id>')
def get_forum_messages(forum_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    messages = realtime_db.child("forums").child(forum_id).get().val()
    
    if not messages:
        return jsonify({'messages': []})
    
    messages_list = [msg for msg in messages.values()]
    messages_list.sort(key=lambda x: x['timestamp'])
    
    return jsonify({'messages': messages_list})

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    recipient_id = data['recipient_id']
    message = data['message']
    sender_id = session['user']['id']
    
    chat_id = '-'.join(sorted([sender_id, recipient_id]))
    
    message_data = {
        'sender_id': sender_id,
        'sender_name': session['user']['name'],
        'recipient_id': recipient_id,
        'message': message,
        'timestamp': int(time.time() * 1000),
        'read': False
    }
    
    new_message_ref = realtime_db.child("chats").child(chat_id).push(message_data)
    return jsonify({'success': True, 'message_id': new_message_ref['name']})

@app.route('/send_forum_message', methods=['POST'])
def send_forum_message():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    forum_id = data['forum_id']
    message = data['message']
    
    message_data = {
        'sender_id': session['user']['id'],
        'sender_name': session['user']['name'],
        'message': message,
        'timestamp': int(time.time() * 1000)
    }
    
    new_message_ref = realtime_db.child("forums").child(forum_id).push(message_data)
    return jsonify({'success': True, 'message_id': new_message_ref['name']})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)