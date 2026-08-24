import asyncio
import os
import json
from groq import AsyncGroq
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test_groq():
    groq_key = os.environ.get("GROQ_API_KEY")
    print(f"Key loaded: {bool(groq_key)}")
    
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncGroq(api_key=groq_key, http_client=http_client)
    
    primary_model = "llama-3.3-70b-versatile"
    system_prompt = "You are a helpful assistant. Output a JSON object with a single key 'status' set to 'ok'."
    user_prompt = "Test."

    try:
        completion = await client.chat.completions.create(
            model=primary_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=6000,
            response_format={"type": "json_object"},
            timeout=90.0,
        )
        print("Success!")
        print(completion.choices[0].message.content)
    except Exception as e:
        print("Failed!")
        print(type(e))
        print(e)

if __name__ == "__main__":
    asyncio.run(test_groq())
