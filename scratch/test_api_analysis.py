import requests
import io
import fitz

def create_dummy_pdf(text_content):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 50), text_content)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()

def test_analyze():
    # 1. Prepare dummy PDF resume content
    resume_text = "Skills: Python, FastAPI, Docker, SQL. Experience: Software Engineer with 2 years of experience."
    pdf_bytes = create_dummy_pdf(resume_text)
    
    # 2. Prepare JD text (brief metadata format similar to frontend)
    jd_text = (
        "Job Title: Startup Ecosystem Associate\n"
        "Company: Jobgether\n\n"
        "Description:\n"
        "This opportunity is ideal for a curious and organized professional who wants hands-on exposure to the operations behind a global startup...\n\n"
        "URL: https://www.adzuna.in/details/5853729058?utm_medium=api&utm_source=f3cf569d"
    )
    
    # 3. Send request
    url = "http://localhost:9000/v1/analyze"
    headers = {
        "X-API-Key": "resumerank-pro-2026"
    }
    files = {
        "resume": ("resume.pdf", pdf_bytes, "application/pdf")
    }
    data = {
        "jd_text": jd_text
    }
    
    print("Sending request to /v1/analyze...")
    response = requests.post(url, headers=headers, files=files, data=data)
    
    print(f"Status Code: {response.status_code}")
    try:
        print("Response JSON:")
        import json
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(f"Response Text: {response.text}")

if __name__ == "__main__":
    test_analyze()
