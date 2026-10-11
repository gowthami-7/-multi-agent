import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY was not found in the .env file."
    )


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

MODEL = "openrouter/free"


def generate_ai_response(prompt: str) -> str:
    """Send a prompt to the configured Generative AI model."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()