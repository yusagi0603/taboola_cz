import gradio as gr

from exam_maker.config import (
    ASSISTANT_MODEL,
    CORRECT_PASSWORD,
)
from exam_maker.logger import app_logger
from exam_maker.client import llm_client
from exam_maker.handlers.prompt_handler import PromptHandler

prompt_handler = PromptHandler()


def check_password(input_password):
    if input_password == CORRECT_PASSWORD:
        return gr.update(visible=False), gr.update(visible=True), ""
    else:
        return gr.update(visible=True), gr.update(visible=False), gr.update(value="Wrong Password. Please Retry. hint: channel name", visible=True)


def _call_llm_with_prompt(system_prompt, user_prompt, response_format=None):
    msg_lst = []
    for role, prompt in zip(["system", "user"], [system_prompt, user_prompt]):
        if prompt is not None:
            msg_lst.append({"role": role, "content": prompt})

    response = llm_client.chat.completions.create(
        model=ASSISTANT_MODEL,
        messages=msg_lst,
        response_format=response_format
    )
    generated_article = response.choices[0].message.content
    return generated_article    


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
    else:
        user_prompt = prompt_handler.render_template("article_generation", context)
        app_logger.info("Generating article with prompt: \n" + user_prompt) 

    generated_article = _call_llm_with_prompt(
        system_prompt=None, 
        user_prompt=user_prompt,
        response_format=None
    )
    return generated_article


def call_llm_to_generate_question(question_type):

    system_prompt = "You are a question generator for English exam in Taiwan."
    user_prompt = f"Please generate a question based on the question type: {question_type}"

    generated_question = _call_llm_with_prompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format={"type": "json_object"}
    )
    return generated_question

