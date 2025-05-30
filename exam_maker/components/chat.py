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
from exam_maker.handlers.llm_handler import LLMHandler
from exam_maker.config import ASSISTANT_MODEL
from exam_maker.utils.token_tracker import token_tracker


CONVERSATION_STARTER = "Click this button to make the passage longer"

class Chat:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.chat_ui = None  # Will store reference to the chat UI group
        self.prompt_handler = PromptHandler()
        self.exam_paper_handler = ExamPaperHandler()
        self.question_formatter = QuestionFormatter()
        self.llm_handler = LLMHandler(client)
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

        # Token usage components
        self.token_summary = gr.Textbox(
            label="Session Token Usage Summary",
            value="No LLM calls made yet",
            interactive=False,
            lines=3,
            render=False
        )
        
        self.export_usage_button = gr.Button("Export Usage Data", render=False)
        self.usage_download = gr.DownloadButton("Download Usage Report", visible=False, render=False)

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
        start_time = time.time()
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

        # Estimate token usage for assistant streaming (since usage data isn't directly available)
        duration = time.time() - start_time
        estimated_prompt_tokens = len(integrated_message.split()) * 1.3  # Rough estimation
        estimated_completion_tokens = len(full_response.split()) * 1.3
        
        usage_data = {
            'prompt_tokens': int(estimated_prompt_tokens),
            'completion_tokens': int(estimated_completion_tokens),
            'total_tokens': int(estimated_prompt_tokens + estimated_completion_tokens)
        }
        
        context = {
            'message_type': 'assistant_streaming',
            'original_message': message,
            'integrated_message_length': len(integrated_message),
            'response_length': len(full_response)
        }
        
        # Track the estimated usage
        token_tracker.track_usage(
            function_name="assistant_streaming",
            model="assistant_api",  # Different model identifier for assistant API
            usage_data=usage_data,
            duration=duration,
            context=context
        )

        yield suggestion, current_lesson_plan, next_step_prompt

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
            
            duration = time.time() - start_time
            
            # Track token usage
            usage_data = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            context = {
                'prompt_length': len(prompt),
                'response_format': 'json_schema'
            }
            
            usage = token_tracker.track_usage(
                function_name="generate_problem",
                model=ASSISTANT_MODEL,
                usage_data=usage_data,
                duration=duration,
                context=context
            )
            
            # Get the response content
            return response.choices[0].message.content, usage
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error during problem generation: {str(e)} (duration: {duration:.2f}s)")
            return f"Error generating problem: {str(e)}", None

    def create_problem(self, problem_type, prompt_preview, problems, timeout=60):
        start_time = time.time()
        
        try:
            raw_problem_text = self.llm_handler.generate_response(prompt_preview, timeout=timeout, schema=QUESTION_SCHEMA)
            raw_problem_text, usage = self.generate_problem(prompt_preview, timeout=timeout)
            
            problem_text = self.question_formatter.normalize_question_output(raw_problem_text)
            
            generation_time = time.time() - start_time
            print(f"Problem generated and post-processed in {generation_time:.2f} seconds")
            
            # Add the problem to the list
            problems.append((problem_type, problem_text))
            
            # Return problems and usage info for chat display
            usage_message = token_tracker.format_usage_message(usage) if usage else ""
            return problems, usage_message
            
        except Exception as e:
            self.logger.error(f"Error in create_problem: {str(e)}")
            problems.append((problem_type, f"Error generating problem: {str(e)}"))
            
        return problems

    def rewrite_problem(self, problem_index, difficulty_change, current_article, problems, timeout=60):
        if problem_index is None or not problems or problem_index >= len(problems):
            self.logger.warn("Invalid problem index or empty list for update.")
            return problems, "❌ Invalid problem selection"

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
            raw_updated_problem_text, usage = self.generate_problem(update_prompt, timeout=timeout)
            raw_updated_problem_text = self.llm_handler.generate_response(update_prompt, timeout=timeout, schema=QUESTION_SCHEMA)
            
            updated_problem_text = self.question_formatter.normalize_question_output(
                # problem_type=original_problem_type, # Use original type for post-processing
                question_text=raw_updated_problem_text
            )
            
            generation_time = time.time() - start_time
            self.logger.info(f"Problem at index {problem_index} updated and post-processed in {generation_time:.2f} seconds.")
            
            # Update the problem in the list
            problems.append((original_problem_type, updated_problem_text))
            
            # Return problems and usage info for chat display
            usage_message = token_tracker.format_usage_message(usage) if usage else ""
            return problems, usage_message
            
        except Exception as e:
            self.logger.error(f"Error in rewrite_problem for index {problem_index}: {str(e)}")
            # Optionally, you could keep the original problem or mark it as errored
            # For now, let's keep the original if update fails catastrophically before list modification
            return problems, f"❌ Error updating question: {str(e)}"

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
                
            # Token usage section
            with gr.Row():
                with gr.Column():
                    self.token_summary.render()
                    with gr.Row():
                        self.export_usage_button.render()
                        self.usage_download.render()
        
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
            fn=lambda problem_type, history: history + [{"role": "user", "content": f"Help me generate a {problem_type} question."}],
            inputs=[self.question_type_dropdown, self.chatbot],
            outputs=[self.chatbot]
        ).then(
            fn=lambda problem_type, prompt_preview, problems: self.create_problem(problem_type, prompt_preview, problems, timeout=30)[0],  # Just return problems, ignore usage message
            inputs=[self.question_type_dropdown, self.prompt_preview, self.problem_list],
            outputs=[self.problem_list],
        ).then(
            fn=lambda problem_type, history: history + [{"role": "assistant", "content": f"✅ Finished generating {problem_type} question. Check the right panel for the new question."}],
            inputs=[self.question_type_dropdown, self.chatbot],
            outputs=[self.chatbot]
        ).then(
            fn=lambda: gr.update(visible=False),  # Hide spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=self.update_token_summary,  # Update token summary
            outputs=self.token_summary
        )

        self.problem_list.change(
            fn=self._get_problem_choices,
            inputs=[self.problem_list],
            outputs=[self.rewrite_question_dropdown]
        )


        # Event handler for updating question
        self.rewrite_question_dropdown.change(
            fn=None, # No preview update for now, or a dedicated one
            inputs=None,
            outputs=None 
            # fn=self.update_prompt_preview, 
            # inputs=[self.question_type_dropdown, self.difficulty_dropdown, self.textbox],
            # outputs=[self.prompt_preview]
        )

        self.update_question_dropdown.change(
            fn=None, # No preview update for now, or a dedicated one
            inputs=None,
            outputs=None
            # fn=self.update_prompt_preview,
            # inputs=[self.question_type_dropdown, self.difficulty_dropdown, self.textbox],
            # outputs=[self.prompt_preview]
        )

        self.rewrite_question_confirm_button.click(
            fn=lambda: gr.update(visible=True),  # Show spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=lambda idx, diff, history: history + [{"role": "user", "content": f"Help me update question {idx} to be {diff}."}],
            inputs=[self.rewrite_question_dropdown, self.update_question_dropdown, self.chatbot],
            outputs=[self.chatbot]
        ).then(
            fn=lambda idx, diff, article, problems: self.update_one_problem(idx, diff, article, problems, timeout=30)[0],  # Just return problems, ignore usage message
            inputs=[self.rewrite_question_dropdown, self.update_question_dropdown, self.textbox, self.problem_list],
            outputs=[self.problem_list],
        ).then(
            fn=lambda idx, diff, history: history + [{"role": "assistant", "content": f"✅ Finished updating question {idx} to be {diff}. Check the right panel for the updated question."}],
            inputs=[self.rewrite_question_dropdown, self.update_question_dropdown, self.chatbot],
            outputs=[self.chatbot]
        ).then(
            fn=self._get_problem_choices,  # Update choices after modifying problem list
            inputs=[self.problem_list],
            outputs=[self.rewrite_question_dropdown]
        ).then(
            fn=lambda: gr.update(visible=False),  # Hide spinner
            outputs=self.spinner,
            show_progress=False,
        ).then(
            fn=self.update_token_summary,  # Update token summary
            outputs=self.token_summary
        )

        self.submit_button.click(
            fn=lambda article, problems: self.exam_paper_handler.generate_final_exam_doc(article, problems)[0],
            inputs=[self.textbox, self.problem_list],
            outputs=download_button
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=download_button
        )

        # Export usage data event handler
        self.export_usage_button.click(
            fn=lambda: token_tracker.export_usage_data(),
            outputs=self.usage_download
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=self.usage_download
        )

        # Update token summary when chatbot changes (after assistant responses)
        self.chatbot.change(
            fn=self.update_token_summary,
            outputs=self.token_summary
        )

        return chat_ui  # Return the group for access in the main app

    def update_prompt_preview(self, question_type, current_article):
        """
        Updates the prompt preview based on question type.
        """
        return self.prepare_prompt_template(question_type, current_article)

    def handle_prompt_edit(self, prompt_preview):
        self.user_edited_prompt = prompt_preview
        
    def reset_prompt_edit(self, question_type):
        """Reset user edited prompt when question type changes"""
        self.user_edited_prompt = None
        return self.update_prompt_preview(question_type, self.textbox.value)

    def update_token_summary(self):
        """Update the token usage summary display"""
        summary = token_tracker.get_session_summary()
        if summary['total_calls'] == 0:
            return "No LLM calls made yet"
        
        summary_text = (
            f"Total Calls: {summary['total_calls']}\n"
            f"Total Tokens: {summary['total_tokens']:,}\n"
            f"Total Cost: ${summary['total_cost']:.4f}\n"
            f"Avg Tokens/Call: {summary['average_tokens_per_call']:.1f}\n"
            f"Functions Used: {', '.join(summary['functions_used'])}"
        )
        return summary_text

    def export_usage_data(self):
        """Export token usage data and return file path"""
        try:
            filepath = token_tracker.export_usage_data()
            return gr.update(visible=True), filepath
        except Exception as e:
            self.logger.error(f"Error exporting usage data: {str(e)}")
            return gr.update(visible=False), None
