import time

from openai import OpenAI
import gradio as gr
from components.question_generator import QuestionGenerator
from components.article_generator import generate_article_with_chat_interface

import option
from config import (
    OPENAI_API_KEY,
    ASSISTANT_ID
)
from utils import (
    check_password
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

chat_box_component = QuestionGenerator(llm_client, ASSISTANT_ID)

# thread = open_ai_client.beta.threads.create() # for assistant API

with gr.Blocks() as demo:
    
    # password UI popup
    with gr.Group(visible=True) as password_popup:
        password_input = gr.Textbox(label="請輸入密碼", type="password")
        submit_button = gr.Button("提交")
        error_message = gr.Textbox(label="", visible=False, interactive=False)
    
    # Main UI 
    with gr.Group(visible=False) as main_ui:
        with gr.Column():
            with gr.Group() as selection_ui:
                gr.Markdown("## 請選擇文章生成參數")
                
                # Three dropdown boxes with multi-select
                grade = gr.Dropdown(
                    choices=option.GRADE_OPTIONS,
                    label="學生年級",
                    multiselect=True
                )
                
                vocabulary_range = gr.Dropdown(
                    choices=option.VOCABULARY_OPTIONS,
                    label="單字範圍",
                    multiselect=True
                )

                grammar_range = gr.Dropdown(
                    choices=option.GRAMMAR_OPTIONS,
                    label="文法範圍",
                    multiselect=True
                )
                
                topic_range = gr.Dropdown(
                    choices=option.TOPIC_OPTIONS,
                    label="主題範圍",
                    multiselect=True
                )
                
                generate_button = gr.Button("生成初始文章")
            
            # Chat interface (initially hidden)
            with gr.Group(visible=False) as chat_ui:
                chat_box_component.render()
            
    # Validate password
    submit_button.click(
        check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )
    password_input.submit(
        check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )
    # Connect generate button to show chat interface and populate textbox
    generate_button.click(
        generate_article_with_chat_interface,
        inputs=[
            grade, vocabulary_range, topic_range, grammar_range
        ],
        outputs=[chat_box_component.textbox, chat_ui, selection_ui],
        show_progress="full"
    )

demo.launch(debug=True)