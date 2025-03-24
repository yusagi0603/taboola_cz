'''
Note
- DO NOT create an assistant every time! UPDATE through assistant_id.
'''

'''
References
- https://github.com/openai/openai-cookbook/blob/main/examples/Assistants_API_overview_python.ipynb
'''
import os
import json


from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import GoogleCredentials
from openai import OpenAI
import gradio as gr
from json_repair import repair_json
import json_repair  # enable streaming
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from components.chat import Chat
from components.entry_form import EntryForm
from components.password import Password

import option
from config import (
    OPENAI_API_KEY,
    ASSISTANT_NAME,
    ASSISTANT_DESCRIPTION,
    ASSISTANT_INSTRUCTION,
    ASSISTANT_MODEL,
    RESPONSE_FORMAT,
    CONVERSATION_STARTER,
    VECTOR_STORE_NAME,
)


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# View existing assistants
existed_assistants = client.beta.assistants.list(
    order="desc",
    limit="20",
)
print(len(existed_assistants.data),existed_assistants.data)

# Delete assistant by id 
def delete_asst(assistant_id):
  response = client.beta.assistants.delete(assistant_id)
  print(response)

# Assistant setting (Playground: https://platform.openai.com/playground/assistants)

# Record once created
assistant_id = os.getenv('assistant_id')  
google_drive_folder_id = os.getenv('google_drive_folder_id')


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


# spent 4m 50s downloading all 175 files
def embed_from_drive(folder_id):
  # auth.authenticate_user()
  gauth = GoogleAuth()
  gauth.credentials = GoogleCredentials.get_application_default()
  drive = GoogleDrive(gauth)

  # Get all files in '定稿專案' folder: https://drive.google.com/drive/folders/1dlsf5BNjNczzUYKPZvYXd2mLW21QCLUK?usp=drive_link
  file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

  # Download files to local (`/content/`), since file_streams don't recieve google docs
  local_file_paths = []
  for file1 in file_list:
      print('Processing file title: %s, id: %s' % (file1['title'], file1['id']))
      local_path = f"/content/{file1['title']}.docx"

      if 'exportLinks' in file1:
          if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in file1['exportLinks']:
              # update type if needed (application/vnd.openxmlformats-officedocument.wordprocessingml.document == .docx)
              export_url = file1['exportLinks']['application/vnd.openxmlformats-officedocument.wordprocessingml.document']
              print(f"Downloading as Word document: {file1['title']}")
              downloaded_file = drive.CreateFile({'id': file1['id']})
              downloaded_file.GetContentFile(local_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
              local_file_paths.append(local_path)
          else:
              print(f"No Word export available for: {file1['title']}")
      else:
          print(f"Skipping non-Google Docs file: {file1['title']}")

  for path in local_file_paths:
      print(f"Downloaded file: {path}")

  file_streams = [open(path, "rb") for path in local_file_paths]
  return file_streams

# Embed files (downloaded from drive folder)
def get_vector_store_id(file_streams):
  vector_store = client.beta.vector_stores.create(name=VECTOR_STORE_NAME)

#   # spent 51s batching all 175 files
#   file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
#     vector_store_id=vector_store.id, files=file_streams
#   )

#   print("file_batch status",file_batch.status)
#   print("file_counts",file_batch.file_counts)

  return vector_store.id

# Create a completely new assistant
def create_assistant(vector_store_id):
  assistant = client.beta.assistants.create(
    name=ASSISTANT_NAME,
    description=ASSISTANT_DESCRIPTION,
    instructions=ASSISTANT_INSTRUCTION,
    model=ASSISTANT_MODEL,
    tools=[{"type": "file_search"}],
    tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}},
    response_format=RESPONSE_FORMAT
  )
  show_json(assistant)
  return assistant.id

# Update existing assistant through ID (please customize prefered inputs)
def update_assistant(assistant_id):
  assistant = client.beta.assistants.update(
    assistant_id=assistant_id,
    name=ASSISTANT_NAME,
    description=ASSISTANT_DESCRIPTION,
    instructions=ASSISTANT_INSTRUCTION,
    model=ASSISTANT_MODEL,
    tools=[{"type": "file_search"}],
    # tool_resources={'file_search': {'vector_store_ids': [vector_store_id]}},
    response_format=RESPONSE_FORMAT
  )
  show_json(assistant)

# Create assistant if assistant_id does not exist
try:
  assistant = client.beta.assistants.retrieve(assistant_id)
  # update_assistant(assistant_id)
except Exception as e:
  print(f"Assistant DNE: {e}, create assistant instead.")
  file_streams = embed_from_drive(google_drive_folder_id)
  vector_store_id = get_vector_store_id(file_streams)
  print(vector_store_id)
  assistant_id = create_assistant(vector_store_id)

ASSISTANT_ID = assistant_id

# Update assistant if needed
assistant = client.beta.assistants.update(
    assistant_id=ASSISTANT_ID,
    instructions=ASSISTANT_INSTRUCTION,
    response_format=RESPONSE_FORMAT
)
show_json(assistant)

class EventHandler(AssistantEventHandler):
  @override
  def on_text_created(self, text: Text) -> None:
    print(f"\nassistant > ", end="", flush=True)

  @override
  def on_text_delta(self, delta: TextDelta, snapshot: Text):
    print(delta.value, end="", flush=True)

  @override
  def on_tool_call_created(self, tool_call: ToolCall):
    print(f"\nassistant > {tool_call.type}\n", flush=True)




# Initialize components
chat = Chat(client, ASSISTANT_ID)
entry_form = EntryForm(client, ASSISTANT_ID)
password = Password()

with gr.Blocks() as demo:
    # Render password UI
    password_popup, password_input, submit_button, error_message = password.render()
    
    # Main UI 
    with gr.Group(visible=False) as main_ui:
        entry_form_ui = entry_form.render()
        chat_ui = chat.render()
        
    # Connect generate button to show chat interface and populate textbox
    entry_form.generate_button.click(
        entry_form.generate_initial_content,
        inputs=[entry_form.grade, entry_form.vocabulary_range, entry_form.topic_range, entry_form.grammar_range],
        outputs=[chat.textbox, chat_ui, entry_form_ui]
    )
            
    # Connect password events
    submit_button.click(
        password.check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )
    
    password_input.submit(
        password.check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )

demo.launch(debug=True)