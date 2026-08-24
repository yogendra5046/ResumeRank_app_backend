import os
import io
import base64
import requests
import fitz
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def test_groq_vision():
    # 1. Create a simple PDF and render it to a PNG pixmap
    doc = fitz.open()
    page = doc.new_page(width=300, height=100)
    page.insert_text(fitz.Point(20, 50), "Hello Groq OCR World!")
    
    pix = page.get_pixmap()
    png_bytes = pix.tobytes("png")
    doc.close()
    
    # 2. Encode to base64
    base64_image = base64.b64encode(png_bytes).decode("utf-8")
    
    # 3. Call Groq
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_key:
        print("GROQ_API_KEY is not set.")
        return
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen/qwen3.6-27b",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Extract all text from this scanned image verbatim. Do not add any extra conversational text."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    print("Calling Groq Vision API...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        print("Transcription:")
        print(res_json["choices"][0]["message"]["content"])
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_groq_vision()
