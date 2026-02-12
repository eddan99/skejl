import json
from typing import Dict, Any

def parse_gemini_response(gemini_text: str) -> Dict[str, Any]:
    text = gemini_text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse JSON",
            "raw": gemini_text,
            "parse_error": str(e)
        }
