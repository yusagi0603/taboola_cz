import sys
from pathlib import Path

# Add the parent directory of cz_english to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import gradio as gr
from components.chat import Chat
from components.entry_form import EntryForm
from components.password import Password

from config import (
    ASSISTANT_ID
)
from client import llm_client

# View existing assistants
existed_assistants = llm_client.beta.assistants.list(
    order="desc",
    limit="20",
)

# Load custom CSS
css_path = Path(__file__).parent / "styles" / "styles.css"
with open(css_path, "r") as f:
    custom_css = f.read()

# Initialize components
chat = Chat(llm_client, ASSISTANT_ID)
entry_form = EntryForm(llm_client, ASSISTANT_ID)
password = Password()

with gr.Blocks(css=custom_css) as demo:
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