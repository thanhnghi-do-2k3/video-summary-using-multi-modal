from concurrent.futures import ThreadPoolExecutor
import cv2, torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from utils import device

class Captioner:
    def __init__(self, max_batch_size=8, max_workers=2):
        repo_id = "Salesforce/blip2-flan-t5-xl"   # ✅ tên chính xác

        self.processor = Blip2Processor.from_pretrained(
            repo_id,
            token=None,                 # tải ẩn danh
            trust_remote_code=False,
        )

        self.model = Blip2ForConditionalGeneration.from_pretrained(
            repo_id,
            token=None,
            trust_remote_code=False,
            torch_dtype=torch.float16,
        ).to(device)

        self.max_batch_size = max_batch_size
        self.max_workers   = max_workers

    def generate_captions(self, frames):
        batches = [frames[i:i+self.max_batch_size]
                   for i in range(0, len(frames), self.max_batch_size)]
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = [ex.submit(self.process_batch, b) for b in batches]
            return [cap for fu in futures for cap in fu.result()]

    def process_batch(self, batch):
        inputs = self.processor(
            images=[cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in batch],
            return_tensors="pt",
            padding=True
        ).to(device)

        with torch.inference_mode():
            outs = self.model.generate(**inputs, max_length=200, num_beams=3)

        return [self.processor.decode(o, skip_special_tokens=True) for o in outs]