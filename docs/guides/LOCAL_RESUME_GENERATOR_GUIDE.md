# Local Resume Generator Integration Guide

This branch (`local-resume-generator`) implements a custom resume generation strategy that bypasses the original AIHawk resume builder library. Instead, it integrates directly with your n8n webhook API to generate tailored PDF resumes.

## Architecture

1.  **Source**: AIHawk (Python/Selenium) acts as the orchestrator.
2.  **Trigger**: When a job application requires a resume upload.
3.  **Generation**: AIHawk sends a POST request to your n8n Webhook (`https://n8n.tiancreates.com/webhook/15b02df0-e24b-4b9f-8cb3-43cf83d59cd7`) containing:
    *   `masterResume`: Content from your `master_resume.md` file.
    *   `jobDescription`: The job description scraped from LinkedIn.
    *   `cf_token`: An empty string (as n8n no longer enforces Turnstile verification).
4.  **Output**: The n8n webhook returns a PDF binary, which is saved locally and then uploaded to LinkedIn.

## Prerequisites

1.  **Master Resume**: Ensure `master_resume.md` exists in the project root directory. This content is sent to n8n.
2.  **n8n Webhook**: The webhook URL is set to `https://n8n.tiancreates.com/webhook/15b02df0-e24b-4b9f-8cb3-43cf83d59cd7`. Ensure this n8n workflow is active and configured to:
    *   Receive POST requests.
    *   Process `masterResume` and `jobDescription` from the JSON payload.
    *   **Do not enforce Cloudflare Turnstile verification** (as confirmed, you have disabled it).
    *   Return the generated PDF as binary content in its HTTP response.

## Code Modifications

*   **`src/aihawk_easy_applier.py`**: The `_create_and_upload_resume` method has been completely rewritten to use Python's `requests` library to directly call your n8n webhook.
*   **`test_n8n_generation.py`**: A standalone test script to verify the generation process by making a direct API call to n8n (no real browser required).

## How to Run

### 1. Test the Generation Logic First
Run the test script to ensure your n8n connection and generation workflow are functioning correctly:

```bash
python test_n8n_generation.py
```
*   This script will print logs indicating the request to n8n and the saving of the PDF.
*   Check `generated_cv/` for the output PDF.

### 2. Run the Main Bot
Once the test passes, run the bot normally:

```bash
python main.py
```
When the bot encounters a "Upload Resume" field, it will automatically trigger your n8n webhook.