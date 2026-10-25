
# AI Learning Roadmap Generator

A Streamlit application that uses a Hugging Face language model to generate personalized learning roadmaps.

## Features

- Personalized learning plans
- Beginner, intermediate, and advanced levels
- Adjustable study duration and daily study hours
- Learning style preferences
- Multiple explanation languages
- Weekly topics and practical exercises
- Project recommendations
- Downloadable Markdown roadmaps

## Technologies

- Python
- Streamlit
- Hugging Face Inference API
- python-dotenv

## Installation

1. Clone or download this project.
2. Open the project folder in your terminal.
3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file and configure `HF_TOKEN` and `MODEL_NAME`.
5. Start the application:

   ```bash
   python -m streamlit run app.py
   ```

6. Open the local URL shown in the terminal.

## Security

Keep your Hugging Face token private. Do not commit `.env` to GitHub.
