import json
from os import name
import subprocess
import questionary as q
import requests as r
import time as t
from tools import FileTools



file_tools = FileTools()


SERVER_URL = "http://localhost:11434"
MODEL = "qwen3:4b"
OLLAMA_PATH = r"C:\Users\treyl\AppData\Local\Programs\Ollama\ollama.exe"
prompt = """
    you are a local ai assistant for common tasks around the desktop.
    you will be given specific tools for tasks around the desktop.
    you will not do anything destructive.
    you will not do anything that might hurt the users information.
    you will use the tools provided to you when needed to complete the task.
    after a tool returns success, do not call the same tool again; reply to the user with the result.

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
    test = subprocess.run(
        ["ollama", "list"],
        check=True,
        capture_output=True,
        text=True
    )

    lines = test.stdout.splitlines()

    models = []

    for line in lines[1:]:
        if line.strip():
            model_name = line.split()[0]
            models.append(model_name)

    if MODEL in models:
        print(f"Model {MODEL} is installed")
        return True
    else:
        print(f"Model {MODEL} is not installed")
        return False
  




message = []
def message_to_model():
    if check_server_status() == False:
        print("Server is not running")
        return

    else:
        while True:
            user_message = input("what do you need: ")
            message.append({"role": "user", "content": user_message})
            if user_message == "exit":
                return
            else:
                try:
                    response = r.post(f"{SERVER_URL}/api/chat", json={
                        "model": MODEL,
                        "messages": message,
                        "system": prompt,
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
                                tool_response = getattr(file_tools, tool_name)(**arguments)
                                print(f"Tool called: {tool_name} with arguments {arguments}")
                                print(f"Result from tool '{tool_name}': {tool_response}")
                                message.append({
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": str(tool_response),
                                })
                            else:
                                print(f"Tool '{tool_name}' not found in the provided file_tools instance.")
                                message.append({
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": str({"status": "error", "message": f"Unknown tool '{tool_name}'"}),
                                })

                        response = r.post(f"{SERVER_URL}/api/chat", json={
                            "model": MODEL,
                            "messages": message,
                            "system": prompt,
                            "stream": False,
                            "think": True,
                            "tool_choice": "auto",
                            "tools": tool_json,
                        })
                        data = response.json()
                        print(f"New response from model: {data.get('message', {}).get('content', '')}")

                    # Final assistant reply (no tool_calls), including when no tools were used
                    if "message" in data:
                        message.append(data["message"])
                        if data["message"].get("content"):
                            print(data["message"]["content"])

                except r.exceptions.RequestException as e:
                    print(f"you got an error {e}")
                    return

    
             




def warm_model():
        response = r.post(f"{SERVER_URL}/api/generate", json={
        "model": MODEL,
        "prompt": "Hello, world!",
        "stream": False,
        "thinking": False
        })

        if response.status_code == 200:
            print("Model is warmed up")
            return True








def start_server():
    try:
        response = r.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            print("Server is already running")
            return True
    except Exception as e:
        if e:
            subprocess.Popen(
                [OLLAMA_PATH, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Server is starting...")
            t.sleep(20)
            if check_server_status() == True:
                if check_if_model_is_installed() == False:
                    print("Model is not installed")
                    return False
                else:
                    print("warming up model...")
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
            print("Server is stopped")
            return
        except Exception as e:
            print(f"Error stopping server: {e}")
            
    else:
        print("server is not running")
        return

def main():
    while True:
        action = q.select("What do you want to do?", choices=["Start Server", "Stop Server", "Check Server Status", "what is your task", "Exit", "exit without stoping server"]).ask()
        if action == "Start Server":
            start_server()
        elif action == "Stop Server":
            stop_server()
        elif action == "what is your task":
            message_to_model()

        elif action == "Check Server Status":
            if check_server_status() == True:
                print("Server is running")
            else:
                print("Server is not running")
        elif action == "Exit":
            print("Stoping server...")
            stop_server()
            break
        elif action == "exit without stoping server":
            break
if __name__ == "__main__":
    main()