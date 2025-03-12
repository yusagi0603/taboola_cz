import gradio as gr
from config import CONVERSATION_STARTER
import json
from json_repair import repair_json
import json_repair

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        
        # Initialize components
        self.chatbot = gr.Chatbot(type="messages")
        self.textbox = gr.Textbox(  # Canvas
            label="文章編輯",
            lines=20,
            render=False
        )
        self.prompt_input = gr.Textbox(  # User prompt
            submit_btn=True,
            render=False
        )
        self.quick_response = gr.Dataset(  # Suggested user prompt
            samples=[[CONVERSATION_STARTER]],
            components=[self.prompt_input],
            render=False
        )
        self.hidden_list = gr.JSON(
            value=[[]],
            render=False,
            visible=False
        )

    def handle_response(self, message, history, textbox_content):
        integrated_message = message

        if not (message == CONVERSATION_STARTER or textbox_content == ""):
            integrated_message = f"""
            用戶當前的需求：
            {message}

            用戶對您生成的題目進行了以下修改：
            {textbox_content}

            請根據用戶的需求和修改內容，更新題目，並依照步驟生成下一部分內容。
            確保您：
            1. 完整保留用戶的修改。
            2. 提供清晰的建議（`suggestion`）。
            3. 提供下一步的行動選項（`next_step_prompt`）。
            """

        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=integrated_message,
        )
        full_response = ""
        current_lesson_plan = ""
        suggestion = ""
        next_step_prompt = [[]]

        with self.client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        ) as stream:
            for text_delta in stream.text_deltas:
                full_response += text_delta

                repaired_json = json_repair.loads(full_response)
                try:
                    current_lesson_plan = repaired_json.get('current_lesson_plan', '')
                except:
                    current_lesson_plan = ""
                try:
                    suggestion = repaired_json.get('suggestion', '')
                except:
                    suggestion = ""

                yield suggestion, current_lesson_plan, [[]]

        try:
            repaired_json = json.loads(full_response)
            next_step_prompt = repaired_json.get('next_step_prompt', [["進入下一步"]])
        except:
            next_step_prompt = [["進入下一步"]]

        yield suggestion, current_lesson_plan, next_step_prompt

    def handle_quick_response_click(self, selected):
        return selected[0]

    def handle_quick_response_samples(self, next_step_prompt):
        if len(next_step_prompt) > 0 and len(next_step_prompt[0]) > 0:
            return gr.Dataset(samples=next_step_prompt, visible=True)
        return gr.Dataset(samples=[['-']], visible=False)

    def render(self):
        with gr.Row(equal_height=True):
            with gr.Column():
                self.textbox.render()
                self.prompt_input.render()
                self.quick_response.render()
                self.hidden_list.render()
            with gr.Column():
                gr.ChatInterface(
                    self.handle_response,
                    textbox=self.prompt_input,
                    examples=[[CONVERSATION_STARTER, None]],
                    additional_inputs=[self.textbox],
                    additional_outputs=[self.textbox, self.hidden_list],
                    type="messages"
                )

        # Set up event handlers
        self.quick_response.click(
            self.handle_quick_response_click,
            self.quick_response,
            self.prompt_input
        )
        self.hidden_list.change(
            self.handle_quick_response_samples,
            self.hidden_list,
            self.quick_response
        ) 