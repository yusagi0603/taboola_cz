import re
import json
import time
import gradio as gr
from datetime import datetime
from json_repair import repair_json

from logger import app_logger
from utils import generate_docx_file
from handlers.prompt_handler import PromptHandler


CONVERSATION_STARTER = "Click this button to make the passage longer"

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.chat_ui = None  # Will store reference to the chat UI group
        self.prompt_handler = PromptHandler()
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
            "chapter_summary": 3,
            "chapter_details": 4,
            "chapter_structure": 5
        }

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

        # Add spinner component
        self.spinner = gr.HTML(
            '<div style="display:flex;justify-content:center;margin:10px;"><img src="https://cdnjs.cloudflare.com/ajax/libs/galleriffic/2.0.1/css/loader.gif" width="50"></div>',
            visible=False
        )

    def _generate_final_exam_doc(
            self, 
            article_content,
            problem_list
        ):
        """Compose the final exam from the three problem textboxes."""
        
        # Compose the full exam content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc_file_name = f"英文考題 - {timestamp}"
        
        # Return the exam content as a downloadable document
        question_info_tuple = [("文章", article_content)]
        for problem_type, problem_content in problem_list:
            question_info_tuple.append((problem_type, problem_content))
        doc_file_name = generate_docx_file(
            doc_file_name,
            question_info_tuple
        )
        
        return doc_file_name, gr.update(visible=True) 

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

    def prepare_prompt_template(self, problem_type, difficulty, current_article):
        """Delegate prompt preparation to the QuestionPromptHandler"""
        return self.prompt_handler.prepare_question_prompt(
            problem_type=problem_type,
            current_article=current_article,
            difficulty=difficulty
        )

    def generate_problem(self, prompt, timeout=60):
        print(f"Generate problem with prompt: {prompt[:100]}...")
        
        # Start timing
        start_time = time.time()

        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
        )
        
        full_response = "" 
        
        try:
            with self.client.beta.threads.runs.stream(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            ) as stream:
                for text_delta in stream.text_deltas:
                    # Check if it exceeded the timeout
                    if time.time() - start_time > timeout:
                        print(f"Generation timed out after {timeout} seconds")
                        break
                        
                    full_response += text_delta
        except Exception as e:
            self.logger.error(f"Error during problem generation: {str(e)}")
            return f"Error generating problem: {str(e)}"
        
        # Try to extract question content from JSON if present
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
        
        # If we couldn't extract JSON or no question_content was found,
        # return the full raw response for post-processing
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

    def post_process_question(self, problem_type, question_text):
        if not question_text:
            return f"Error: Empty response for {problem_type} question."

        text = question_text.strip()
        if text.startswith('{') and text.endswith('}'):
            try:
                json_data = json.loads(text)
                if 'current_lesson_plan' in json_data:
                    text = json_data['current_lesson_plan']
            except Exception:
                pass

        text = re.sub(r'```[a-zA-Z]*\n', '', text)
        text = re.sub(r'```', '', text)

        text = text.replace('\r\n', '\n')
        option_patterns = [
            (r'Option\s*([A-D])[:\.\s]*', r'\1) '),    # Option A: -> A)
            (r'([A-D])\.\s*', r'\1) '),                # A. -> A)
            (r'\(([A-D])\)', r'\1)'),                  # (A) -> A)
            (r'([A-D]):', r'\1)'),                     # A: -> A)
            (r'([A-D])\)\s*\)', r'\1)'),               # A)) -> A)
            (r'([A-D])\)\s*([^\s])', r'\1) \2'),        # Ensure space after A)
        ]
        for pattern, repl in option_patterns:
            text = re.sub(pattern, repl, text)

        if not text.startswith("Question:") and "Question:" not in text:
            match = re.search(r'^\s*(\d+\.\s*|Q\d+\.\s*|Question\s*\d+:)', text, re.IGNORECASE)
            if match:
                text = "Question: " + text[match.end():].strip()
            else:
                text = "Question: " + text

        if "Options:" not in text and any(opt in text for opt in ["A)", "B)", "C)", "D)"]):
            first_option = re.search(r'(A\))', text)
            if first_option:
                idx = first_option.start()
                text = text[:idx] + "Options:\n" + text[idx:]

        if "Answer:" not in text:
            text += "\n\nNote: Missing 'Answer:' field."
        else:
            answer_match = re.search(r'Answer:\s*([A-D])\s*[^)]?', text)
            if answer_match:
                answer_letter = answer_match.group(1)
                text = re.sub(r'Answer:\s*([A-D])\s*[^)]?', f'Answer: {answer_letter})', text)

        text = re.sub(r'\n{3,}', '\n\n', text)

        required_elements = ["Question:", "Options:", "A)", "B)", "C)", "D)", "Answer:"]
        missing_elements = [elem for elem in required_elements if elem not in text]
        if missing_elements:
            text += "\n\nNote: The following elements are missing: " + ", ".join(missing_elements)

        return text

    def create_problem(self, problem_type, difficulty, prompt_preview, current_article, problems, timeout=60):

        start_time = time.time()
        
        try:
            raw_problem_text = self.generate_problem(prompt_preview, timeout=timeout)
            
            problem_text = self.post_process_question(
                problem_type=problem_type,
                question_text=raw_problem_text
            )
            
            generation_time = time.time() - start_time
            print(f"Problem generated and post-processed in {generation_time:.2f} seconds")
            
            # Add the problem to the list
            problems.append((problem_type, problem_text))
            
        except Exception as e:
            self.logger.error(f"Error in create_problem: {str(e)}")
            problems.append((problem_type, f"Error generating problem: {str(e)}"))
            
        return problems

    def reprocess_problems(self, problems):
        if not problems:
            return problems
            
        reprocessed_problems = []
        for problem_type, problem_text in problems:
            processed_text = self.post_process_question(
                problem_type=problem_type,
                question_text=problem_text
            )
            reprocessed_problems.append((problem_type, processed_text))
            
        return reprocessed_problems

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

                        self.question_type_dropdown = gr.Dropdown(
                            choices=["word_comprehension", "grammatical_structure", "textual_inference", "chapter_summary", "chapter_details", "chapter_structure"],
                            value= "word_comprehension",
                            label="Question Type"
                        )
                        self.difficulty_dropdown.render()
                                        
                    self.prompt_preview = gr.Textbox(
                        label="Prompt Preview",
                        lines=10,
                        elem_classes=["fullscreen-editor"],
                        value=self.prepare_prompt_template(self.question_type_dropdown.value, self.difficulty_dropdown.value, self.textbox.value)
                    )
                    
                    self.generate_question_button.render()
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
                

        self.generate_question_button.click(
            fn=lambda: gr.update(visible=True),  # Show spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=lambda problem_type, difficulty, prompt_preview, current_article, problems: 
                self.create_problem(problem_type, difficulty, prompt_preview, current_article, problems, timeout=30),
            inputs=[self.question_type_dropdown, self.difficulty_dropdown, self.prompt_preview, self.textbox, self.problem_list],
            outputs=self.problem_list,
        ).then(
            fn=lambda: gr.update(visible=False),  # Hide spinner
            outputs=self.spinner,
            show_progress=False,
        )

        # Add event handlers for prompt preview updates
        self.question_type_dropdown.change(
            fn=self.update_prompt_preview,
            inputs=[self.question_type_dropdown, self.difficulty_dropdown, self.textbox],
            outputs=[self.prompt_preview]
        )

        self.difficulty_dropdown.change(
            fn=self.update_prompt_preview,
            inputs=[self.question_type_dropdown, self.difficulty_dropdown, self.textbox],
            outputs=[self.prompt_preview]
        )

        self.submit_button.click(
            fn=self._generate_final_exam_doc,
            inputs=[self.textbox, self.problem_list],
            outputs=[download_button, download_button]
        )

        return chat_ui  # Return the group for access in the main app 

    def update_prompt_preview(self, question_type, difficulty, current_article):
        return self.prepare_prompt_template(question_type, difficulty, current_article)
