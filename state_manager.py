import streamlit as st
from typing import Dict, Any, Optional
import json
import os

class StateManager:
    STATE_FILE = ".quiz_state.json"

    @staticmethod
    def initialize_state():
        from quiz_manager import QuizManager  # Move import here to avoid circular import
        
        # Initialize session state variables
        if 'quiz_manager' not in st.session_state:
            st.session_state.quiz_manager = QuizManager()  # Now this will work
        
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        
        if 'current_questions' not in st.session_state:
            st.session_state.current_questions = []
        
        if 'quiz_started' not in st.session_state:
            st.session_state.quiz_started = False  # Initialize quiz_started here

    @staticmethod
    def save_quiz_state(quiz_state: Dict[str, Any]) -> None:
        """
        Save the current quiz state to both session state and file
        """
        st.session_state.quiz_state = quiz_state
        st.session_state.quiz_state_saved = True
        
        # Save to file
        try:
            with open(StateManager.STATE_FILE, 'w') as f:
                json.dump(quiz_state, f)
        except Exception as e:
            st.error(f"Failed to save state to file: {e}")

    @staticmethod
    def load_quiz_state() -> Optional[Dict[str, Any]]:
        """
        Load the quiz state from file or session state
        """
        # Try session state first
        if st.session_state.get('quiz_state_saved', False):
            return st.session_state.quiz_state
            
        # Try loading from file
        try:
            if os.path.exists(StateManager.STATE_FILE):
                with open(StateManager.STATE_FILE, 'r') as f:
                    state = json.load(f)
                    st.session_state.quiz_state = state
                    st.session_state.quiz_state_saved = True
                    return state
        except Exception as e:
            st.error(f"Failed to load state from file: {e}")
            
        return None

    @staticmethod
    def clear_quiz_state() -> None:
        """
        Clear the saved quiz state from both session and file
        """
        if 'quiz_state' in st.session_state:
            del st.session_state.quiz_state
        if 'quiz_state_saved' in st.session_state:
            del st.session_state.quiz_state_saved
        if 'quiz_started' in st.session_state:
            del st.session_state.quiz_started
            
        # Remove state file if it exists
        try:
            if os.path.exists(StateManager.STATE_FILE):
                os.remove(StateManager.STATE_FILE)
        except Exception as e:
            st.error(f"Failed to remove state file: {e}")