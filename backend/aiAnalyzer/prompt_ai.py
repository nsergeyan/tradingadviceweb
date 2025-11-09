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
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500
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

def local_llm(prompt : str) -> str:
    """Prompts the local llm with the given prompt and returns the output of the llm"""
    response = requests.post(
        "http://localhost:11434/api/generate", #This port should be the same, even if running llama not in docker
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        },
        timeout=1000
    )
    response.raise_for_status()
    data = response.json()
    return data["response"].strip()

if __name__ == "__main__":
    print(local_llm("Hello, can you hear and who are you."))

