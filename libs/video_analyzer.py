import json
import requests
import time
from frame_processor import FrameProcessor
from captioner import Captioner
from audio_processor import TranscriptProcessor
from utils import get_video_info
from prompts import VIDEO_SUMMARY
from gemini_api_client import geminiClient

class SmartVideoAnalyzer:
    def __init__(self, api_key, frame_interval=10, audio_duration=600):
        self.api_key = api_key
        self.frame_processor = FrameProcessor(sample_interval=frame_interval)
        self.captioner = Captioner()
        self.audio_processor = TranscriptProcessor(max_duration=audio_duration)
    
    def construct_prompt(self, video_title, duration, frame_captions, transcript, video_description):
        prompt_template = VIDEO_SUMMARY
        return prompt_template.substitute(
            title=video_title,
            duration=duration,
            frame_count=len(frame_captions),
            frame_samples='\n'.join(frame_captions),
            audio_duration=self.audio_processor.max_duration,
            transcript_sample=transcript,
            video_description=video_description
        ).strip()

    def analyze(self, video_url):
        try:
            # Start overall timer
            start_time = time.time()
            
            # Stage 1: Video info retrieval
            stage_1_start = time.time()
            video_info = get_video_info(video_url)
            stage_1_end = time.time()
            print(f"Video info retrieved in {stage_1_end - stage_1_start:.2f}s")
            
            # Stage 2: Frame extraction
            stage_2_start = time.time()
            frames = self.frame_processor.get_frames(video_info['stream_url'])
            stage_2_end = time.time()
            print(f"Frames extracted in {stage_2_end - stage_2_start:.2f}s")
            
            frame_captions = [f"Frame {i+1}: {cap}" for i, cap in enumerate(self.captioner.generate_captions(frames))]
            
            # Stage 3: Audio processing
            stage_3_start = time.time()
            transcript = self.audio_processor.process(video_info['video_url'])
            stage_3_end = time.time()
            print(f"Audio processed in {stage_3_end - stage_3_start:.2f}s")
            
            print(f"Transcription: {transcript}")
            print(f"Frame Captions: {frame_captions}")
            
            # Stage 4: Content generation (using Gemini API)
            stage_4_start = time.time()
            analysis_prompt = self.construct_prompt(
                video_info['title'],
                video_info['duration'],
                frame_captions,
                transcript,
                video_info['description']
            )
            
            response = geminiClient.generate_content(
                prompt=analysis_prompt            
            )
            stage_4_end = time.time()
            print(f"Content generated in {stage_4_end - stage_4_start:.2f}s")
            
            # Process the response
            start = response.find('[')
            end = response.find(']') + 1
            keywords = json.loads(response[start:end])
            
            # Total time for pipeline
            total_processing_time = time.time() - start_time
            print(f"Total processing time: {total_processing_time:.2f}s")
            
            return {
                'title': video_info['title'],
                'duration': video_info['duration'],
                'keywords': keywords,
                'processing_time': total_processing_time,
                'frames_processed': len(frames),
                'audio_processed': f"{self.audio_processor.max_duration}s"
            }
            
        except Exception as e:
            print(f"Analysis failed: {str(e)}")
            return None