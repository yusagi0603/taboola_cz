import gradio as gr
import option  # Import options directly in the EntryForm module

# from utils import call_llm_to_generate_article
from utils import call_llm_to_generate_article

class EntryForm:
    def __init__(self, llm_client, assistant_id):
        self.llm_client = llm_client
        self.assistant_id = assistant_id
        # Use options directly from the option module
        self.grade_options = option.GRADE_OPTIONS
        self.unit_options = option.UNIT_OPTIONS
        self.grammar_options = option.GRAMMAR_OPTIONS
        self.topic_options = option.TOPIC_OPTIONS
        self._define_components()

    def _define_components(self):
        # Initialize components
        self.grade = gr.CheckboxGroup(
            choices=self.grade_options,
            label="學生年級",
        )
        
        self.unit = gr.CheckboxGroup(
            choices=self.unit_options,
            label="課程範圍",
        )

        self.grammar = gr.CheckboxGroup(
            choices=self.grammar_options,
            label="文法範圍",
        )
        
        self.topic = gr.CheckboxGroup(
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

    def generate_initial_content(self, grade_values, unit_values, topic_values, grammar_values, input_article_value):
        generated_article = call_llm_to_generate_article(
            grade_values=grade_values,
            topic_values=topic_values,
            grammar_values=grammar_values,
            unit_values=unit_values,
            input_article_value=input_article_value
        )

        # Enable the chat interface
        return generated_article, gr.update(visible=True), gr.update(visible=False)

    def render(self):
        with gr.Group() as selection_ui:
            gr.Markdown("## 請選擇文章生成參數")
            
            # Render components
            self.grade.render()
            self.unit.render()
            self.grammar.render()
            self.topic.render()
            self.input_article.render()
            self.generate_button.render()
            self.spinner.render()

        return selection_ui
