from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class QuizState:
    current_questions: List[Dict] = field(default_factory=list)
    current_question_index: int = 0
    current_options: List[str] = field(default_factory=list)
    current_correct_answers: List[bool] = field(default_factory=list)
    answers_given: List[List[bool]] = field(default_factory=list)
    flagged_questions: List[bool] = field(default_factory=list)
    quiz_completed: bool = False
    quiz_started: bool = False
    score: int = 0 