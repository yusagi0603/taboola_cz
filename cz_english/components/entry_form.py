import gradio as gr
import option  # Import options directly in the EntryForm module

from utils import call_llm_to_generate_article

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
        self.grade = gr.Dropdown(
            choices=self.grade_options,
            label="學生年級",
            multiselect=True
        )
        
        self.vocabulary_range = gr.Dropdown(
            choices=self.vocabulary_options,
            label="單字範圍",
            multiselect=True
        )

        self.grammar_range = gr.Dropdown(
            choices=self.grammar_options,
            label="文法範圍",
            multiselect=True
        )
        
        self.topic_range = gr.Dropdown(
            choices=self.topic_options,
            label="主題範圍",
            multiselect=True
        )
        
        self.generate_button = gr.Button("生成初始文章")

        # Add the loading spinner component
        self.spinner = gr.HTML(
            '<div style="display:flex;justify-content:center;margin:10px;"><img src="https://cdnjs.cloudflare.com/ajax/libs/galleriffic/2.0.1/css/loader.gif" width="50"></div>',
            visible=False
        )

    def generate_initial_content(self, grade_values, vocabulary_range_values, topic_range_values, grammar_range_values):
        # Create a summary of selected options
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
            llm_client=self.llm_client,
            grade_values=grade_values,
            topic_range_values=topic_range_values,
            grammar_range_values=grammar_range_values,
            vocabulary_range_values=vocabulary_range_values
        )

        # Combine parameters summary with the generated article
        # params_summary = _compose_params_summary(
        #     grade_values, vocabulary_range_values, topic_range_values, grammar_range_values
        # )
        # content = params_summary + "\n## 生成的文章\n\n" + generated_article + "\n\n請編輯上述文章或使用聊天功能獲取更多幫助。"

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
            self.generate_button.render()
            self.spinner.render()

        return selection_ui
