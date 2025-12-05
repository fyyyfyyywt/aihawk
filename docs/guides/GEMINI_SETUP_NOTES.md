# Gemini Support Implementation Guide for AIHawk Resume Builder

This document serves as a comprehensive guide to the modifications applied to the `lib_resume_builder_AIHawk` library (version 0.1) to enable support for Google Gemini models (e.g., `gemini-2.5-pro`, `gemini-1.5-flash`).

**Status**: ✅ Implemented & Verified
**Date**: 2025-12-02

## 1. Problem Overview

The original `lib_resume_builder_AIHawk` library had the following limitations that prevented Gemini usage:
*   **Hardcoded OpenAI**: It explicitly instantiated `ChatOpenAI` clients, ignoring any other configuration.
*   **Missing Configuration**: There was no mechanism to pass a custom model name or type into the library's core logic.
*   **Bugs**: A critical `AttributeError` in the `LoggerChatModel` class caused crashes during error handling.
*   **LangChain Compatibility**: The Google GenAI integration in LangChain (`ChatGoogleGenerativeAI`) is stricter than OpenAI's regarding input formats, causing `ValueError` when receiving `ChatPromptValue` objects directly.

## 2. Quick Fix Guide (Modified Files)

The following files within the python virtual environment (`venv/Lib/site-packages/`) were modified:

1.  `lib_resume_builder_AIHawk/config.py`
2.  `lib_resume_builder_AIHawk/manager_facade.py`
3.  `lib_resume_builder_AIHawk/gpt_resume_job_description.py`

## 3. Detailed Code Changes

### A. Global Configuration Expansion
**File**: `lib_resume_builder_AIHawk/config.py`

**Change**: Added fields to store the selected LLM model type and model name.

```python
class GlobalConfig:
    def __init__(self):
        # ... existing fields ...
        self.API_KEY: str = None
        self.LLM_MODEL_TYPE: str = "openai"  # <--- Added: Store model type (gemini/openai)
        self.LLM_MODEL: str = None           # <--- Added: Store specific model name (e.g., gemini-2.5-pro)
        self.html_template = """..."""
```

### B. Parameter Propagation
**File**: `lib_resume_builder_AIHawk/manager_facade.py`

**Change**: Updated `FacadeManager.__init__` to accept model configuration from the main application and store it globally.

```python
# Updated Constructor Signature
def __init__(self, api_key, style_manager, resume_generator, resume_object, log_path, llm_model_type="openai", llm_model=None):
    # ... existing code ...
    global_config.API_KEY = api_key
    
    # <--- Added Lines --->
    global_config.LLM_MODEL_TYPE = llm_model_type
    global_config.LLM_MODEL = llm_model
    # <--- End Added Lines --->
    
    self.style_manager = style_manager
    # ...
```

### C. Core Logic & Gemini Integration
**File**: `lib_resume_builder_AIHawk/gpt_resume_job_description.py`

This file received the most significant changes.

#### 1. Imports
Added necessary LangChain Google GenAI imports and `ChatPromptValue` for type checking.

```python
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompt_values import ChatPromptValue
```

#### 2. Bug Fix: LoggerChatModel
Fixed `AttributeError: 'LoggerChatModel' object has no attribute 'logger'` by using the global `logger` object instead of `self.logger`.

```python
# Inside LoggerChatModel.__call__ exception handling:
# Before: self.logger.error(...)
# After: logger.error(...)
```

#### 3. Compatibility Fix: ChatPromptValue Conversion
Fixed `ValueError: Unexpected message with type <class 'tuple'>` by converting `ChatPromptValue` to a list of messages before passing to Gemini.

```python
# Inside LoggerChatModel.__call__:
# Before: reply = self.llm(messages)

# After:
if isinstance(messages, ChatPromptValue):
    messages_to_send = messages.to_messages()
else:
    messages_to_send = messages
reply = self.llm(messages_to_send)
```

#### 4. Dynamic Model Initialization
Updated `LLMResumeJobDescription.__init__` to initialize the correct LLM based on `global_config`.

```python
def __init__(self, api_key, strings):
    # Check if the user selected Gemini
    if getattr(global_config, "LLM_MODEL_TYPE", "openai") == "gemini":
        # Use specific model name from config, fallback to gemini-pro if missing
        model_name = getattr(global_config, "LLM_MODEL", None) or "gemini-pro"
        
        self.llm_cheap = LoggerChatModel(ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=api_key, 
            temperature=0.4
        ))
        # Use standard text-embedding-004 for Gemini
        self.llm_embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=api_key
        )
    else:
        # Fallback to original OpenAI implementation
        self.llm_cheap = LoggerChatModel(ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=api_key, temperature=0.4))
        self.llm_embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    self.strings = strings
```

## 4. Usage

To use Gemini, ensure your `config.yaml` is set as follows:

```yaml
llm_model_type: gemini
llm_model: gemini-2.5-pro  # Or gemini-1.5-flash, etc.
```

Ensure your `secrets.yaml` contains a valid Google Gemini API key.

## 5. Debugging Log (Lessons Learned)

*   **Silent Failures**: The library's retry mechanism (`max_retries=15`) combined with exponential backoff can make the program appear to hang when API keys are invalid. Using `print(..., flush=True)` inside `except` blocks is crucial for diagnosing these loops.
*   **Hardcoding Risks**: Initially hardcoding `gemini-1.5-flash` caused 404 errors when the API expected a different model or the user wanted a different one. Always propagate configuration values.
*   **LangChain Differences**: OpenAI components in LangChain are often more permissive with input types than Google GenAI components. Explicit type conversion (`to_messages()`) is safer.
*   **`NameError` for `ChatPromptValue`**: Forgetting to import `ChatPromptValue` when introducing `isinstance(messages, ChatPromptValue)` caused a `NameError`. Always ensure all referenced types are imported.
*   **Incorrect `dummy_job_description` scope**: Accidentally moving the definition of `dummy_job_description` below its usage in `generate_resume_test.py` resulted in a `NameError`. Variable definitions must precede their first use.

## 6. Optimizations and Fixes (2025-12-02)

Several optimizations were applied to the main application (`src/`) to improve efficiency, robustness, and cost-effectiveness.

### A. Lazy Summarization (Cost Saving)
*   **File**: `src/llm/llm_manager.py`
*   **Problem**: The bot was summarizing the job description via LLM immediately upon selecting a job, even if the application form was simple (e.g., only autofilled fields) and the summary was never needed.
*   **Solution**: Removed the immediate call to `summarize_job_description` in `set_job`. The summary is now only generated if explicitly requested (though currently it appears unused, essentially disabling it to save costs).

### B. Autofill Wait Logic (Efficiency)
*   **File**: `src/aihawk_easy_applier.py`
*   **Problem**: The bot often attempted to answer questions using the LLM (like phone numbers) that LinkedIn was in the process of autofilling, leading to race conditions and unnecessary API calls.
*   **Solution**: Added a wait loop (up to 2 seconds) in `_find_and_handle_textbox_question` to check for browser autofill before deciding to call the LLM.

### C. Radio Button & Dropdown Improvements (Robustness)
*   **File**: `src/aihawk_easy_applier.py`
*   **Problem**:
    *   New LinkedIn HTML structures (using `data-test-text-selectable-option`) caused the bot to miss some radio button questions.
    *   Clicking radio labels sometimes failed silently.
    *   Logs were flooded with hundreds of country codes from dropdowns.
*   **Solution**:
    *   Updated `fill_up` to check for `[data-test-form-element]` selectors.
    *   Updated `_select_radio` to robustly try clicking the input element if the label click fails.
    *   Truncated dropdown option logging to show only the first 5 options.

### D. Logger Crash Fix (Stability)
*   **File**: `src/llm/llm_manager.py`
*   **Problem**: `LoggerChatModel` crashed with `AttributeError: 'tuple' object has no attribute 'items'` when `messages` wasn't a list of dicts (e.g., when it was a `ChatPromptValue`).
*   **Solution**: Updated the logging truncation logic to safely handle `list`, `dict`, `PromptValue`, and other types without assuming a specific structure.

### E. Job Match Scoring (Quality Filter)
*   **Files**: `src/aihawk_easy_applier.py`, `src/llm/llm_manager.py`, `src/aihawk_job_manager.py`, `main.py`
*   **Feature**: Implemented a "Job Match Score" check before applying.
*   **Mechanism**: The bot now reads the full Markdown resume from `master_resume.md` (falling back to the YAML resume if missing) and sends it along with the job description to the LLM to calculate a match score (0-100). If the score is below 70, the application is skipped, and the job is logged to `skipped.json` instead of `failed.json`. This saves time and avoids applying to irrelevant jobs.

### F. Login Timeout Fix (Stability)
*   **File**: `src/aihawk_authenticator.py`
*   **Problem**: The login check had a short timeout (3 seconds), causing the bot to falsely assume the user was logged out on slower connections, leading to unnecessary re-login attempts.
*   **Solution**: Increased the timeout to 10 seconds.

### G. Persistent Seen Jobs (Efficiency Across Sessions)
*   **File**: `src/aihawk_job_manager.py`
*   **Problem**: The bot would re-evaluate and potentially re-attempt applications for jobs (including those previously skipped due to low match scores) after restarting, leading to redundant LLM calls and wasted effort.
*   **Solution**: Implemented `_load_seen_jobs` in `AIHawkJobManager` to read job links from `success.json`, `failed.json`, and `skipped.json` at startup. These links are added to `self.seen_jobs`, ensuring that previously processed jobs are automatically skipped in subsequent runs. This makes the job matching and application process persistent across bot restarts.

## 7. Recommended Running Intervals

With the persistent seen jobs feature, the bot can now be run periodically without re-processing old jobs. Here are some recommendations:

*   **Active Job Hunt**: Run **every 3-4 hours** during business hours (e.g., 9 AM, 1 PM, 5 PM). This ensures new job postings are caught quickly.
*   **Casual Job Hunt**: Run **once a day** (e.g., in the morning).

You can use tools like Windows Task Scheduler (for Windows) or cron jobs (for Linux/macOS) to automate the execution of `python main.py` at your desired intervals. The bot will efficiently process only the newly available jobs since the last run. 