# app.py — Streamlit + Silero STT & TTS (with File Upload + Recording)
import streamlit as st
import torch
import sounddevice as sd
import numpy as np
import soundfile as sf
import tempfile
import io
import librosa

# --------------------------------------------------
# Device setup
# --------------------------------------------------
device = torch.device("cpu")

# --------------------------------------------------
# Load Silero Models (cached for performance)
# --------------------------------------------------
@st.cache_resource
def load_models():
    # Load Speech-to-Text (STT) model
    stt_model, decoder, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_stt",
        language="en",
        device=device,
    )
    (read_batch, split_into_batches, read_audio, prepare_model_input) = utils

    # Load Text-to-Speech (TTS) model — new API returns only 2 values
    tts_model, example_texts = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language='en',
        speaker='v3_en'
    )

    return stt_model, decoder, prepare_model_input, tts_model


# Load models once (cached)
stt_model, decoder, prepare_model_input, tts_model = load_models()

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------
st.set_page_config(page_title="Silero Speech ↔ Text App", page_icon="🎤", layout="centered")
st.title("🎤  Speech ↔ Text App")
st.write("Select an option below to convert speech to text or text to speech.")

mode = st.radio("Select Mode", ["Speech to Text", "Text to Speech"])

# --------------------------------------------------
# SPEECH → TEXT
# --------------------------------------------------
if mode == "Speech to Text":
    st.subheader("🎙️ Speech → Text (STT)")

    option = st.radio("Choose input method:", ["Record via Microphone", "Upload Audio File"])

    # --- Record via Microphone ---
    if option == "Record via Microphone":
        duration = st.slider("Recording duration (seconds)", 3, 10, 5)
        if st.button("Start Recording"):
            st.info("Recording... please speak now!")
            fs = 16000
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
            sd.wait()
            st.success("Recording complete!")

            # Convert to tensor and transcribe
            audio = np.squeeze(audio)
            input_tensor = torch.from_numpy(audio)
            batch = prepare_model_input([input_tensor], device=device)
            output = stt_model(batch)
            text = decoder(output[0].cpu())
            st.success("✅ Transcription Complete")
            st.text_area("Recognized Text", text, height=150)

    # --- Upload Audio File ---
    elif option == "Upload Audio File":
        uploaded = st.file_uploader("Upload a .wav or .mp3 file", type=["wav", "mp3"])
        if uploaded is not None:
            st.audio(uploaded)
            data, samplerate = sf.read(io.BytesIO(uploaded.read()), dtype="float32")
            if len(data.shape) > 1:
                data = data[:, 0]  # convert to mono
            if samplerate != 16000:
                st.warning("Resampling to 16 kHz for best results...")
                data = librosa.resample(data, orig_sr=samplerate, target_sr=16000)
            input_tensor = torch.from_numpy(data)
            batch = prepare_model_input([input_tensor], device=device)
            output = stt_model(batch)
            text = decoder(output[0].cpu())
            st.success("✅ Transcription Complete")
            st.text_area("Recognized Text", text, height=150)

# --------------------------------------------------
# TEXT → SPEECH
# --------------------------------------------------
elif mode == "Text to Speech":
    st.subheader("💬 Text → Speech (TTS)")
    text = st.text_area("Enter your text below:", "Hello! This is Silero running with Streamlit.")

    if st.button("Generate Speech"):
        if text.strip() == "":
            st.warning("Please enter some text first.")
        else:
            st.info("Generating speech, please wait...")
            # Generate waveform
            audio = tts_model.apply_tts(text=text, speaker='en_0')


            # Save to temporary .wav for playback
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                sf.write(tmp.name, audio, 48000)
                st.audio(tmp.name)
            st.success("✅ Speech generated successfully!")
