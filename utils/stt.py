import speech_recognition as sr

def listen(audio_path):
    r = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = r.record(source)

    try:
        return r.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError:
        return "[Não entendi o que foi dito]"
    except sr.RequestError:
        return "[Erro ao acessar serviço de transcrição]"
