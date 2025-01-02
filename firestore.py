import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("shopperspy-key.json")

try:
    firebase_admin.initialize_app(cred)
except ValueError:
    print("Firebase already initialized")

db = firestore.client()

def get_name():
    doc_ref = db.collection('home').document('test')
    doc = doc_ref.get()

    # Check if document exists and get the name field
    if doc.exists:
        data = doc.to_dict()
        name = data.get('name', 'Guest') 
    else:
        name = 'Guest'
    return name
