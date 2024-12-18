import streamlit as st
from typing import Dict, Any, Optional
import json

class StateManager:
    def __init__(self):
        self.QUIZ_STATE_KEY = "quiz_state"
        self.QUESTIONS_KEY = "current_questions"

    def initialize_state(self):
        from quiz_manager import QuizManager
        
        # Initialize session state variables
        if 'quiz_manager' not in st.session_state:
            st.session_state.quiz_manager = QuizManager()
        
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        
        # Try to load questions from session state
        if self.QUESTIONS_KEY not in st.session_state:
            st.session_state[self.QUESTIONS_KEY] = []
        
        if 'quiz_started' not in st.session_state:
            st.session_state.quiz_started = False

    def save_quiz_state(self, quiz_state: Dict[str, Any]) -> None:
        """
        Save the current quiz state to session state
        """
        st.session_state[self.QUIZ_STATE_KEY] = quiz_state
        st.session_state.quiz_state_saved = True

    def load_quiz_state(self) -> Optional[Dict[str, Any]]:
        """
        Load the quiz state from session state
        """
        if st.session_state.get('quiz_state_saved', False):
            return st.session_state.get(self.QUIZ_STATE_KEY)
        return None

    def clear_quiz_state(self) -> None:
        """
        Clear the saved quiz state from session state
        """
        if self.QUIZ_STATE_KEY in st.session_state:
            del st.session_state[self.QUIZ_STATE_KEY]
        if 'quiz_state_saved' in st.session_state:
            del st.session_state.quiz_state_saved
        if 'quiz_started' in st.session_state:
            del st.session_state.quiz_started
        if self.QUESTIONS_KEY in st.session_state:
            del st.session_state[self.QUESTIONS_KEY]

    def save_questions(self, questions: list) -> None:
        """
        Save the current questions to session state
        """
        st.session_state[self.QUESTIONS_KEY] = questions