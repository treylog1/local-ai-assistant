# Local AI Assistant

A Windows CLI assistant that runs fully locally with [Ollama](https://ollama.com). Chat with a small local model and let it use tools to create, read, write, rename, and delete files on your machine.

## Features

- Local inference through Ollama (no cloud API keys)
- Function calling for desktop file tasks
- Interactive menu to start/stop Ollama, check status, and chat
- Startup checks that Ollama and the required model are available
- Confirmation prompt before any file delete

## Requirements

- Windows
- Python 3.10+
- [Ollama](https://ollama.com) installed in the default location:
  `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`

## Setup

```powershell
git clone https://github.com/treylog1/Local-AI-assistant.git
cd Local-AI-assistant

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Pull the model used by the app:

```powershell
ollama pull qwen3:4b
```

## Run

```powershell
python main.py
```

Or double-click `main.bat`.

## Usage

1. Choose **Start Ollama** if the server is not already running.
2. Choose **Chat**.
3. Ask for a file task, for example:
   - `Create a file called notes.txt on my Desktop`
   - `Read notes.txt from my Desktop`
   - `Rename notes.txt to todo.txt on my Desktop`
4. Type `exit` to leave chat and return to the menu.
5. Choose **Exit and Stop Ollama** or **Exit (Keep Ollama Running)**.

Deleting a file always asks for confirmation first.

## Project structure

```
Local-AI-assistant/
├── main.py            # Menu, Ollama lifecycle, chat + tool loop
├── tools.py           # File tools (create, read, write, rename, delete)
├── main.bat           # Windows launcher
├── requirements.txt
└── README.md
```

## How it works

```
You → CLI menu → Ollama (/api/chat) → model
                      ↓
                 tool_calls
                      ↓
                 FileTools → result back to model → reply
```

The assistant sends a system prompt as a chat message (`role: system`), exposes file tools to the model, runs any requested tools, then returns the model’s final answer.

## Config

Defaults in `main.py`:

| Setting | Default |
|---------|---------|
| Model | `qwen3:4b` |
| Ollama API | `http://localhost:11434` |
| Ollama binary | `%LOCALAPPDATA%\Programs\Ollama\ollama.exe` |

Change `MODEL` in `main.py` if you want a different local model (pull it with Ollama first).

## Dependencies

- `questionary` — interactive CLI menus
- `requests` — Ollama HTTP API

## Notes

- This project is local-first: prompts and file contents stay on your machine.
- File tools operate on the paths the model provides. Be specific when you ask for locations.
- Built for personal desktop use and as a portfolio example of local LLM tool calling.
