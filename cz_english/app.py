import time

from openai import OpenAI
import gradio as gr
# from components.article_generator import generate_article_with_chat_interface
# from typing_extensions import override
from components.chat import Chat
from components.entry_form import EntryForm
from components.password import Password

import option
from config import (
    ASSISTANT_ID,
    OPENAI_API_KEY,
    ASSISTANT_NAME,
    ASSISTANT_DESCRIPTION,
    ASSISTANT_INSTRUCTION,
    ASSISTANT_MODEL,
    RESPONSE_FORMAT,
    CONVERSATION_STARTER,
    VECTOR_STORE_NAME,
)
from logger import app_logger
from client import llm_client

# View existing assistants
existed_assistants = llm_client.beta.assistants.list(
    order="desc",
    limit="20",
)

# app_logger.info("Existed assistants:")
# for assistant in existed_assistants:
    # app_logger.info("  ", assistant.id, assistant.name)

# chat_box_component = QuestionGenerator(llm_client, ASSISTANT_ID)



# Initialize components
chat = Chat(llm_client, ASSISTANT_ID)
entry_form = EntryForm(llm_client, ASSISTANT_ID)
password = Password()

with gr.Blocks() as demo:
    # Render password UI
    password_popup, password_input, submit_button, error_message = password.render()
    
    # Main UI 
    with gr.Group(visible=False) as main_ui:
        entry_form_ui = entry_form.render()
        chat_ui = chat.render()
        
    # Connect generate button to show chat interface and populate textbox
    entry_form.generate_button.click(
        fn=lambda: gr.update(visible=True),  # Show loading spinner
        outputs=entry_form.spinner,
        show_progress=False,
    ).then(
        fn=entry_form.generate_initial_content,
        inputs=[entry_form.grade, entry_form.vocabulary_range, entry_form.topic_range, entry_form.grammar_range],
        outputs=[chat.textbox, chat_ui, entry_form_ui],
    ).then(
        fn=lambda: gr.update(visible=False),  # Hide loading spinner when done
        outputs=entry_form.spinner,
        show_progress=False,
    )
            
    # Connect password events
    # TODO: move to password.py
    submit_button.click(
        password.check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )
    password_input.submit(
        password.check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )

demo.launch(debug=True)