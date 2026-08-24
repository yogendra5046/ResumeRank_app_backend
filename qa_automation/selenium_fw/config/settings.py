import os
from dotenv import load_dotenv

load_dotenv()

# Base URL to test against. Default to localhost for safety, but CI sets it to GitHub Pages.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

# Headless mode config
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Timeouts
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 20

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure dirs exist
for d in [REPORTS_DIR, SCREENSHOTS_DIR, LOGS_DIR, os.path.join(REPORTS_DIR, "Excel"), os.path.join(REPORTS_DIR, "HTML"), os.path.join(REPORTS_DIR, "Summary")]:
    os.makedirs(d, exist_ok=True)
