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
load_dotenv()
st.set_page_config(page_title="PDF AI & Audio Neural", layout="wide")

api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Inserisci Google Gemini API Key", type="password")

if not api_key:
    st.warning("👈 Chiave API mancante.")
    st.stop()

genai.configure(api_key=api_key)

# --- MEMORIA ---
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None

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
    """Pulizia avanzata per voce naturale."""
    text = text.replace('\n', ' ')
    
    # Rimuove simboli lista nera (cerchi, quadrati, frecce)
    bad_chars = ['○', '◦', '•', '●', '▪', '■', '□', '➢', '➣', '➤', '->', '★', '☆', '—', '–', '|', '/', '\\']
    for char in bad_chars:
        text = text.replace(char, '')

    # Rimuove tutto tranne lettere, numeri e punteggiatura
    text = re.sub(r'[^\w\s\.,:;?!àèéìòùÀÈÉÌÒÙ\'\"]', '', text)
    # Rimuove puntini di sospensione lunghi
    text = re.sub(r'[\.,:;?!]{2,}', '.', text)
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

# Funzione Asincrona per Edge-TTS
async def _generate_audio_stream(text, voice_code):
    communicate = edge_tts.Communicate(text, voice_code)
    audio_data = b""
    # Raccoglie i chunk audio man mano che arrivano
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def generate_audio(text, voice_gender):
    try:
        # 1. Pulizia
        clean_text = clean_text_for_audio(text)
        if not clean_text.strip():
            st.warning("Nessun testo valido per l'audio.")
            return None
        
        # 2. Safety Check Lunghezza
        if len(clean_text) > 4000:
            st.warning(f"Testo troppo lungo ({len(clean_text)} caratteri). Verranno letti solo i primi 4000.")
            clean_text = clean_text[:4000]

        # 3. Selezione Voce
        voice_code = "it-IT-DiegoNeural" if "Diego" in voice_gender else "it-IT-ElsaNeural"

        # 4. Esecuzione Asincrona Isolata
        # Creiamo un nuovo loop specifico per questa esecuzione per evitare conflitti con Streamlit
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_bytes = loop.run_until_complete(_generate_audio_stream(clean_text, voice_code))
        finally:
            loop.close()
            
        # Verifica se abbiamo generato byte
        if not audio_bytes or len(audio_bytes) == 0:
            st.error("Errore: L'audio generato è vuoto.")
            return None
            
        return audio_bytes

    except Exception as e:
        st.error(f"Errore generazione audio: {e}")
        return None

# --- INTERFACCIA ---
st.title("📄 PDF: Analisi AI + Voce Neurale")

with st.sidebar:
    st.header("1. Carica File")
    uploaded_file = st.file_uploader("Trascina qui il PDF", type=["pdf"], accept_multiple_files=True)
    
    st.divider()
    
    st.header("2. Impostazioni Audio")
    voice_choice = st.radio("Scegli la voce:", ["Maschile (Diego)", "Femminile (Elsa)"])

    if uploaded_file:
        current_text = get_pdf_text(uploaded_file)
        if current_text != st.session_state.pdf_text:
            st.session_state.pdf_text = current_text
            st.session_state.analysis_result = None
            st.session_state.audio_file = None
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
        st.subheader("🔊 Audio Neurale")
        st.info("Genera audio con intonazione umana.")
        if st.button("Crea Audio MP3", type="primary", use_container_width=True):
            with st.spinner(f"Generazione voce {voice_choice}..."):
                st.session_state.audio_file = generate_audio(st.session_state.pdf_text, voice_choice)

    st.divider()
    
    if st.session_state.audio_file:
        st.audio(st.session_state.audio_file, format='audio/mp3')
        st.download_button("⬇️ Scarica MP3", st.session_state.audio_file, "audio_neurale.mp3", "audio/mp3")
        
    if st.session_state.analysis_result:
        st.markdown("### Risultato:")
        st.markdown(st.session_state.analysis_result)
else:
    st.info("Carica un PDF.")
