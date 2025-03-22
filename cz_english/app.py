import time

import openai
from openai import OpenAI
import gradio as gr
from typing_extensions import override
from components.chat import Chat

import option
from config import (
    OPENAI_API_KEY,
    ASSISTANT_ID,
    ASSISTANT_INSTRUCTION,
    RESPONSE_FORMAT,
    ASSISTANT_USER_PROMPT
)
from utils import (
    check_password,
    call_llm_to_generate_article
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# View existing assistants
existed_assistants = client.beta.assistants.list(
    order="desc",
    limit="20",
)

print("Existed assistants:")
# for assistant in existed_assistants:
    # print("  ", assistant.id, assistant.name)

chat_box_component = Chat(client, ASSISTANT_ID)

thread = client.beta.threads.create()

# Function to generate content based on dropdown selections
def generate_article_with_chat_interface(grade_values, vocabulary_range_values, topic_range_values, grammar_range_values):
   
    def _compose_params_summary(grade_values, vocabulary_range_values, topic_range_values, grammar_range_values):
        params_summary = "## 初始文章生成參數\n\n"
        
        params_summary += "### 學生年級\n"
        if grade_values:
            params_summary += "選擇的年級: " + ", ".join(grade_values) + "\n\n"
        else:
            params_summary += "未選擇年級\n\n"
            
        params_summary += "### 單字範圍\n"
        if vocabulary_range_values:
            params_summary += "選擇的單字: " + ", ".join(vocabulary_range_values) + "\n\n"
        else:
            params_summary += "未選擇單字\n\n"
            
        params_summary += "### 主題範圍\n"
        if topic_range_values:
            params_summary += "選擇的主題: " + ", ".join(topic_range_values) + "\n\n"
        else:
            params_summary += "未選擇主題\n\n"

        params_summary += "### 文法範圍\n"
        if grammar_range_values:
            params_summary += "選擇的文法: " + ", ".join(grammar_range_values) + "\n\n"
        else:
            params_summary += "未選擇文法\n\n"
        return params_summary
  
    generated_article = call_llm_to_generate_article(
        llm_client=client,
        grade_values=grade_values,
        topic_range_values=topic_range_values,
        grammar_range_values=grammar_range_values,
        vocabulary_range_values=vocabulary_range_values       
    )

    # Combine parameters summary with the generated article
    params_summary = _compose_params_summary(grade_values, vocabulary_range_values, topic_range_values, grammar_range_values)
    content = params_summary + "\n## 生成的文章\n\n" + generated_article + "\n\n請編輯上述文章或使用聊天功能獲取更多幫助。"
    # Enable the chat interface
    return content, gr.update(visible=True), gr.update(visible=False)

with gr.Blocks() as demo:
    
    progress = gr.Progress()

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
            
            # Connect generate button to show chat interface and populate textbox
            generate_button.click(
                generate_article_with_chat_interface,
                inputs=[grade, vocabulary_range, topic_range, grammar_range],
                outputs=[chat_box_component.textbox, chat_ui, selection_ui],
                show_progress="full"
            )

            progress(1.0, "Waiting for response.")
            
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

demo.launch(debug=True)