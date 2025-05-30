import gradio as gr
import time

from exam_maker.config import (
    ASSISTANT_MODEL,
    CORRECT_PASSWORD,
)
from exam_maker.logger import app_logger
from exam_maker.client import llm_client
from exam_maker.handlers.prompt_handler import PromptHandler
from exam_maker.utils.token_tracker import token_tracker

prompt_handler = PromptHandler()


def check_password(input_password):
    if input_password == CORRECT_PASSWORD:
        return gr.update(visible=False), gr.update(visible=True), ""
    else:
        return gr.update(visible=True), gr.update(visible=False), gr.update(value="Wrong Password. Please Retry. hint: channel name", visible=True)


def _call_llm_with_prompt(system_prompt, user_prompt, response_format=None, function_name="unknown"):
    """Enhanced LLM call with token tracking"""
    start_time = time.time()
    
    msg_lst = []
    for role, prompt in zip(["system", "user"], [system_prompt, user_prompt]):
        if prompt is not None:
            msg_lst.append({"role": role, "content": prompt})

    try:
        response = llm_client.chat.completions.create(
            model=ASSISTANT_MODEL,
            messages=msg_lst,
            response_format=response_format
        )
        
        duration = time.time() - start_time
        generated_content = response.choices[0].message.content
        
        # Track token usage
        usage_data = {
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        }
        
        context = {
            'system_prompt_length': len(system_prompt) if system_prompt else 0,
            'user_prompt_length': len(user_prompt) if user_prompt else 0,
            'response_format': str(response_format) if response_format else None
        }
        
        usage = token_tracker.track_usage(
            function_name=function_name,
            model=ASSISTANT_MODEL,
            usage_data=usage_data,
            duration=duration,
            context=context
        )
        
        return generated_content, usage
        
    except Exception as e:
        duration = time.time() - start_time
        app_logger.error(f"Error in {function_name}: {str(e)} (duration: {duration:.2f}s)")
        raise


def call_llm_to_generate_article(
        grade_values, unit_values, topic_values, grammar_values, input_article_value, textbook_vocab_values, additional_vocab_values=None
    ):

    context = {
        "grade_values": grade_values,
        "topic_values": topic_values,
        "grammar_values": grammar_values,
        "unit_values": unit_values,
        "textbook_vocab_values": textbook_vocab_values,
        "additional_vocab_values": additional_vocab_values if additional_vocab_values else ""
    }

    if input_article_value:
        context["input_article_value"] = input_article_value
        user_prompt = prompt_handler.render_template("article_rewrite", context)
        app_logger.info("Rewriting article with prompt: \n" + user_prompt)
        function_name = "article_rewrite"
    else:
        user_prompt = prompt_handler.render_template("article_generation", context)
        app_logger.info("Generating article with prompt: \n" + user_prompt)
        function_name = "article_generation"

    generated_article, usage = _call_llm_with_prompt(
        system_prompt=None, 
        user_prompt=user_prompt,
        response_format=None,
        function_name=function_name
    )
    
    # Return both content and usage info
    return generated_article, usage


def call_llm_to_generate_question(question_type):

    system_prompt = "You are a question generator for English exam in Taiwan."
    user_prompt = f"Please generate a question based on the question type: {question_type}"

    generated_question, usage = _call_llm_with_prompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format={"type": "json_object"},
        function_name=f"question_generation_{question_type}"
    )
    
    return generated_question, usage

