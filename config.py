
# config.py

import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

# Load environment variables from the local .env file
load_dotenv()


def get_setting(name, default=None):
    """
    Read a setting from Streamlit Secrets first,
    then fall back to the local .env file.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        # Streamlit Secrets may not be configured locally
        pass

    return os.getenv(name, default)


def create_client():
    """
    Create and return the Gemini API client.
    """
    api_key = get_setting("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. "
            "Add it to your local .env file or Streamlit Secrets."
        )

    return genai.Client(api_key=api_key)


def get_model_name():
    """
    Return the configured Gemini model name.
    """
    return get_setting("GEMINI_MODEL", "gemini-3.8-flash")
