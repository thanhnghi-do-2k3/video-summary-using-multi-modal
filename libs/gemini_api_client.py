from google import genai
from constants import API_KEY

class GeminiApiClient: 
    def __init__(self, api_key: str):

        self.api_key = api_key
        self.client = genai.Client(
            api_key=self.api_key,
        )

    def generate_content(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

geminiClient = GeminiApiClient(
    api_key=API_KEY,
)

