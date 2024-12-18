# Streamlit Quiz App

## Description

A dynamic Streamlit-based quiz application for creating and managing interactive quizzes. This repository includes example `.apkg` files for both default questions and templates to create your own quizzes in the Anki app. The example files are also provided in text format for reference.

---

## Features

- **Anki Integration:** Upload `.apkg` files or use built-in example questions.
- **Default Example Questions:** A sample Anki `.apkg` file provided to get started quickly.
- **Template for Custom Questions:** An `.apkg` file with two types of questions to help users create their own quizzes in Anki.
- **Real-Time Feedback:** Interactive quizzes with explanations and score tracking.
- **State Management:** Maintains session states for seamless progress tracking.
- **Modular Design:** Easy to customize and extend functionality.

---

## Example Files

1. **Example Questions (`AWS Practioner AI Generated.txt`):**
   - Preloaded AWS-related questions for use as default content when no `.apkg` file is uploaded.
2. **Custom Question Template (`Dummy.txt`):**
   - Includes two example questions:
     - Single-choice question: "What is the capital of Germany?"
     - Multiple-choice question: "What are the colors of the German flag?"
   - Contains clear comments and structure to guide users in creating their own questions in Anki.

---

## Technology Stack

- **Frontend:** Streamlit for the UI.
- **Backend:** Python for quiz logic and SQLite for database handling.
- **Compression:** `zstandard` for handling `.apkg` decompression.
- **Logging:** Python logging for debugging and monitoring.

---

## How to Use

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/username/streamlit-quiz-app.git
   ```

2. Navigate to the project folder:

   ```bash
   cd streamlit-quiz-app
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### Running the App

1. Start the Streamlit app:

   ```bash
   streamlit run main.py
   ```

2. Access the app in your browser at `http://localhost:8501`.

### Usage

1. **Default Quiz:** If no `.apkg` file is uploaded, default questions from `AWS Practioner AI Generated.txt` will be used.
2. **Custom Quiz:**
   - Upload a `.apkg` file created with the provided `Dummy.txt` structure.
   - Follow the template to create tailored quizzes using Anki.

---

## Contributing

Contributions are welcome! Please submit a pull request or open an issue to suggest improvements or report bugs.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 

---

## Contact

For issues or questions, open an issue or contact the maintainer. Let's build something awesome together! 🚀