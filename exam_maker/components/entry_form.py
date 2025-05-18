import gradio as gr
from exam_maker import option
import pandas as pd
from exam_maker.utils.utils import call_llm_to_generate_article
from exam_maker.logger import app_logger

class EntryForm:
    def __init__(self, llm_client, assistant_id):
        self.llm_client = llm_client
        self.assistant_id = assistant_id
        # Use options directly from the option module
        self.publisher_options = option.PUBLISHER_OPTIONS
        self.grade_options = option.GRADE_OPTIONS
        self.unit_options = option.UNIT_OPTIONS
        self.grammar_options = option.GRAMMAR_OPTIONS
        self.topic_options = option.TOPIC_OPTIONS
        self._define_components()

    def _define_components(self):

        # filter to get the vocabulary list
        self.publisher = gr.CheckboxGroup(
            choices=self.publisher_options,
            label="出版社",
        )
        
        self.grade = gr.CheckboxGroup(
            choices=self.grade_options,
            label="學生年級",
        )
        
        self.unit = gr.CheckboxGroup(
            choices=self.unit_options,
            label="課程範圍",
        )

        # show the vocabulary list
        self.textbook_vocab_list = gr.Textbox(
            label="課本單字列表",
            lines=4,
            max_lines=4,
            interactive=False,
            placeholder="Select units to see vocabulary"
        )

        # custom vocabulary list
        self.additional_vocab_list = gr.Textbox(
            label="額外單字列表 (請使用者自行輸入)",
            lines=4,
            max_lines=4,
            placeholder="Enter additional vocabulary words, separated by commas"
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

    def update_textbook_vocab_list(self, grade_values, unit_values, publisher_values):
        try:
            # Read the vocabulary file
            vocab_df = pd.read_csv("data/vocab/cz_english_vocabulary_sheet.csv")
            
            # If no selections made, return empty message
            if not unit_values:
                return ""
            
            UNIT_MAPPING = {
                "第一課": "lesson 1", 
                "第二課": "lesson 2", 
                "第三課": "lesson 3", 
                "第四課": "lesson 4", 
                "第五課": "lesson 5", 
                "第六課": "lesson 6"
            }
            unit_values = [
                UNIT_MAPPING.get(unit) for unit in unit_values
            ]

            app_logger.info(f"Get the vocabulary list for {publisher_values} {grade_values} {unit_values}")

            # Filter based on unit
            filtered_df = vocab_df[
                (vocab_df['publisher'].isin(publisher_values)) &
                (vocab_df['grade'].isin(grade_values)) &
                (vocab_df['unit'].isin(unit_values))
            ]

            app_logger.info(f"Data cnt: {filtered_df.shape[0]}")
            
            # get just the words and join them with commas
            words = filtered_df['word'].tolist()

            # remove the () explanation from vocabulary sheet: ex: mouse（複數為mice）
            words = [word.split('（')[0] for word in words]

            return ', '.join(words)
            
        except Exception as e:
            app_logger.error(f"Error loading vocabulary: {e}")
            return "Error loading vocabulary list"

    def generate_initial_content(self, grade_values, unit_values, topic_values, grammar_values, input_article_value, textbook_vocab_values, additional_vocab_values):
        # Combine textbook vocabulary with additional vocabulary
        generated_article = call_llm_to_generate_article(
            grade_values=grade_values,
            topic_values=topic_values,
            grammar_values=grammar_values,
            unit_values=unit_values,
            input_article_value=input_article_value,
            textbook_vocab_values=textbook_vocab_values,
            additional_vocab_values=additional_vocab_values
        )

        # Enable the chat interface
        return generated_article, gr.update(visible=True), gr.update(visible=False)

    def render(self):
        with gr.Group() as selection_ui:
            gr.Markdown("## 請選擇文章生成參數")
            
            # Render components
            self.publisher.render()
            self.grade.render()
            self.unit.render()
            self.textbook_vocab_list.render()
            self.additional_vocab_list.render()  # Add the new component
            self.grammar.render()
            self.topic.render()
            self.input_article.render()
            self.generate_button.render()
            self.spinner.render()

            # Bind the events
            self.unit.change(
                fn=self.update_textbook_vocab_list,
                inputs=[self.grade, self.unit, self.publisher],
                outputs=[self.textbook_vocab_list]
            )
        return selection_ui
