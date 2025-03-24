import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from utils import device

class OptimizedAudioProcessor:
    def __init__(self, max_duration=60):
        self.max_duration = max_duration
        self.processor = WhisperProcessor.from_pretrained("openai/whisper-base")
        self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base").to(device).half().eval()

    def process_audio(self, direct_url):
        command = [
            'ffmpeg',
            '-hwaccel', 'auto',
            '-i', direct_url,
            '-t', str(self.max_duration),
            '-vn', '-ac', '1', '-ar', '16000',
            '-f', 's16le', '-'
        ]
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                bufsize=16000 * 2 * 10,  
                stderr=subprocess.DEVNULL
            )
            audio_data = process.stdout.read()
        finally:
            process.stdout.close()
            process.terminate()
            process.wait(timeout=5)
        
        chunk_size = 16000 * 2 * 10
        chunks = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self.process_chunk, idx, chunk) for idx, chunk in enumerate(chunks)]
            return ' '.join([future.result()[1] for future in as_completed(futures)])

    def process_chunk(self, idx, raw_chunk):
        try:
            if len(raw_chunk) % 2 != 0:
                raw_chunk = raw_chunk[:-1]
                
            audio = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            inputs = self.processor(
                audio,
                sampling_rate=16000,
                return_tensors="pt",
                return_attention_mask=True
            )
            
            # Sử dụng config rõ ràng
            outputs = self.model.generate(
                inputs.input_features.to(device).half(),
                max_length=448,
                num_beams=1,
                temperature=0.0,
                language="vi",
                task="transcribe",
            )
            return idx, self.processor.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            print(f"Audio chunk {idx} error: {str(e)}")
            return idx, ""