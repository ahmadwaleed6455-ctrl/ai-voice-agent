import os
import json
import uuid
from flask import Flask, request, jsonify, render_template
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from livekit import api

# 1. Environment aur App Setup (Ye hamesha routes se upar hoga)
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# 2. Groq Setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 3. Firebase Setup
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
    print("⚠️ Error: FIREBASE_SERVICE_ACCOUNT not found!")

# 4. Hospital Data Read
try:
    with open("hospital_data.txt", "r", encoding="utf-8") as f:
        hospital_info = f.read()
except FileNotFoundError:
    hospital_info = "Hospital data not available."

# --- 🚀 ROUTES (Raste) ---

# Home Page (404 Error khatam karne ke liye)
@app.route('/')
def index():
    return render_template('index.html')

# Voice Token (Mike connect karne ke liye)
@app.route('/get_voice_token')
def get_voice_token():
    room_name = "lrh_voice_room"
    participant_identity = f"patient_{uuid.uuid4().hex[:6]}"
    
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    ).with_identity(participant_identity) \
     .with_grants(api.VideoGrants(room_join=True, room=room_name))
     
    return jsonify({
        "token": token.to_jwt(),
        "url": os.getenv("LIVEKIT_URL")
    })

# Web Chat API
@app.route('/chat', methods=['POST'])
def web_chat():
    data = request.json
    user_msg = data.get('message')
    user_id = data.get('user_id', 'anonymous')

    prompt = f"System: You are Fahad, an AI assistant at Lady Reading Hospital (LRH). STRICTLY answer in Roman Urdu or Urdu. Use this data: {hospital_info}\nUser: {user_msg}\nSara:"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    reply = completion.choices[0].message.content

    if fb_content:
        db.collection('chats').add({
            'user_id': user_id,
            'message': user_msg,
            'reply': reply,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    return jsonify({'reply': reply})

# WhatsApp Route
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    prompt = f"System: {hospital_info}\nUser: {incoming_msg}\nSara:"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    
    reply_text = completion.choices[0].message.content
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

# --- 🏁 RUN APP ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)