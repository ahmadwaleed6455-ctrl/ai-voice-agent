import os
import json
import uuid
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, firestore
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from livekit import api
from google import genai
from google.genai import types

# --- 1. Environment & App Setup ---
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- 2. Security Setup (Rate Limiter) ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# --- 3. Gemini 3 Flash Setup ---
# Groq ki jagah ab Google ka AI dimagh lag gaya hai
ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- 4. Firebase Setup ---
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

def get_user_status(user_id):
    """Check user status from Firebase (Premium vs Free)"""
    try:
        user_ref = db.collection('users').document(user_id).get()
        if user_ref.exists:
            return user_ref.to_dict().get('status', 'free')
        return 'free'
    except:
        return 'free'

# --- 5. Hospital Data Read ---
try:
    with open("hospital_data.txt", "r", encoding="utf-8") as f:
        hospital_info = f.read()
except FileNotFoundError:
    hospital_info = "Hospital data not available."

# --- 🚀 ROUTES (Raste) ---

# Home Page (Frontend Render)
@app.route('/')
def index():
    return render_template('index.html')

# Voice Token for Avatar (With Call Limit logic)
@app.route('/get_voice_token')
@limiter.limit("5 per hour") # Free IPs ko din mein limited calls
def get_voice_token():
    user_id = request.args.get('user_id', 'anonymous')
    status = get_user_status(user_id)
    
    room_name = f"lrh-room-{uuid.uuid4().hex[:6]}" 
    participant_identity = f"user_{uuid.uuid4().hex[:4]}"
    
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    ).with_identity(participant_identity) \
     .with_grants(api.VideoGrants(room_join=True, room=room_name))
     
    return jsonify({
        "token": token.to_jwt(),
        "url": os.getenv("LIVEKIT_URL"),
        "status": status,
        "timeout": 60 if status == 'free' else 600 # 1 min for free, 10 min for premium
    })

# Web Chat API
@app.route('/chat', methods=['POST'])
@limiter.limit("20 per hour")
def web_chat():
    data = request.json
    user_msg = data.get('message')
    user_id = data.get('user_id', 'anonymous')

    prompt = f"""
    System: You are 'LRH Rahbar', a helpful AI assistant at Lady Reading Hospital. 
    Answer in Roman Urdu, Urdu, or Pashto based on user's language. 
    Use this data: {hospital_info}
    User: {user_msg}
    LRH Rahbar:"""
    
    # --- NAYI GEMINI 3 FLASH API CALL ---
    response = ai_client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    
    reply = response.text

    if fb_content:
        db.collection('chats').add({
            'user_id': user_id,
            'message': user_msg,
            'reply': reply,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

    return jsonify({'reply': reply})

# WhatsApp Route (Twilio)
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').lower()
    
    prompt = f"""
    System: You are 'LRH Rahbar', a helpful AI assistant at Lady Reading Hospital. 
    Answer in Roman Urdu, Urdu, or Pashto based on user's language. Keep answers brief for WhatsApp.
    Use this data: {hospital_info}
    User: {incoming_msg}
    LRH Rahbar:"""
    
    # --- NAYI GEMINI 3 FLASH API CALL ---
    response = ai_client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    
    reply_text = response.text
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

# --- 🏁 RUN APP ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)