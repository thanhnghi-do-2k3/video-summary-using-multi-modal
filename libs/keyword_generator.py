import json

from gemini_api_client import geminiClient
from prompts import GENERATE_KEYWORD

class KeywordGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.search_template = GENERATE_KEYWORD

    def generate_search_terms(self, base_keywords):
        print(f"\n🔄 Bắt đầu tạo từ khóa tìm kiếm từ {len(base_keywords)} từ khóa gốc...")
        try:

            response = geminiClient.generate_content(
                prompt=self.search_template.substitute(keywords=base_keywords),
            )

            result_text = response
            print(f"🔑 Từ khóa tìm kiếm: {result_text}")
            
            try:
                start = result_text.find('[')
                end = result_text.find(']') + 1
                return json.loads(result_text[start:end])[:5]
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format in response")
                
        except Exception as e:
            print(f"❌ Lỗi tạo từ khóa: {str(e)}")
            return []