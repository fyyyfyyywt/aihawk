# AIHawk (local-resume-generator branch) - Release Notes

## Version: v1.0.0-local-resume
## Release Date: 2025-12-02

---

## 🚀 Key Features & Improvements

This branch introduces a significant change in how AIHawk generates resumes, replacing the default `lib_resume_builder_AIHawk` library's generation with a custom, API-driven approach.

*   **Custom Resume Generation Integration**: AIHawk now integrates directly with a user-provided n8n webhook (or any compatible HTTP endpoint) to generate job-tailored PDF resumes. This allows developers to use their preferred resume generation backend, detached from AIHawk's internal LLM-based generation.
*   **`master_resume.md` Support**: The system now reads the user's master resume content directly from `master_resume.md` (located in the project root) for submission to the custom generation service.
*   **Gemini AI Model Support (inherited from `main` branch)**: Full compatibility and integration with Google Gemini models for other LLM-driven tasks (e.g., answering application questions), leveraging previous patches to the `lib_resume_builder_AIHawk` internal components.
*   **Enhanced Testability**: A dedicated test script (`test_n8n_generation.py`) is provided to verify the custom resume generation API call independently.

## 🔄 Differences from `main` Branch

*   **Resume Generation Logic**: The primary difference is the complete replacement of `AIHawkEasyApplier._create_and_upload_resume` method. It no longer calls `self.resume_generator_manager.pdf_base64`.
*   **Dependency on External Service**: This branch now relies on an external HTTP service (e.g., n8n webhook) for resume PDF generation, rather than the internal Python library.
*   **Removed Local HTML Automation Attempt**: Earlier attempts to automate a local HTML page via Selenium for generation were reverted for a more direct API integration.

## 🛠️ Installation & Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/fyyyfyyywt/aihawk.git
    cd aihawk
    ```
2.  **Switch to this Branch**:
    ```bash
    git checkout local-resume-generator
    ```
3.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  **Install Dependencies**:
    ```bash
    .\venv\Scripts\pip install -r requirements.txt
    ```
5.  **Apply Patches for Gemini Support**:
    The patches to `lib_resume_builder_AIHawk` (for Gemini support) are documented in `GEMINI_SETUP_NOTES.md` and their files are backed up in the `patches/` directory. You will need to manually apply these patches to your `venv` if you wish to use Gemini for other LLM tasks.
6.  **Configure `data_folder/config.yaml` & `data_folder/secrets.yaml`**:
    *   Place your `config.yaml` and `secrets.yaml` in the `data_folder/` directory. (Refer to the `README.md` for template details).
    *   Ensure `llm_model_type: gemini` and `llm_model: your_gemini_model_name` are correctly set in `config.yaml`.
    *   Your Google Gemini API Key must be in `secrets.yaml`.
7.  **Prepare `master_resume.md`**: Place your plain text/markdown master resume in the project root directory.

## 🚀 Usage

### 1. Test Custom Resume Generation (Recommended)

Before running the full bot, verify your n8n integration:

```bash
.\venv\Scripts\python test_n8n_generation.py
```
This script will:
*   Read `master_resume.md`.
*   Send a simulated job description and your master resume to your n8n webhook (`https://n8n.tiancreates.com/webhook/15b02df0-e24b-4b9f-8cb3-43cf83d59cd7`).
*   Save the returned PDF to `generated_cv/`.
*   Confirm the success or log any errors.

### 2. Run AIHawk Bot

Once the test passes, you can launch the main AIHawk application:

```bash
.\venv\Scripts\python main.py
```
The bot will proceed as follows:
1.  Open a Chrome browser and navigate to LinkedIn.
2.  **Manual Login**: You will need to manually log in to LinkedIn in the opened browser window.
3.  Search for jobs based on your `config.yaml` settings.
4.  When an "Easy Apply" job requires a resume upload, it will trigger the custom n8n resume generation process.
5.  The generated PDF will be automatically uploaded.

## ⚠️ Important Notes

*   **n8n Webhook Configuration**: Ensure your n8n workflow for `https://n8n.tiancreates.com/webhook/15b02df0-e24b-4b9f-8cb3-43cf83d59cd7` is **active** and **does NOT enforce Cloudflare Turnstile verification**, as confirmed during development. It should accept JSON payload with `masterResume` and `jobDescription` and return a PDF binary.
*   **API Key Security**: `secrets.yaml` should **NEVER** be committed to version control. It contains sensitive API keys.
*   **Error Handling**: If n8n returns an error (e.g., 5xx status), AIHawk will log it and attempt to continue or raise an exception, depending on the error type.
*   **LinkedIn Changes**: Be aware that LinkedIn's UI/UX can change, which may break Selenium locators.

## Known Issues / Limitations

*   Currently, the `lib_resume_builder_AIHawk` library is still patched in `venv` directly. While these patches are committed to the `patches/` directory for backup, they are not automatically applied upon `pip install`. Users must manually replace the original files in `venv/Lib/site-packages/lib_resume_builder_AIHawk/` with the patched versions from `patches/` if they reinstall dependencies. This is a temporary solution until the upstream library is updated.
