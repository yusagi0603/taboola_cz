import gradio as gr
from config import ASSISTANT_INSTRUCTION, RESPONSE_FORMAT
import option  # Import options directly in the EntryForm module

class EntryForm:
    def __init__(self, client, assistant_id):
        self.client = client
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

    def generate_initial_content(self, grade_values, vocabulary_range_values, topic_range_values, grammar_range_values):
        # Create a summary of selected options
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
        
        # Update the assistant with the customized instruction
        self.client.beta.assistants.update(
            assistant_id=self.assistant_id,
            instructions= ASSISTANT_INSTRUCTION.format(
                grade_values=grade_values,
                topic_values=topic_range_values,
                grammar_values=grammar_range_values,
                vocabulary_values=vocabulary_range_values
            ),
            response_format=RESPONSE_FORMAT
        )
        
        # Generate article using OpenAI API based on selected parameters
        user_prompt = f"""
        Generate an English article suitable for {', '.join(grade_values) if grade_values else 'middle school'} Taiwanese students.
        
        Vocabulary range: {', '.join(vocabulary_range_values) if vocabulary_range_values else 'general'}
        Topics: {', '.join(topic_range_values) if topic_range_values else 'general interest'}
        Grammar: {', '.join(grammar_range_values) if grammar_range_values else 'general'}

        The article should be appropriate for the student level, using vocabulary from the specified range, 
        and covering topics from the selected categories. 
        
        Generate a well-structured article with 3-5 paragraphs, with a clear introduction, body, and conclusion.
        Include a title for the article.
        
        Reply with just the article text, without any explanations or notes.
        """
        
        # Create progress bar
        progress = gr.Progress()
        
        # Make API call with progress updates
        progress(0, "Generating article...")
        progress(0.3, "Sending request to GPT...")
        response = self.client.chat.completions.create(
            model="gpt-4o",  # Using the same model as the assistant
            messages=[
                {"role": "system", "content": "You are an educational content creator specializing in creating English reading materials for students."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
        )
        
        progress(0.6, "Processing response...")
        # Extract the generated article
        generated_article = response.choices[0].message.content
        
        progress(0.9, "Formatting output...")
        # Combine parameters summary with the generated article
        content = params_summary + "\n## 生成的文章\n\n" + generated_article + "\n\n請編輯上述文章或使用聊天功能獲取更多幫助。"
        
        progress(1.0, "Done!")
        # Enable the chat interface
        return content, gr.update(visible=True), gr.update(visible=False)

    def render(self):
        with gr.Group() as selection_ui:
            gr.Markdown("## 請選擇文章生成參數")
            
            # Render components
            self.grade.render()
            self.vocabulary_range.render()
            self.grammar_range.render()
            self.topic_range.render()
            self.generate_button.render()
            
        return selection_ui
