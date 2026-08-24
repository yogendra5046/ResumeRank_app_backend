import socket
import asyncio
from groq import AsyncGroq
import os
from dotenv import load_dotenv

load_dotenv()

# Monkey patch socket to force IPv4
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = new_getaddrinfo

async def main():
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Hello!"}],
            timeout=10.0
        )
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
