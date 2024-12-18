import streamlit as st
import os
import tempfile
from dataclasses import asdict
from data_handler import load_questions, convert_apkg_to_json
from processor import validate_questions, check_answer, get_shuffled_options, get_question_type
from quiz_manager import QuizManager
from ui_components import QuizUI
from state_manager import StateManager
from quiz_state import QuizState
import json
from typing import Callable
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def handle_file_upload(uploaded_file):
    try:
        with st.spinner("Converting Anki deck..."):
            # Create a temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_apkg = os.path.join(temp_dir, "deck.apkg")
                with open(temp_apkg, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Convert the APKG to JSON
                questions = convert_apkg_to_json(temp_apkg)
                
                # Validate questions
                is_valid, error_msg = validate_questions(questions)
                if not is_valid:
                    st.error(f"❌ Invalid APKG file format: {error_msg}")
                    return None
                
                # Check if each question has the necessary fields
                for question in questions:
                    if 'Question' not in question or 'Answers' not in question:
                        st.error("One or more questions are missing the 'Question' or 'Answers' field.")
                        return None
                    # Check for options
                    options_present = any(f"Q_{i}" in question for i in range(1, 7))
                    if not options_present:
                        st.error("One or more questions are missing the 'Options' field.")
                        return None
                
                st.success("Anki deck converted successfully!")
                st.write(f"Total questions loaded: {len(questions)}")
                
                return questions
                
    except Exception as e:
        st.error(f"""
        ❌ Error processing APKG file: {str(e)}
        
        This could be due to:
        - Corrupted APKG file
        - Unsupported Anki deck format
        - File read/write permissions
        
        Please try with a different APKG file or check the file format.
        """)
        return None

def render_quiz_results(quiz_manager, state_manager):
    st.header("Quiz Results")
    total_score, total_questions, percentage = quiz_manager.calculate_final_score()
    
    st.success(f"**Final Score:** {total_score}/{total_questions} ({percentage:.1f}%)")
    
    if percentage >= 85:
        st.balloons()
        st.success("🎉 Excellent! You've passed with distinction!")
    elif percentage >= 75:
        st.success("✨ Congratulations! You've passed!")
    else:
        st.warning("Good effort! Review missed answers and try again.")
    
    st.markdown("---")
    
    for i, (question, user_answer) in enumerate(zip(quiz_manager.state.current_questions, 
                                                  quiz_manager.state.answers_given)):
        options, correct_answers = get_shuffled_options(question)
        
        # Ensure user_answer and correct_answers have the same length
        max_len = max(len(user_answer), len(correct_answers))
        user_answer = user_answer[:max_len] + [False] * (max_len - len(user_answer))
        correct_answers = correct_answers[:max_len] + [0] * (max_len - len(correct_answers))
        
        is_correct = check_answer(user_answer, correct_answers)
        
        correctness_str = "✅ correct" if is_correct else "❌ wrong"
        st.markdown(f"### Question {i + 1} - {correctness_str}")
        st.markdown(question['Question'], unsafe_allow_html=True)
        
        st.write("##### Answers:")
        for j, option in enumerate(options):
            if j >= len(user_answer) or j >= len(correct_answers):
                break
                
            prefix = ""
            suffix = ""
            
            if user_answer[j] and correct_answers[j]:
                prefix = "<div style='color:green; padding: 5px; border: 1px green solid;'>✓"
                suffix = "<span style='float: right;'>Your answer</span></div>"
            elif user_answer[j] and not correct_answers[j]:
                prefix = "<div style='color:red; padding: 5px; border: 1px red solid;'>⨂"
                suffix = "<span style='float: right;'>Your answer</span></div>"
            elif not user_answer[j] and correct_answers[j]:
                prefix = "<div style='color:green; padding: 5px; border: 1px green solid;'>✓"
                suffix = "<span style='float: right;'>Correct answer</span></div>"
            else:
                prefix = "<div style='padding:5px;'>⨂"
                suffix = "</div>"
            
            st.markdown(f"{prefix} {option}{suffix}", unsafe_allow_html=True)
        
        if question.get('Extra_1'):
            st.markdown("**Explanation:**")
            st.markdown(question['Extra_1'], unsafe_allow_html=True)
        
        st.markdown("---")

    if st.button("Retake Quiz"):
        quiz_manager.reset()
        state_manager.clear_quiz_state()
        st.rerun()

def on_file_upload(uploaded_file, quiz_manager: QuizManager):
    questions = handle_file_upload(uploaded_file)
    if questions:
        # Store the uploaded file and questions in session state only
        st.session_state.uploaded_file = uploaded_file
        st.session_state.current_questions = questions
        st.session_state.num_questions = len(questions)
        st.session_state.questions_loaded = True
        st.session_state.saved_questions = questions
        return questions
    st.session_state.questions_loaded = False
    return None

def on_reset_files(quiz_manager: QuizManager, state_manager: StateManager):
    """Handle resetting uploaded files and returning to default questions"""
    quiz_manager.reset()
    
    keys_to_clear = {
        'saved_questions', 'current_questions', 'num_questions', 
        'uploaded_file', 'questions_loaded', 'quiz_started'
    }
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    state_manager.clear_quiz_state()
    st.success("Files have been reset. Using default questions.")
    st.rerun()

def on_restart(quiz_manager: QuizManager, state_manager: StateManager):
    """Handle resetting just the quiz state while preserving uploaded files"""
    quiz_manager.reset()
    
    preserved_state = {
        'uploaded_file': st.session_state.get('uploaded_file'),
        'saved_questions': st.session_state.get('saved_questions'),
        'current_questions': st.session_state.get('current_questions'),
        'num_questions': st.session_state.get('num_questions'),
        'questions_loaded': st.session_state.get('questions_loaded')
    }
    
    if 'quiz_started' in st.session_state:
        del st.session_state.quiz_started
    
    for key, value in preserved_state.items():
        if value is not None:
            st.session_state[key] = value
    
    state_manager.clear_quiz_state()
    st.success("Quiz has been restarted. You can start a new quiz with the current questions.")
    st.rerun()

def on_start_quiz(questions, num_questions, quiz_manager: QuizManager, state_manager: StateManager):
    if not questions:
        st.error("No questions available. Please upload a quiz file or use the default questions.")
        return
    
    if not isinstance(questions, list) or len(questions) == 0:
        st.error("Invalid question format. Please upload a valid quiz file.")
        return
    
    if num_questions <= 0:
        st.error("Please select a valid number of questions (greater than 0).")
        return
    
    if num_questions > len(questions):
        st.warning(f"Requested {num_questions} questions, but only {len(questions)} are available. Using all available questions.")
        num_questions = len(questions)
    
    # Store the quiz state before starting
    st.session_state.saved_questions = questions
    quiz_manager.start_quiz(questions, num_questions)
    st.session_state.quiz_started = True
    state_manager.save_quiz_state(asdict(quiz_manager.state))
    st.rerun()

def main():
    # Initialize state manager first
    state_manager = StateManager()
    state_manager.initialize_state()

    # Initialize questions variable
    questions = None  # or questions = []

    st.set_page_config(page_title="ANKI Quiz", layout="wide")
    
    # Initialize quiz manager in session state if not present
    if 'quiz_manager' not in st.session_state:
        st.session_state.quiz_manager = QuizManager()
    
    quiz_manager = st.session_state.quiz_manager

    # Initialize current_questions and num_questions in session state if not present
    if 'current_questions' not in st.session_state:
        st.session_state.current_questions = []
    if 'num_questions' not in st.session_state:
        st.session_state.num_questions = 0

    # Try to restore saved state first
    saved_state = state_manager.load_quiz_state()
    if saved_state:
        quiz_manager.state = QuizState(**saved_state)
        st.session_state.quiz_started = quiz_manager.state.quiz_started
        if quiz_manager.state.quiz_started:
            st.session_state.current_questions = quiz_manager.state.current_questions
            questions = quiz_manager.state.current_questions
            state_manager.save_quiz_state(asdict(quiz_manager.state))
    
    # Remove file-based state loading
    if not quiz_manager.state.quiz_started:
        if 'current_questions' in st.session_state and st.session_state.current_questions:
            questions = st.session_state.current_questions
            st.write("Current questions loaded from session state.")
        elif not st.session_state.get('uploaded_file'):
            try:
                questions = load_questions("data/default_questions.json")
                st.session_state.current_questions = questions
                st.session_state.num_questions = len(questions)
                st.info(f"Using default quiz file. Total questions: {len(questions)}")
            except FileNotFoundError:
                questions = None
                st.info("Please upload a quiz file to begin")
    else:
        questions = quiz_manager.state.current_questions

    # Update the questions variable based on the session state after file upload
    if st.session_state.get('questions_loaded', False):
        questions = st.session_state.current_questions

    def on_submit(user_answers):
        current_idx = quiz_manager.state.current_question_index
        last_question_idx = len(quiz_manager.state.current_questions) - 1
        
        quiz_manager.submit_answer(user_answers)
        
        if current_idx == last_question_idx:
            for i, answer in enumerate(quiz_manager.state.answers_given):
                if not answer:
                    quiz_manager.navigate_to_question(i)
                    break
        
        state_manager.save_quiz_state(asdict(quiz_manager.state))
        st.rerun()

    # Render UI
    if quiz_manager.state.quiz_started:
        QuizUI.render_question_navigation(
            quiz_manager, 
            on_restart,
            state_manager  # Pass state_manager to the navigation renderer
        )  
        
        # Check if all questions are answered
        all_answered = all(quiz_manager.state.answers_given)
        
        if quiz_manager.is_quiz_complete and all_answered:
            total_score, total_questions, percentage = quiz_manager.calculate_final_score()
            st.success(f"Quiz Completed! Your score: {total_score}/{total_questions} ({percentage:.2f}%)")
            render_quiz_results(quiz_manager, state_manager)  # Pass state_manager
        else:
            # Show how many questions still need to be answered
            remaining = sum(1 for answer in quiz_manager.state.answers_given if not answer)
            if remaining > 0:
                st.info(f"You still have {remaining} question(s) to answer.")
            
            current_question = quiz_manager.get_current_question()
            if current_question:
                QuizUI.render_question(quiz_manager, on_submit)  # Render the current question
            else:
                # Find the first unanswered question and navigate to it
                for i, answer in enumerate(quiz_manager.state.answers_given):
                    if not answer:
                        quiz_manager.navigate_to_question(i)
                        st.rerun()
                        break
    else:
        QuizUI.render_sidebar(
            on_file_upload, 
            lambda q, n: on_start_quiz(q, n, quiz_manager, state_manager),  # Pass state_manager
            lambda qm: on_reset_files(qm, state_manager),  # Pass state_manager
            questions, 
            quiz_manager
        )

       
    if not quiz_manager.state.quiz_started:
        st.markdown("**Get started by uploading a file in the sidebar and then choose the number of questions.**")
    
    # Add version number in footer
    st.markdown("""
    ---
    <div style='text-align: center; color: #666; padding: 10px;'>
    Streamlit Anki Quiz App v1.0.1
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()