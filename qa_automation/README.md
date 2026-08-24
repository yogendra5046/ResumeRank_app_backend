# Complete QA Automation & CI/CD Framework

This repository contains the enterprise-grade End-to-End testing frameworks for both web (Selenium) and mobile (Appium), along with comprehensive GitHub Actions deployment pipelines.

## Project Structure

```
qa_automation/
│
├── selenium_fw/            # Web Automation (400+ Test Cases)
│   ├── config/             # Environment configs (BASE_URL, headless mode)
│   ├── pages/              # Page Object Model classes
│   ├── tests/              # Pytest parameterized test suites
│   ├── utils/              # Loggers, Excel generators, Markdown summary
│   ├── reports/            # Output directory for HTML, Excel, and JSON
│   ├── screenshots/        # Output directory for failure captures
│   └── requirements.txt    # Python dependencies
│
└── appium_fw/              # Mobile Automation (300+ Test Cases)
    └── tests/              # Appium Pytest suites
```

## 1. Local Execution Guide

**Prerequisites:**
- Python 3.11+
- Google Chrome installed
- ChromeDriver (handled automatically by `webdriver-manager`)
- Appium Server (if running mobile tests)

**Setup:**
1. Navigate to the Web Automation folder:
   ```bash
   cd qa_automation/selenium_fw
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the complete suite:
   ```bash
   # You can set BASE_URL in your environment or rely on the default localhost fallback
   BASE_URL=https://your-preview-url.com pytest tests/
   ```
4. View Reports:
   - Excel: `qa_automation/selenium_fw/reports/Excel/Automation_Test_Report.xlsx`
   - HTML: `qa_automation/selenium_fw/reports/HTML/execution-report.html`

## 2. CI/CD Execution Guide

The CI/CD pipeline is fully automated via GitHub Actions (`.github/workflows/deploy-and-test.yml`).

**Workflow Flow:**
1. **Trigger**: Push to `main`, Pull Request to `main`, or Manual Trigger (Workflow Dispatch).
2. **Build & Deploy**: The Flutter web app is built and deployed to GitHub Pages.
3. **Verify Deployment**: The pipeline pings the live URL to ensure an HTTP 200 response.
4. **Test Execution**: The Selenium framework automatically executes 400+ E2E tests against the **LIVE** GitHub Pages deployment.
5. **Artifact Upload**: Excel Reports, HTML Reports, Screenshots, and Logs are uploaded and retained for 30 days.
6. **Summary Publication**: A customized Markdown summary is appended to the GitHub Actions execution page.

**Manual Dispatch Configuration:**
When triggering manually, you can optionally override the `base_url` parameter to test against a specific staging environment.

## 3. Troubleshooting Guide

**Issue: Tests fail due to `ConnectionRefusedError` or `Timeout` in CI/CD**
- **Cause**: The deployment might not be fully propagated by GitHub Pages before the tests start.
- **Resolution**: Check the "Wait for Deployment" step duration in the workflow. Increase the sleep timer if necessary.

**Issue: Screenshots are missing for failed tests**
- **Cause**: The test might be failing before the driver is fully initialized, or the `conftest.py` hook is missing the driver context.
- **Resolution**: Ensure the fixture is passing `request.cls.driver = driver` properly and the hook can access `item.funcargs.get("driver")`.

**Issue: Pipeline fails even though pass percentage is high**
- **Cause**: The GitHub Action is configured to fail the entire job if *any* test fails to maintain strict quality gates (or if the pass rate drops below 95%).
- **Resolution**: Review the step failure threshold. Currently, `pytest` will exit with code `1` if any test fails, which fails the workflow step unless `|| true` or `continue-on-error` is used. The pipeline is currently configured to attempt summary generation regardless of pytest's exit code (`if: always()`).

**Issue: Appium Mobile Tests failing**
- **Cause**: Missing Appium server or incorrect APK path.
- **Resolution**: Start `appium` locally on port 4723 and update the `.apk` path in `appium_fw/tests/test_mobile_suite.py`.

## 4. Excel Report Requirements Implemented
The `utils/excel_manager.py` generates the exact specifications requested:
- `Automation_Test_Report.xlsx` with multiple sheets (Executed, Passed, Failed, Skipped, Metrics, Defect Summary).
- Separate `Passed_Test_Cases.xlsx`
- Separate `Failed_Test_Cases.xlsx`
- Separate `Summary_Report.xlsx`

## 5. Artifact Management
All logs, screenshots, and reports are managed via `actions/upload-artifact@v4` in the deployment workflow.
