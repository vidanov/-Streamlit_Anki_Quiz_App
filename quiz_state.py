from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class QuizState:
    current_questions: List[Dict] = field(default_factory=list)
    current_question_index: int = 0
    current_options: List[str] = field(default_factory=list)
    current_correct_answers: List[int] = field(default_factory=list)
    answers_given: List[List[bool]] = field(default_factory=list)
    flagged_questions: List[bool] = field(default_factory=list)
    quiz_started: bool = False
    quiz_completed: bool = False
    score: int = 0
    # Timer fields
    start_time: Optional[datetime] = field(default=None)
    end_time: Optional[datetime] = field(default=None)
    completion_time: Optional[datetime] = field(default=None)

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