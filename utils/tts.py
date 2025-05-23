from gtts import gTTS
import os
import time

def speak(text):
    os.makedirs("static/audio", exist_ok=True)
    
    # Gerar um nome de arquivo único com timestamp
    timestamp = int(time.time())
    filename = f"tts_output_{timestamp}.mp3"
    
    audio_file = os.path.join("static/audio", filename)
    
    tts = gTTS(text=text, lang='pt-br', slow=False)
    tts.save(audio_file)
    
    # Retornar o caminho com o timestamp para evitar cache
    return f"/static/audio/{filename}"
