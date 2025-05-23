import os
import sys
import ffmpeg

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

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python script.py <UPLOAD_FOLDER> <video_id>")
        sys.exit(1)

    UPLOAD_FOLDER = sys.argv[1]
    video_id = sys.argv[2]

    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp4")
    audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.wav")
    srt_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.srt")
    output_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_legendado.mp4")

    burn_subtitles(video_path, srt_path, output_path)
