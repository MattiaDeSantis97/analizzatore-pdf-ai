import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
from dotenv import load_dotenv
import asyncio
import edge_tts
import re
import io

# --- CONFIGURAZIONE ---
MODEL_ID = "gemini-2.5-flash"
load_dotenv()
st.set_page_config(page_title="PDF AI & Audio Neural", layout="wide")

api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Inserisci Google Gemini API Key", type="password")
    if not api_key:
        st.stop()

genai.configure(api_key=api_key)

# --- STATO TEMPORANEO (Necessario per i download) ---
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'temp_chat_result' not in st.session_state: # Buffer temporaneo per download chat
    st.session_state.temp_chat_result = None
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None

# --- FUNZIONI ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for page in reader.pages:
            content = page.extract_text()
            if content: text += content
    return text

def clean_text_for_audio(text):
    text = text.replace('\n', ' ')
    text = re.sub(r'[^\w\s\.,:;?!àèéìòùÀÈÉÌÒÙ\'\"]', '', text)
    text = re.sub(r'[\.,:;?!]{2,}', '.', text)
    return text.strip()

def analyze_with_gemini(text, prompt):
    try:
        model = genai.GenerativeModel(MODEL_ID)
        response = model.generate_content(f"{prompt}\n\n--- TESTO ---\n{text}")
        return response.text
    except Exception as e:
        return f"Errore: {e}"

# --- FUNZIONI AUDIO ---
def chunk_text(text, max_chars=2500):
    chunks = []
    current_chunk = ""
    for sentence in text.replace('.', '.|||').split('|||'):
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk: chunks.append(current_chunk)
    return chunks

async def _gen_audio_stream(text, voice, status):
    chunks = chunk_text(text)
    data = b""
    for i, ch in enumerate(chunks):
        if not ch.strip(): continue
        if status: status.text(f"Generazione audio... ({i+1}/{len(chunks)})")
        async for item in edge_tts.Communicate(ch, voice).stream():
            if item["type"] == "audio": data += item["data"]
    return data

def generate_audio(text, gender):
    clean = clean_text_for_audio(text)
    if not clean: return None
    clean = clean[:20000] # Limite sicurezza
    
    voice = "it-IT-DiegoNeural" if "Diego" in gender else "it-IT-ElsaNeural"
    status = st.empty()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        audio = loop.run_until_complete(_gen_audio_stream(clean, voice, status))
    except Exception as e:
        st.error(f"Errore audio: {e}")
        return None
    finally:
        loop.close()
        status.empty()
    return audio

# --- INTERFACCIA ---
st.title(f"📄 PDF AI Analyzer ({MODEL_ID})")

with st.sidebar:
    st.header("1. Upload")
    files = st.file_uploader("PDF", type=["pdf"], accept_multiple_files=True)
    st.divider()
    st.header("2. Audio")
    voice_opt = st.radio("Voce", ["Maschile (Diego)", "Femminile (Elsa)"])
    source_opt = st.radio("Sorgente Audio", ["Testo PDF", "Analisi AI"])

    if files:
        txt = get_pdf_text(files)
        if txt != st.session_state.pdf_text:
            st.session_state.pdf_text = txt
            # Reset dei buffer quando cambia il file
            st.session_state.analysis_result = None
            st.session_state.temp_chat_result = None 
            st.session_state.audio_file = None
            st.toast("PDF Caricato!")

if st.session_state.pdf_text:
    col1, col2 = st.columns(2)
    
    # --- SX: INTELLIGENZA ---
    with col1:
        st.subheader("🧠 Analisi")
        mode = st.selectbox("Tipo:", ["Sintesi", "Validazione", "Action Items", "Critica"])
        
        if st.button("Esegui Analisi", use_container_width=True):
            prompts = {"Sintesi": "Riassumi.", "Validazione": "Verifica fatti.", "Action Items": "Azioni.", "Critica": "Errori."}
            with st.spinner("Elaborazione..."):
                st.session_state.analysis_result = analyze_with_gemini(st.session_state.pdf_text, prompts[mode])

        if st.session_state.analysis_result:
            st.markdown(st.session_state.analysis_result)
            st.download_button("💾 Scarica Analisi", st.session_state.analysis_result, "analisi.md")

        st.divider()
        st.subheader("💬 Domanda Rapida")
        q = st.text_input("Chiedi qualcosa:")
        
        # Logica "Usa e Getta": il risultato vive solo finché non ne chiedi un altro
        if q and st.button("Rispondi"):
            with st.spinner("..."):
                st.session_state.temp_chat_result = analyze_with_gemini(st.session_state.pdf_text, q)
        
        # Mostra risultato e bottone solo se c'è qualcosa nel buffer
        if st.session_state.temp_chat_result:
            st.markdown(f"**Risposta:**\n{st.session_state.temp_chat_result}")
            st.download_button("⬇️ Scarica Risposta", st.session_state.temp_chat_result, "risposta_chat.md")

    # --- DX: AUDIO ---
    with col2:
        st.subheader("🔊 Audio")
        if st.button("Genera MP3", type="primary", use_container_width=True):
            src = st.session_state.pdf_text if source_opt == "Testo PDF" else st.session_state.analysis_result
            if src:
                with st.spinner("Creazione audio..."):
                    st.session_state.audio_file = generate_audio(src, voice_opt)
            else:
                st.error("Nessun testo da leggere.")

        if st.session_state.audio_file:
            st.audio(io.BytesIO(st.session_state.audio_file), format='audio/mpeg')
            st.download_button("⬇️ Scarica MP3", st.session_state.audio_file, "audio.mp3", "audio/mpeg")

else:
    st.info("Carica un PDF.")
