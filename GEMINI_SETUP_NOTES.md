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