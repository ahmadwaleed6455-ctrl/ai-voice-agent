import streamlit as st
import os
import shutil # Folder delete karne ke liye
from rag_utils import process_file_to_vdb

import torch.nn as nn
import builtins

# Ye 'nn' ko poori windows mein global bana dega taaki 
# libraries ko jahan 'nn' chahiye ho wo mil jaye
if not hasattr(builtins, "nn"):
    builtins.nn = nn
    
st.set_page_config(page_title="AI Agent Builder", layout="centered")

st.title("🤖 Generalized RAG Agent Builder")
st.subheader("Bina coding ke apna AI Agent tayar karein")

# --- Step 1: Agent ki Shakhsiyat ---
with st.expander("1. Agent Identity", expanded=True):
    agent_name = st.text_input("Agent ka naam?", "Mia")
    role = st.selectbox("Agent ka kaam kya hoga?", 
                        ["Order Taker", "Customer Support", "Information Desk", "Ward Clerk"])
    language = st.selectbox("Primary Language?", ["Urdu", "English", "Both (Mix)"])

# --- Step 2: Knowledge Base ---
with st.expander("2. Upload Knowledge Base"):
    uploaded_file = st.file_uploader("Upload PDF, TXT, or MD file", type=["pdf", "txt", "md"])

# --- Step 3: Build Agent ---
if st.button("Build & Deploy Agent"):
    if uploaded_file:
        with st.spinner("Processing file and building Vector Database (ChromaDB)..."):
            # File ko aarzi (temp) taur par save karna
            temp_path = uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # RAG Engine call karna (Vectors banenge)
            status = process_file_to_vdb(temp_path)
            os.remove(temp_path) # Temp file delete karna
            
            # Dynamic Instructions Tayar Karna (Notice the Tool instruction)
            dynamic_instructions = f"""
            You are {agent_name}, a professional {role} at the hospital. 
            Your primary language for responding is {language}.

            ABSOLUTE STRICT RULES:
            1. You have ZERO memory of doctor timings, availability, or hospital policies. 
            2. Keep your responses extremely concise. No introductory filler phrases. Max 2 short sentences.
            3. You MUST USE YOUR SEARCH TOOL to find answers regarding doctors or hospital data. NEVER answer from your own memory.
            4. NEVER guess, invent, or hallucinate schedules. If you haven't used the tool, you do not know the answer.
            5. If the user's audio is unclear (e.g. "Guest for doctor"), ask them to repeat the doctor's name clearly before searching.
            6. Speak smoothly and naturally. Do NOT speak out your function names, JSON, or coding syntax.
            7. If the search tool returns empty results, politely say "I couldn't find that specific information in the hospital records."
            """
            
            with open("current_agent_config.txt", "w", encoding="utf-8") as f:
                f.write(dynamic_instructions)
                
            st.success(f"✅ {agent_name} ka dimaagh aur Vector Database tayar hai!")
            st.info("Ab terminal mein 'python agent.py dev' chalayen.")
    else:
        st.error("Please upload a file first!")

# --- Step 4: Danger Zone (Delete Memory) ---
st.divider() # Ek line lagane ke liye
st.subheader("⚠️ Danger Zone")

if st.button("🗑️ Delete Agent Memory (Reset ChromaDB)"):
    chroma_path = "chroma_db"
    
    # Check karein ke folder mojood hai ya nahi
    if os.path.exists(chroma_path):
        # Folder aur uske andar ka sara data delete kar dega
        shutil.rmtree(chroma_path)
        st.error("🚨 Agent ki memory (ChromaDB) mukammal taur par delete ho chuki hai! Ab naya agent banayein.")
    else:
        st.info("Agent ki memory pehle hi khali hai.")