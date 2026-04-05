import os
from flask import Flask, request, jsonify, render_template
from groq import Groq
from firebase_admin import credentials, firestore, initialize_app
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# 1. Groq Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 2. Firebase Setup (JSON file Codespace mein upload karni hogi)
cred = credentials.Certificate("firebase_key.json")
initialize_app(cred)
db = firestore.client()

# Hospital Data
with open("hospital_data.txt", "r", encoding="utf-8") as f:
    hospital_info = f.read()

# --- WEB FRONTEND ROUTE ---
@app.route('/')
def index():
    return render_template('index.html')

# --- WEB CHAT API ---
@app.route('/chat', methods=['POST'])
def web_chat():
    data = request.json
    user_msg = data.get('message')
    user_id = data.get('user_id', 'anonymous')

    prompt = f"System: {hospital_info}\nUser: {user_msg}\nSara:"
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = completion.choices.message.content

    # Save to Firebase
    db.collection('chats').add({
        'user_id': user_id,
        'message': user_msg,
        'reply': reply,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'reply': reply})

# --- WHATSAPP ROUTE (Existing) ---
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    prompt = f"System: {hospital_info}\nUser: {incoming_msg}\nSara:"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    reply_text = completion.choices.message.content
    
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
