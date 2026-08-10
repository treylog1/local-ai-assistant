import ast
import json
import os
import re
import subprocess
import questionary as q
import requests as r
import time as t
from pathlib import Path
from tools import FileTools

art = r"""
+===============================================================+
|                                                               |
|      __                 __   ___    ____          .--.        |
|     / /  ___  ____ ___ / /  / _ |  /  _/         |o_o |       |
|    / /__/ _ \/ __/ _ `/ /  / __ | _/ /          <|:_/ |       |
|   /____/\___/\__/\_,_/_/  /_/ |_|/___/         //   \ \       |
|              A S S I S T A N T                (|     | )      |
|      [ local ]  [ ollama ]  [ offline ]      /'\_   _/`\      |
|                                              \___)=(___/      |
|                                                               |
|      create | read | write | rename | delete                  |
|                                                               |
+===============================================================+
"""







file_tools = FileTools()


SERVER_URL = "http://localhost:11434"
MODEL = "qwen3:4b"
OLLAMA_PATH = str(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe")
prompt = """
You are a local desktop assistant. Help the user with everyday file tasks using only the tools provided.

Rules:
- Prefer tools over guessing. Use them when you need to create, read, write, rename, or delete a file.
- Be careful with the user's files. Do not delete or overwrite anything unless they clearly asked for it.
- For deletion: call deleting_file. The app will ask the user to confirm. Do not ask for confirmation in chat yourself.
- If the user cancels deletion, acknowledge that briefly and stop.
- After a tool returns success, do not call that same tool again for the same action. Reply with a short, clear result.
- If a tool fails, explain the error briefly and suggest a next step.
- Reply with short user-facing text only. Never narrate your reasoning, rules, or internal analysis.
- Never use \\boxed{}, LaTeX, or roleplay as "the assistant should...".
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






def clean_assistant_content(content: str) -> str:
    """Hide model reasoning; return only the user-facing reply."""
    if not content:
        return ""

    text = content

    # Full think / thinking blocks
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r"<thinking>.*?</thinking>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # With think=false, Ollama often drops the opening tag and leaves
    # reasoning + a trailing </think>. Keep only text after the last closer.
    closer = re.search(r"</think\s*>|</thinking\s*>", text, flags=re.IGNORECASE)
    if closer:
        text = text[closer.end():]

    # Drop any leftover open tags if the closer never arrived
    text = re.sub(r"<think\s*>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking\s*>.*", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Qwen-style final answers sometimes land only inside \boxed{...}
    boxed = re.findall(
        r"\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
        text,
    )
    if boxed:
        return boxed[-1].strip()

    text = re.sub(r"\$\$\s*", "", text)
    return text.strip()


def assistant_message_for_history(msg: dict) -> dict:
    cleaned = {
        "role": msg.get("role", "assistant"),
        "content": clean_assistant_content(msg.get("content") or ""),
    }
    if msg.get("tool_calls"):
        cleaned["tool_calls"] = msg["tool_calls"]
    return cleaned


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
    tool_call_count = 0
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
                        # Keep the assistant turn without thinking traces
                        message.append(assistant_message_for_history(data["message"]))

                        # Run every tool from this turn, then ask the model once
                        for tool_call in data["message"]["tool_calls"]:
                            if tool_call_count > 8:
                                print("Tool call limit exceeded for this user message. Limit is 8 tools per step.")
                                tool_response = {
                                    "status": "limit_exceeded",
                                    "message": "Tool call limit of 8 has been reached. Further actions have been stopped."
                                }
                                message.append({
                                    "role": "tool",
                                    "name": tool_call["function"]["name"],
                                    "content": str(tool_response),
                                })
                                break  # stop processing more tool calls
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
                            tool_call_count += 1
                 

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
                        # Prefer content; never print message.thinking
                        cleaned = assistant_message_for_history(data["message"])
                        reply = cleaned.get("content") or ""

                        # If the model only thought and left no final text, fall back
                        # to the latest tool result message so the user still gets a reply.
                        if not reply:
                            for prior in reversed(message):
                                if prior.get("role") != "tool" or not prior.get("content"):
                                    continue
                                try:
                                    parsed = (
                                        ast.literal_eval(prior["content"])
                                        if isinstance(prior["content"], str)
                                        else prior["content"]
                                    )
                                except (SyntaxError, ValueError):
                                    continue
                                if isinstance(parsed, dict) and parsed.get("message"):
                                    reply = str(parsed["message"])
                                    break

                        cleaned["content"] = reply
                        message.append(cleaned)
                        if reply:
                            print(f"Assistant: {reply}")

                except r.exceptions.RequestException as e:
                    print(f"Could not reach Ollama: {e}")
                    return

    
             




def warm_model():
        response = r.post(f"{SERVER_URL}/api/generate", json={
        "model": MODEL,
        "prompt": "Hello, world!",
        "stream": False,
        "think": False,
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
    print(art)
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