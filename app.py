import os
import uuid
import srt
import ffmpeg
from flask import Flask, request, jsonify, send_file
from faster_whisper import WhisperModel
from datetime import timedelta
from deep_translator import GoogleTranslator
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

model = WhisperModel("base")

process_status = {}
status_lock = Lock()

def set_status(video_id, message):
    with status_lock:
        process_status[video_id] = message

def extract_audio(video_path, audio_path):
    ffmpeg.input(video_path).output(audio_path, ac=1, ar='16000').run(overwrite_output=True)

def transcribe_audio(audio_path):
    segments, _ = model.transcribe(audio_path, beam_size=5, language='en')
    subtitles = []
    for i, segment in enumerate(segments):
        subtitles.append(srt.Subtitle(
            index=i + 1,
            start=timedelta(seconds=segment.start),
            end=timedelta(seconds=segment.end),
            content=segment.text.strip()
        ))

    return subtitles

def translate_subtitles(subtitles, target_lang="pt"):
    fallback_lang = target_lang.lower().split("-")[0]

    def translate_content(sub):
        try:
            translated = GoogleTranslator(source='en', target=fallback_lang).translate(sub.content)
            sub.content = translated
        except Exception as err:
            print(f"Erro ao traduzir '{sub.content}': {err}")
        return sub

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(translate_content, sub): sub for sub in subtitles}
        for future in as_completed(futures):
            future.result()

    return subtitles

def write_srt_file(subtitles, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

def burn_subtitles(video_path, srt_path, output_path):
    (
        ffmpeg.input(video_path).output(
            output_path,
            vf=f"subtitles={srt_path}:force_style='FontName=Sora,FontSize=14,Bold=1'",
            vcodec='libx264',
            acodec='copy',
            crf=15,
            preset='veryfast'
        ).run(overwrite_output=True)
    )

@app.route("/legendado", methods=["POST"])
def process_video():
    if 'video' not in request.files:
        return jsonify({'error': 'Envie um arquivo de vídeo com o campo "video"'}), 400

    target_lang = request.form.get("lang", "PT-BR").upper()

    video_file = request.files['video']
    video_id = str(uuid.uuid4())

    UPLOAD_FOLDER = video_id
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp4")
    audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.wav")
    srt_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.srt")

    set_status(video_id, "Salvando vídeo...")
    video_file.save(video_path)

    set_status(video_id, "Extraindo áudio...")
    extract_audio(video_path, audio_path)

    set_status(video_id, "Transcrevendo...")
    subtitles = transcribe_audio(audio_path)

    set_status(video_id, "Gerando arquivo SRT...")
    write_srt_file(subtitles, srt_path)

    set_status(video_id, "Finalizado")

    return jsonify({"video_id": video_id})

@app.route("/status/<video_id>")
def get_status(video_id):
    with status_lock:
        return jsonify({"status": process_status.get(video_id, "Desconhecido")})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
