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

# --- FUNZIONI DI UTILITÀ ---
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
    text = text.replace('\n', ' ')
    bad_chars = ['○', '◦', '•', '●', '▪', '■', '□', '➢', '➣', '➤', '->', '★', '☆', '—', '–', '|', '/', '\\']
    for char in bad_chars:
        text = text.replace(char, '')
    text = re.sub(r'[^\w\s\.,:;?!àèéìòùÀÈÉÌÒÙ\'\"]', '', text)
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

# --- FUNZIONI AUDIO (SMART CHUNKING) ---
def chunk_text(text, max_chars=2500):
    """Divide il testo in blocchi rispettando la punteggiatura."""
    chunks = []
    current_chunk = ""
    sentences = text.replace('.', '.|||').split('|||')
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
            
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

async def _generate_audio_stream_chunked(text, voice_code, status_placeholder):
    chunks = chunk_text(text)
    full_audio_data = b""
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        # Aggiorna UI
        if status_placeholder:
            status_placeholder.text(f"Generazione audio: blocco {i+1} di {total_chunks}...")
        
        communicate = edge_tts.Communicate(chunk, voice_code)
        async for item in communicate.stream():
            if item["type"] == "audio":
                full_audio_data += item["data"]
    return full_audio_data

def generate_audio(text, voice_gender):
    try:
        clean_text = clean_text_for_audio(text)
        if not clean_text.strip():
            st.warning("Nessun testo valido.")
            return None
        
        # Limite aumentato
        LIMIT = 20000 
        if len(clean_text) > LIMIT:
            st.warning(f"Testo enorme ({len(clean_text)} caratteri). Taglio ai primi {LIMIT}.")
            clean_text = clean_text[:LIMIT]

        voice_code = "it-IT-DiegoNeural" if "Diego" in voice_gender else "it-IT-ElsaNeural"
        status_box = st.empty()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_bytes = loop.run_until_complete(
                _generate_audio_stream_chunked(clean_text, voice_code, status_box)
            )
        finally:
            loop.close()
            status_box.empty()
            
        if not audio_bytes:
            st.error("Errore: Audio vuoto.")
            return None
        return audio_bytes

    except Exception as e:
        st.error(f"Errore generazione audio: {e}")
        return None

# --- INTERFACCIA UTENTE ---
st.title("📄 PDF: Analisi AI + Voce Neurale")

with st.sidebar:
    st.header("1. Carica File")
    uploaded_file = st.file_uploader("Trascina qui il PDF", type=["pdf"], accept_multiple_files=True)
    
    st.divider()
    
    st.header("2. Impostazioni Audio")
    voice_choice = st.radio("Scegli la voce:", ["Maschile (Diego)", "Femminile (Elsa)"])
    
    # NOVITÀ: Scelta della sorgente
    st.divider()
    source_choice = st.radio("Cosa vuoi ascoltare?", ["Testo Originale PDF", "Risultato Analisi AI"])

    if uploaded_file:
        current_text = get_pdf_text(uploaded_file)
        if current_text != st.session_state.pdf_text:
            st.session_state.pdf_text = current_text
            st.session_state.analysis_result = None
            st.session_state.audio_file = None
            st.toast("Nuovo PDF caricato!", icon="✅")

if st.session_state.pdf_text:
    col1, col2 = st.columns(2)
    
    # --- COLONNA 1: ANALISI ---
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
        
        # MOSTRA RISULTATO ANALISI
        if st.session_state.analysis_result:
            st.markdown("### Risultato:")
            st.markdown(st.session_state.analysis_result)
            st.download_button(
                label="💾 Scarica Report AI",
                data=st.session_state.analysis_result,
                file_name="analisi_ai.md",
                mime="text/markdown"
            )

        # Q&A CHAT
        st.divider()
        st.subheader("💬 Chiedi al PDF")
        user_question = st.text_input("Fai una domanda specifica:")
        if user_question and st.button("Chiedi"):
            with st.spinner("Cerco la risposta..."):
                answer = analyze_with_gemini(st.session_state.pdf_text, user_question, "gemini-pro")
                st.markdown(f"**Risposta:**\n{answer}")

    # --- COLONNA 2: AUDIO ---
    with col2:
        st.subheader("🔊 Audio Neurale")
        st.info(f"Modalità: {source_choice}")
        
        if st.button("Crea Audio MP3", type="primary", use_container_width=True):
            # Determina cosa leggere
            text_to_read = st.session_state.pdf_text if source_choice == "Testo Originale PDF" else st.session_state.analysis_result
            
            if not text_to_read:
                st.error("⚠️ Testo mancante. Fai prima l'analisi o carica un PDF.")
            else:
                with st.spinner(f"Generazione voce {voice_choice}..."):
                    st.session_state.audio_file = generate_audio(text_to_read, voice_choice)

        st.divider()
        
        if st.session_state.audio_file:
            # FIX PLAYER AUDIO
            st.audio(io.BytesIO(st.session_state.audio_file), format='audio/mpeg')
            st.download_button(
                "⬇️ Scarica MP3", 
                st.session_state.audio_file, 
                "audio_neurale.mp3", 
                "audio/mpeg"
            )

else:
    st.info("Carica un PDF dalla barra laterale per iniziare.")
