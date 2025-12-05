import time
import random
import traceback
from typing import List, Tuple, Any, Optional

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ActionChains

from src.forms.form_navigator import FormNavigator
from src.forms.form_filler import FormFiller

class JobScoreTooLowException(Exception):
    pass

class AIHawkEasyApplier:
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List[Tuple[str, str, str]],
                 gpt_answerer: Any, resume_generator_manager):
        logger.debug("Initializing AIHawkEasyApplier")
        self.driver = driver
        self.resume_path = resume_dir
        self.set_old_answers = set_old_answers
        self.gpt_answerer = gpt_answerer
        self.resume_generator_manager = resume_generator_manager
        
        self.navigator = FormNavigator(driver)
        # Passing self.gpt_answerer and resume_generator_manager to FormFiller
        self.form_filler = FormFiller(driver, gpt_answerer, resume_generator_manager)

    def apply_to_job(self, job: Any) -> None:
        logger.debug(f"Applying to job: {job}")
        try:
            self.job_apply(job)
            logger.info(f"Successfully applied to job: {job.title}")
        except JobScoreTooLowException as e:
            logger.warning(f"Skipping job: {job.title}. Reason: {e}")
            raise e
        except Exception as e:
            logger.error(f"Failed to apply to job: {job.title}, error: {str(e)}")
            raise e

    def job_apply(self, job: Any):
        logger.debug(f"Starting job application for job: {job}")
        try:
            self.driver.get(job.link)
            time.sleep(random.uniform(3, 5))
            self.navigator.check_for_premium_redirect(job)
            self.driver.execute_script("document.activeElement.blur();")
            
            easy_apply_button = self.navigator.find_easy_apply_button(job)
            
            logger.debug("Retrieving job description")
            job_description = self._get_job_description()
            job.set_job_description(job_description)
            
            score = self.gpt_answerer.score_job_match(job_description)
            if score < 70:
                raise JobScoreTooLowException(f"Job match score {score} is below threshold 70.")
            
            recruiter_link = self._get_job_recruiter()
            job.set_recruiter_link(recruiter_link)
            
            ActionChains(self.driver).move_to_element(easy_apply_button).click().perform()
            self.gpt_answerer.set_job(job)
            
            self._fill_application_form(job)

        except JobScoreTooLowException:
            raise
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"Failed to apply to job: {job}, error: {tb_str}")
            self.navigator.discard_application()
            raise Exception(f"Failed to apply to job! Original exception:\nTraceback:\n{tb_str}")

    def _fill_application_form(self, job):
        while True:
            self.form_filler.fill_up(job)
            if self.navigator.next_or_submit():
                break

    def _get_job_description(self) -> str:
        # Kept local as it's specific to the job page structure before application
        try:
            try:
                see_more = self.driver.find_element(By.XPATH, '//button[@aria-label="Click to see more description"]')
                ActionChains(self.driver).move_to_element(see_more).click().perform()
                time.sleep(2)
            except Exception:
                pass

            try:
                description = self.driver.find_element(By.CLASS_NAME, 'jobs-description-content__text').text
            except Exception:
                description = self.driver.find_element(By.ID, 'job-details').text
            return description
        except Exception as e:
             raise Exception(f"Job description not found: {e}")

    def _get_job_recruiter(self):
        try:
            hiring_team = self.driver.find_element(By.XPATH, '//h2[text()="Meet the hiring team"]')
            recruiter_elements = hiring_team.find_elements(By.XPATH, './/following::a[contains(@href, "linkedin.com/in/")]')
            if recruiter_elements:
                return recruiter_elements[0].get_attribute('href')
        except Exception:
            return ""
        return ""
