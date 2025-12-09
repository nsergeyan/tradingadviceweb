from openai import OpenAI
import requests

GPT_API_KEY = "YOUR_OPENAI_KEY_HERE"

GEMINI_API_KEY = "AIzaSyCN7erQInU9KkNFYCAYrVBI3IgkQWrpg68"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def gpt(prompt : str) -> str:
    """
    Prompts ChatGPT with the given prompt and returns the llm response.
    """
    client = OpenAI(api_key=GPT_API_KEY)

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        #max_tokens=2500
    )
    return response.choices[0].message.content


def gemini(prompt : str) -> str:
    """
    Prompts Gemmini with the given prompt and returns the llm response.
    """

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    response = requests.post(
        GEMINI_API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()  #Raises error for HTTPS fails (like server not found, unauthorised, etc)

    data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]


def local_llm(prompt: str, system_prompt: str = None) -> str:
    """
    Prompts the local LLM with the given prompt and returns the llm response.
    """

    # If a system prompt is supplied, wrap it in Ollama's <system> tag
    if system_prompt:
        full_prompt = f"<system>\n{system_prompt}\n</system>\n{prompt}"
    else:
        full_prompt = prompt

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": full_prompt,
            "stream": False  # non-streaming mode for simplicity
        },
        timeout=300  # increase if processing long full-article prompts
    )

    response.raise_for_status()
    data = response.json()
    return data["response"].strip()


if __name__ == "__main__":
    print(local_llm("Hello, can you hear and who are you."))

