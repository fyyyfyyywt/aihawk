import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock
from loguru import logger

# Ensure src can be imported
sys.path.append(os.getcwd())

from src.aihawk_easy_applier import AIHawkEasyApplier

# Mock classes
class MockJob:
    def __init__(self):
        self.title = "Test Software Engineer"
        self.company = "Test Company"
        self.description = """
        We are looking for a Software Engineer with Python experience.
        Must know AI/ML and web development.
        """
        self.pdf_path = None
        self.cover_letter_path = None

class MockElement:
    def send_keys(self, path):
        logger.info(f"MOCK ELEMENT: Uploading file from path: {path}")

def test_n8n_api_generation(): # Renamed function
    logger.info("Starting n8n API generation test...")
    
    # 1. Mock dependencies (no real driver needed)
    mock_driver = MagicMock() # Mock driver
    mock_gpt_answerer = MagicMock()
    mock_resume_generator = MagicMock()
    
    try:
        # 2. Initialize Applier
        applier = AIHawkEasyApplier(mock_driver, None, [], mock_gpt_answerer, mock_resume_generator)
        
        # 3. Create mocks
        mock_element = MockElement()
        mock_job = MockJob()
        
        # 4. Call the modified method
        logger.info("Calling _create_and_upload_resume (which now calls n8n API)...")
        applier._create_and_upload_resume(mock_element, mock_job)
        
        if mock_job.pdf_path and os.path.exists(mock_job.pdf_path):
            logger.success(f"Test passed! Resume generated and 'uploaded': {mock_job.pdf_path}")
            # Optional: Clean up
            # os.remove(mock_job.pdf_path)
        else:
            logger.error("Test failed: File was not saved correctly.")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Test finished.")

if __name__ == "__main__":
    test_n8n_api_generation()
