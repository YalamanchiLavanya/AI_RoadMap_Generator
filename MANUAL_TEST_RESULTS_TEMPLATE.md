# Manual Test Results — AI Learning Roadmap Generator

## 1. Objective

The objective of this testing is to verify that the AI Learning Roadmap Generator produces personalized learning plans, identifies skill gaps, recommends learning resources, supports follow-up questions, and retrieves relevant information from uploaded PDF documents.

## 2. Testing Environment

- **Project:** AI Learning Roadmap Generator
- **Programming Language:** Python
- **User Interface:** Streamlit
- **LLM API:** Hugging Face Inference API
- **Embedding Model:** sentence-transformers/all-MiniLM-L6-v2
- **Vector Search:** FAISS
- **Testing Type:** Manual Testing

## 3. Test Cases

| Test ID | Test Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| TC01 | Generate a Data Analyst roadmap for a beginner with 8 weeks and 8 study hours per week. | Generates an ordered weekly plan with skill gaps, practice tasks, milestones, and resources. | To be filled after testing. | Not Tested |
| TC02 | Generate a Python Developer roadmap for a beginner with no prior programming skills. | Starts with Python fundamentals and gradually introduces practical projects. | To be filled after testing. | Not Tested |
| TC03 | Generate a Frontend Developer roadmap for someone who knows HTML and CSS. | Focuses on JavaScript, responsive design, React, APIs, and projects. | To be filled after testing. | Not Tested |
| TC04 | Generate a Machine Learning roadmap for a beginner with basic Python knowledge. | Introduces data handling and mathematical foundations before model development. | To be filled after testing. | Not Tested |
| TC05 | Generate a Power BI Analyst roadmap for 4 weeks with 4 study hours per week. | Creates a short, practical plan appropriate for the available time. | To be filled after testing. | Not Tested |
| TC06 | Generate a roadmap for a learner who can study only 2 hours per week. | Prioritizes essential topics and keeps weekly study hours within the limit. | To be filled after testing. | Not Tested |
| TC07 | Generate a Cybersecurity Analyst roadmap for a beginner. | Includes networking, security fundamentals, hands-on practice, and milestones. | To be filled after testing. | Not Tested |
| TC08 | Generate a Java Backend Developer roadmap for an intermediate learner. | Covers relevant Java concepts, databases, APIs, testing, and a project. | To be filled after testing. | Not Tested |
| TC09 | Ask the Roadmap Coach to revise Week 2 because the learner has only 5 hours available per week. | Uses the existing roadmap and conversation context to suggest a revised schedule. | To be filled after testing. | Not Tested |
| TC10 | Upload and index a PDF syllabus, then ask a question about its prerequisites. | Retrieves relevant PDF excerpts and answers using the available document evidence. | To be filled after testing. | Not Tested |

## 4. Error Handling Tests

| Test ID | Test Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| EC01 | Submit an empty career goal. | Displays a validation message asking for a career goal. | To be filled after testing. | Not Tested |
| EC02 | Start the app without a valid Hugging Face token. | Displays a configuration error instead of silently failing. | To be filled after testing. | Not Tested |
| EC03 | Simulate or encounter an API rate limit. | Handles the failure and displays an understandable error message. | To be filled after testing. | Not Tested |
| EC04 | Upload a PDF containing no extractable text. | Displays a message explaining that PDF text could not be extracted. | To be filled after testing. | Not Tested |

## 5. Test Summary

- Total functional test cases: 10
- Functional tests passed: To be updated after testing
- Functional tests failed: To be updated after testing
- Error handling tests executed: To be updated after testing

## 6. Conclusion

Manual testing is used to evaluate the roadmap generator's personalization, skill-gap analysis, weekly planning, resource recommendations, conversation memory, PDF retrieval, and error handling. The final conclusion will be recorded after executing the test cases and reviewing the observed results.

