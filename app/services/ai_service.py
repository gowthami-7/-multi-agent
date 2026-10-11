
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Use local .env during development, or Streamlit Secrets in the cloud.
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY is missing. Configure it in your "
        ".env file locally or in Streamlit Cloud Secrets."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "openrouter/free"


def generate_ai_response(prompt: str) -> str:
    """Send a prompt to the configured AI model."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    return (content or "").strip()
