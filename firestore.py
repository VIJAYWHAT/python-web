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

doc_ref = db.collection('home')
docs = doc_ref.stream()

for doc in docs:
    print("Document ID: ", doc.id)

doc_id = input("Enter the document ID: ")

doc = doc_ref.document(doc_id)

d = doc.get().to_dict()
print(d)
