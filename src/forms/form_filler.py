import time
import json
import os
import re
import traceback
import requests
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from loguru import logger
from Levenshtein import ratio
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import src.utils as utils

class FormFiller:
    def __init__(self, driver, gpt_answerer, resume_generator_manager):
        self.driver = driver
        self.gpt_answerer = gpt_answerer
        self.resume_generator_manager = resume_generator_manager
        self.all_data = self._load_questions_from_json()

    def _load_questions_from_json(self) -> List[dict]:
        output_file = 'data_folder/answers.json'
        try:
            with open(output_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_questions_to_json(self, question_data: dict) -> None:
        output_file = 'data_folder/answers.json'
        question_data['question'] = self._sanitize_text(question_data['question'])
        try:
            data = self._load_questions_from_json()
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            data.append(question_data)
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving question: {e}")

    def _sanitize_text(self, text: str) -> str:
        return re.sub(r'[\x00-\x1F\x7F]', '', text.lower().strip().replace('"', '').replace('\\', '').replace('\n', ' ').replace('\r', '').rstrip(','))

    def _find_best_matching_answer(self, question_text: str, question_type: str, options: List[str] = None) -> Optional[str]:
        sanitized_question = self._sanitize_text(question_text)
        best_match = None
        highest_score = 0.0
        THRESHOLD = 0.85

        for item in self.all_data:
            if item.get('type') != question_type:
                continue
            score = ratio(sanitized_question, item.get('question', ''))
            if score > highest_score:
                highest_score = score
                best_match = item

        if highest_score >= THRESHOLD:
            answer = best_match['answer']
            if options:
                normalized_options = [opt.lower().strip() for opt in options]
                if answer.lower().strip() in normalized_options:
                    return answer
            else:
                return answer
        return None

    def fill_up(self, job) -> None:
        try:
            try:
                easy_apply_content = self.driver.find_element(By.CLASS_NAME, 'jobs-easy-apply-content')
            except NoSuchElementException:
                easy_apply_content = self.driver.find_element(By.CLASS_NAME, 'artdeco-modal__content')
            
            elements = easy_apply_content.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__element')
            if not elements:
                elements = easy_apply_content.find_elements(By.CSS_SELECTOR, '[data-test-form-element]')
            if not elements:
                elements = easy_apply_content.find_elements(By.XPATH, ".//div[./label]")

            for element in elements:
                self._process_form_element(element, job)
        except Exception as e:
            logger.error(f"Failed to fill form: {e}")

    def _process_form_element(self, element: WebElement, job) -> None:
        if self._is_upload_field(element):
            self._handle_upload_fields(element, job)
        else:
            self._handle_form_section(element)

    def _handle_form_section(self, section: WebElement):
        if self._handle_terms_of_service(section): return
        if self._handle_radio_question(section): return
        if self._handle_textbox_question(section): return
        if self._handle_date_question(section): return
        if self._handle_dropdown_question(section): return

    def _is_upload_field(self, element: WebElement) -> bool:
        return bool(element.find_elements(By.XPATH, ".//input[@type='file']"))

    def _handle_upload_fields(self, element: WebElement, job) -> None:
        file_upload_elements = self.driver.find_elements(By.XPATH, "//input[@type='file']")
        for upload_element in file_upload_elements:
            parent = upload_element.find_element(By.XPATH, "..")
            self.driver.execute_script("arguments[0].classList.remove('hidden')", upload_element)
            output = self.gpt_answerer.resume_or_cover(parent.text.lower())
            
            if 'resume' in output:
                self._upload_resume(upload_element, job)
            elif 'cover' in output:
                self._create_and_upload_cover_letter(upload_element, job)

    def _upload_resume(self, element, job):
        if job.resume_path and os.path.exists(job.resume_path):
             element.send_keys(str(os.path.abspath(job.resume_path)))
        else:
             self._create_and_upload_resume_n8n(element, job)

    def _create_and_upload_resume_n8n(self, element, job):
        folder_path = 'generated_cv'
        os.makedirs(folder_path, exist_ok=True)
        timestamp = int(time.time())
        file_path_pdf = os.path.join(folder_path, f"n8n_resume_{timestamp}.pdf")
        
        try:
            with open("master_resume.md", 'r', encoding='utf-8') as f:
                master_resume_content = f.read()
            
            payload = {
                "masterResume": master_resume_content,
                "jobDescription": job.description,
                "cf_token": ""
            }
            response = requests.post("https://n8n.tiancreates.com/webhook/15b02df0-e24b-4b9f-8cb3-43cf83d59cd7", json=payload, timeout=120)
            response.raise_for_status()
            
            with open(file_path_pdf, "wb") as f:
                f.write(response.content)
            
            element.send_keys(os.path.abspath(file_path_pdf))
            job.pdf_path = os.path.abspath(file_path_pdf)
        except Exception as e:
            logger.error(f"N8N Resume Generation failed: {e}")
            raise

    def _create_and_upload_cover_letter(self, element, job):
        cover_letter_text = self.gpt_answerer.answer_question_textual_wide_range("Write a cover letter")
        folder_path = 'generated_cv'
        os.makedirs(folder_path, exist_ok=True)
        file_path_pdf = os.path.join(folder_path, f"Cover_Letter_{int(time.time())}.pdf")
        
        c = canvas.Canvas(file_path_pdf, pagesize=A4)
        c.drawString(100, 750, cover_letter_text[:500]) # Simple implementation for now
        c.save()
        
        element.send_keys(os.path.abspath(file_path_pdf))
        job.cover_letter_path = os.path.abspath(file_path_pdf)

    def _handle_terms_of_service(self, element: WebElement) -> bool:
        checkbox = element.find_elements(By.TAG_NAME, 'label')
        if checkbox and any(term in checkbox[0].text.lower() for term in ['terms of service', 'privacy policy']):
            checkbox[0].click()
            return True
        return False

    def _handle_radio_question(self, section: WebElement) -> bool:
        try:
            question = section.find_element(By.CLASS_NAME, 'jobs-easy-apply-form-element')
        except NoSuchElementException:
            question = section
        
        radios = question.find_elements(By.CLASS_NAME, 'fb-text-selectable__option')
        if not radios:
            radios = question.find_elements(By.CSS_SELECTOR, 'div[data-test-text-selectable-option]')
            
        if radios:
            question_text = section.text.split('\n')[0].lower()
            options = [radio.text.lower() for radio in radios]
            
            existing = self._find_best_matching_answer(question_text, 'radio', options)
            answer = existing if existing else self.gpt_answerer.answer_question_from_options(question_text, options)
            
            if not existing:
                self._save_questions_to_json({'type': 'radio', 'question': question_text, 'answer': answer})
                
            self._select_radio(radios, answer)
            return True
        return False

    def _select_radio(self, radios: List[WebElement], answer: str) -> None:
        for radio in radios:
            if answer in radio.text.lower():
                try:
                    radio.find_element(By.TAG_NAME, 'label').click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", radio.find_element(By.TAG_NAME, 'input'))
                return
        # Fallback to last
        try:
            radios[-1].find_element(By.TAG_NAME, 'label').click()
        except:
             pass

    def _handle_textbox_question(self, section: WebElement) -> bool:
        text_fields = section.find_elements(By.TAG_NAME, 'input') + section.find_elements(By.TAG_NAME, 'textarea')
        text_fields = [f for f in text_fields if f.tag_name == 'textarea' or f.get_attribute('type') in ['text', 'number', 'email', 'tel']]
        
        if text_fields:
            text_field = text_fields[0]
            question_text = section.find_element(By.TAG_NAME, 'label').text.lower()
            
            # Check for autofill
            time.sleep(1)
            if text_field.get_attribute('value'):
                return True
            
            is_numeric = self._is_numeric_field(text_field)
            if is_numeric:
                answer = self.gpt_answerer.answer_question_numeric(question_text)
            else:
                 existing = self._find_best_matching_answer(question_text, 'textbox')
                 answer = existing if existing else self.gpt_answerer.answer_question_textual_wide_range(question_text)
                 if not existing:
                     self._save_questions_to_json({'type': 'textbox', 'question': question_text, 'answer': answer})

            text_field.clear()
            text_field.send_keys(answer)
            return True
        return False

    def _is_numeric_field(self, field: WebElement) -> bool:
        return 'numeric' in field.get_attribute("id").lower() or field.get_attribute('type') == 'number'

    def _handle_date_question(self, section: WebElement) -> bool:
        date_fields = section.find_elements(By.CLASS_NAME, 'artdeco-datepicker__input ')
        if date_fields:
            date_field = date_fields[0]
            answer = self.gpt_answerer.answer_question_date().strftime("%Y-%m-%d")
            date_field.clear()
            date_field.send_keys(answer)
            return True
        return False

    def _handle_dropdown_question(self, section: WebElement) -> bool:
        dropdowns = section.find_elements(By.TAG_NAME, 'select')
        if dropdowns:
            dropdown = dropdowns[0]
            select = Select(dropdown)
            options = [o.text for o in select.options]
            question_text = section.text.split('\n')[0].lower()
            
            existing = self._find_best_matching_answer(question_text, 'dropdown', options)
            answer = existing if existing else self.gpt_answerer.answer_question_from_options(question_text, options)
            
            if not existing:
                self._save_questions_to_json({'type': 'dropdown', 'question': question_text, 'answer': answer})
                
            select.select_by_visible_text(answer)
            return True
        return False
