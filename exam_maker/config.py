import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CORRECT_PASSWORD = os.getenv('ui_password')
ASSISTANT_ID = os.getenv('assistant_id')  
GOOGLE_DRIVE_FOLDER_ID = os.getenv('google_drive_folder_id')

ASSISTANT_MODEL = 'gpt-4.1-mini'
ASSISTANT_NAME = "English reading comprehension passages and question generation"
ASSISTANT_DESCRIPTION = "Generate an English passage based on the conditions provided by the teacher. Then, create comprehension questions based on the passage and rewrite the questions into different formats."
VECTOR_STORE_NAME = "english-question"