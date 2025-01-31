import os
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("shopperspy-key.json")
    
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    print("Firebase already initialized")

db = firestore.client()

data = {
    'name': 'VJ',
    'desc': 'This is a test description'
}

doc_ref = db.collection('home').document('test1')
doc = doc_ref.get()

if doc.exists:
    print("Data added to Firestore, Document ID: ", doc.to_dict())
else:
    print("No such document")