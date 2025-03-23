import gradio as gr

from utils import call_llm_to_generate_article
from client import llm_client

# TODO: refactor this function to be a class
# Function to generate content based on dropdown selections
def generate_article_with_chat_interface(
        grade_values, vocabulary_range_values, topic_range_values, grammar_range_values
    ):
   
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
        llm_client=llm_client,
        grade_values=grade_values,
        topic_range_values=topic_range_values,
        grammar_range_values=grammar_range_values,
        vocabulary_range_values=vocabulary_range_values       
    )

    # Combine parameters summary with the generated article
    params_summary = _compose_params_summary(
        grade_values, vocabulary_range_values, topic_range_values, grammar_range_values
    )
    content = params_summary + "\n## 生成的文章\n\n" + generated_article + "\n\n請編輯上述文章或使用聊天功能獲取更多幫助。"
    # Enable the chat interface
    return content, gr.update(visible=True), gr.update(visible=False)