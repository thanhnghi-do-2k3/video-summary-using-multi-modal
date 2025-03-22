import subprocess
import cv2
import numpy as np
import yt_dlp
import torch
import librosa
from transformers import AutoProcessor, Blip2ForConditionalGeneration
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
from transformers import pipeline

###########################################
# 1. Device selection based on platform
###########################################
def get_device():
    """
    Check for the best available device.
    On M1 macs, use "mps" if available; otherwise check for "cuda"; else use "cpu".
    """
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"

device = get_device()
print("Using device:", device)

###########################################
# 2. Get YouTube Direct Stream URL
###########################################
def get_youtube_stream_url(video_url, format_code="best"):
    """
    Retrieve a direct video stream URL from a YouTube URL using yt_dlp.
    """
    print("Retrieving direct stream URL...")
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': format_code,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        stream_url = info['url']
    print("Direct stream URL retrieved.")
    return stream_url

###########################################
# 3. Stream Video Frames via ffmpeg Pipe
###########################################
def stream_youtube_frames(direct_url, desired_fps=0.5, width=480, height=270):
    """
    Stream frames from the direct video URL using ffmpeg.
    - desired_fps: sampling rate (e.g., 0.5 means one frame every 2 seconds)
    - width, height: resize dimensions for efficiency.
    Yields frames as NumPy arrays (BGR format).
    """
    command = [
        'ffmpeg',
        '-i', direct_url,
        '-vf', f"fps={desired_fps},scale={width}:{height}",
        '-f', 'image2pipe',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        '-'
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
    frame_size = width * height * 3  # 3 bytes per pixel (bgr24)
    while True:
        raw_frame = process.stdout.read(frame_size)
        if not raw_frame:
            break
        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        yield frame
    process.stdout.close()
    process.wait()

###########################################
# 4. Stream Audio and Transcribe
###########################################
def stream_youtube_audio(direct_url, chunk_sec=30):
    """
    Stream the audio from the direct video URL in chunks using ffmpeg.
    Outputs 16-bit PCM, mono, 16 kHz audio.
    Yields chunks as numpy arrays.
    """
    print("Starting audio stream via ffmpeg...")
    cmd = [
        'ffmpeg',
        '-i', direct_url,
        '-vn',                  # no video
        '-ac', '1',             # mono channel
        '-ar', '16000',         # 16 kHz sample rate
        '-f', 's16le',          # raw PCM 16-bit little endian
        '-'
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=4096)
    sample_rate = 16000
    samples_per_chunk = sample_rate * chunk_sec
    bytes_per_sample = 2  # 16-bit PCM => 2 bytes
    chunk_size_bytes = samples_per_chunk * bytes_per_sample

    while True:
        raw_data = process.stdout.read(chunk_size_bytes)
        if not raw_data:
            break
        audio_chunk = np.frombuffer(raw_data, np.int16).astype(np.float32) / 32768.0
        print("Processed an audio chunk of", chunk_sec, "seconds.")
        yield audio_chunk
    process.stdout.close()
    process.wait()

def transcribe_streamed_audio(direct_url, chunk_sec=30):
    """
    Transcribe the audio stream in chunks using Wav2Vec2.
    Concatenates the transcript from each chunk.
    """
    print("Starting audio transcription...")
    proc = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h-lv60-self")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h-lv60-self").to(device)
    full_transcript = []

    for idx, chunk in enumerate(stream_youtube_audio(direct_url, chunk_sec=chunk_sec)):
        if len(chunk) == 0:
            continue
        print(f"Transcribing audio chunk {idx+1}...")
        inputs = proc(chunk, sampling_rate=16000, return_tensors="pt", padding=True)
        input_values = inputs.input_values.to(device)
        with torch.no_grad():
            logits = model(input_values).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = proc.decode(predicted_ids[0])
        full_transcript.append(transcription)
    final_transcript = " ".join(full_transcript)
    print("Audio transcription complete.")
    return final_transcript

###########################################
# 5. Process Video Frames with BLIP-2 (Optimized)
###########################################
def caption_video_frames(direct_url, desired_fps=0.5, width=480, height=270, max_frames=20, batch_size=8):
    """
    Streams frames from the direct URL and generates captions using BLIP-2.
    This function processes frames in batches for efficiency.
    Returns a list of captions (one per sampled frame). Processing is limited to max_frames.
    """
    print("Starting frame streaming and captioning...")
    # Use a smaller model (blip2-flan-t5-base) for faster processing
    blip_processor = AutoProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
    blip_model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b").to(device)

    captions = []
    frames_generator = stream_youtube_frames(direct_url, desired_fps=desired_fps, width=width, height=height)
    
    # Collect frames in batches
    batch_frames = []
    for idx, frame in enumerate(frames_generator):
        if idx >= max_frames:
            print(f"Reached maximum frame limit of {max_frames}.")
            break

        print(f"Processing frame {idx+1}...")

        # Convert frame from BGR to RGB as expected by BLIP-2
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        batch_frames.append(rgb_frame)

        # Process the batch when we reach batch_size
        if len(batch_frames) == batch_size:
            # Convert the batch to tensor and send it to the model
            inputs = blip_processor(images=batch_frames, return_tensors="pt").to(device)
            output_ids = blip_model.generate(**inputs)
            for i, output_id in enumerate(output_ids):
                caption = blip_processor.tokenizer.decode(output_id, skip_special_tokens=True)
                captions.append(f"Frame {idx - len(batch_frames) + i}: {caption}")

            # Clear the batch frames
            batch_frames = []
    
    # Process any remaining frames in the last batch
    if batch_frames:
        inputs = blip_processor(images=batch_frames, return_tensors="pt").to(device)
        output_ids = blip_model.generate(**inputs)
        for i, output_id in enumerate(output_ids):
            caption = blip_processor.tokenizer.decode(output_id, skip_special_tokens=True)
            captions.append(f"Frame {max_frames - len(batch_frames) + i}: {caption}")
    
    print("Frame captioning complete.")
    return captions

###########################################
# 6. Generate Summary using BART Pipeline
###########################################
def generate_summary_pipeline(prompt, max_new_tokens=200, min_length=50):
    """
    Generate summary text from a prompt using Hugging Face's BART summarization pipeline.
    """
    pipeline_device = 0 if device in ["cuda", "mps"] else -1
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=pipeline_device)
    result = summarizer(prompt, max_length=max_new_tokens, min_length=min_length, do_sample=False)
    return result[0]["summary_text"]

###########################################
# 8. Full Pipeline for YouTube Video
###########################################
def process_youtube_video_pipeline(video_url, max_chunk_size=1500, chunk_sec=30, max_frames=20):
    """
    Complete pipeline:
      - Retrieves a direct stream URL from the YouTube video.
      - Streams and captions video frames using BLIP-2 (limited to max_frames).
      - Streams and transcribes the audio using Wav2Vec2.
      - Constructs a combined prompt from the frame captions and audio transcript.
      - If the prompt is too long, chunks and summarizes iteratively.
      - Generates a final summary using the BART summarization pipeline.
    """
    # 1. Get direct stream URL.
    direct_url = get_youtube_stream_url(video_url)

    # 2. Generate captions for sampled video frames.
    print("Processing video frames...")
    frame_captions = caption_video_frames(direct_url, desired_fps=0.5, width=480, height=270, max_frames=max_frames)

    # 3. Transcribe audio stream.
    print("Processing audio stream...")
    audio_transcript = transcribe_streamed_audio(direct_url, chunk_sec=chunk_sec)

    # 4. Construct the overall prompt.
    combined_text = (
        "Video Frame Captions:\n" + "\n".join(frame_captions) +
        "\n\nAudio Transcript:\n" + audio_transcript
    )

    # 5. If text is long, chunk and summarize iteratively.
    if len(combined_text) > max_chunk_size:
        chunks = chunk_text(combined_text, max_chunk_size)
        print(f"Combined text length is {len(combined_text)} characters. Summarizing in {len(chunks)} chunks...")
        final_summary = summarize_chunks(chunks, max_new_tokens=200)
    else:
        final_summary = generate_summary_pipeline(combined_text, max_new_tokens=300)

    return final_summary

###########################################
# 9. Example Usage
###########################################
if __name__ == "__main__":
    # Replace with the actual YouTube video URL you wish to summarize.
    video_url = "https://www.youtube.com/watch?v=8Fy_3TEh5_0"
    summary = process_youtube_video_pipeline(video_url, max_chunk_size=1500, chunk_sec=30, max_frames=20)
    print("===== Final Video Summary =====")
    print(summary)