import json

import requests


class KeywordGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.search_template = """Hãy tạo 5 từ khóa tìm kiếm YouTube từ các từ khóa gốc.
Các từ khóa nên tập trung vào các nội dung liên quan và có khả năng tìm thấy video tương tự.
Đầu vào gốc: {keywords}
Định dạng đầu ra: JSON array chứa các chuỗi"""

    def generate_search_terms(self, base_keywords):
        print(f"\n🔄 Bắt đầu tạo từ khóa tìm kiếm từ {len(base_keywords)} từ khóa gốc...")
        try:
            response = requests.post(
f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": self.search_template.format(
                                keywords=', '.join(base_keywords[:15]))  # Giới hạn đầu vào
                        }]
                    }]
                },
                timeout=20
            )
            
            # Kiểm tra phản hồi hợp lệ
            if response.status_code != 200:
                raise ValueError(f"API error: {response.text}")
                
            response_json = response.json()
            if 'candidates' not in response_json:
                raise ValueError("Invalid API response structure")
                
            result_text = response_json['candidates'][0]['content']['parts'][0]['text']

            print(f"🔑 Từ khóa tìm kiếm: {result_text}")
            
            # Xử lý đầu ra an toàn
            try:
                start = result_text.find('[')
                end = result_text.find(']') + 1
                return json.loads(result_text[start:end])[:5]
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format in response")
                
        except Exception as e:
            print(f"❌ Lỗi tạo từ khóa: {str(e)}")
            return []