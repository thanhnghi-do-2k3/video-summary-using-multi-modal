import json
import requests
import time
from frame_processor import FrameProcessor
from captioner import Captioner
from audio_processor import OptimizedAudioProcessor
from utils import get_video_info
from prompts import VIDEO_SUMMARY
from gemini_api_client import geminiClient

class SmartVideoAnalyzer:
    def __init__(self, api_key, frame_interval=10, audio_duration=60):
        self.api_key = api_key
        self.frame_processor = FrameProcessor(sample_interval=frame_interval)
        self.captioner = Captioner()
        self.audio_processor = OptimizedAudioProcessor(max_duration=audio_duration)
    
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
            start_time = time.time()
            video_info = get_video_info(video_url)
            print(f"Processing: {video_info['title']} ({video_info['duration']}s)")
            
            frames = self.frame_processor.get_frames(video_info['stream_url'])
            frame_captions = [f"Frame {i+1}: {cap}" for i, cap in enumerate(self.captioner.generate_captions(frames))]
            
            transcript = self.audio_processor.process_audio(video_info['stream_url'])
            
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
            
            start = response.find('[')
            end = response.find(']') + 1
            keywords = json.loads(response[start:end])
            
            return {
                'title': video_info['title'],
                'duration': video_info['duration'],
                'keywords': keywords,
                'processing_time': time.time() - start_time,
                'frames_processed': len(frames),
                'audio_processed': f"{self.audio_processor.max_duration}s"
            }
            
        except Exception as e:
            print(f"Analysis failed: {str(e)}")
            return None