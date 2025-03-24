import json

from typing_extensions import override

from config import (
    OPENAI_API_KEY,
    ASSISTANT_NAME,
    ASSISTANT_DESCRIPTION,
    ASSISTANT_INSTRUCTION,
    ASSISTANT_MODEL,
    RESPONSE_FORMAT,
    CORRECT_PASSWORD,
    ASSISTANT_ID,
    ASSISTANT_USER_PROMPT
)

from openai import AssistantEventHandler

import os
import json


from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import GoogleCredentials
from openai import OpenAI
import gradio as gr
from json_repair import repair_json
from typing_extensions import override
from openai import OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from docx import Document
import tempfile
    
from logger import app_logger
from client import llm_client


# spent 4m 50s downloading all 175 files
# def embed_from_drive(folder_id):
#   # auth.authenticate_user()
#   gauth = GoogleAuth()
#   gauth.credentials = GoogleCredentials.get_application_default()
#   drive = GoogleDrive(gauth)

#   # Get all files in '定稿專案' folder: https://drive.google.com/drive/folders/1dlsf5BNjNczzUYKPZvYXd2mLW21QCLUK?usp=drive_link
#   file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

#   # Download files to local (`/content/`), since file_streams don't recieve google docs
#   local_file_paths = []
#   for file1 in file_list:
#       print('Processing file title: %s, id: %s' % (file1['title'], file1['id']))
#       local_path = f"/content/{file1['title']}.docx"

#       if 'exportLinks' in file1:
#           if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in file1['exportLinks']:
#               # update type if needed (application/vnd.openxmlformats-officedocument.wordprocessingml.document == .docx)
#               export_url = file1['exportLinks']['application/vnd.openxmlformats-officedocument.wordprocessingml.document']
#               print(f"Downloading as Word document: {file1['title']}")
#               downloaded_file = drive.CreateFile({'id': file1['id']})
#               downloaded_file.GetContentFile(local_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
#               local_file_paths.append(local_path)
#           else:
#               print(f"No Word export available for: {file1['title']}")
#       else:
#           print(f"Skipping non-Google Docs file: {file1['title']}")

#   for path in local_file_paths:
#       print(f"Downloaded file: {path}")

#   file_streams = [open(path, "rb") for path in local_file_paths]
#   return file_streams


# Embed files (downloaded from drive folder)
# def get_vector_store_id(file_streams):
#   vector_store = client.beta.vector_stores.create(name=VECTOR_STORE_NAME)

# #   # spent 51s batching all 175 files
# #   file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
# #     vector_store_id=vector_store.id, files=file_streams
# #   )

# #   print("file_batch status",file_batch.status)
# #   print("file_counts",file_batch.file_counts)

#   return vector_store.id


# Create a completely new assistant
# def create_assistant(vector_store_id):
#   assistant = client.beta.assistants.create(
#     name=ASSISTANT_NAME,
#     description=ASSISTANT_DESCRIPTION,
#     instructions=ASSISTANT_INSTRUCTION,
#     model=ASSISTANT_MODEL,
#     tools=[{"type": "file_search"}],
#     tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}},
#     response_format=RESPONSE_FORMAT
#   )
#   show_json(assistant)
#   return assistant.id


# Update existing assistant through ID (please customize prefered inputs)
# def update_assistant(assistant_id):
#   assistant = client.beta.assistants.update(
#     assistant_id=assistant_id,
#     name=ASSISTANT_NAME,
#     description=ASSISTANT_DESCRIPTION,
#     instructions=ASSISTANT_INSTRUCTION,
#     model=ASSISTANT_MODEL,
#     tools=[{"type": "file_search"}],
#     # tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}},
#     response_format=RESPONSE_FORMAT
#   )
#   show_json(assistant)


# Update assistant if needed
# assistant = client.beta.assistants.update(
#     assistant_id=ASSISTANT_ID,
#     instructions=ASSISTANT_INSTRUCTION,
#     response_format=RESPONSE_FORMAT
# )
# show_json(assistant)


def check_password(input_password):
    if input_password == CORRECT_PASSWORD:
        return gr.update(visible=False), gr.update(visible=True), ""
    else:
        return gr.update(visible=True), gr.update(visible=False), gr.update(value="Wrong Password. Please Retry. hint: channel name", visible=True)

def _call_llm_with_prompt(system_prompt, user_prompt, llm_client=llm_client, response_format=None):
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
        llm_client, grade_values, vocabulary_range_values, topic_range_values, grammar_range_values
    ):
  
    system_prompt, user_prompt = ASSISTANT_INSTRUCTION, ASSISTANT_USER_PROMPT.format(
        grade_values=grade_values,
        topic_values=topic_range_values,
        grammar_values=grammar_range_values,
        vocabulary_values=vocabulary_range_values
    )

    # Use Assistant API to generate article
    # user_prompt = ASSISTANT_USER_PROMPT.format(
    #     grade_values=grade_values,
    #     topic_values=topic_range_values,
    #     grammar_values=grammar_range_values,
    #     vocabulary_values=vocabulary_range_values
    # )
    # print(user_prompt)
    # # Create a new user message for the given thread
    # message = client.beta.threads.messages.create(
    #     thread_id=thread.id,
    #     role="user",
    #     content=user_prompt
    # )

    # # Run an wait for the assistant to complete the task
    # run = client.beta.threads.runs.create_and_poll(
    #     thread_id=thread.id,
    #     assistant_id=ASSISTANT_ID,
    #     instructions=ASSISTANT_INSTRUCTION,
    #     response_format=RESPONSE_FORMAT
    # )

    # # TODO: set timeout
    # while run.status != 'completed':
    #     print(run.status)
    #     time.sleep(2)

    # # Extract the messages from the thread
    # message_responses = client.beta.threads.messages.list(
    #     thread_id=thread.id
    # )

    # generated_article = message_responses.data[0].content[0].text.value

    # Use ChatCompletion API to generate article
    generated_article = _call_llm_with_prompt(
        system_prompt=None, 
        user_prompt=user_prompt, 
        llm_client=llm_client, 
        response_format=RESPONSE_FORMAT
    )
    return generated_article

def call_llm_to_generate_question(llm_client, question_type):

    system_prompt, user_prompt = "You are a question generator for English exam in Taiwan.", \
        f"Please generate a question based on the question type: {question_type}"

    generated_question = _call_llm_with_prompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_client=llm_client,
        response_format=None
    )
    return generated_question

def create_google_doc(self, title, content):
    """Create a Google Doc with the given title and content."""
    try:
        # Import necessary libraries for Google Docs API
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        # Set up credentials and service
        SCOPES = ['https://www.googleapis.com/auth/documents']
        SERVICE_ACCOUNT_FILE = 'credentials.json'  # Path to your service account credentials
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        docs_service = build('docs', 'v1', credentials=credentials)
        
        # Create a new document
        document = {
            'title': title
        }
        doc = docs_service.documents().create(body=document).execute()
        document_id = doc.get('documentId')
        
        # Insert content into the document
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1
                    },
                    'text': content
                }
            }
        ]
        
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        # Get the document URL
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        return doc_url
        
    except Exception as e:
        app_logger.error(f"Error creating Google Doc: {str(e)}")
        return None
    
def generate_docx_file(doc_file_name, question_info_tuple):
    
    # # Create a Word document
    doc = Document()
    doc.add_heading(doc_file_name, 0)
    
    # # Add each question to the document
    for question_type, question in question_info_tuple:
        doc.add_heading(f"{question_type}", level=1)
        doc.add_paragraph(question)
        doc.add_paragraph("")  # Add some spacing

    doc.save(doc_file_name)

    return doc_file_name

