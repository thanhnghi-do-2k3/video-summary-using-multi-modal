from concurrent.futures import ThreadPoolExecutor
import cv2
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from utils import device

class Captioner:
    def __init__(self, max_batch_size=8, max_workers=2):
        # Use the publicly available BLIP-2 model (opt-2.7b) for image captioning
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
        self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b").to(device)
        self.max_batch_size = max_batch_size
        self.max_workers = max_workers

    def generate_captions(self, frames):
        """
        This method generates captions for a batch of image frames.
        It uses a thread pool to process batches of frames concurrently for faster processing.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Split the frames into batches
            batches = [frames[i:i+self.max_batch_size] for i in range(0, len(frames), self.max_batch_size)]
            futures = [executor.submit(self.process_batch, batch) for batch in batches]
            # Collect results from all futures and return them
            return [caption for future in futures for caption in future.result()]

    def process_batch(self, batch):
        """
        This method processes a batch of frames and generates captions.
        It converts frames to RGB, processes them through the model, and decodes the generated outputs.
        """
        # Convert each frame in the batch to RGB format as required by the processor
        inputs = self.processor(
            images=[cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in batch],
            return_tensors="pt", 
            padding=True
        ).to(device)  # Make sure that the inputs are transferred to the correct device (GPU/CPU)
        
        # Run the inference in evaluation mode (no gradients calculated)
        with torch.inference_mode():
            outputs = self.model.generate(**inputs, max_length=200, num_beams=3)
            
        # Decode the generated output captions into readable text
        return [self.processor.decode(gen, skip_special_tokens=True) for gen in outputs]
