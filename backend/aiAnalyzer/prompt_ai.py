import requests
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
            "stream": False
        },
        timeout=300
    )

    response.raise_for_status()
    data = response.json()
    return data["response"].strip()


if __name__ == "__main__":
    print(local_llm("Hello, can you hear and who are you."))

