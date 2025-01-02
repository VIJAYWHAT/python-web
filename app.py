from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, firestore
import firestore

# Initialize Flask
app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/')
def home():
    
    name = firestore.get_name()
    return render_template('home.html', name=name)

if __name__ == '__main__':
    app.run(debug=True)
