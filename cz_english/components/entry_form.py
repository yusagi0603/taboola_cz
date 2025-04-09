import gradio as gr
# from config import ASSISTANT_INSTRUCTION, RESPONSE_FORMAT
import cz_english.option as option  # Import options directly in the EntryForm module

# from utils import call_llm_to_generate_article
from cz_english.utils import call_llm_to_generate_article

class EntryForm:
    def __init__(self, llm_client, assistant_id):
        self.llm_client = llm_client
        self.assistant_id = assistant_id
        # Use options directly from the option module
        self.grade_options = option.GRADE_OPTIONS
        self.vocabulary_options = option.VOCABULARY_OPTIONS
        self.grammar_options = option.GRAMMAR_OPTIONS
        self.topic_options = option.TOPIC_OPTIONS
        self._define_components()

    def _define_components(self):
        # Initialize components
        self.grade = gr.CheckboxGroup(
            choices=self.grade_options,
            label="學生年級",
        )
        
        self.vocabulary_range = gr.CheckboxGroup(
            choices=self.vocabulary_options,
            label="單字範圍",
        )

        self.grammar_range = gr.CheckboxGroup(
            choices=self.grammar_options,
            label="文法範圍",
        )
        
        self.topic_range = gr.CheckboxGroup(
            choices=self.topic_options,
            label="主題範圍",
        )

        self.input_article = gr.Textbox(
            label="初始文章",
            lines=5,
            render=True
        )
        
        self.generate_button = gr.Button("生成初始文章")

        # Add the loading spinner component
        self.spinner = gr.HTML(
            '<div style="display:flex;justify-content:center;margin:10px;"><img src="https://cdnjs.cloudflare.com/ajax/libs/galleriffic/2.0.1/css/loader.gif" width="50"></div>',
            visible=False
        )

    def generate_initial_content(self, grade_values, vocabulary_range_values, topic_range_values, grammar_range_values, input_article_value):

        generated_article = call_llm_to_generate_article(
            grade_values=grade_values,
            topic_range_values=topic_range_values,
            grammar_range_values=grammar_range_values,
            vocabulary_range_values=vocabulary_range_values,
            input_article_value=input_article_value
        )

        # Enable the chat interface
        return generated_article, gr.update(visible=True), gr.update(visible=False)

    def render(self):
        with gr.Group() as selection_ui:
            gr.Markdown("## 請選擇文章生成參數")
            
            # Render components
            self.grade.render()
            self.vocabulary_range.render()
            self.grammar_range.render()
            self.topic_range.render()
            self.input_article.render()
            self.generate_button.render()
            self.spinner.render()

        return selection_ui
