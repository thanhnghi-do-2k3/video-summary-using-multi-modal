from google import genai
from constants import API_KEY

class GeminiApiClient: 
    """
    A client for the Gemini API.
    """
    def __init__(self, api_key: str):
        """
        Initialize the Gemini API client.

        :param api_key: The API key for authentication.
        :param api_secret: The API secret for authentication.
        """
        self.api_key = api_key
        self.client = genai.Client(
            api_key=self.api_key,
        )

    def generate_content(self, prompt: str) -> str:
        """
        Generate content using the Gemini API.
        :param prompt: The input prompt for content generation.
        :return: The generated content.
        """
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

geminiClient = GeminiApiClient(
    api_key=API_KEY,
)

