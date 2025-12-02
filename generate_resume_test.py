import base64
import yaml
from pathlib import Path
import os
import sys
from lib_resume_builder_AIHawk import Resume, StyleManager, FacadeManager, ResumeGenerator
from loguru import logger



def generate_test_resume():
    logger.remove()  # Remove default logger to customize
    logger.add(sys.stderr, level="INFO") # Add a logger for INFO level output

    data_folder = Path("data_folder")
    output_folder = data_folder / 'output'
    output_folder.mkdir(exist_ok=True)

    secrets_path = data_folder / 'secrets.yaml'
    config_path = data_folder / 'config.yaml'
    plain_text_resume_path = data_folder / 'plain_text_resume.yaml'

    if not secrets_path.exists():
        logger.error(f"Error: secrets.yaml not found at {secrets_path}")
        return
    if not config_path.exists():
        logger.error(f"Error: config.yaml not found at {config_path}")
        return
    if not plain_text_resume_path.exists():
        logger.error(f"Error: plain_text_resume.yaml not found at {plain_text_resume_path}")
        return

    # Load secrets
    with open(secrets_path, 'r', encoding='utf-8') as f:
        secrets = yaml.safe_load(f)
    llm_api_key = secrets.get('llm_api_key')
    if not llm_api_key:
        logger.error("Error: llm_api_key not found in secrets.yaml. Please update it.")
        return

    # Load config for LLM model type
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    llm_model_type = config.get('llm_model_type', 'openai') # Default to openai if not specified
    llm_model = config.get('llm_model', 'gpt-4o-mini')

    # Load plain text resume
    with open(plain_text_resume_path, 'r', encoding='utf-8') as f:
        plain_text_resume_content = f.read()

    import lib_resume_builder_AIHawk
    import inspect
    logger.info(f"Library location: {lib_resume_builder_AIHawk.__file__}")
    logger.info(f"FacadeManager init signature: {inspect.signature(FacadeManager.__init__)}")

    try:
        resume_object = Resume(plain_text_resume_content)
        style_manager = StyleManager()
        resume_generator = ResumeGenerator()

        # Define a dummy job description
        dummy_job_description = """
        We are seeking a highly motivated and skilled Software Engineer to join our dynamic team.
        The ideal candidate will have experience in Python, AI/ML, and web development.
        Responsibilities include designing, developing, and maintaining software applications,
        collaborating with cross-functional teams, and contributing to all phases of the development lifecycle.
        Experience with natural language processing and cloud platforms (AWS, Azure, GCP) is a plus.
        """

        # Initialize FacadeManager with required parameters
        resume_generator_manager = FacadeManager(llm_api_key, style_manager, resume_generator, resume_object, output_folder, llm_model_type, llm_model)

        # Allow user to choose a style interactively
        logger.info("Please choose a resume style in the console when prompted by the resume builder library.")
        resume_generator_manager.choose_style()
        
        logger.info("Generating resume for a dummy job description...")
        resume_pdf_base64 = resume_generator_manager.pdf_base64(job_description_text=dummy_job_description)

        if resume_pdf_base64:
            output_pdf_path = output_folder / "generated_resume_test.pdf"
            with open(output_pdf_path, "wb") as f:
                f.write(base64.b64decode(resume_pdf_base64))
            logger.success(f"Test resume generated successfully at: {output_pdf_path}")
        else:
            logger.error("Failed to generate resume (empty content returned).")

    except Exception as e:
        logger.error(f"An error occurred during resume generation: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    generate_test_resume()
