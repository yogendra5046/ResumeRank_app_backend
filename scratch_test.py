import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
groq_key = os.environ.get("GROQ_API_KEY")

async def test():
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=groq_key)
        resp = await client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": "hello"}]
        )
        print("Success:", resp.choices[0].message.content)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
