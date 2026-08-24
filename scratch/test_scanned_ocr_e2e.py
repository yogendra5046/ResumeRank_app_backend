import os
import requests
import fitz
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def test_scanned_pdf_e2e():
    # 1. Create a scanned PDF (render a text to a pixmap, then insert that image into the PDF)
    print("Generating simulated scanned PDF...")
    doc_temp = fitz.open()
    page_temp = doc_temp.new_page(width=400, height=300)
    page_temp.insert_text(
        fitz.Point(30, 50), 
        "John Doe\nSoftware Engineer\nEmail: john.doe@example.com\n\nSkills: Python, FastAPI, Docker, Kubernetes\n\nExperience:\n- Backend Engineer at TechCorp: Developed REST APIs using Python and FastAPI."
    )
    pix = page_temp.get_pixmap()
    img_bytes = pix.tobytes("png")
    doc_temp.close()
    
    # Create the final PDF containing ONLY the rendered image (no text layer)
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    rect = fitz.Rect(0, 0, 400, 300)
    page.insert_image(rect, stream=img_bytes)
    
    pdf_buffer = doc.write()
    doc.close()
    
    print(f"Generated PDF with image-only content. Size: {len(pdf_buffer)} bytes.")
    
    # 2. Call the backend API
    url = "http://127.0.0.1:9000/v1/analyze"
    headers = {
        "X-API-Key": "resumerank-pro-2026"
    }
    
    files = {
        "resume": ("scanned_resume.pdf", pdf_buffer, "application/pdf")
    }
    
    data = {
        "jd_text": "We are seeking a Python Backend Engineer with experience in FastAPI, Docker, and Kubernetes."
    }
    
    print("Sending request to /v1/analyze...")
    response = requests.post(url, headers=headers, files=files, data=data, timeout=60.0)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        print("Success! Analysis Result:")
        print(f"Score: {res_json.get('score')}%")
        print(f"Grade: {res_json.get('grade')}")
        print(f"Detected Persona: {res_json.get('professional_persona', {}).get('primary_persona')}")
        print("Found Skills:", [s['name'] for s in res_json.get('skills', [])])
    else:
        print(f"Failed! Response: {response.text}")

if __name__ == "__main__":
    test_scanned_pdf_e2e()
