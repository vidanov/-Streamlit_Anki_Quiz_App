import streamlit as st
from typing import Callable, Dict, Any
from quiz_manager import QuizManager
from processor import get_question_type
import os

class QuizUI:
    @staticmethod
    def render_sidebar(on_file_upload: Callable, on_start_quiz: Callable, 
                      on_reset_files: Callable, questions: list = None, 
                      quiz_manager: QuizManager = None) -> None:
        with st.sidebar:
            st.header("Quiz Setup")
            
            uploaded_file = st.file_uploader("Upload an APKG file:", type=['apkg'])
            if uploaded_file:
                st.session_state.uploaded_file = uploaded_file
                questions = on_file_upload(uploaded_file, quiz_manager)
                if questions is None:
                    st.error("Error processing the uploaded file.")
            
            # Show the name of the uploaded file if it exists
            if 'uploaded_file' in st.session_state:
                st.write(f"Uploaded file: {st.session_state.uploaded_file.name}")

            # Check if questions are loaded from any source
            if st.session_state.get('questions_loaded', False) or questions:
                num_questions = st.number_input(
                    "Number of questions:",
                    min_value=1,
                    max_value=st.session_state.num_questions,
                    value=min(5, st.session_state.num_questions)
                )
                
                if st.button("Start Quiz", use_container_width=True):
                    on_start_quiz(questions, num_questions)
            
            # Only show the Reset Files button if a file has been uploaded
            if 'uploaded_file' in st.session_state:
                if st.button("Reset Files", use_container_width=True):
                    on_reset_files(quiz_manager)

    @staticmethod
    def render_question_navigation(quiz_manager: QuizManager, on_restart: Callable) -> None:
        st.sidebar.markdown("### Questions")
        
        total_questions = len(quiz_manager.state.current_questions)
        
        # Ensure flagged_questions is properly initialized
        if len(quiz_manager.state.flagged_questions) != total_questions:
            quiz_manager.state.flagged_questions = [False] * total_questions
            quiz_manager._save_state()
   
        
        # Create columns for the grid
        cols = st.sidebar.columns(4)
        
        # Create navigation buttons with status indicators
        for i in range(total_questions):
            col = cols[i % 4]
            
            # Determine question status
            is_current = i == quiz_manager.state.current_question_index
            is_answered = (len(quiz_manager.state.answers_given) > i and 
                          quiz_manager.state.answers_given[i])
            is_flagged = quiz_manager.state.flagged_questions[i]
            
            # Determine status indicator
            if is_flagged:
                status = "🚩"
            elif is_answered:
                status = "✅"
            else:
                status = "⭕"
                
            # Create button with status indicator
            if col.button(f"{status}\n{i + 1}", key=f"nav_{i}"):
                quiz_manager.navigate_to_question(i)
                st.rerun()
        st.sidebar.markdown("\n\n---\n\n")
        # Add a Reset Quiz button in the sidebar
        if st.sidebar.button("Reset Quiz", use_container_width=True):
            on_restart(quiz_manager)  # Pass quiz_manager here

    @staticmethod
    def render_question(quiz_manager: QuizManager, on_submit: Callable) -> None:
        current_question = quiz_manager.get_current_question()
        if not current_question:
            st.error("No current question available.")
            return

        # Navigation and flag buttons
        col1, col2, col3, col4 = st.columns([1, 3, 1, 1])  # Adjust column sizes as needed
        with col1:
            if quiz_manager.state.current_question_index > 0:
                if st.button("← Previous"):
                    quiz_manager.navigate_to_question(quiz_manager.state.current_question_index - 1)
                    st.rerun()

        with col2:
            st.markdown(f"**Question {quiz_manager.state.current_question_index + 1} of {len(quiz_manager.state.current_questions)}**")

        with col3:
            if quiz_manager.state.current_question_index < len(quiz_manager.state.current_questions) - 1:
                if st.button("→ Next"):
                    quiz_manager.navigate_to_question(quiz_manager.state.current_question_index + 1)
                    st.rerun()

        with col4:
            # Flag button
            current_idx = quiz_manager.state.current_question_index
            is_flagged = quiz_manager.state.flagged_questions[current_idx]
            flag_text = "Unflag" if is_flagged else "Flag"
            if st.button(flag_text):
                quiz_manager.toggle_flag()
                st.rerun()

        # Display the question title
        question_title = current_question.get('Question', 'No Title Available')
        st.markdown(f"""
    <h3>{question_title}</h3>
""", unsafe_allow_html=True)  # Display the question title

        # Extract options from the current question
        options = []
        for i in range(1, 7):  # Assuming Q_1 to Q_6
            key = f"Q_{i}"
            if key in current_question and current_question[key].strip():  # Check if the key exists and is not empty
                options.append(current_question[key])

        # Check if options were found
        if not options:
            st.error("The current question does not contain any options.")
            return

        # Prepare options if not already prepared
        quiz_manager.prepare_question_options()
        question_type, num_correct = get_question_type(current_question)

        # Display the number of correct answers needed
        if question_type != 'single':
            st.markdown(f"**Select {num_correct} correct answer(s):**")  # Indicate how many correct answers are needed


        # Initialize user answers based on the number of options
        user_answers = [False] * len(options)  # Initialize user answers to match the number of options

        # Render the multiple choice options
        is_valid = False
        if question_type == 'single':
            is_valid = QuizUI._render_single_choice(options, quiz_manager.state.current_question_index, user_answers)
        else:
            is_valid = QuizUI._render_multiple_choice(options, num_correct, quiz_manager.state.current_question_index, user_answers)

        # Submit button - only enable if the required number of answers are selected
        if st.button("Submit Answer", disabled=not is_valid):
            on_submit(user_answers)

    @staticmethod
    def _render_answer_inputs(question_type: str, num_correct: int, 
                            options: list, question_idx: int,
                            user_answers: list) -> bool:
        if question_type == 'single':
            return QuizUI._render_single_choice(
                options, question_idx, user_answers
            )
        else:
            return QuizUI._render_multiple_choice(
                options, num_correct, question_idx, user_answers
            )

    @staticmethod
    def _render_single_choice(options: list, question_idx: int, user_answers: list) -> bool:
        # Render the question with HTML content
        question_html = f"<div>{options[0]}</div>"  # Assuming options[0] contains the HTML content for the question
        st.markdown(question_html, unsafe_allow_html=True)

        # Use plain text options for the radio buttons
        option_texts = [f"{i + 1}. {opt}" for i, opt in enumerate(options)]
        
        selected_option = st.radio(
            "Select your answer:",
            options=option_texts,
            key=f"q_{question_idx}_radio",
            index=None  # Remove default selection
        )

        if selected_option is not None:
            selected_idx = option_texts.index(selected_option)
            for i in range(len(user_answers)):
                user_answers[i] = (i == selected_idx)
            return True
        return False

    @staticmethod
    def _render_multiple_choice(options: list, num_correct: int, 
                              question_idx: int, user_answers: list) -> bool:
        changed = False
        for i, option in enumerate(options):
            checked = st.checkbox(
                option,
                key=f"q_{question_idx}_checkbox_{i}",
                value=user_answers[i] if i < len(user_answers) else False
            )
            if checked != user_answers[i]:
                user_answers[i] = checked
                changed = True
        
        num_selected = sum(1 for x in user_answers if x)
        if num_selected > 0 and num_selected != num_correct:
            st.warning(f"Please select exactly {num_correct} answers (currently selected {num_selected}).")
            return False
        
        return num_selected == num_correct