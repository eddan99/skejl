from google import genai
from config.settings import settings

class GeminiClientError(Exception):
    pass

def get_gemini_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY

    if not api_key:
        raise GeminiClientError(
            "GEMINI_API_KEY not found. Please set it in your .env file or environment."
        )

    return genai.Client(api_key=api_key)

def get_model_name() -> str:
    return settings.GEMINI_MODEL_NAME
