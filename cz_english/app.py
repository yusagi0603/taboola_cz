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
    CORRECT_PASSWORD,
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




# Function to generate content based on dropdown selections
def generate_initial_content(grade_values, vocabulary_range_values, topic_range_values, grammar_range_values):
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
    client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
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
    response = client.chat.completions.create(
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
    return content, gr.update(visible=True)


def check_password(input_password):
    if input_password == CORRECT_PASSWORD:
        return gr.update(visible=False), gr.update(visible=True), ""
    else:
        return gr.update(visible=True), gr.update(visible=False), gr.update(value="Wrong Password. Please Retry. hint: channel name", visible=True)

chat = Chat(client, ASSISTANT_ID)

with gr.Blocks() as demo:
    # Initialize chat component
    
    # password UI popup
    with gr.Group(visible=True) as password_popup:
        password_input = gr.Textbox(label="請輸入密碼", type="password")
        submit_button = gr.Button("提交")
        error_message = gr.Textbox(label="", visible=False, interactive=False)
    # Main UI 
    with gr.Group(visible=False) as main_ui:
        with gr.Column():
            with gr.Group() as selection_ui:
                gr.Markdown("## 請選擇文章生成參數")
                
                # Three dropdown boxes with multi-select
                grade = gr.Dropdown(
                    choices=option.GRADE_OPTIONS,
                    label="學生年級",
                    multiselect=True
                )
                
                vocabulary_range = gr.Dropdown(
                    choices=option.VOCABULARY_OPTIONS,
                    label="單字範圍",
                    multiselect=True
                )

                grammar_range = gr.Dropdown(
                    choices=option.GRAMMAR_OPTIONS,
                    label="文法範圍",
                    multiselect=True
                )
                
                topic_range = gr.Dropdown(
                    choices=option.TOPIC_OPTIONS,
                    label="主題範圍",
                    multiselect=True
                )
                
                generate_button = gr.Button("生成初始文章")
            
            # Chat interface (initially hidden)
            with gr.Group(visible=False) as chat_ui:
                chat.render()
            
            # Connect generate button to show chat interface and populate textbox
            generate_button.click(
                generate_initial_content,
                inputs=[grade, vocabulary_range, topic_range, grammar_range],
                outputs=[chat.textbox, chat_ui]
            )
            
    # submit button event
    submit_button.click(
        check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )
    # password input submit event (click enter)
    password_input.submit(
        check_password,
        inputs=password_input,
        outputs=[password_popup, main_ui, error_message]
    )

demo.launch(debug=True)