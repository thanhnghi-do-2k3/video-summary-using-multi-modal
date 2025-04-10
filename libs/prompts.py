from string import Template
import os

def load_prompt(filename: str) -> Template:
    prompt_dir = os.path.join(os.path.dirname(__file__), './prompts')
    with open(os.path.join(prompt_dir, filename), 'r', encoding='utf-8') as f:
        return Template(f.read())
    
GENERATE_KEYWORD = load_prompt('generate_keyword.txt')
VIDEO_SUMMARY = load_prompt('video_summary.txt')