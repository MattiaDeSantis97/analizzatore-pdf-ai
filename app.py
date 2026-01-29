import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
from dotenv import load_dotenv
from gtts import gTTS
from io import BytesIO
import re

# --- CONFIGURAZIONE INIZIALE ---
load_dotenv()
st.set_page_config(page_title="PDF AI & Audio", layout="wide")

# Gestione API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Inserisci Google Gemini API Key", type="password")

if not api_key:
    st.warning("👈 Inserisci la tua API Key nella barra laterale per iniziare.")
    st.stop()

genai.configure(api_key=api_key)

# --- INIZIALIZZAZIONE SESSION STATE (MEMORIA) ---
# Serve per non far sparire i risultati quando clicchi i pulsanti
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'audio_bytes' not in st.session_state:
    st.session_state.audio_bytes = None

# --- FUNZIONI ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                text += content
    return text

def clean_text_for_audio(text):
    """Pulisce il testo per evitare pause robotiche."""
    # Sostituisce i ritorni a capo con spazi
    text = text.replace('\n', ' ')
    # Rimuove spazi doppi
    text = re.sub(' +', ' ', text)
    # Rimuove caratteri speciali che la voce non legge bene
    text = text.replace('*', '').replace('#', '')
    return text

def analyze_with_gemini(text, prompt_logic, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        full_prompt = f"{prompt_logic}\n\n--- TESTO PDF ---\n{text}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Errore: {e}"

def generate_audio(text):
    try:
        clean_text = clean_text_for_audio(text)
        if not clean_text.strip():
            return None
        # Genera audio
        tts = gTTS(text=clean_text, lang='it')
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception as e:
        st.error(f"Errore generazione audio: {e}")
        return None

# --- INTERFACCIA ---
st.title("📄 PDF: Analisi AI + Creazione Audio")

# 1. UPLOAD
with st.sidebar:
    st.header("1. Carica File")
    uploaded_file = st.file_uploader("Trascina qui il PDF", type=["pdf"], accept_multiple_files=True)
    
    st.divider()
    
    # Reset memoria se cambia il file
    if uploaded_file:
        current_text = get_pdf_text(uploaded_file)
        if current_text != st.session_state.pdf_text:
            st.session_state.pdf_text = current_text
            st.session_state.analysis_result = None
            st.session_state.audio_bytes = None
            st.toast("Nuovo PDF caricato!", icon="✅")

# 2. PANNELLO DI CONTROLLO
if st.session_state.pdf_text:
    
    col1, col2 = st.columns(2)
    
    # COLONNA 1: ANALISI GEMINI
    with col1:
        st.subheader("🧠 Analisi AI")
        logic_option = st.selectbox(
            "Tipo di Analisi:",
            ["Sintesi Esecutiva", "Validazione Fattuale", "Action Items", "Analisi Critica"]
        )
        
        if st.button("Analizza con Gemini", use_container_width=True):
            with st.spinner("Gemini sta analizzando..."):
                prompt_dict = {
                    "Sintesi Esecutiva": "Fai un riassunto strutturato.",
                    "Validazione Fattuale": "Verifica i dati nel testo.",
                    "Action Items": "Estrai lista azioni da fare.",
                    "Analisi Critica": "Trova punti deboli."
                }
                st.session_state.analysis_result = analyze_with_gemini(
                    st.session_state.pdf_text, 
                    prompt_dict[logic_option], 
                    "gemini-pro"
                )

    # COLONNA 2: CREAZIONE AUDIO
    with col2:
        st.subheader("🔊 Creazione Audio")
        st.info("Crea un file MP3 leggendo il testo originale del PDF.")
        
        # PULSANTE DEDICATO PER L'AUDIO
        if st.button("Crea File Audio", type="primary", use_container_width=True):
            with st.spinner("Conversione testo in voce..."):
                st.session_state.audio_bytes = generate_audio(st.session_state.pdf_text)

    st.divider()

    # 3. AREA RISULTATI (Visualizza se presenti in memoria)
    
    # Risultato Audio
    if st.session_state.audio_bytes:
        st.success("File Audio Generato!")
        st.audio(st.session_state.audio_bytes, format='audio/mp3')
        st.download_button(
            label="⬇️ Scarica MP3",
            data=st.session_state.audio_bytes,
            file_name="lettura_pdf.mp3",
            mime="audio/mp3"
        )
    
    # Risultato Analisi
    if st.session_state.analysis_result:
        st.markdown("### Risultato Analisi:")
        st.markdown(st.session_state.analysis_result)

else:
    st.info("Carica un PDF nella barra laterale per attivare i comandi.")