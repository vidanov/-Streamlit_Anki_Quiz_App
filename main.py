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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add global JavaScript for timer
st.set_page_config(page_title="Anki Quiz", page_icon="📚", layout="wide")

# Add global timer script
st.markdown("""
    <script>
        function startTimer(endTimeStr) {
            const endTime = new Date(endTimeStr);
            
            function updateTimer() {
                const timer = document.getElementById('quiz-timer');
                if (timer) {
                    const now = new Date();
                    const remaining = Math.max(0, Math.floor((endTime - now) / 1000));
                    const minutes = Math.floor(remaining / 60);
                    const seconds = remaining % 60;
                    
                    if (remaining > 0) {
                        timer.innerHTML = '⏱️ Time Remaining: ' + 
                            String(minutes).padStart(2, '0') + ':' + 
                            String(seconds).padStart(2, '0');
                        window.requestAnimationFrame(updateTimer);
                    } else {
                        timer.innerHTML = '⏱️ Time\'s Up!';
                        window.location.reload();
                    }
                }
            }
            
            window.requestAnimationFrame(updateTimer);
        }
    </script>
""", unsafe_allow_html=True)

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

def on_retake_quiz(quiz_manager: QuizManager, state_manager: StateManager):
    """Handle retaking the current quiz with the same questions"""
    logger.debug("Retaking current quiz")
    
    # Store the current questions with their display options
    current_questions = []
    for question in quiz_manager.state.current_questions:
        # Create a deep copy of the question to preserve display options
        q_copy = question.copy()
        if "display_options" in question:
            q_copy["display_options"] = question["display_options"].copy()
            q_copy["display_correct_answers"] = question["display_correct_answers"].copy()
        current_questions.append(q_copy)
    
    num_questions = len(current_questions)
    logger.debug(f"Preserved questions with options: {current_questions}")
    
    # Reset quiz state
    quiz_manager.reset()
    
    # Clear quiz-related session state
    quiz_related_keys = [
        'quiz_started', 'quiz_state_saved', 'last_question_message',
        'quiz_completed', 'is_quiz_complete'
    ]
    for key in quiz_related_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Start fresh quiz with the same questions and preserved options
    quiz_manager.start_quiz(current_questions, num_questions)
    st.session_state.quiz_started = True
    
    # Save the new state
    quiz_manager.save_state()
    state_manager.save_quiz_state(asdict(quiz_manager.state))
    
    logger.debug("Quiz restarted with preserved options")
    st.rerun()

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
    
    # Loop over each question and the user's chosen answers
    for i, question in enumerate(quiz_manager.state.current_questions):
        # Get user's answer for this question
        user_answer = quiz_manager.state.answers_given[i] if i < len(quiz_manager.state.answers_given) else None
        logger.debug(f"Question {i + 1} - User answer: {user_answer}")
        
        # Use the stored display options that were shown during the quiz
        options = question.get("display_options", [])
        correct_answers = question.get("display_correct_answers", [])
        
        logger.debug(f"Question {i + 1} - Options: {options}")
        logger.debug(f"Question {i + 1} - Correct answers: {correct_answers}")
        
        # Skip if we don't have valid answers
        if not user_answer or not options or not correct_answers:
            logger.warning(f"Skipping question {i + 1} due to missing data")
            continue
        
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

    if st.button("🔄 Retake Quiz", key="retake_quiz_button"):
        logger.debug("Retake Quiz button clicked")
        on_retake_quiz(quiz_manager, state_manager)

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
    logger.debug("Resetting files and loading default questions")
    quiz_manager.reset()
    
    keys_to_clear = {
        'saved_questions', 'current_questions', 'num_questions', 
        'uploaded_file', 'questions_loaded', 'quiz_started', 'quiz_state_saved'
    }
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    state_manager.clear_quiz_state()
    
    try:
        questions = load_questions("data/default_questions.json")
        st.session_state.current_questions = questions
        st.session_state.num_questions = len(questions)
        st.session_state.questions_loaded = True
        st.success("Files have been reset. Using default questions.")
        logger.debug("Default questions loaded: %s", questions)
    except FileNotFoundError:
        st.error("Could not load default questions. Please upload a quiz file.")
        logger.error("Default questions file not found")
    
    st.rerun()

def on_restart(quiz_manager: QuizManager, state_manager: StateManager):
    """Handle resetting the quiz completely and return to setup state"""
    logger.debug("Restarting quiz - returning to setup")
    
    # Reset quiz manager
    quiz_manager.reset()
    
    # Preserve only the uploaded file and questions
    preserved_state = {
        'uploaded_file': st.session_state.get('uploaded_file'),
        'saved_questions': st.session_state.get('saved_questions'),
        'questions_loaded': True  # Keep this flag to show the setup options
    }
    
    # Clear all session state
    for key in list(st.session_state.keys()):
        if key not in preserved_state:
            del st.session_state[key]
    
    # Restore preserved state
    for key, value in preserved_state.items():
        if value is not None:
            st.session_state[key] = value
    
    # If we have saved questions, restore them as current_questions
    if 'saved_questions' in st.session_state:
        st.session_state.current_questions = st.session_state.saved_questions
        st.session_state.num_questions = len(st.session_state.saved_questions)
    
    logger.debug("Quiz reset to setup state")
    st.rerun()

def on_start_quiz(questions, num_questions, quiz_manager: QuizManager, state_manager: StateManager):
    logger.debug("Starting quiz with %d questions", num_questions)
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
    
    st.session_state.saved_questions = questions
    quiz_manager.start_quiz(questions, num_questions)
    st.session_state.quiz_started = True
    state_manager.save_quiz_state(asdict(quiz_manager.state))
    logger.debug("Quiz started with questions: %s", questions)
    st.rerun()

def main():
    # Initialize state manager first
    state_manager = StateManager()
    state_manager.initialize_state()

    # Initialize or get quiz manager
    if 'quiz_manager' not in st.session_state:
        quiz_manager = QuizManager()
        quiz_manager.set_state_manager(state_manager)
        st.session_state.quiz_manager = quiz_manager
    
    quiz_manager = st.session_state.quiz_manager
    
    # Load questions from state manager
    questions = st.session_state.get(state_manager.QUESTIONS_KEY, [])

    # Ensure current_questions and num_questions are initialized
    if 'current_questions' not in st.session_state:
        st.session_state.current_questions = questions
    if 'num_questions' not in st.session_state:
        st.session_state.num_questions = len(questions)

    # Try to restore saved state first
    saved_state = state_manager.load_quiz_state()
    if saved_state:
        quiz_manager.state = QuizState(**saved_state)
        st.session_state.quiz_started = quiz_manager.state.quiz_started
        if quiz_manager.state.quiz_started:
            st.session_state.current_questions = quiz_manager.state.current_questions
            questions = quiz_manager.state.current_questions
            state_manager.save_quiz_state(asdict(quiz_manager.state))
    
    # Load default questions if no questions are loaded
    if not quiz_manager.state.quiz_started and not st.session_state.get('questions_loaded', False):
        try:
            questions = load_questions("data/default_questions.json")
            st.session_state.current_questions = questions
            st.session_state.num_questions = len(questions)
            st.session_state.questions_loaded = True
            st.info(f"Using default quiz file. Total questions: {len(questions)}")
        except FileNotFoundError:
            questions = None
            st.info("Please upload a quiz file to begin")

    # Update the questions variable based on the session state after file upload
    if st.session_state.get('questions_loaded', False):
        questions = st.session_state.current_questions

    def on_submit(user_answers):
        quiz_manager.submit_answer(user_answers)
        
        # Check if quiz is completed after submission
        if quiz_manager.state.quiz_completed:
            state_manager.save_quiz_state(asdict(quiz_manager.state))
            st.rerun()
        else:
            state_manager.save_quiz_state(asdict(quiz_manager.state))
            st.rerun()

    # Render UI based on state
    if not quiz_manager.state.quiz_completed:
        if quiz_manager.state.quiz_started:
            # Show quiz navigation and questions
            QuizUI.render_question_navigation(
                quiz_manager, 
                on_restart,
                state_manager
            )  
            
            current_question = quiz_manager.get_current_question()
            if current_question:
                QuizUI.render_question(quiz_manager, on_submit)
        else:
            # Show setup sidebar
            QuizUI.render_sidebar(
                on_file_upload, 
                lambda q, n: on_start_quiz(q, n, quiz_manager, state_manager),
                lambda qm: on_reset_files(qm, state_manager),
                questions, 
                quiz_manager
            )
            st.markdown("# Anki Quiz")
            st.markdown("**Get started by uploading a file in the sidebar and then choose the number of questions.**")
            st.markdown("To learn more visit https://github.com/vidanov/streamlit_anki_quiz_app/")
    
    # Show results if quiz is completed
    if quiz_manager.state.quiz_completed:
        st.markdown("---")
        total_score, total_questions, percentage = quiz_manager.calculate_final_score()
        QuizUI.render_quiz_results(quiz_manager, state_manager, on_retake_quiz)
        
        
    # Add version number in footer
    st.markdown("""
    ---
    <div style='text-align: center; color: #666; padding: 10px;'>
    Streamlit Anki Quiz App v1.0.3
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()