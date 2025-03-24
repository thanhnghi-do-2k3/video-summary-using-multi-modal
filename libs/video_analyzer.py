import json
import requests
import time
from frame_processor import OptimizedFrameProcessor
from captioner import ParallelCaptioner
from audio_processor import OptimizedAudioProcessor
from utils import get_video_info

class SmartVideoAnalyzer:
    def __init__(self, api_key, frame_interval=10, audio_duration=60):
        self.api_key = api_key
        self.frame_processor = OptimizedFrameProcessor(sample_interval=frame_interval)
        self.captioner = ParallelCaptioner()
        self.audio_processor = OptimizedAudioProcessor(max_duration=audio_duration)
    
    def construct_prompt(self, video_title, duration, frame_captions, transcript, video_description):
        prompt_template = """
VIDEO ANALYSIS REQUEST:
Title: {title}
Duration: {duration}s
Sampled Frames ({frame_count}):
{frame_samples}
Partial Transcript (First {audio_duration}s):
{transcript_sample}
Video Description: {video_description}

REQUIREMENTS:
- Generate 15-20 keywords
- Output as JSON array
- No explanations
"""
        return prompt_template.format(
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
            
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                json={"contents": [{"parts": [{"text": analysis_prompt}]}]},
                timeout=30
            )
            response.raise_for_status() 

            result = response.json()
            if 'candidates' not in result or not result['candidates']:
                raise ValueError("Invalid API response: No candidates found")
            
            result_text = result['candidates'][0]['content']['parts'][0]['text']
            start = result_text.find('[')
            end = result_text.find(']') + 1
            keywords = json.loads(result_text[start:end])
            
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