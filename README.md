# 🚀 AI Learning Roadmap Generator

An AI-powered web application built with **Python and Streamlit** that generates personalized learning roadmaps based on a user's goals, current skill level, preferred learning style, study duration, and daily study hours.

The application helps learners organize their learning journey with structured weekly topics, practical exercises, and project recommendations.

## ✨ Features

- 🎯 **Personalized Learning Roadmaps** — Generate learning plans based on individual goals.
- 📊 **Multiple Skill Levels** — Supports beginner, intermediate, and advanced learners.
- 📅 **Flexible Study Plans** — Customize the learning duration and daily study hours.
- 🧠 **Learning Style Preferences** — Adapt the roadmap to your preferred way of learning.
- 🌐 **Multiple Languages** — Generate explanations in your preferred language.
- 📚 **Weekly Learning Topics** — Organize topics into a structured learning schedule.
- 💻 **Practical Exercises** — Reinforce concepts through hands-on activities.
- 🛠️ **Project Recommendations** — Practice skills with relevant projects.
- 📥 **Downloadable Roadmaps** — Download your generated roadmap in Markdown format.
- 🤖 **AI-Powered Generation** — Use the Gemini API to generate personalized learning content.

## 🛠️ Technologies Used

- Python
- Streamlit
- Google Gemini API (`google-genai`)
- python-dotenv

Additional libraries may be used for document processing and retrieval-augmented generation (RAG), depending on the features enabled in your application.

## 📁 Project Structure

```text
AI-Learning-Roadmap-Generator/
│
├── app.py              # Main Streamlit application
├── requirements.txt    # Project dependencies
├── .env.example        # Example environment variables
├── .gitignore          # Files excluded from Git
└── README.md           # Project documentation
```

The `roadmap_engine.py` file is not required if its necessary code has already been moved into `app.py`.

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual GitHub repository URL.

### 2. Open the Project Folder

```bash
cd AI-Learning-Roadmap-Generator
```

### 3. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a file named `.env` in the project root directory.

Add your Gemini API configuration:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Replace the placeholder with your own valid Gemini API key. Make sure your code uses these variable names.

You can use `.env.example` as a reference when creating your `.env` file.

### 6. Run the Application

```bash
python -m streamlit run app.py
```

### 7. Open the Application

After starting the application, Streamlit will display a local URL in the terminal, usually:

```text
http://localhost:8501
```

Open the URL in your web browser to use the application.

## 🔐 Security

- Never upload your `.env` file or API keys to GitHub.
- Add `.env` and `.streamlit/secrets.toml` to `.gitignore`.
- Keep `.env.example` in the repository with placeholder values only.
- If an API key is accidentally exposed, revoke it and create a replacement.
- For Streamlit Community Cloud, configure API keys through the app's Secrets settings.

## 🚀 Deployment

You can deploy the application using Streamlit Community Cloud.

1. Push your project to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Connect your GitHub repository.
4. Select `app.py` as the application entry point.
5. Add the required environment variables in the app's Secrets settings.
6. Deploy the application.

Ensure that `requirements.txt` contains all dependencies required by your application.

## 🎯 Project Objective

The objective of this project is to make learning more organized and accessible by using AI to create personalized study plans. It helps learners break large goals into manageable weekly tasks and build practical skills through exercises and projects.

## 👩‍💻 Author

**Lavanya Yalamanchi**

GitHub: [YalamanchiLavanya](https://github.com/YalamanchiLavanya)

---

⭐ If you find this project useful, consider giving the repository a star!
