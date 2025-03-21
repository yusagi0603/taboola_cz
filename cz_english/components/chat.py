import time
import gradio as gr
from config import CONVERSATION_STARTER
import json
from json_repair import repair_json
import json_repair

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self._define_components()

    def _define_components(self):
        
        # Initialize components
        self.chatbot = gr.Chatbot(type="messages")


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

        self.output_container = gr.Group()

        self.textbox = gr.Textbox(  # Canvas
            label="文章編輯",
            lines=20,
            render=False
        )

        # TODO: Yu uses this to generate final exam questions
        # TOOD: Audrey uses this to populate the problems
        self.textbox_prob1 = gr.Textbox(  # Canvas
            label="題型1",  
            lines=4,
            render=False,
            interactive=True
        )
        self.textbox_prob2 = gr.Textbox(  # Canvas
            label="題型2",
            lines=4,
            render=False,
            interactive=True
        )
        self.textbox_prob3 = gr.Textbox(  # Canvas
            label="題型3",
            lines=4,
            render=False,
            interactive=True
        )

        # TODO: Audrey uses this to add problems
        self.button1 = gr.Button("題型1", elem_id="button1",render=False)
        self.button2 = gr.Button("題型2", elem_id="button2",render=False)
        self.button3 = gr.Button("題型3", elem_id="button3",render=False)
        self.submit_button = gr.Button("產生考題", elem_id="submit_button",render=False)


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

    def handle_response2(self, message, history, textbox_content):
        # Mock response data
        mock_response = {
            'current_lesson_plan': f"Here is a mock lesson plan based on: {textbox_content}",
            'suggestion': "This is a mock suggestion for your content.",
            'next_step_prompt': [["Continue", "Revise", "Start Over"]]
        }
        
        # Simulate streaming by yielding partial responses
        yield "Loading suggestion...", "", [[]]
        yield mock_response['suggestion'], "", [[]]
        yield mock_response['suggestion'], mock_response['current_lesson_plan'], [[]]
        yield mock_response['suggestion'], mock_response['current_lesson_plan'], mock_response['next_step_prompt']
    

    def add_problem(self, problem_type, problems):
        problem_name = problem_type + str(time.time())
        problems[problem_name] = problem_type
        return problems

    def generate_problem(self, problem_type):
        if problem_type == "題型1":
            prompt = "題型1"
        elif problem_type == "題型2":
            prompt = "題型2"
        elif problem_type == "題型3":
            prompt = "題型3"

        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
        )
        with self.client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        ) as stream:
            for text_delta in stream.text_deltas:
                full_response += text_delta

        return full_response

    def generate_final_exam_doc(self, textbox_content):
        pass
        



    def render(self):

        problem_state = gr.State({
        })


        with gr.Row(equal_height=True):
            with gr.Column():
                gr.Markdown("## 英文考題產生器")
        with gr.Row(equal_height=True):
            # Left column
            with gr.Column():
                self.chatbot.render()
                self.prompt_input.render()
                # self.quick_response.render()
                self.hidden_list.render()
                self.button1.render()
                self.button2.render()
                self.button3.render()
                self.submit_button.render()
            
            # Right column
            with gr.Column():
                self.textbox.render()
                self.textbox_prob1.render()
                self.textbox_prob2.render()
                self.textbox_prob3.render()

                # TODO: Dynamic render problem textbox
                # @gr.render(inputs=problem_state)
                # def render_problem(problems):
                #     for name, problem in enumerate(problems):
                #         gr.Textbox(value=problem, interactive=True, elem_id=f"name")


                gr.ChatInterface(
                    self.handle_response,
                    chatbot=self.chatbot,
                    textbox=self.prompt_input,
                    examples=[[CONVERSATION_STARTER, None]],
                    additional_inputs=[self.textbox],
                    additional_outputs=[self.textbox, self.hidden_list],
                    type="messages"
                )

        # TODO: Audrey uses this to add problems
        self.button1.click(self.generate_problem, inputs=[self.button1], outputs=[self.textbox_prob1])
        self.button2.click(self.generate_problem, inputs=[self.button2], outputs=[self.textbox_prob2])
        self.button3.click(self.generate_problem, inputs=[self.button3], outputs=[self.textbox_prob3])


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