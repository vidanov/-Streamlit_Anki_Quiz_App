import streamlit as st
from typing import Callable, Dict, Any
from quiz_manager import QuizManager
from processor import get_question_type, check_answer
import os
from datetime import datetime, timedelta
import base64
from timer_component import timer_component

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
            
            # Show the name of the uploaded file if it exists and is not None
            if 'uploaded_file' in st.session_state and st.session_state.uploaded_file is not None:
                st.write(f"Uploaded file: {st.session_state.uploaded_file.name}")

            # Check if questions are loaded from any source
            if st.session_state.get('questions_loaded', False) or questions:
                num_questions = st.number_input(
                    "Number of questions:",
                    min_value=1,
                    max_value=st.session_state.num_questions,
                    value=min(5, st.session_state.num_questions)
                )
                
                if st.button("Start Quiz", key="start_quiz"):
                    on_start_quiz(questions, num_questions)
            

    @staticmethod
    def render_question_navigation(quiz_manager: QuizManager, on_restart: Callable, state_manager=None) -> None:
        st.sidebar.markdown("# Anki Quiz")
        
        # Timer logic
        if not quiz_manager.state.start_time:
            quiz_manager.state.start_time = datetime.now()
            total_questions = len(quiz_manager.state.current_questions)
            quiz_manager.state.end_time = quiz_manager.state.start_time + timedelta(minutes=2 * total_questions)
            quiz_manager.save_state()
        
        # Create timer component
        timer_component(quiz_manager.state.end_time.isoformat())
        
        # Check if time's up
        if datetime.now() >= quiz_manager.state.end_time:
            if not quiz_manager.state.quiz_completed:
                quiz_manager.complete_quiz()
                st.rerun()
        
        st.sidebar.markdown("### Questions")
        
        total_questions = len(quiz_manager.state.current_questions)
        answered_questions = quiz_manager.get_answered_count()
        
        # Show progress
        st.sidebar.markdown(f"**Progress:** {answered_questions}/{total_questions} answered")
        
        # Ensure flagged_questions is properly initialized
        if len(quiz_manager.state.flagged_questions) != total_questions:
            quiz_manager.state.flagged_questions = [False] * total_questions
            quiz_manager.save_state()
   
        # Create columns for the grid
        cols = st.sidebar.columns(4)
        
        # Create navigation buttons with status indicators
        for i in range(total_questions):
            col = cols[i % 4]
            
            # Determine question status
            is_current = i == quiz_manager.state.current_question_index
            is_answered = quiz_manager.is_question_answered(i)
            is_flagged = quiz_manager.state.flagged_questions[i]
            
            # Determine status indicator
            if is_flagged:
                status = "🚩"
            elif is_answered:
                status = "✅"
            else:
                status = "◻️"
                
            # Create button with status indicator
            if col.button(f"{status}\n{i + 1}", key=f"nav_{i}"):
                quiz_manager.navigate_to_question(i)
                st.rerun()
        
        st.sidebar.markdown("\n\n---\n\n")
        
        # Add Submit Quiz button
        if st.sidebar.button("📝 Show all answers", use_container_width=True, key="submit_quiz"):
            if not quiz_manager.state.completion_time:  # Only set if not already set
                quiz_manager.state.completion_time = datetime.now()
            quiz_manager.complete_quiz()
            st.rerun()
        
        # Add Reset Quiz button
        if st.sidebar.button("🔄 Restart Quiz", use_container_width=True, key="reset_quiz"):
            on_restart(quiz_manager, state_manager)

    @staticmethod
    def render_question(quiz_manager: QuizManager, on_submit: Callable) -> None:
        current_question = quiz_manager.get_current_question()
        if not current_question:
            st.error("No current question available.")
            return

        # Show last question message if exists
        if st.session_state.get('last_question_message'):
            st.warning(f"This is the last question. {st.session_state.last_question_message} before you can see your results.")
            # Clear the message after showing it
            del st.session_state.last_question_message

        # Navigation and flag buttons
        col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
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
            flag_text = "🚩Unflag" if is_flagged else "🚩Flag"
            flag = "🚩 " if is_flagged else ""
            if st.button(flag_text):
                quiz_manager.toggle_flag()
                st.rerun()

        # Display the question title
        question_title = current_question.get('Question', 'No Title Available')
        st.markdown(f"""
    <strong>{flag}{question_title}</strong>
""", unsafe_allow_html=True)

        # Prepare options if not already prepared
        quiz_manager.prepare_question_options()
        question_type, num_correct = get_question_type(current_question)
        
        # Use the stored display options instead of extracting from question
        options = current_question.get("display_options", [])
        if not options:
            st.error("The current question does not contain any options.")
            return

        # Display the number of correct answers needed
        if question_type != 'single':
            st.markdown(f"**Select {num_correct} correct answer(s):**")

        # Get current answers if any
        current_idx = quiz_manager.state.current_question_index
        user_answers = None
        
        # Check if this question has been answered before
        if (current_idx < len(quiz_manager.state.answers_given) and 
            quiz_manager.state.answers_given[current_idx] is not None):
            # Use the stored answer
            user_answers = quiz_manager.state.answers_given[current_idx]
        else:
            # Initialize new answer array
            user_answers = [False] * len(options)

        # Render answer inputs with the correct initial state
        if QuizUI._render_answer_inputs(question_type, num_correct, options, 
                                      quiz_manager.state.current_question_index, 
                                      user_answers):
            if st.button("Submit Answer"):
                on_submit(user_answers)
                st.rerun()

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
        # Create option texts without numbers to avoid confusion
        option_texts = options.copy()  # Just use the options directly
        
        # Find the currently selected option
        selected_index = None
        if user_answers and any(user_answers):
            selected_index = user_answers.index(True)
        
        # Create the radio button with the correct initial selection
        selected_option = st.radio(
            "Select your answer:",
            options=option_texts,
            key=f"q_{question_idx}_radio",
            index=selected_index if selected_index is not None else 0
        )

        # Update user_answers based on selection
        if selected_option:
            # Clear previous selection
            for i in range(len(user_answers)):
                user_answers[i] = False
            # Set new selection based on the actual selected option
            selected_idx = option_texts.index(selected_option)
            user_answers[selected_idx] = True
            return True
            
        return False

    @staticmethod
    def _render_multiple_choice(options: list, num_correct: int, 
                              question_idx: int, user_answers: list) -> bool:
        changed = False
        
        # Ensure user_answers is properly initialized
        if len(user_answers) < len(options):
            user_answers.extend([False] * (len(options) - len(user_answers)))
        
        # Create checkboxes with stored values
        for i, option in enumerate(options):
            # Use the stored answer state
            initial_state = bool(user_answers[i])
            checked = st.checkbox(
                option,
                key=f"q_{question_idx}_checkbox_{i}",
                value=initial_state
            )
            
            if checked != user_answers[i]:
                user_answers[i] = checked
                changed = True
        
        num_selected = sum(1 for x in user_answers if x)
        if num_selected > 0 and num_selected != num_correct:
            st.warning(f"Please select exactly {num_correct} answers (currently selected {num_selected}).")
            return False
        
        return num_selected == num_correct or changed

    @staticmethod
    def render_quiz_results(quiz_manager, state_manager, on_retake_quiz: Callable):
        st.header("Quiz Results")
        total_score, total_questions, percentage = quiz_manager.calculate_final_score()

        # Calculate time statistics
        if quiz_manager.state.completion_time and quiz_manager.state.start_time:
            time_taken = quiz_manager.state.completion_time - quiz_manager.state.start_time
            total_seconds = int(time_taken.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            
            # Calculate average time per question
            avg_seconds = total_seconds / total_questions
            avg_minutes = int(avg_seconds // 60)
            avg_seconds = int(avg_seconds % 60)
            
            # Display time statistics in a more prominent way
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⏱️ Total Time", f"{minutes:02d}:{seconds:02d}")
            with col2:
                st.metric("⌛ Average Time per Question", f"{avg_minutes:02d}:{avg_seconds:02d}")

        # Score display
        st.success(f"**Final Score:** {total_score}/{total_questions} ({percentage:.1f}%)")
        
        if percentage >= 85:
            st.balloons()
            st.success("🎉 Excellent! You've passed with distinction!")
        elif percentage >= 75:
            st.success("✨ Congratulations! You've passed!")
        else:
            st.warning("Good effort! Review missed answers and try again.")
        
        st.markdown("---")
        
        # Loop over each question and show results
        for i, question in enumerate(quiz_manager.state.current_questions):
            # Get user's answer for this question
            user_answer = quiz_manager.state.answers_given[i] if i < len(quiz_manager.state.answers_given) else None
            
            # Use the stored display options that were shown during the quiz
            options = question.get("display_options", [])
            correct_answers = question.get("display_correct_answers", [])
            
            # Skip if we don't have valid answers
            if not user_answer or not options or not correct_answers:
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
            on_retake_quiz(quiz_manager, state_manager)