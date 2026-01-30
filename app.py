import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os
from dotenv import load_dotenv
from gtts import gTTS
from io import BytesIO
import re

# --- CONFIGURAZIONE ---
load_dotenv()
st.set_page_config(page_title="PDF AI & Audio", layout="wide")

api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Inserisci Google Gemini API Key", type="password")

if not api_key:
    st.warning("👈 Chiave API mancante.")
    st.stop()

genai.configure(api_key=api_key)

# --- MEMORIA (Session State) ---
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
    """
    Pulisce aggressivamente il testo per l'audio.
    Rimuove simboli speciali mantenendo solo la punteggiatura di pausa.
    """
    # 1. Unisce le righe spezzate
    text = text.replace('\n', ' ')
    
    # 2. Rimuove caratteri speciali che gTTS legge ad alta voce (asterischi, barre, parentesi quadre, ecc.)
    # Mantiene solo: lettere, numeri, spazi e punteggiatura base (. , : ; ? !)
    # I simboli speciali vengono sostituiti da uno spazio
    text = re.sub(r'[^\w\s\.,:;?!àèéìòùÀÈÉÌÒÙ\'\"]', ' ', text)
    
    # 3. Rimuove sequenze di punteggiatura (es. "....." o ".__.") che creano rumore
    text = re.sub(r'[\.,:;?!]{2,}', '.', text)
    
    # 4. Rimuove underscore e trattini che spesso vengono letti
    text = text.replace('_', ' ').replace('-', ' ')
    
    # 5. Rimuove spazi doppi creati dalle sostituzioni
    text = re.sub(' +', ' ', text)
    
    return text.strip()

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
        # Applica la pulizia profonda
        clean_text = clean_text_for_audio(text)
        
        if not clean_text.strip():
            st.error("Testo troppo breve o vuoto dopo la pulizia.")
            return None
            
        tts = gTTS(text=clean_text, lang='it')
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception as e:
        st.error(f"Errore generazione audio: {e}")
        return None

# --- INTERFACCIA ---
st.title("📄 PDF: Analisi AI + Audio Pulito")

with st.sidebar:
    st.header("1. Carica File")
    uploaded_file = st.file_uploader("Trascina qui il PDF", type=["pdf"], accept_multiple_files=True)
    st.divider()
    if uploaded_file:
        current_text = get_pdf_text(uploaded_file)
        if current_text != st.session_state.pdf_text:
            st.session_state.pdf_text = current_text
            st.session_state.analysis_result = None
            st.session_state.audio_bytes = None
            st.toast("Nuovo PDF caricato!", icon="✅")

if st.session_state.pdf_text:
    col1, col2 = st.columns(2)
    
    # ANALISI
    with col1:
        st.subheader("🧠 Analisi AI")
        logic = st.selectbox("Analisi:", ["Sintesi", "Validazione", "Action Items", "Critica"])
        if st.button("Analizza Testo", use_container_width=True):
            prompts = {
                "Sintesi": "Riassumi il contenuto.",
                "Validazione": "Verifica i fatti.",
                "Action Items": "Estrai azioni.",
                "Critica": "Trova errori."
            }
            with st.spinner("Analisi in corso..."):
                st.session_state.analysis_result = analyze_with_gemini(
                    st.session_state.pdf_text, prompts[logic], "gemini-pro"
                )

    # AUDIO
    with col2:
        st.subheader("🔊 Audio")
        st.info("Genera audio pulito (senza leggere simboli strani).")
        if st.button("Crea Audio MP3", type="primary", use_container_width=True):
            with st.spinner("Pulizia testo e conversione voce..."):
                st.session_state.audio_bytes = generate_audio(st.session_state.pdf_text)

    st.divider()
    
    if st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format='audio/mp3')
        st.download_button("⬇️ Scarica MP3", st.session_state.audio_bytes, "audio_pulito.mp3", "audio/mp3")
        
    if st.session_state.analysis_result:
        st.markdown("### Risultato:")
        st.markdown(st.session_state.analysis_result)
else:
    st.info("Carica un PDF.")
