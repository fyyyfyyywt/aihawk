import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver import ActionChains
from loguru import logger
import src.utils as utils

class FormNavigator:
    def __init__(self, driver):
        self.driver = driver

    def check_for_premium_redirect(self, job, max_attempts=3):
        current_url = self.driver.current_url
        attempts = 0

        while "linkedin.com/premium" in current_url and attempts < max_attempts:
            logger.warning("Redirected to AIHawk Premium page. Attempting to return to job page.")
            attempts += 1
            self.driver.get(job.link)
            time.sleep(2)
            current_url = self.driver.current_url

        if "linkedin.com/premium" in current_url:
            logger.error(f"Failed to return to job page after {max_attempts} attempts. Cannot apply for the job.")
            raise Exception(f"Redirected to AIHawk Premium page and failed to return after {max_attempts} attempts. Job application aborted.")

    def find_easy_apply_button(self, job):
        logger.debug("Searching for 'Easy Apply' button")
        attempt = 0
        
        search_methods = [
            {'description': "ID 'jobs-apply-button-id'", 'xpath': '//button[@id="jobs-apply-button-id"]'},
            {'description': "find all 'Easy Apply' buttons", 'find_elements': True, 'xpath': '//button[contains(@class, "jobs-apply-button") and contains(normalize-space(.), "Easy Apply")]'},
            {'description': "'aria-label' containing 'Easy Apply to'", 'xpath': '//button[contains(@aria-label, "Easy Apply to")]'},
            {'description': "button text search", 'xpath': '//button[contains(normalize-space(.), "Easy Apply") or contains(normalize-space(.), "Apply now")]'},
            {'description': "Any button with 'jobs-apply-button' class", 'xpath': '//button[contains(@class, "jobs-apply-button")]'}
        ]

        while attempt < 2:
            self.check_for_premium_redirect(job)
            self.scroll_page()

            for method in search_methods:
                try:
                    logger.debug(f"Attempting search using {method['description']}")
                    if method.get('find_elements'):
                        buttons = self.driver.find_elements(By.XPATH, method['xpath'])
                        if buttons:
                            for index, button in enumerate(buttons):
                                try:
                                    self._scroll_to_element(button)
                                    WebDriverWait(self.driver, 5).until(EC.visibility_of(button))
                                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(button))
                                    return button
                                except Exception as e:
                                    logger.warning(f"Button {index + 1} found but not clickable: {e}")
                    else:
                        button = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, method['xpath'])))
                        self._scroll_to_element(button)
                        WebDriverWait(self.driver, 5).until(EC.visibility_of(button))
                        WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(button))
                        return button
                except TimeoutException:
                    logger.warning(f"Timeout using {method['description']}")
                except Exception as e:
                    logger.warning(f"Failed using {method['description']}: {e}")

            self.check_for_premium_redirect(job)
            if attempt == 0:
                self.driver.refresh()
                time.sleep(random.randint(3, 5))
            attempt += 1

        raise Exception("No clickable 'Easy Apply' button found")

    def next_or_submit(self):
        logger.debug("Clicking 'Next' or 'Submit' button")
        try:
            next_button = self.driver.find_element(By.CLASS_NAME, "artdeco-button--primary")
            button_text = next_button.text.lower()
            self._scroll_to_element(next_button)
            
            if 'submit application' in button_text:
                logger.debug("Submit button found")
                self.unfollow_company()
                time.sleep(random.uniform(1.5, 2.5))
                self._click_button(next_button)
                time.sleep(random.uniform(1.5, 2.5))
                return True
            
            time.sleep(random.uniform(1.5, 2.5))
            self._click_button(next_button)
            time.sleep(random.uniform(3.0, 5.0))
            self.check_for_errors()
            return False
        except NoSuchElementException:
            logger.debug("Next/Submit button not found.")
            raise

    def check_for_errors(self):
        error_elements = self.driver.find_elements(By.CLASS_NAME, 'artdeco-inline-feedback--error')
        if error_elements:
            logger.error(f"Form submission errors: {[e.text for e in error_elements]}")
            raise Exception(f"Failed answering or file upload. {str([e.text for e in error_elements])}")

    def unfollow_company(self):
        try:
            logger.debug("Unfollowing company")
            follow_checkbox = self.driver.find_element(By.XPATH, "//label[contains(.,'to stay up to date with their page.')]")
            follow_checkbox.click()
        except Exception:
            pass

    def discard_application(self):
        try:
            logger.debug("Discarding application")
            self.driver.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
            time.sleep(random.uniform(2, 3))
            self.driver.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')[0].click()
            time.sleep(random.uniform(2, 3))
        except Exception as e:
            logger.warning(f"Failed to discard application: {e}")

    def scroll_page(self):
        scrollable_element = self.driver.find_element(By.TAG_NAME, 'html')
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=False)
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=True)

    def _scroll_to_element(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)

    def _click_button(self, element):
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
