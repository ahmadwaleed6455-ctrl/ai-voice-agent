import os
import json
from flask import Flask, request, jsonify, render_template
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# 1. Groq Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 2. Firebase Security Setup
fb_content = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if fb_content:
    try:
        fb_dict = json.loads(fb_content)
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Connected Successfully!")
    except Exception as e:
        print(f"❌ Firebase Error: {e}")
else:
    print("⚠️ Error: FIREBASE_SERVICE_ACCOUNT not found in Render env!")

# Hospital Data Read
with open("hospital_data.txt", "r", encoding="utf-8") as f:
    hospital_info = f.read()

# --- WEB CHAT API ---
@app.route('/chat', methods=['POST'])
def web_chat():
    data = request.json
    user_msg = data.get('message')
    user_id = data.get('user_id', 'anonymous')

    # Strict Prompt taake Korean ya koi aur zaban na bole
    prompt = f"System: You are Sara, an AI assistant at Lady Reading Hospital (LRH). STRICTLY answer in Roman Urdu or Urdu. DO NOT use Korean, Chinese, or any other language. Use this data: {hospital_info}\nUser: {user_msg}\nSara:"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2  # Temperature kam karne se AI focus mein rehta hai
    )
    
    # YAHAN LAZMI HAI
    reply = completion.choices[0].message.content

    # Save to Firebase
    if fb_content:
        db.collection('chats').add({
            'user_id': user_id,
            'message': user_msg,
            'reply': reply,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    return jsonify({'reply': reply})
    
# --- WHATSAPP ROUTE ---
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    prompt = f"System: {hospital_info}\nUser: {incoming_msg}\nSara:"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    
      # Correct response extraction
    reply_text = completion.choices[0].message.content
    
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
