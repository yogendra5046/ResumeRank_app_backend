import pytest
import os
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config.settings import HEADLESS, SCREENSHOTS_DIR

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.excel_manager import generate_excel_reports

test_results = []

@pytest.fixture(scope="function")
def driver(request):
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)
    
    request.cls.driver = driver
    yield driver
    driver.quit()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call":
        test_name = item.name
        module_name = item.module.__name__
        markers = [mark.name for mark in item.iter_markers()]
        module = markers[0] if markers else "General"
        priority = "High" if "regression" in markers or "authentication" in markers else "Medium"
        
        status = "Passed" if rep.passed else "Failed" if rep.failed else "Skipped"
        duration = round(rep.duration, 2)
        
        result_dict = {
            "test_id": f"TC_{hash(test_name) % 10000:04d}",
            "module": module.capitalize(),
            "test_name": test_name,
            "status": status,
            "execution_time": duration,
            "priority": priority,
            "failure_reason": str(rep.longrepr) if rep.failed else ""
        }
        test_results.append(result_dict)
        
        if rep.failed:
            driver = item.funcargs.get("driver")
            if driver:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_name = f"{test_name}_{timestamp}.png"
                screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)
                driver.save_screenshot(screenshot_path)

def pytest_sessionfinish(session, exitstatus):
    print(f"Session finished with status {exitstatus}. Generating Excel reports...")
    generate_excel_reports(test_results)
