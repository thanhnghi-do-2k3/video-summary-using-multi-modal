import os
import yt_dlp
from faster_whisper import WhisperModel
from pydub import AudioSegment
from utils import device
from proxy import proxy

class TranscriptProcessor:
    def __init__(self, model_size="medium", compute_type="float32", max_duration=600):
        """
        Args:
            model_size: whisper model (tiny, base, small...)
            compute_type: int8/float16/float32
            max_duration: giới hạn thời lượng (giây)
        """
        self.model = WhisperModel(
            model_size,
            device="cuda" if device == "cuda" else "cpu",
            compute_type=compute_type
        )
        self.max_duration = max_duration

    def _download_audio(self, youtube_url, output_file="temp_audio_full.m4a"):
        print(f"[INFO] Downloading audio stream from YouTube...")
        ydl_opts = {
            'proxy': proxy,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_file,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return output_file

    def _convert_and_trim_audio(self, input_path, output_path="temp_audio.wav"):
        print(f"[INFO] Converting and trimming audio...")
        audio = AudioSegment.from_file(input_path)
        trimmed = audio[:self.max_duration * 1000]  # milliseconds
        trimmed.export(output_path, format="wav")
        print(f"[DEBUG] Exported WAV duration: {len(trimmed)/1000:.2f}s, size: {os.path.getsize(output_path)/1024:.2f} KB")
        return output_path

    def process(self, youtube_url, output_file="output/transcript.txt"):
        os.makedirs("output", exist_ok=True)
        m4a_path = "temp_audio_full.m4a"
        wav_path = "temp_audio.wav"

        self._download_audio(youtube_url, m4a_path)
        self._convert_and_trim_audio(m4a_path, wav_path)

        print("[INFO] Running transcription...")
        segments, _ = self.model.transcribe(wav_path, beam_size=3)

        if segments is None:
            print("[❌ ERROR] Transcription failed.")
            return ""

        transcript = " ".join([seg.text.strip() for seg in segments])
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcript)

        print(f"[✅] Transcript saved to: {output_file}")
        os.remove(m4a_path)
        os.remove(wav_path)
        return transcript