from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from pyrebase import pyrebase
import os
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'supersecretkey'

# Initialize Firebase Admin
cred = credentials.Certificate("shopperspy-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Pyrebase config for client-side operations
firebase_config = {
  "apiKey": "AIzaSyATlfn28N-zL2iW4v84zow3PRb-cPnQ3IM",
  "authDomain": "speak-ease-a221a.firebaseapp.com",
  "databaseURL": "https://speak-ease-a221a-default-rtdb.firebaseio.com",
  "projectId": "speak-ease-a221a",
  "storageBucket": "speak-ease-a221a.firebasestorage.app",
  "messagingSenderId": "814624711121",
  "appId": "1:814624711121:web:9ef1d07a10e121888dc0f0",
  "measurementId" : "G-VRG9W5GSP9"
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
        
        try:
            user = authenticate_user(email)
            print(f"Authenticated user: {user}")
            if not user:
                return render_template('login.html', error="User not found")
            
            # Store user in session
            session['user'] = {
                'id': user['id'],  # Using Firestore document ID
                'email': email,
                'name': user.get('name', email.split('@')[0])
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
    
    # Get all users except current user
    users_ref = db.collection('users')
    users = []
    for doc in users_ref.stream():
        user_data = doc.to_dict()
        if doc.id != session['user']['id']:
            users.append({
                'id': doc.id,
                'name': user_data.get('name', doc.id),
                'email': user_data.get('email', '')
            })
    
    return render_template('chat.html', user=session['user'], users=users)

@app.route('/get_messages/<recipient_id>')
def get_messages(recipient_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sender_id = session['user']['id']
    
    # Generate unique chat ID (sorted to ensure consistency)
    chat_id = '-'.join(sorted([sender_id, recipient_id]))
    
    # Get messages from Realtime Database
    messages = realtime_db.child("chats").child(chat_id).get().val()
    
    if not messages:
        return jsonify({'messages': []})
    
    # Convert messages dict to list and sort by timestamp
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
    
    # Generate unique chat ID
    chat_id = '-'.join(sorted([sender_id, recipient_id]))
    
    # Create message data
    message_data = {
        'sender_id': sender_id,
        'recipient_id': recipient_id,
        'message': message,
        'timestamp': firebase.database.ServerValue.TIMESTAMP,
        'read': False
    }
    
    # Push message to Realtime Database
    new_message_ref = realtime_db.child("chats").child(chat_id).push(message_data)
    
    return jsonify({'success': True, 'message_id': new_message_ref['name']})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)