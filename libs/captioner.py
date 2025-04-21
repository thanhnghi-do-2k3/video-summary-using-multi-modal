from concurrent.futures import ThreadPoolExecutor
import cv2
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, AutoTokenizer
from utils import device

class Captioner:
    def __init__(self, max_batch_size=8, max_workers=2):
        # Load tokenizer explicitly for BLIP-2 OPT
        opt_tokenizer = AutoTokenizer.from_pretrained("facebook/opt-2.7b")
        self.processor = BlipProcessor.from_pretrained(
            "Salesforce/blip2-opt-2.7b",
            tokenizer=opt_tokenizer,
            use_fast=True  # Enable fast image processing
        )
        self.model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip2-opt-2.7b"
        ).to(device)
        self.max_batch_size = max_batch_size
        self.max_workers = max_workers

    def generate_captions(self, frames):
        batches = [frames[i:i+self.max_batch_size] for i in range(0, len(frames), self.max_batch_size)]
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_batch, batch) for batch in batches]
            return [caption for future in futures for caption in future.result()]

    def process_batch(self, batch):
        inputs = self.processor(
            images=[cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in batch],
            return_tensors="pt", 
            padding=True
        ).to(device)
        
        with torch.inference_mode():
            outputs = self.model.generate(**inputs, max_length=200, num_beams=3)
            
        return [self.processor.decode(gen, skip_special_tokens=True) for gen in outputs]