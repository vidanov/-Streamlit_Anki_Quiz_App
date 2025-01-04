from dataclasses import asdict
from typing import List, Dict, Any, Optional
import random
from processor import parse_answers, check_answer, get_question_type, get_shuffled_options
from state_manager import StateManager
from quiz_state import QuizState
import streamlit as st
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QuizManager:
    def __init__(self):
        self.state_manager = StateManager()  # Create instance
        self.state = self._load_or_create_state()

    def _load_or_create_state(self):
        """Load existing state or create new one"""
        saved_state = self.state_manager.load_quiz_state()  # Use instance method
        if saved_state:
            return QuizState(**saved_state)
        return QuizState()

    def save_state(self):
        """Save current state"""
        state_dict = asdict(self.state)
        self.state_manager.save_quiz_state(state_dict)  # Use instance method

    def start_quiz(self, questions: list, num_questions: int = None):
        """Start a new quiz with the given questions"""
        if num_questions is None or num_questions > len(questions):
            num_questions = len(questions)
        
        # Randomly select questions if needed
        selected_questions = questions[:num_questions]
        
        # Clear any stored display options
        for question in selected_questions:
            if "display_options" in question:
                del question["display_options"]
            if "display_correct_answers" in question:
                del question["display_correct_answers"]
        
        self.state.current_questions = selected_questions
        self.state.current_question_index = 0
        self.state.answers_given = [None] * len(selected_questions)  # Initialize with None
        self.state.flagged_questions = [False] * len(selected_questions)
        self.state.quiz_started = True
        self.state.quiz_completed = False
        self.state.score = 0  # Reset score
        
        # Initialize timer
        self.state.start_time = datetime.now()
        self.state.end_time = self.state.start_time + timedelta(minutes=2 * len(selected_questions))
        self.state.completion_time = None
        
        self.save_state()

    def should_complete_quiz(self) -> bool:
        """Check if the quiz should be completed"""
        if not self.state.answers_given:
            return False
        
        # Check if all questions have been answered
        all_answered = all(
            answer is not None and any(answer) 
            for answer in self.state.answers_given
        )
        
        # Check if we're on the last question
        is_last_question = (
            self.state.current_question_index == 
            len(self.state.current_questions) - 1
        )
        
        return all_answered and is_last_question

    def submit_answer(self, user_answers: List[bool]) -> bool:
        """Submit an answer for the current question"""
        current_question = self.get_current_question()
        if current_question:
            # Ensure answers_given is properly initialized
            if self.state.answers_given is None:
                self.state.answers_given = [None] * len(self.state.current_questions)
            
            # Get the current options and correct answers
            options = current_question.get("display_options", [])
            correct_answers = current_question.get("display_correct_answers", [])
            
            # Save the answer aligned with the current options
            self.state.answers_given[self.state.current_question_index] = user_answers.copy()
            
            # Check if answer is correct using the current correct answers
            is_correct = check_answer(user_answers, correct_answers)
            if is_correct:
                self.state.score += 1
            
            # Check if this is the last question
            is_last_question = self.state.current_question_index == len(self.state.current_questions) - 1
            
            # If we should complete the quiz
            if self.should_complete_quiz():
                self.state.completion_time = datetime.now()  # Set completion time
                self.state.quiz_completed = True
                self.state.quiz_started = False
                self.save_state()
                return is_correct
            
            # If it's the last question but not all are answered
            if is_last_question:
                # Count unanswered and flagged questions
                unanswered = sum(1 for answer in self.state.answers_given 
                               if answer is None or not any(answer))
                flagged = sum(1 for flag in self.state.flagged_questions if flag)
                
                # Set message about remaining tasks
                message = []
                if unanswered > 0:
                    message.append(f"{unanswered} question(s) still need to be answered (marked with ◻️)")
                if flagged > 0:
                    message.append(f"{flagged} question(s) are flagged for review (marked with 🚩)")
                st.session_state.last_question_message = " and ".join(message)
            else:
                # Move to next question if not the last
                self.state.current_question_index += 1
                self.state.current_options = []
                self.state.current_correct_answers = []
            
            self.save_state()
            return is_correct
        return False

    def reset(self) -> None:
        self.state_manager.clear_quiz_state()
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
            # Always use stored options if they exist
            if "display_options" in current_question:
                # Use the previously stored (shuffled) options
                options = current_question["display_options"]
                correct_answers = current_question["display_correct_answers"]
                logger.debug(f"Using stored options: {options}")
            else:
                # First time seeing this question, shuffle and store
                options, correct_answers, _ = get_shuffled_options(current_question)
                # Store them in the question for persistence
                current_question["display_options"] = options.copy()
                current_question["display_correct_answers"] = correct_answers.copy()
                logger.debug(f"Generated new shuffled options: {options}")
            
            # Always update the state with current options
            self.state.current_options = options
            self.state.current_correct_answers = correct_answers
            self.save_state()

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
        self.save_state()

    def navigate_to_question(self, question_index: int) -> None:
        """Navigate to a specific question"""
        if 0 <= question_index < len(self.state.current_questions):
            self.state.current_question_index = question_index
            # Don't clear options and answers anymore
            self.prepare_question_options()  # Ensure options are loaded
            self.save_state()

    def complete_quiz(self):
        """Mark the quiz as complete and save state"""
        # Initialize answers_given if it's None
        if self.state.answers_given is None:
            self.state.answers_given = []
        
        # Fill any unanswered questions with empty answers
        for i in range(len(self.state.current_questions)):
            if i >= len(self.state.answers_given):
                self.state.answers_given.append([False] * len(self.state.current_options))
            elif self.state.answers_given[i] is None:
                self.state.answers_given[i] = [False] * len(self.state.current_options)
        
        # Record completion time
        if not self.state.completion_time:  # Only set if not already set
            self.state.completion_time = datetime.now()
        
        self.state.quiz_completed = True
        self.state.quiz_started = False
        self.save_state()
        
        # Force a state save to ensure persistence
        if self.state_manager:
            self.state_manager.save_quiz_state(asdict(self.state))

    def get_answered_count(self) -> int:
        """Get the number of answered questions"""
        if not self.state.answers_given:
            return 0
        return sum(1 for answer in self.state.answers_given 
                  if answer is not None and any(answer))

    def is_question_answered(self, index: int) -> bool:
        """Check if a specific question is answered"""
        if (self.state.answers_given and 
            0 <= index < len(self.state.answers_given) and 
            self.state.answers_given[index] is not None):
            return any(self.state.answers_given[index])
        return False