import torch
import yt_dlp

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"

device = get_device()
torch.backends.cudnn.benchmark = True if device == "cuda" else False

def get_video_info(video_url):
    ydl_opts = {'quiet': True, 'skip_download': True, 'format': 'best'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            'stream_url': info['url'],
            'duration': info.get('duration', 0),
            'title': info.get('title', 'No Title'),
            'description': info.get('description', ''),
            'width': info.get('width', 640),
            'height': info.get('height', 360)
        }