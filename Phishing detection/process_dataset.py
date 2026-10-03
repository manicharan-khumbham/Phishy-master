# process_dataset.py

import pandas as pd

# Load raw dataset
df = pd.read_csv('original_dataset.csv')  # Replace with your actual filename

# Combine subject + body as email text
df['email'] = df['subject'].fillna('') + ' ' + df['body'].fillna('')

# Feature Engineering
def extract_features(text, urls):
    url_count = len(str(urls).split()) if pd.notnull(urls) else 0
    suspicious_url_present = int(any(sub in str(urls).lower() for sub in ['bit.ly', 'tinyurl', 'http://']))
    urgent_word_present = int(any(word in str(text).lower() for word in ['urgent', 'verify', 'account', 'immediately']))
    return pd.Series([url_count, suspicious_url_present, urgent_word_present])

df[['url_count', 'suspicious_url_present', 'urgent_word_present']] = df.apply(
    lambda row: extract_features(row['email'], row['urls']),
    axis=1
)

# Keep necessary columns
processed_df = df[['email', 'label', 'url_count', 'suspicious_url_present', 'urgent_word_present']]

# Save processed dataset
processed_df.to_csv('emails_dataset.csv', index=False)

print("✅ Processed dataset saved as 'emails_dataset.csv'.")
