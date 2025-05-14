import re
import json
from exam_maker.logger import app_logger

class QuestionFormatter:
    def __init__(self):
        self.logger = app_logger

    def normalize_question_output(self, question_text):
        """
        Normalizes the format of a question text to ensure consistent structure.
        
        Args:
            question_text (str): The raw question text to be normalized
            
        Returns:
            str: The normalized question text with consistent formatting
        """
        self.logger.debug("--------------------------------")
        self.logger.debug(question_text)
        self.logger.debug("--------------------------------")

        if not question_text:
            return "Error: Empty response for question."

        text = question_text.strip()
        if text.startswith('{') and text.endswith('}'):
            try:
                json_data = json.loads(text)
                if 'current_lesson_plan' in json_data:
                    text = json_data['current_lesson_plan']
            except Exception:
                pass

        # Remove markdown code blocks
        text = re.sub(r'```[a-zA-Z]*\n', '', text)
        text = re.sub(r'```', '', text)

        # Normalize line endings
        text = text.replace('\r\n', '\n')

        # Standardize option formats
        option_patterns = [
            (r'Option\s*([A-D])[:\.\s]*', r'\1) '),    # Option A: -> A)
            (r'([A-D])\.\s*', r'\1) '),                # A. -> A)
            (r'\(([A-D])\)', r'\1)'),                  # (A) -> A)
            (r'([A-D]):', r'\1)'),                     # A: -> A)
            (r'([A-D])\)\s*\)', r'\1)'),               # A)) -> A)
            (r'([A-D])\)\s*([^\s])', r'\1) \2'),      # Ensure space after A)
        ]
        for pattern, repl in option_patterns:
            text = re.sub(pattern, repl, text)

        # Ensure Question: prefix
        if not text.startswith("Question:") and "Question:" not in text:
            match = re.search(r'^\s*(\d+\.\s*|Q\d+\.\s*|Question\s*\d+:)', text, re.IGNORECASE)
            if match:
                text = "Question: " + text[match.end():].strip()
            else:
                text = "Question: " + text

        # Add Options: section if missing
        if "Options:" not in text and any(opt in text for opt in ["A)", "B)", "C)", "D)"]):
            first_option = re.search(r'(A\))', text)
            if first_option:
                idx = first_option.start()
                text = text[:idx] + "Options:\n" + text[idx:]

        # Ensure Answer: section
        if "Answer:" not in text:
            text += "\n\nNote: Missing 'Answer:' field."
        else:
            answer_match = re.search(r'Answer:\s*([A-D])\s*[^)]?', text)
            if answer_match:
                answer_letter = answer_match.group(1)
                text = re.sub(r'Answer:\s*([A-D])\s*[^)]?', f'Answer: {answer_letter})', text)

        # Normalize multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Check for missing required elements
        required_elements = ["Question:", "Options:", "A)", "B)", "C)", "D)", "Answer:"]
        missing_elements = [elem for elem in required_elements if elem not in text]
        if missing_elements:
            text += "\n\nNote: The following elements are missing: " + ", ".join(missing_elements)

        return text 