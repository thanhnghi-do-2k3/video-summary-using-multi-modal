import subprocess
import cv2
import numpy as np

class FrameProcessor:
    def __init__(self, sample_interval=5, base_size=160):
        self.sample_interval = sample_interval
        self.base_size = base_size
    
    def get_frames(self, direct_url, max_duration=300):
        command = [
            'ffmpeg',
            '-hwaccel', 'auto',
            '-i', direct_url,
            '-t', str(max_duration),
            '-vf', f"fps=1/{self.sample_interval},scale={self.base_size}:-1",
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-'
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**7)
        frame_size = self.base_size * (self.base_size * 3 // 4) * 3
        
        frames = []
        while True:
            raw_frame = process.stdout.read(frame_size)
            if not raw_frame:
                break
            frames.append(np.frombuffer(raw_frame, np.uint8).reshape((-1, self.base_size * 3 // 4, 3)))
        
        process.stdout.close()
        process.wait()
        return frames[:100]