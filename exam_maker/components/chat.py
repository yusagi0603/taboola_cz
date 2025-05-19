import re
import json
import time
import gradio as gr
from datetime import datetime
from json_repair import repair_json

from exam_maker.logger import app_logger
from exam_maker.handlers.prompt_handler import PromptHandler
from exam_maker.handlers.exam_paper_handler import ExamPaperHandler
from exam_maker.handlers.question_formatter import QuestionFormatter, QUESTION_SCHEMA
from exam_maker.config import ASSISTANT_MODEL


CONVERSATION_STARTER = "Click this button to make the passage longer"

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.chat_ui = None  # Will store reference to the chat UI group
        self.prompt_handler = PromptHandler()
        self.user_edited_prompt = None 
        self.exam_paper_handler = ExamPaperHandler()
        self.question_formatter = QuestionFormatter()
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

        self.problem_list = gr.State([])

        # Problem type to index mapping
        self.problem_type_to_index = {
            "word_comprehension": 0,
            "grammatical_structure": 1,
            "textual_inference": 2,
            "paragraph_summary": 3,
            "paragraph_details": 4,
            "paragraph_structure": 5,
            "cloze": 6
        }

        # For generating question
        self.question_type_dropdown = gr.Dropdown(
            choices=list(self.problem_type_to_index.keys()),
            value="word_comprehension",
            label="Question Type",
            render=False
        )


        self.generate_question_button = gr.Button("Generate Question", render=False)
        
        # For updating question
        self.rewrite_question_dropdown = gr.Dropdown(
            choices=[],  # Initialize with empty choices
            label="Rewrite Question",
            render=False
        )

        self.update_question_dropdown = gr.Dropdown(
            choices=["easier", "harder"],
            label="Update Difficulty",
            render=False
        )

        self.rewrite_question_confirm_button = gr.Button("Update Question", render=False)
        
        self.submit_button = gr.Button("產生考題", elem_id="submit_button", render=False)

        # Add spinner component
        self.spinner = gr.HTML(
            '<div style="display:flex;justify-content:center;margin:10px;"><img src="https://cdnjs.cloudflare.com/ajax/libs/galleriffic/2.0.1/css/loader.gif" width="50"></div>',
            visible=False
        )

    def _get_problem_choices(self, problem_list_value):
        if not problem_list_value:
            return gr.update(choices=[], value=None)
        
        choices = []
        for i, (problem_type, problem_text) in enumerate(problem_list_value):
            # Create a more descriptive label, e.g., "Q1 (word_comprehension): What is..."
            question_intro_words = problem_text.split("Question:", 1)[-1].strip().split()[:5]
            question_preview = " ".join(question_intro_words) + "..." if question_intro_words else "N/A"
            choices.append((f"Q{i+1} ({problem_type}): {question_preview}", i)) 
        
        new_value = choices[0][1] if choices else None 
        return gr.update(choices=choices, value=new_value)

    def _handle_response(self, message, history, textbox_content):
        integrated_message = message

        if message == CONVERSATION_STARTER:
            integrated_message = self.prompt_handler.prepare_article_revision_prompt(
                article_content=textbox_content, 
                message=message
            )
        elif textbox_content != "":
            integrated_message = self.prompt_handler.prepare_article_format_prompt(
                article_content=textbox_content,
                message=message
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

    def prepare_prompt_template(self, problem_type, current_article):
        """Delegate prompt preparation to the QuestionPromptHandler"""
        return self.prompt_handler.prepare_question_prompt(
            problem_type=problem_type,
            current_article=current_article,
        )

    def generate_problem(self, prompt, timeout=60):
        print(f"Generate problem with prompt: {prompt[:100]}...")
        
        # Start timing
        start_time = time.time()
        
        try:
            # Use chat completion API
            response = self.client.chat.completions.create(
                model=ASSISTANT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {          # ← mandatory wrapper
                        "name": "MultipleChoiceQuestion",   # any identifier you like
                        "strict": True,                     # optional, but enables token-level validation
                        "schema": QUESTION_SCHEMA           # your schema lives here
                    },
                }
            )
            
            # Get the response content
            full_response = response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error during problem generation: {str(e)}")
            return f"Error generating problem: {str(e)}"
        
        try:
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
                if question_content:
                    return question_content
        except Exception as e:
            self.logger.error(f"Error parsing JSON: {str(e)}")
        

        return full_response

    def create_problem(self, problem_type, prompt_preview, problems, timeout=60):
        start_time = time.time()
        
        try:
            raw_problem_text = self.generate_problem(prompt_preview, timeout=timeout)
            
            problem_text = self.question_formatter.normalize_question_output(raw_problem_text)
            
            generation_time = time.time() - start_time
            print(f"Problem generated and post-processed in {generation_time:.2f} seconds")
            
            # Add the problem to the list
            problems.append((problem_type, problem_text))
            
        except Exception as e:
            self.logger.error(f"Error in create_problem: {str(e)}")
            problems.append((problem_type, f"Error generating problem: {str(e)}"))
            
        return problems

    def update_one_problem(self, problem_index, difficulty_change, current_article, problems, timeout=60):
        if problem_index is None or not problems or problem_index >= len(problems):
            self.logger.warn("Invalid problem index or empty list for update.")
            return problems

        original_problem_type, original_problem_text = problems[problem_index]
        
        self.logger.info(f"Updating problem at index {problem_index} to be {difficulty_change}. Original text: {original_problem_text[:50]}...")

        # Prepare prompt for updating the question
        # This assumes you have a method like prepare_question_update_prompt in your PromptHandler
        update_prompt = self.prompt_handler.prepare_question_update_prompt(
            original_question_text=original_problem_text,
            difficulty_change=difficulty_change,
            current_article=current_article 
        )
        
        start_time = time.time()
        try:
            raw_updated_problem_text = self.generate_problem(update_prompt, timeout=timeout)
            
            updated_problem_text = self.question_formatter.normalize_question_output(
                # problem_type=original_problem_type, # Use original type for post-processing
                question_text=raw_updated_problem_text
            )
            
            generation_time = time.time() - start_time
            self.logger.info(f"Problem at index {problem_index} updated and post-processed in {generation_time:.2f} seconds.")
            
            # Update the problem in the list
            problems.append((original_problem_type, updated_problem_text))
            
        except Exception as e:
            self.logger.error(f"Error in update_one_problem for index {problem_index}: {str(e)}")
            # Optionally, you could keep the original problem or mark it as errored
            # For now, let's keep the original if update fails catastrophically before list modification
            pass # problems list remains unchanged if error before assignment
            
        return problems

    def render(self):  
        with gr.Group(visible=False) as chat_ui:
            with gr.Row(equal_height=True):
                # Left Column
                with gr.Column():
                    self.chatbot.render()
                    self.prompt_input.render()
                    self.hidden_list.render()
                    
                    with gr.Tabs():
                        with gr.Tab("Generate Question"):
                            self.question_type_dropdown.render()
                            self.prompt_preview = gr.Textbox(
                                label="Prompt Preview",
                                lines=10,
                                elem_classes=["fullscreen-editor"],
                                value=self.update_prompt_preview(self.question_type_dropdown.value, self.textbox.value)
                            )
                            self.generate_question_button.render()
                        
                        with gr.Tab("Update Question"):
                            with gr.Row():
                                self.rewrite_question_dropdown.render()
                                self.update_question_dropdown.render()
                            self.rewrite_question_confirm_button.render()
                    
                    self.spinner.render()
                    
                # Right column
                with gr.Column():
                    self.textbox.render()
                    
                    self.problem_list.render()

                    @gr.render(inputs=[self.problem_list])
                    def render_problem_textboxes(problems):
                        """Render all problem textboxes"""
                        for i, textbox in enumerate(problems):
                            problem_type, problem_text = textbox
                            textbox = gr.Textbox(
                                label=problem_type,
                                value=problem_text,
                                lines=4,
                                interactive=True,
                                elem_classes=["fullscreen-editor"]
                            )

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
                
        # Add load event to update prompt_preview when interface loads
        self.textbox.change(
            fn=self.update_prompt_preview,
            inputs=[self.question_type_dropdown, self.textbox],
            outputs=[self.prompt_preview]
        )
        
        # Event handler for generating question
        self.question_type_dropdown.change(
            fn=self.update_prompt_preview,
            inputs=[self.question_type_dropdown, self.textbox],
            outputs=[self.prompt_preview]
        )

        self.generate_question_button.click(
            fn=lambda: gr.update(visible=True),  # Show spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=lambda problem_type, prompt_preview, problems: 
                self.create_problem(problem_type, prompt_preview, problems, timeout=30),
            inputs=[self.question_type_dropdown, self.prompt_preview, self.problem_list],
            outputs=[self.problem_list],
        ).then(
            fn=self._get_problem_choices,
            inputs=[self.problem_list],
            outputs=[self.rewrite_question_dropdown]
        ).then(
            fn=lambda: gr.update(visible=False),  # Hide spinner
            outputs=self.spinner,
            show_progress=False,
        )

        # Event handler for updating question
        self.rewrite_question_dropdown.change(
            fn=None, # No preview update for now, or a dedicated one
            inputs=None,
            outputs=None 
        )

        self.update_question_dropdown.change(
            fn=None, # No preview update for now, or a dedicated one
            inputs=None,
            outputs=None
        )

        self.rewrite_question_confirm_button.click(
            fn=lambda: gr.update(visible=True),  # Show spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=self.update_one_problem,
            inputs=[self.rewrite_question_dropdown, self.update_question_dropdown, self.textbox, self.problem_list],
            outputs=self.problem_list,
        ).then(
            fn=self._get_problem_choices, # Update choices after modifying problem list
            inputs=[self.problem_list],
            outputs=[self.rewrite_question_dropdown]
        ).then(
            fn=lambda: gr.update(visible=False),  # Hide spinner
            outputs=self.spinner,
            show_progress=False,
        )
        
        self.prompt_preview.change(
            fn=self.handle_prompt_edit,
            inputs=[self.prompt_preview],
            outputs=[]
        )


        self.submit_button.click(
            fn=lambda article, problems: self.exam_paper_handler.generate_final_exam_doc(article, problems)[0],
            inputs=[self.textbox, self.problem_list],
            outputs=download_button
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=download_button
        )

        return chat_ui  # Return the group for access in the main app

    def update_prompt_preview(self, question_type, current_article):
        """
        Updates the prompt preview based on question type.
        If the user has edited the prompt, we preserve their edits.
        """

        if self.user_edited_prompt is not None and not hasattr(self, '_last_question_type'):
            # First time initialization
            self._last_question_type = question_type
            
        if hasattr(self, '_last_question_type') and question_type != self._last_question_type:
            # Question type changed, reset edited prompt
            self.user_edited_prompt = None
            self._last_question_type = question_type
        
        if self.user_edited_prompt is not None:
            return self.user_edited_prompt
            
        # if question_type == "cloze":
        #     marked_article = current_article
        #     return self.prepare_prompt_template(question_type, marked_article)
     
        return self.prepare_prompt_template(question_type, current_article)

    def handle_prompt_edit(self, prompt_preview):
        self.user_edited_prompt = prompt_preview
        
    def reset_prompt_edit(self, question_type):
        """Reset user edited prompt when question type changes"""
        self.user_edited_prompt = None
        return self.update_prompt_preview(question_type, self.textbox.value)

