---
title: Cz Base SEL COACH
emoji: 📈
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 5.22.0
python_version: 3.10.0
app_file: app.py
pinned: false
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

## Local Development Setup

### Setting up Virtual Environment

1. Create a Virtual Environment
```bash
python3 -m venv venv
```

2. Activate the Virtual Environment
```bash
# On Unix/macOS
source venv/bin/activate

# On Windows
.\venv\Scripts\activate
```

3. Install Dependencies
```bash
pip install -r requirements.txt
```

4. Verify Installation
```bash
pip list
```

5. Start the Application
```bash
# Make sure the script is executable
chmod +x run_app.sh

# Run the application
./run_app.sh
```

6. When you're done, deactivate the Virtual Environment
```bash
deactivate
```

## Notes
- Make sure you have Python 3.13.0 installed
- The application runs on Gradio SDK version 5.12.0


```
# Project Root Directory

handlers/ - Group all event handlers here
│   ├── __init__.py       # Initialize the handlers package
│   ├── chat_handler.py   # Handles chat-related events
│   ├── history_handler.py # Manages undo/redo actions
│   ├── file_handler.py   # Handles different output file events

services/ - Business logic & external APIs
│   ├── drive_service.py  # Handles interactions with Drive
│   ├── openai_service.py # Manages OpenAI API calls

interface/ - UI logic (CLI, GUI, etc.)
│   ├── main_interface.py # Main interface logic
│   ├── components/       # Reusable UI components
│       ├── __init__.py   # Initialize the components package

utils/ - Generic helper functions
│   ├── logger.py         # Logging utilities

app.py - Main entry point of the application
```
