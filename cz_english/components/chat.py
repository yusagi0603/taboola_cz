from pathlib import Path
import time
import gradio as gr
import json
from json_repair import repair_json
import re

CONVERSATION_STARTER = "Click this button to make the passage longer"
ARTICLE_REVISION_PATH = Path(__file__).parent.parent / "prompt" / "article_revision.jinja"
ARTICLE_FORMAT_PROMPT = Path(__file__).parent.parent / "prompt" / "article_format.jinja"
QUESTION_FORMAT_PROMPT = Path(__file__).parent.parent / "prompt" / "question_format.jinja"
CLOZE_GENERATION_PATH = Path(__file__).parent.parent / "prompt" / "cloze_generation.jinja"
COMPREHENSION_GENERATION_PATH = Path(__file__).parent.parent / "prompt" / "comprehension_generation.jinja"
SUMMARY_GENERATION_PATH = Path(__file__).parent.parent / "prompt" / "summary_generation.jinja"
with open(ARTICLE_REVISION_PATH, 'r', encoding='utf-8') as f:
    ARTICLE_REVISION_PROMPT = f.read()

with open(ARTICLE_FORMAT_PROMPT, 'r', encoding='utf-8') as f:
    ARTICLE_FORMAT_PROMPT = f.read()

with open(QUESTION_FORMAT_PROMPT, 'r', encoding='utf-8') as f:
    QUESTION_FORMAT_PROMPT = f.read()

with open(CLOZE_GENERATION_PATH, 'r', encoding='utf-8') as f:
    CLOZE_PROMPT = f.read()

with open(COMPREHENSION_GENERATION_PATH, 'r', encoding='utf-8') as f:
    COMPREHENSION_PROMPT = f.read()

with open(SUMMARY_GENERATION_PATH, 'r', encoding='utf-8') as f:
    SUMMARY_PROMPT = f.read()

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
            label="Cloze",  
            lines=4,
            render=False,
            interactive=True
        )
        self.textbox_prob2 = gr.Textbox(  # Canvas
            label="Comprehension",
            lines=4,
            render=False,
            interactive=True
        )
        self.textbox_prob3 = gr.Textbox(  # Canvas
            label="Summary",
            lines=4,
            render=False,
            interactive=True
        )

        # TODO: Audrey uses this to add problems
        self.button1 = gr.Button("Cloze", elem_id="button1",render=False)
        self.button2 = gr.Button("Comprehension", elem_id="button2",render=False)
        self.button3 = gr.Button("Summary", elem_id="button3",render=False)
        self.submit_button = gr.Button("產生考題", elem_id="submit_button",render=False)


    def handle_response(self, message, history, textbox_content):
        integrated_message = message

        if message == CONVERSATION_STARTER:
            integrated_message = ARTICLE_REVISION_PROMPT.format(
                generated_article=textbox_content, 
                message=message,
            )
        elif textbox_content != "":
            integrated_message = ARTICLE_FORMAT_PROMPT.format(
                generated_article=textbox_content,  # Use the parameter
                message=message,
                textbox_content=textbox_content
            )

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

                try:
                    # Use repair_json function instead of json_repair.loads
                    repaired_json = repair_json(full_response)
                    if isinstance(repaired_json, str):
                        repaired_json = json.loads(repaired_json)
                    
                    current_lesson_plan = repaired_json.get('current_lesson_plan', '')
                    
                    suggestion = repaired_json.get('suggestion', '')
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
                    pass

                yield suggestion, current_lesson_plan, [[]]

        try:
            repaired_json = repair_json(full_response)
            if isinstance(repaired_json, str):
                repaired_json = json.loads(repaired_json)
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

    def add_problem(self, problem_type, problems):
        problem_name = problem_type + str(time.time())
        problems[problem_name] = problem_type
        return problems

    def generate_problem(self, problem_type, current_article):
        
        if problem_type == "Cloze":
            prompt = CLOZE_PROMPT
        elif problem_type == "Comprehension":
            prompt = COMPREHENSION_PROMPT
        elif problem_type == "Summary":
            prompt = SUMMARY_PROMPT

        integrated_prompt = QUESTION_FORMAT_PROMPT.format(
            generated_article=current_article,
            prompt=prompt
        )

        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=integrated_prompt,
        )
        
        full_response = "" 
        
        with self.client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        ) as stream:
            for text_delta in stream.text_deltas:
                full_response += text_delta
        
        json_objects = []
        start_positions = [m.start() for m in re.finditer(r'{\s*"', full_response)]
        
        for start in start_positions:
            try:
                json_str = full_response[start:]
                parsed = json.loads(json_str)
                json_objects.append(parsed)
            except:
                pass

        if json_objects:
            last_json = json_objects[-1]
            question_content = last_json.get('current_lesson_plan', '')
            if question_content and self._validate_question_format(question_content):
                return question_content

        return full_response
    
    def _validate_question_format(self, text):
        required_elements = [
            r'Question: ',
            r'Options:',
            r'A\) ',
            r'B\) ',
            r'C\) ',
            r'D\) ',
            r'Answer: [A-D]\)'
        ]
        
        for element in required_elements:
            if not re.search(element, text, re.MULTILINE):
                return False
        return True

    def generate_final_exam_doc(self, textbox_content):
        pass
        
    def append_problem(self, problem_type, current_content, current_article):
        new_problem = self.generate_problem(problem_type, current_article)
        
        if current_content.strip():
            return current_content + "\n---\n" + new_problem
        else:
            return new_problem

    def render(self):

        problem_state = gr.State({})

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
        self.button1.click(self.append_problem, inputs=[self.button1, self.textbox_prob1, self.textbox], outputs=[self.textbox_prob1])
        self.button2.click(self.append_problem, inputs=[self.button2, self.textbox_prob2, self.textbox], outputs=[self.textbox_prob2])
        self.button3.click(self.append_problem, inputs=[self.button3, self.textbox_prob3, self.textbox], outputs=[self.textbox_prob3])


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
