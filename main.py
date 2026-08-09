import json
import os
import subprocess
import questionary as q
import requests as r
import time as t
from pathlib import Path
from tools import FileTools



file_tools = FileTools()


SERVER_URL = "http://localhost:11434"
MODEL = "qwen3:4b"
OLLAMA_PATH = str(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe")
prompt = """
You are a local desktop assistant. Help the user with everyday file tasks using only the tools provided.

Rules:
- Prefer tools over guessing. Use them when you need to create, read, write, rename, or delete a file.
- Be careful with the user's files. Do not delete or overwrite anything unless they clearly asked for it.
- File deletion requires the user's confirmation in the app. If they cancel, acknowledge that and stop.
- After a tool returns success, do not call that same tool again for the same action. Reply with a short, clear result.
- If a tool fails, explain the error briefly and suggest a next step.
- Keep answers concise and practical.
"""

tool_json = [
    {
        "type": "function",
        "function": {
            "name": "making_file",
            "description": "Creates a file at the given location",
            "parameters": {
                "type": "object",
                "required": ["file_name", "file_location"],
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Name of the file"
                    },
                    "file_location": {
                        "type": "string",
                        "description": "Folder path"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reading_file",
            "description": "Reads a file at the given location",
            "parameters": {
                "type": "object",
                "required": ["file_name", "file_location"],
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Name of the file"
                    },
                    "file_location": {
                        "type": "string",
                        "description": "Folder path"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "writing_file",
            "description": "Writes to a file at the given location",
            "parameters": {
                "type": "object",
                "required": ["file_name", "file_location", "content"],
                "properties": {
                    "file_name": {
                        "type": "string",   
                        "description": "Name of the file"
                    },
                    "file_location": {
                        "type": "string",
                        "description": "Folder path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                }
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "renaming_file",
            "description": "Renames a file at the given location",
            "parameters": {
                "type": "object",
                "required": ["file_name", "new_file_name", "file_location"],
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Name of the file"
                    },
                    "new_file_name": {
                        "type": "string",
                        "description": "New name of the file"
                    },
                    "file_location": {
                        "type": "string",
                        "description": "Folder path"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deleting_file",
            "description": "Deletes a file at the given location",
            "parameters": {
                "type": "object",
                "required": ["file_name", "file_location"],
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Name of the file"
                    },
                    "file_location": {
                        "type": "string",
                        "description": "Folder path"
                    }
                }
            }
        }
    }
]






def check_if_model_is_installed():
    # Check if ollama is installed
    try:
        version_check = subprocess.run(
            [OLLAMA_PATH, "--version"],
            check=True,
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        print(f"Could not find Ollama at:\n  {OLLAMA_PATH}")
        print("Install Ollama from https://ollama.com, then restart this app.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Ollama failed to start: {e}")
        print("Check your Ollama install and try again.")
        return False

    # Now check if the model is installed
    try:
        test = subprocess.run(
            [OLLAMA_PATH, "list"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Could not list models: {e}")
        return False

    lines = test.stdout.splitlines()

    models = []

    for line in lines[1:]:
        if line.strip():
            model_name = line.split()[0]
            models.append(model_name)

    if MODEL in models:
        print(f"Ready: {MODEL} is available.")
        return True
    else:
        print(f"Required model not found: {MODEL}")
        print(f"Run this command, then restart:\n  ollama pull {MODEL}")
        return False
  




message = [{"role": "system", "content": prompt.strip()}]
def message_to_model():
    if check_server_status() == False:
        print("Ollama is not running. Start it from the menu first.")
        return

    else:
        while True:
            user_message = input("Ask something (or type exit): ")
            message.append({"role": "user", "content": user_message})
            if user_message == "exit":
                return
            else:
                try:
                    response = r.post(f"{SERVER_URL}/api/chat", json={
                        "model": MODEL,
                        "messages": message,
                        "stream": False,
                        "think": True,
                        "tool_choice": "auto",
                        "tools": tool_json
                    })
                    
                    data = response.json()

                    # Tool loop: assistant(tool_calls) -> tool results -> model again
                    while (
                        "message" in data
                        and data["message"].get("tool_calls")
                    ):
                        # Keep the full assistant turn (includes tool_calls)
                        message.append(data["message"])

                        # Run every tool from this turn, then ask the model once
                        for tool_call in data["message"]["tool_calls"]:
                            tool_name = tool_call["function"]["name"]
                            arguments = tool_call["function"]["arguments"]
                            if isinstance(arguments, str):
                                arguments = json.loads(arguments)

                            if hasattr(file_tools, tool_name):
                                # Check if the tool is deleting_file before proceeding
                                if tool_name == "deleting_file":
                                    confirm = q.confirm(
                                        "Delete this file? This cannot be undone.",
                                        default=False
                                    ).ask()
                                    if not confirm:
                                        print("Deletion cancelled.")
                                        tool_response = {
                                            "status": "cancelled",
                                            "message": "File deletion has been cancelled by the user."
                                        }
                                        message.append({
                                            "role": "tool",
                                            "name": tool_name,
                                            "content": str(tool_response),
                                        })
                                    else:
                                        tool_response = getattr(file_tools, tool_name)(**arguments)
                                        print(f"Running: {tool_name}")
                                        print(f"Args: {arguments}")
                                        print(f"Result: {tool_response}")
                                        message.append({
                                            "role": "tool",
                                            "name": tool_name,
                                            "content": str(tool_response),
                                        })
                                else:
                                    tool_response = getattr(file_tools, tool_name)(**arguments)
                                    print(f"Running: {tool_name}")
                                    print(f"Args: {arguments}")
                                    print(f"Result: {tool_response}")
                                    message.append({
                                        "role": "tool",
                                        "name": tool_name,
                                        "content": str(tool_response),
                                    })
                         
                            else:
                                print(f"Skipped unknown tool: {tool_name}")
                                message.append({
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": str({"status": "error", "message": f"Unknown tool '{tool_name}'"}),
                                })

                        response = r.post(f"{SERVER_URL}/api/chat", json={
                            "model": MODEL,
                            "messages": message,
                            "stream": False,
                            "think": True,
                            "tool_choice": "auto",
                            "tools": tool_json,
                        })
                        data = response.json()

                    # Final assistant reply (no tool_calls), including when no tools were used
                    if "message" in data:
                        message.append(data["message"])
                        if data["message"].get("content"):
                            print(f"Assistant: {data['message']['content']}")

                except r.exceptions.RequestException as e:
                    print(f"Could not reach Ollama: {e}")
                    return

    
             




def warm_model():
        response = r.post(f"{SERVER_URL}/api/generate", json={
        "model": MODEL,
        "prompt": "Hello, world!",
        "stream": False,
        "thinking": False
        })

        if response.status_code == 200:
            print("Model ready.")
            return True








def start_server():
    try:
        response = r.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            print("Ollama is already running.")
            return True
    except Exception as e:
        if e:
            subprocess.Popen(
                [OLLAMA_PATH, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Starting Ollama...")
            t.sleep(20)
            if check_server_status() == True:
                print("Loading model...")
                warm_model()
            return True



def check_server_status():
    try:
        response = r.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            return True
    except Exception as e:
        return False



def stop_server():
    if check_server_status() == True:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "ollama.exe", "/T"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["taskkill", "/F", "/IM", "ollama app.exe", "/T"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Ollama stopped.")
            return
        except Exception as e:
            print(f"Could not stop Ollama: {e}")
            
    else:
        print("Ollama is not running.")
        return

def main():
    if not check_if_model_is_installed():
        return
    while True:
        action = q.select(
            "What would you like to do?",
            choices=[
                "Start Ollama",
                "Stop Ollama",
                "Check Status",
                "Chat",
                "Exit and Stop Ollama",
                "Exit (Keep Ollama Running)",
            ],
        ).ask()
        if action == "Start Ollama":
            start_server()
        elif action == "Stop Ollama":
            stop_server()
        elif action == "Chat":
            message_to_model()

        elif action == "Check Status":
            if check_server_status() == True:
                print("Ollama is running.")
            else:
                print("Ollama is not running.")
        elif action == "Exit and Stop Ollama":
            print("Stopping Ollama...")
            stop_server()
            break
        elif action == "Exit (Keep Ollama Running)":
            break
if __name__ == "__main__":
    main()