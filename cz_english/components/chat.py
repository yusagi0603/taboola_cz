from pathlib import Path
import time
import gradio as gr
import json
from json_repair import repair_json
import re
import logging
from datetime import datetime
from typing import List, Tuple

from cz_english.logger import app_logger
from cz_english.utils import generate_docx_file


CONVERSATION_STARTER = "Click this button to make the passage longer"
ARTICLE_REVISION_PATH = Path(__file__).parent.parent / "prompt" / "article_revision.jinja"
ARTICLE_FORMAT_PROMPT = Path(__file__).parent.parent / "prompt" / "article_format.jinja"
QUESTION_FORMAT_PROMPT = Path(__file__).parent.parent / "prompt" / "question_format.jinja"
word_comprehension_generation_path = Path(__file__).parent.parent / "prompt" / "word_comprehension.jinja"
grammatical_structure_generation_path = Path(__file__).parent.parent / "prompt" / "grammatical_structure.jinja"
textual_inference_generation_path = Path(__file__).parent.parent / "prompt" / "textual_inference.jinja"
chapter_summary_generation_path = Path(__file__).parent.parent / "prompt" / "chapter_summary.jinja"
chapter_details_generation_path = Path(__file__).parent.parent / "prompt" / "chapter_details.jinja"
chapter_structure_generation_path = Path(__file__).parent.parent / "prompt" / "chapter_structure.jinja"
with open(ARTICLE_REVISION_PATH, 'r', encoding='utf-8') as f:
    ARTICLE_REVISION_PROMPT = f.read()

with open(ARTICLE_FORMAT_PROMPT, 'r', encoding='utf-8') as f:
    ARTICLE_FORMAT_PROMPT = f.read()

with open(QUESTION_FORMAT_PROMPT, 'r', encoding='utf-8') as f:
    QUESTION_FORMAT_PROMPT = f.read()

with open(word_comprehension_generation_path, 'r', encoding='utf-8') as f:
    word_comprehension_prompt = f.read()

with open(grammatical_structure_generation_path, 'r', encoding='utf-8') as f:
    grammatical_structure_prompt = f.read()

with open(textual_inference_generation_path, 'r', encoding='utf-8') as f:
    textual_inference_prompt = f.read()

with open(chapter_summary_generation_path, 'r', encoding='utf-8') as f:
    chapter_summary_prompt = f.read()

with open(chapter_details_generation_path, 'r', encoding='utf-8') as f:
    chapter_details_prompt = f.read()

with open(chapter_structure_generation_path, 'r', encoding='utf-8') as f:
    chapter_structure_prompt = f.read()

# Mapping of problem types to their corresponding prompts
PROBLEM_TYPE_TO_PROMPT = {
    "word_comprehension": word_comprehension_prompt,
    "grammatical_structure": grammatical_structure_prompt,
    "textual_inference": textual_inference_prompt,
    "chapter_summary": chapter_summary_prompt,
    "chapter_details": chapter_details_prompt,
    "chapter_structure": chapter_structure_prompt
}

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.chat_ui = None  # Will store reference to the chat UI group
        self._define_components()
        self.logger = app_logger

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
            render=False,
            elem_classes=["fullscreen-editor"],
        )

        # Store problem textboxes in a list
        self.problem_textboxes = [
            gr.Textbox(  # word_comprehension
                label="word_comprehension",  
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            ),
            gr.Textbox(  # grammatical_structure
                label="grammatical_structure",
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            ),
            gr.Textbox(  # textual_inference
                label="textual_inference",
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            ),
            gr.Textbox(  # chapter_summary
                label="chapter_summary",
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            ),
            gr.Textbox(  # chapter_details
                label="chapter_details",
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            ),
            gr.Textbox(  # chapter_structure
                label="chapter_structure",
                lines=4,
                render=False,
                interactive=True,
                elem_classes=["fullscreen-editor"]
            )
        ]

        # Problem type to index mapping
        self.problem_type_to_index = {
            "word_comprehension": 0,
            "grammatical_structure": 1,
            "textual_inference": 2,
            "chapter_summary": 3,
            "chapter_details": 4,
            "chapter_structure": 5
        }

        self.selected_problem_index = gr.State(value=0)

        # Replace buttons with dropdowns
        self.difficulty_dropdown = gr.Dropdown(
            choices=["lower", "same", "higher"],
            value="same",
            label="Difficulty Level",
            render=False
        )
        
        self.question_type_dropdown = gr.Dropdown(
            choices=list(self.problem_type_to_index.keys()),
            value="word_comprehension",
            label="Question Type",
            render=False
        )
        
        self.generate_question_button = gr.Button("Generate Question", render=False)
        
        # Keep the old buttons for reference but don't render them
        self.button1 = gr.Button("word_comprehension", elem_id="button1", visible=False, render=False)
        self.button2 = gr.Button("grammatical_structure", elem_id="button2", visible=False, render=False)
        self.button3 = gr.Button("textual_inference", elem_id="button3", visible=False, render=False)
        
        self.submit_button = gr.Button("產生考題", elem_id="submit_button", render=False)

    def _generate_final_exam_doc(
            self, 
            article_content,
            question_1, question_2, question_3, question_4, question_5, question_6
        ):
        """Compose the final exam from the three problem textboxes."""
        
        # Compose the full exam content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc_file_name = f"英文考題 - {timestamp}"
        
        # Return the exam content as a downloadable document
        question_info_tuple = [
            ("文章", article_content),
            ("題型1 - Word Comprehension", question_1),
            ("題型2 - Grammatical Structure", question_2),
            ("題型3 - Textual Inference", question_3),
            ("題型4 - Chapter Summary", question_4),
            ("題型5 - Chapter Details", question_5),
            ("題型6 - Chapter Structure", question_6)
        ]
        doc_file_name = generate_docx_file(
            doc_file_name,
            question_info_tuple
        )
        
        return doc_file_name, gr.update(visible=True) 


    def _handle_response(self, message, history, textbox_content):
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

    def generate_problem(self, problem_type, current_article, difficulty="Medium", current_problem_content=""):
        prompt = PROBLEM_TYPE_TO_PROMPT[problem_type]

        current_problem_context = ""
        if current_problem_content.strip():
            problems = current_problem_content.split("\n---\n")
            last_problem = problems[-1].strip()
            if last_problem:
                current_problem_context = f"Here is the last problem generated of this type:\n{last_problem}\n\nPlease generate a new, different problem."

        integrated_prompt = QUESTION_FORMAT_PROMPT.format(
            generated_article=current_article,
            prompt=prompt,
            difficulty=difficulty
        )
        
        if current_problem_context:
            integrated_prompt = integrated_prompt.format(
                current_problem_context=current_problem_context
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
            # if question_content and self._validate_question_format(question_content):
            return question_content
            # else:
                # app_logger.error(f"Invalid question format: {question_content}")
                # return "Invalid question format. Please try again."
    # def handle_response_for_exceeding_token_quota(self, message, history, textbox_content):
    #     # Mock response data
    #     mock_response = {
    #         'current_lesson_plan': f"Here is a mock lesson plan based on: {textbox_content}",
    #         'suggestion': "This is a mock suggestion for your content.",
    #         'next_step_prompt': [["Continue", "Revise", "Start Over"]]
    #     }
        
    #     # Simulate streaming by yielding partial responses
    #     yield "Loading suggestion...", "", [[]]
    #     yield mock_response['suggestion'], "", [[]]
    #     yield mock_response['suggestion'], mock_response['current_lesson_plan'], [[]]
    #     yield mock_response['suggestion'], mock_response['current_lesson_plan'], mock_response['next_step_prompt']
    


    
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

    def append_problem(self, question_type, difficulty, current_content, current_article):
        new_problem = self.generate_problem(question_type, current_article, difficulty)
        
        if current_content.strip():
            return current_content + "\n---\n" + new_problem
        else:
            return new_problem

    def handle_generate_question(self, question_type, difficulty, selected_textbox, current_article):
        # Generate the new problem
        # print(selected_textbox)
        new_problem = self.generate_problem(question_type, current_article, difficulty, selected_textbox)
        
        # Prepare the output
        if new_problem and selected_textbox.strip():
            return selected_textbox + "\n---\n" + new_problem
        else:
            return new_problem or selected_textbox or ""

    def update_selected_problem_index(self, problem_type, current_problem_index):
        print(self.problem_type_to_index[problem_type])
        return self.problem_type_to_index[problem_type]


    def render(self):
        with gr.Group(visible=False) as chat_ui:

            with gr.Row(equal_height=True):
                # Left Column
                with gr.Column():
                    self.chatbot.render()
                    self.prompt_input.render()
                    # self.quick_response.render()
                    self.hidden_list.render()
                    # Don't render the old buttons
                    
                    # Move dropdowns and button to left column
                    with gr.Row():
                        self.question_type_dropdown.render()
                        self.difficulty_dropdown.render()
                    
                    self.selected_problem_index.render()
                    
                    self.prompt_display = gr.Textbox(
                        label="Generated Prompt",
                        lines=10,
                        elem_classes=["fullscreen-editor"],
                    )
                    
                    self.generate_question_button.render()
                    
                # Right column
                with gr.Column():
                    self.textbox.render()
                    
                    # Render all textboxes from the list
                    for textbox in self.problem_textboxes:
                        textbox.render()

            # Move ChatInterface outside of the columns to avoid duplicate rendering
            gr.ChatInterface(
                self._handle_response,
                chatbot=self.chatbot,
                textbox=self.prompt_input,
                examples=[[CONVERSATION_STARTER, None]],
                additional_inputs=[self.textbox],
                additional_outputs=[self.textbox, self.hidden_list],
                type="messages"
            )

            with gr.Row():
                self.submit_button.render()
            with gr.Row():
                download_button = gr.DownloadButton("Download Word Document", visible=False)


        self.question_type_dropdown.change(
            fn=self.update_selected_problem_index,
            inputs=[self.question_type_dropdown, self.selected_problem_index],
            outputs=[self.selected_problem_index]
        )

        self.generate_question_button.click(
            fn=self.handle_generate_question,
            inputs=[
                self.question_type_dropdown,
                self.difficulty_dropdown,
                self.problem_textboxes[self.selected_problem_index.value],
                self.textbox
            ],
            outputs=self.problem_textboxes[self.selected_problem_index.value]
        )
        
        # Keep the old button handlers for reference but they won't be used
        # self.button1.click(self.append_problem, inputs=[self.button1, self.textbox_prob1, self.textbox], outputs=[self.textbox_prob1])
        # self.button2.click(self.append_problem, inputs=[self.button2, self.textbox_prob2, self.textbox], outputs=[self.textbox_prob2])
        # self.button3.click(self.append_problem, inputs=[self.button3, self.textbox_prob3, self.textbox], outputs=[self.textbox_prob3])
        
        self.submit_button.click(
            fn=self._generate_final_exam_doc,
            inputs=[self.textbox] + self.problem_textboxes,
            outputs=[download_button, download_button]
        )

        return chat_ui  # Return the group for access in the main app 
