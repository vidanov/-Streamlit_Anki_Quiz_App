from dataclasses import asdict
from typing import List, Dict, Any, Optional
import random
from processor import parse_answers, check_answer, get_question_type, get_shuffled_options
from state_manager import StateManager
from quiz_state import QuizState
import streamlit as st

class QuizManager:
    def __init__(self):
        from state_manager import StateManager  # Move import here to avoid circular import
        self.state = StateManager()  # Initialize state manager
        
        # Ensure that the state is set up correctly
        if 'quiz_started' not in st.session_state:
            st.session_state.quiz_started = False  # Initialize if not already done

        self.state = self._load_or_create_state()
        # Save state immediately after loading to ensure persistence
        if self.state.quiz_started:
            self._save_state()

    def _load_or_create_state(self) -> QuizState:
        saved_state = StateManager.load_quiz_state()
        if saved_state:
            return QuizState(**saved_state)
        return QuizState()

    def start_quiz(self, questions: List[Dict[str, Any]], num_questions: int) -> None:
        selected_questions = random.sample(questions, num_questions)
        self.state = QuizState(
            current_questions=selected_questions,
            current_question_index=0,
            current_options=[],
            current_correct_answers=[],
            answers_given=[[] for _ in range(num_questions)],
            flagged_questions=[False] * num_questions,
            quiz_completed=False,
            quiz_started=True,
            score=0
        )
        self._save_state()

    def submit_answer(self, user_answers: List[bool]) -> bool:
        current_question = self.get_current_question()
        if current_question:
            self.state.answers_given[self.state.current_question_index] = user_answers
            is_correct = check_answer(user_answers, self.state.current_correct_answers)
            if is_correct:
                self.state.score += 1
            
            # Check if all questions are answered
            all_answered = all(answer for answer in self.state.answers_given)
            
            if all_answered:
                self.state.quiz_completed = True
            else:
                # Move to the next question or find an unanswered one
                next_idx = (self.state.current_question_index + 1) % len(self.state.current_questions)
                while next_idx != self.state.current_question_index:
                    if not self.state.answers_given[next_idx]:
                        break
                    next_idx = (next_idx + 1) % len(self.state.current_questions)
                self.state.current_question_index = next_idx
            
            self.state.current_options = []
            self.state.current_correct_answers = []
            
            self._save_state()
            return is_correct
        return False

    def _save_state(self) -> None:
        StateManager.save_quiz_state(asdict(self.state))

    def reset(self) -> None:
        StateManager.clear_quiz_state()
        self.state = self._load_or_create_state()

    def get_current_question(self) -> Optional[Dict]:
        # Only return None if the quiz is complete AND all questions are answered
        all_answered = all(answer for answer in self.state.answers_given)
        if self.state.quiz_completed and all_answered:
            return None
        
        if self.state.current_question_index < len(self.state.current_questions):
            return self.state.current_questions[self.state.current_question_index]
        return None

    def prepare_question_options(self) -> None:
        current_question = self.get_current_question()
        if current_question:
            # Always prepare new options for each question
            options, correct_answers = get_shuffled_options(current_question)
            self.state.current_options = options
            self.state.current_correct_answers = correct_answers
            self._save_state()  # Save state after preparing options

    def calculate_final_score(self) -> tuple[int, int, float]:
        total_questions = len(self.state.answers_given)
        if total_questions == 0:
            return 0, 0, 0.0
        
        total_score = self.state.score
        percentage = (total_score / total_questions) * 100
        return total_score, total_questions, percentage

    @property
    def is_quiz_complete(self) -> bool:
        return self.state.quiz_completed

    def toggle_flag(self) -> None:
        """Toggle flag status for current question"""
        current_idx = self.state.current_question_index
        self.state.flagged_questions[current_idx] = not self.state.flagged_questions[current_idx]
        self._save_state()

    def navigate_to_question(self, question_index: int) -> None:
        """Navigate to a specific question"""
        if 0 <= question_index < len(self.state.current_questions):
            self.state.current_question_index = question_index
            self.state.current_options = []
            self.state.current_correct_answers = []
            self._save_state()