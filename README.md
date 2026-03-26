# Analizzatore PDF AI & Lettore Vocale Neurale

Applicazione web sviluppata in Python e Streamlit per l'estrazione, l'analisi e la lettura vocale di documenti PDF. Utilizza l'API di Google Gemini per l'elaborazione del testo e Edge-TTS per la generazione di audio neurale ad alta fedeltà.

## Funzionalità

* **Estrazione Testo:** Lettura e acquisizione del contenuto testuale da file PDF tramite `pypdf`.
* **Analisi AI (Google Gemini):**
    * Sintesi Esecutiva
    * Validazione Fattuale
    * Estrazione Action Items
    * Analisi Critica
* **Sintesi Vocale Neurale (Edge-TTS):**
    * Generazione di file audio MP3 scaricabili.
    * Voci italiane disponibili: Maschile (DiegoNeural) e Femminile (ElsaNeural).
    * Sistema di pulizia del testo basato su espressioni regolari (Regex) per ignorare elenchi puntati, formattazione e caratteri speciali durante la generazione audio, garantendo una lettura fluida.

## Prerequisiti

* Python 3.8 o superiore.
* Chiave API valida per Google Gemini.

## Installazione Locale

1. Clonare il repository:
   ```bash
   git clone <URL_DEL_REPOSITORY>
   cd <NOME_CARTELLA>
   ```

2. Installare le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

3. Configurare l'API Key:
   Creare un file `.env` nella directory principale e inserire la chiave in questo formato:
   ```text
   GOOGLE_API_KEY=la_tua_chiave_api_qui
   ```

## Avvio dell'Applicazione

Eseguire il seguente comando nel terminale per avviare il server locale:
```bash
streamlit run app.py
```
L'interfaccia sarà accessibile all'indirizzo `http://localhost:8501`.

## Deploy su Streamlit Community Cloud

Per rendere l'applicazione accessibile via web e dispositivi mobili:

1. Collegare il repository GitHub a [Streamlit Cloud](https://share.streamlit.io/).
2. Impostare `app.py` come file principale (Main file path).
3. Nelle impostazioni dell'app su Streamlit Cloud (Settings > Secrets), configurare la chiave API in formato TOML:
   ```toml
   GOOGLE_API_KEY = "la_tua_chiave_api_qui"
   ```

## Tecnologie Utilizzate

* **[Streamlit](https://streamlit.io/)** - Interfaccia Web e gestione stato.
* **[Google Generative AI](https://ai.google.dev/)** - Motore LLM per l'analisi testuale.
* **[PyPDF](https://pypi.org/project/pypdf/)** - Parsing dei documenti PDF.
* **[Edge-TTS](https://github.com/rany2/edge-tts)** - Modulo Text-to-Speech basato su Microsoft Edge.
* **[Python-dotenv](https://saurabh-kumar.com/python-dotenv/)** - Gestione sicura delle variabili d'ambiente.
