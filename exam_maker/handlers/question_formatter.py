import re
import json
from exam_maker.logger import app_logger

# Define the question schema
QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "Question": {
            "type": "string",
            "description": "The question text"
        },
        "Options": {
            "type": "object",
            "properties": {
                "A": {"type": "string"},
                "B": {"type": "string"},
                "C": {"type": "string"},
                "D": {"type": "string"}
            },
            "required": ["A", "B", "C", "D"],
            "additionalProperties": False
        },
        "Answer": {
            "type": "string",
            "enum": ["A", "B", "C", "D"],
            "description": "The correct answer option"
        }
    },
    "required": ["Question", "Options", "Answer"],
    "additionalProperties": False
}

class QuestionFormatter:
    def __init__(self):
        self.logger = app_logger

    def normalize_question_output(self, question_text):
        """
        Formats the question text from JSON into a standardized string format.
        
        Args:
            question_text (str): The JSON response from the model
            
        Returns:
            str: The formatted question text
        """
        self.logger.debug("--------------------------------")
        self.logger.debug(question_text)
        self.logger.debug("--------------------------------")

        if not question_text:
            return "Error: Empty response for question."

        try:
            # Parse the JSON response
            data = json.loads(question_text)
            
            # Format the question text
            formatted_text = f"Question: {data['Question']}\n\n"
            formatted_text += "Options:\n"
            for option in ['A', 'B', 'C', 'D']:
                formatted_text += f"{option}) {data['Options'][option]}\n"
            formatted_text += f"\nAnswer: {data['Answer']})"
            
            return formatted_text
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {str(e)}")
            return f"Error: Invalid JSON format - {str(e)}"
        except KeyError as e:
            self.logger.error(f"Missing required field: {str(e)}")
            return f"Error: Missing required field - {str(e)}"
        except Exception as e:
            self.logger.error(f"Error formatting question: {str(e)}")
            return f"Error: {str(e)}" 