import streamlit as st

# Page ki setting
st.set_page_config(page_title="AI Voice Agent Control", page_icon="🎙️", layout="wide")

st.title("🎙️ AI Voice Agent Control Panel")
st.write("Ye hamara Streamlit Frontend (Microservice 1) hai. Yahan se hum apne AI agent ko instructions denge.")
st.markdown("---")

# RAG ke liye Data Upload Section
st.header("1. Knowledge Base (RAG)")
st.write("Apne AI ko 'padhane' ke liye company ke FAQs ya manual upload karein:")
uploaded_file = st.file_uploader("PDF ya Text file choose karein", type=['pdf', 'txt'])

if uploaded_file is not None:
    st.success(f"File '{uploaded_file.name}' upload ho gayi! (Isko hum baad mein vector database mein bhejenge)")

st.markdown("---")

# Agent Controls
st.header("2. Voice Agent Control")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Start Voice Agent", type="primary"):
        # Baad mein ye button hamare backend Python script ko on karega
        st.info("Background mein LiveKit Agent start ho raha hai... ⏳")
        
with col2:
    if st.button("🛑 Stop Agent"):
        st.warning("Agent ko stop kar diya gaya hai.")