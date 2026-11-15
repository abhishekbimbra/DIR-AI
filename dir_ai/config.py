"""
Configuration — Load environment variables and project settings.
Copy .env.example to .env and fill in your API key.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "\n[DIR-AI] GEMINI_API_KEY is not set.\n"
        "Create a .env file with:\n\n"
        "  GEMINI_API_KEY=your_key_here\n"
    )
