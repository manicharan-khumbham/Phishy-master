# training.py

import pandas as pd
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier
import numpy as np
import os

# Load dataset
df = pd.read_csv('emails_dataset.csv')
emails = df['email'].tolist()
labels = df['label'].tolist()

# Sentence embeddings
embedder = SentenceTransformer('all-MiniLM-L6-v2')
email_embeddings = embedder.encode(emails)

# Structured features
structured_features = df[['url_count', 'suspicious_url_present', 'urgent_word_present']].values

# Combine embeddings + structured features
X = np.hstack([email_embeddings, structured_features])
y = np.array(labels)

# Train XGBoost
classifier = XGBClassifier()
classifier.fit(X, y)

# Save model
os.makedirs('model', exist_ok=True)
classifier.save_model('model/xgb_model.json')
print("✅ Model trained and saved to 'model/xgb_model.json'.")
