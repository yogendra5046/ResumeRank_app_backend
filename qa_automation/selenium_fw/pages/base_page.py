from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
from config.settings import EXPLICIT_WAIT

class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, EXPLICIT_WAIT)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def navigate_to(self, url):
        self.logger.info(f"Navigating to {url}")
        self.driver.get(url)
        
    def wait_for_element(self, locator, timeout=EXPLICIT_WAIT):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element {locator}")
            return None
            
    def click_element(self, locator):
        element = self.wait_for_element(locator)
        if element:
            self.logger.info(f"Clicking element {locator}")
            element.click()
            return True
        return False
        
    def enter_text(self, locator, text):
        element = self.wait_for_element(locator)
        if element:
            self.logger.info(f"Entering text into {locator}")
            element.clear()
            element.send_keys(text)
            return True
        return False
        
    def get_text(self, locator):
        element = self.wait_for_element(locator)
        if element:
            return element.text
        return ""
        
    def is_displayed(self, locator):
        try:
            element = self.wait_for_element(locator, timeout=5)
            return element.is_displayed() if element else False
        except:
            return False
