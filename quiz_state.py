from dataclasses import dataclass
from typing import List, Any, Optional

@dataclass
class QuizState:
    current_questions: List[dict] = None
    current_question_index: int = 0
    current_options: List[str] = None
    current_correct_answers: List[bool] = None
    answers_given: List[Any] = None
    flagged_questions: List[bool] = None
    quiz_completed: bool = False
    quiz_started: bool = False
    score: int = 0
    is_quiz_complete: bool = False

    def __post_init__(self):
        if self.current_questions is None:
            self.current_questions = []
        if self.current_options is None:
            self.current_options = []
        if self.current_correct_answers is None:
            self.current_correct_answers = []
        if self.answers_given is None:
            self.answers_given = []
        if self.flagged_questions is None:
            self.flagged_questions = [] 