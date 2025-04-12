import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, messagebox, font as tkfont
import google.generativeai as genai
import threading
import queue
import os
import configparser
from PIL import Image, ImageTk, UnidentifiedImageError
import base64
import io
import json
import datetime

# --- Configuration ---
APP_NAME = "Gemini Chat GUI"
CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME.lower().replace(' ', '_')}")
CHATS_DIR = os.path.join(CONFIG_DIR, "chats")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")

API_SECTION = "API"
API_KEY_OPTION = "google_api_key"
SETTINGS_SECTION = "Settings"
APPEARANCE_OPTION = "appearance_mode"
THEME_OPTION = "color_theme"
MODEL_OPTION = "gemini_model"

DEFAULT_MODEL = "gemini-1.5-flash"
AVAILABLE_MODELS = ["gemini-1.5-flash", "gemini-pro"]

SIDEBAR_WIDTH = 200
TOGGLE_BUTTON_WIDTH = 20 # Reduced width

# --- Embedded Icons ---
ICON_PLACEHOLDER_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
SEND_ICON_B64 = ICON_PLACEHOLDER_B64

# --- Helper Functions ---
def load_icon(base64_string, size=(20, 20)):
    image = None
    try:
        cleaned_b64 = "".join(base64_string.strip().split())
        image_data = base64.b64decode(cleaned_b64)
        image = Image.open(io.BytesIO(image_data))
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        return ctk_image
    except base64.binascii.Error: pass
    except (UnidentifiedImageError, OSError, IOError): pass
    except Exception: pass
    return None

def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def ensure_chats_dir():
    os.makedirs(CHATS_DIR, exist_ok=True)

# --- Config Handling ---
def load_config():
    ensure_config_dir()
    config = configparser.ConfigParser()
    config[API_SECTION] = {API_KEY_OPTION: ''}
    config[SETTINGS_SECTION] = {
        APPEARANCE_OPTION: 'System',
        THEME_OPTION: 'blue',
        MODEL_OPTION: DEFAULT_MODEL
    }
    config.read(CONFIG_FILE)
    return config

def save_config(config):
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        try: os.chmod(CONFIG_FILE, 0o600)
        except OSError: pass
        return True
    except IOError:
        messagebox.showerror("Save Error", f"Could not save config to {CONFIG_FILE}.")
        return False

# --- Chat History Handling ---
def get_chat_files():
    ensure_chats_dir()
    try:
        files = [f for f in os.listdir(CHATS_DIR) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(CHATS_DIR, x)), reverse=True)
        return files
    except OSError:
        return []

def save_chat_to_file(chat_history, file_path):
    ensure_chats_dir()
    try:
        serializable_history = []
        for msg in chat_history:
             try:
                 text_content = "".join(part.text for part in msg.parts if hasattr(part, 'text'))
                 serializable_history.append({'role': msg.role, 'content': text_content})
             except AttributeError:
                 if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                      serializable_history.append(msg)
                 else: pass # Skip unknown format

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_history, f, indent=2)
        return True
    except (IOError, TypeError, AttributeError) as e:
        messagebox.showerror("Save Error", f"Failed to save chat: {e}")
        return False

def load_chat_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        loaded_history = []
        for item in history_data:
             loaded_history.append({'role': item['role'], 'content': item['content']})
        return loaded_history
    except (IOError, json.JSONDecodeError, KeyError) as e:
        messagebox.showerror("Load Error", f"Failed to load chat: {e}")
        return None

def delete_chat_file(file_path):
    try:
        os.remove(file_path)
        return True
    except OSError as e:
        messagebox.showerror("Delete Error", f"Failed to delete chat file: {e}")
        return False

# --- Settings Window ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.config = parent.config

        self.title("Settings")
        self.geometry("450x400")
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Settings", font=("Arial", 16, "bold")).pack(pady=(10, 15))

        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(api_frame, text="Gemini API Key:").pack(side="left", padx=(0, 10))
        self.api_key_var = tk.StringVar(value=self.config.get(API_SECTION, API_KEY_OPTION, fallback=""))
        api_entry = ctk.CTkEntry(api_frame, textvariable=self.api_key_var, show="*")
        api_entry.pack(side="left", fill="x", expand=True)

        model_frame = ctk.CTkFrame(self)
        model_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(model_frame, text="AI Model:").pack(side="left", padx=(0, 10))
        self.model_var = tk.StringVar(value=self.config.get(SETTINGS_SECTION, MODEL_OPTION, fallback=DEFAULT_MODEL))
        model_dropdown = ctk.CTkOptionMenu(model_frame, variable=self.model_var, values=AVAILABLE_MODELS)
        model_dropdown.pack(side="left", fill="x", expand=True)

        appearance_frame = ctk.CTkFrame(self)
        appearance_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(appearance_frame, text="Appearance Mode:").pack(side="left", padx=(0, 10))
        self.appearance_var = tk.StringVar(value=self.config.get(SETTINGS_SECTION, APPEARANCE_OPTION, fallback="System"))
        appearance_options = ["Light", "Dark", "System"]
        appearance_menu = ctk.CTkOptionMenu(appearance_frame, variable=self.appearance_var, values=appearance_options, command=self.parent_app.change_appearance_mode)
        appearance_menu.pack(side="left", fill="x", expand=True)

        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(theme_frame, text="Color Theme:").pack(side="left", padx=(0, 10))
        self.theme_var = tk.StringVar(value=self.config.get(SETTINGS_SECTION, THEME_OPTION, fallback="blue"))
        theme_options = ["blue", "green", "dark-blue"]
        theme_menu = ctk.CTkOptionMenu(theme_frame, variable=self.theme_var, values=theme_options, command=self.parent_app.change_color_theme)
        theme_menu.pack(side="left", fill="x", expand=True)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(20, 10))

        save_button = ctk.CTkButton(button_frame, text="Save & Close", command=self.save_and_close)
        save_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy, fg_color="gray")
        cancel_button.pack(side="left", padx=10)

    def save_and_close(self):
        new_api_key = self.api_key_var.get()
        current_api_key = self.config.get(API_SECTION, API_KEY_OPTION)
        api_key_changed = new_api_key != current_api_key

        new_model = self.model_var.get()
        current_model = self.config.get(SETTINGS_SECTION, MODEL_OPTION)
        model_changed = new_model != current_model

        self.config.set(API_SECTION, API_KEY_OPTION, new_api_key)
        self.config.set(SETTINGS_SECTION, APPEARANCE_OPTION, self.appearance_var.get())
        self.config.set(SETTINGS_SECTION, THEME_OPTION, self.theme_var.get())
        self.config.set(SETTINGS_SECTION, MODEL_OPTION, new_model)

        if save_config(self.config):
            messagebox.showinfo("Settings Saved", "Settings have been saved.", parent=self)
            if api_key_changed or model_changed:
                self.parent_app.reconfigure_api_from_settings()
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings.", parent=self)


# --- Main Application Class ---
class GeminiChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config = load_config()

        self.title(APP_NAME)
        self.geometry("950x650")
        self.minsize(700, 450)

        self.appearance_mode = self.config.get(SETTINGS_SECTION, APPEARANCE_OPTION, fallback="System")
        self.color_theme = self.config.get(SETTINGS_SECTION, THEME_OPTION, fallback="blue")
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme(self.color_theme)

        self.base_font_family = "Arial"
        self.base_font_size = 12
        self.chat_font = ctk.CTkFont(family=self.base_font_family, size=self.base_font_size)
        self.input_font = ctk.CTkFont(family=self.base_font_family, size=11)
        self.status_font = ctk.CTkFont(family=self.base_font_family, size=10)
        self.sidebar_font = ctk.CTkFont(family=self.base_font_family, size=13, weight="bold")
        self.chatlist_font = ctk.CTkFont(family=self.base_font_family, size=11)

        self.api_key = None
        self.model = None
        self.chat = None
        self.api_ready = False
        self.message_queue = queue.Queue()
        self.last_bot_response = ""
        self.safety_settings = []
        self.current_model_name = self.config.get(SETTINGS_SECTION, MODEL_OPTION, fallback=DEFAULT_MODEL)

        self.current_chat_file = None
        self.chat_is_dirty = False

        self.sidebar_visible = True
        self.settings_window = None

        self.send_icon = load_icon(SEND_ICON_B64)

        self.create_widgets()
        self.load_chat_list()

        threading.Thread(target=self.setup_api, daemon=True).start()
        self.after(100, self.process_message_queue)

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH if self.sidebar_visible else 0)
        self.grid_columnconfigure(1, weight=0, minsize=TOGGLE_BUTTON_WIDTH) # Use constant for toggle button width
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        self.sidebar_frame = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0)
        if self.sidebar_visible:
             self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(3, weight=1)

        sidebar_title = ctk.CTkLabel(self.sidebar_frame, text="Chats", font=self.sidebar_font)
        sidebar_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        new_chat_button = ctk.CTkButton(button_frame, text="New", command=self.new_chat, width=SIDEBAR_WIDTH//2 - 15)
        new_chat_button.grid(row=0, column=0, padx=(0,5), pady=0, sticky="w")
        save_chat_button = ctk.CTkButton(button_frame, text="Save", command=self.save_current_chat, width=SIDEBAR_WIDTH//2 - 15)
        save_chat_button.grid(row=0, column=1, padx=(5,0), pady=0, sticky="e")

        self.chat_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="History", fg_color="transparent")
        self.chat_list_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=(5,5), sticky="nsew")
        self.chat_list_frame.grid_columnconfigure(0, weight=1)

        settings_button = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.open_settings_window)
        settings_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.toggle_button_var = tk.StringVar(value="<" if self.sidebar_visible else ">")
        self.toggle_button = ctk.CTkButton(self, textvariable=self.toggle_button_var,
                                           width=TOGGLE_BUTTON_WIDTH, # Use constant
                                           command=self.toggle_sidebar, anchor="center",
                                           corner_radius=0,
                                           fg_color=("#303030", "#303030"), # Dark background
                                           hover_color=("#404040", "#404040")) # Slightly lighter hover
        self.toggle_button.grid(row=0, column=1, rowspan=3, sticky="ns")

        self.chat_display = ctk.CTkTextbox(
            self, wrap=tk.WORD, state=tk.DISABLED, font=self.chat_font, border_width=1
        )
        self.chat_display.grid(row=0, column=2, padx=(0, 10), pady=(10, 5), sticky="nsew")
        self.chat_display.tag_config("user", foreground="#0077CC")
        self.chat_display.tag_config("bot", foreground="#009955")
        self.chat_display.tag_config("error", foreground="#CC0000")
        self.chat_display.tag_config("info", foreground="#888888")

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=2, padx=(0, 10), pady=(0, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(1, weight=0)

        self.input_entry = ctk.CTkEntry(
            self.input_frame, placeholder_text="Type your message...", font=self.input_font, height=40
        )
        self.input_entry.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.input_entry.bind("<Return>", self.on_enter_pressed)

        self.send_button = ctk.CTkButton(
            self.input_frame, text="", image=self.send_icon, command=self.send_message,
            width=40, height=40, state=tk.DISABLED
        )
        self.send_button.grid(row=0, column=1, padx=(0, 0), pady=5)

        self.status_bar = ctk.CTkLabel(
            self, text="Initializing...", anchor="w", font=self.status_font
        )
        self.status_bar.grid(row=2, column=2, padx=(0, 10), pady=(0, 5), sticky="ew")

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsw")
            self.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH)
            self.toggle_button_var.set("<")
        else:
            self.sidebar_frame.grid_remove()
            self.grid_columnconfigure(0, minsize=0)
            self.toggle_button_var.set(">")
        self.update_idletasks()

    def open_settings_window(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
            self.settings_window.focus()
        else:
            self.settings_window.focus()

    def change_appearance_mode(self, new_mode_str):
        ctk.set_appearance_mode(new_mode_str)
        self.appearance_mode = new_mode_str

    def change_color_theme(self, new_theme_str):
        ctk.set_default_color_theme(new_theme_str)
        self.color_theme = new_theme_str

    def reconfigure_api_from_settings(self):
        self.update_status("Settings updated. Reconfiguring API...")
        self.api_ready = False
        self.set_input_state(tk.DISABLED)
        self.current_model_name = self.config.get(SETTINGS_SECTION, MODEL_OPTION, fallback=DEFAULT_MODEL)
        self.message_queue.put(("UPDATE_TITLE", None))
        threading.Thread(target=self.setup_api, daemon=True).start()
        if messagebox.askyesno("Model Changed", "Model changed. Start new chat?", parent=self):
             self.new_chat(confirm_discard=False)

    def setup_api(self):
        self.update_status("Loading API key...")
        self.api_key = self.config.get(API_SECTION, API_KEY_OPTION, fallback=None)
        if not self.api_key:
            self.message_queue.put(("PROMPT_API_KEY", None))
            return
        self.current_model_name = self.config.get(SETTINGS_SECTION, MODEL_OPTION, fallback=DEFAULT_MODEL)
        self.message_queue.put(("UPDATE_TITLE", None))
        self.configure_google_api()

    def prompt_for_api_key(self):
        api_key = simpledialog.askstring(
            "API Key Required", "Please enter your Google AI (Gemini) API Key:",
            parent=self, show='*'
        )
        if api_key:
            self.config.set(API_SECTION, API_KEY_OPTION, api_key)
            if save_config(self.config):
                self.api_key = api_key
                self.update_status("API Key saved. Initializing model...")
                threading.Thread(target=self.configure_google_api, daemon=True).start()
            else:
                self.update_status("Failed to save API Key.")
                self.set_input_state(tk.DISABLED)
        else:
            self.update_status("API Key not provided. Chat disabled.")
            self.display_message("Error: API Key required.", tag="error")
            self.set_input_state(tk.DISABLED)

    def configure_google_api(self):
        if not self.api_key:
             self.message_queue.put(("STATUS_UPDATE", "API Key missing."))
             self.message_queue.put(("DISPLAY_MSG", ("Cannot configure API without key.", "error")))
             self.set_input_state(tk.DISABLED)
             return
        try:
            self.message_queue.put(("STATUS_UPDATE", f"Configuring {self.current_model_name}..."))
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.current_model_name)
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            if self.current_chat_file is None:
                 self.chat = self.model.start_chat(history=[])
            else:
                 loaded_history = load_chat_from_file(self.current_chat_file)
                 if loaded_history:
                     try:
                          self.chat = self.model.start_chat(history=loaded_history)
                     except Exception as start_chat_err:
                           self.message_queue.put(("DISPLAY_MSG", (f"Error re-loading history.", "error")))
                           self.chat = self.model.start_chat(history=[])
                 else:
                      self.chat = self.model.start_chat(history=[])
            self.api_ready = True
            self.message_queue.put(("STATUS_UPDATE", "Ready."))
            self.message_queue.put(("SET_INPUT_STATE", tk.NORMAL))
        except Exception as e:
            if "API key not valid" in str(e): error_msg_display = "Invalid API Key."
            elif "not found" in str(e).lower() and self.current_model_name in str(e): error_msg_display = f"Model '{self.current_model_name}' not found."
            else: error_msg_display = f"API Error: {type(e).__name__}."
            self.message_queue.put(("STATUS_UPDATE", "API Error!"))
            self.message_queue.put(("DISPLAY_MSG", (error_msg_display, "error")))
            self.api_ready = False
            self.message_queue.put(("SET_INPUT_STATE", tk.DISABLED))

    def display_message(self, message, tag="user", append_newlines=True):
        self.chat_display.configure(state=tk.NORMAL)
        prefix = ""
        if tag == "user": prefix = "You: "
        elif tag == "error": prefix = "Error: "
        elif tag == "info": prefix = "[INFO] "
        self.chat_display.insert(tk.END, f"{prefix}{message}", tag)
        if append_newlines:
             self.chat_display.insert(tk.END, "\n\n" if tag != "info" else "\n")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def display_stream_chunk(self, chunk):
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, chunk, "bot")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def update_status(self, message):
        dirty_indicator = "*" if self.chat_is_dirty else ""
        filename = os.path.basename(self.current_chat_file) if self.current_chat_file else "New Chat"
        self.status_bar.configure(text=f"{filename}{dirty_indicator} | {message}")

    def set_input_state(self, state):
        send_final_state = state if self.send_icon and self.api_ready else tk.DISABLED
        self.input_entry.configure(state=state)
        self.send_button.configure(state=send_final_state)

    def send_message_thread(self, user_message):
        if not self.api_ready or not self.chat:
            self.message_queue.put(("DISPLAY_MSG", ("API not ready.", "error")))
            self.message_queue.put(("SET_INPUT_STATE", tk.NORMAL))
            self.message_queue.put(("STATUS_UPDATE", "API Error!"))
            return

        self.message_queue.put(("SET_INPUT_STATE", tk.DISABLED))
        self.message_queue.put(("STATUS_UPDATE", "Gemini is thinking..."))
        self.message_queue.put(("DISPLAY_MSG", (user_message, "user")))

        try:
            response = self.chat.send_message(
                user_message, stream=True, safety_settings=self.safety_settings
            )
            full_response = ""
            self.message_queue.put(("DISPLAY_BOT_PREFIX", None))
            blocked = False
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                if not chunk.parts and hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback.block_reason:
                    reason = chunk.prompt_feedback.block_reason
                    block_msg = f" [Response blocked: {reason}.]"
                    self.message_queue.put(("STREAM_CHUNK", block_msg))
                    full_response += block_msg
                    blocked = True
                    self.message_queue.put(("STATUS_UPDATE", f"Blocked: {reason}"))
                    continue
                try:
                     chunk_text = chunk.text
                     self.message_queue.put(("STREAM_CHUNK", chunk_text))
                     full_response += chunk_text
                except ValueError: continue
            if chunk_count > 0:
                 self.message_queue.put(("MARK_DIRTY", True))
            self.message_queue.put(("STORE_BOT_RESPONSE", full_response))
        except Exception as e:
            if "API key not valid" in str(e): err_display = "Invalid API Key."
            elif "Quota" in str(e): err_display = "API Quota exceeded."
            elif "timeout" in str(e): err_display = "Request timed out."
            else: err_display = f"{type(e).__name__}."
            self.message_queue.put(("DISPLAY_MSG", (err_display, "error")))
            self.message_queue.put(("STATUS_UPDATE", "Error!"))
            self.message_queue.put(("STORE_BOT_RESPONSE", ""))
        finally:
            self.message_queue.put(("SET_INPUT_STATE", tk.NORMAL))
            current_status_text = self.status_bar.cget("text").split("|")[-1].strip() # Check current status text more directly
            if "Error!" not in current_status_text and not blocked:
                 self.message_queue.put(("STATUS_UPDATE", "Ready."))
            elif not blocked:
                 self.message_queue.put(("STATUS_UPDATE", current_status_text)) # Refresh status to show dirty state


    def send_message(self):
        user_message = self.input_entry.get().strip()
        if not user_message or self.send_button.cget("state") == tk.DISABLED:
            return
        if not self.api_ready:
            self.display_message("API not initialized.", tag="error")
            return
        self.input_entry.delete(0, tk.END)
        threading.Thread(target=self.send_message_thread, args=(user_message,), daemon=True).start()

    def on_enter_pressed(self, event):
        self.send_message()

    def process_message_queue(self):
        try:
            while True:
                message_type, data = self.message_queue.get_nowait()
                if message_type == "DISPLAY_MSG": self.display_message(data[0], data[1], data[2] if len(data)>2 else True)
                elif message_type == "STREAM_CHUNK": self.display_stream_chunk(data)
                elif message_type == "STATUS_UPDATE": self.update_status(data)
                elif message_type == "SET_INPUT_STATE": self.set_input_state(data)
                elif message_type == "PROMPT_API_KEY": self.prompt_for_api_key()
                elif message_type == "DISPLAY_BOT_PREFIX":
                     self.chat_display.configure(state=tk.NORMAL)
                     self.chat_display.insert(tk.END, f"Gemini: ", "bot")
                     self.chat_display.configure(state=tk.DISABLED)
                elif message_type == "STORE_BOT_RESPONSE":
                     self.last_bot_response = data
                     if data and not (data.strip().startswith("[") and data.strip().endswith("]")):
                         self.chat_display.configure(state=tk.NORMAL)
                         self.chat_display.insert(tk.END, "\n\n")
                         self.chat_display.configure(state=tk.DISABLED)
                         self.chat_display.see(tk.END)
                elif message_type == "MARK_DIRTY":
                     self.chat_is_dirty = data
                     self.update_status(self.status_bar.cget("text").split("|")[-1].strip())
                elif message_type == "UPDATE_TITLE":
                      self.title(f"{APP_NAME} ({self.current_model_name})")
        except queue.Empty: pass
        finally: self.after(100, self.process_message_queue)

    def load_chat_list(self):
        for widget in self.chat_list_frame.winfo_children():
            widget.destroy()
        chat_files = get_chat_files()
        if not chat_files:
            no_chats_label = ctk.CTkLabel(self.chat_list_frame, text="No saved chats", text_color="gray", font=self.chatlist_font)
            no_chats_label.grid(row=0, column=0, pady=5, sticky="ew")
            return
        for i, filename in enumerate(chat_files):
            file_path = os.path.join(CHATS_DIR, filename)
            display_name = os.path.splitext(filename)[0].replace('_', ' ')
            chat_item_frame = ctk.CTkFrame(self.chat_list_frame, fg_color="transparent")
            chat_item_frame.grid(row=i, column=0, pady=(0, 2), sticky="ew")
            chat_item_frame.grid_columnconfigure(0, weight=1)
            load_button = ctk.CTkButton(
                chat_item_frame, text=display_name, font=self.chatlist_font, anchor="w",
                fg_color="transparent", hover_color=("#dbdbdb", "#2b2b2b"),
                command=lambda p=file_path: self.load_chat(p)
            )
            load_button.grid(row=0, column=0, padx=(5,0), sticky="ew")
            delete_button = ctk.CTkButton(
                chat_item_frame, text="X", font=self.chatlist_font, width=20, height=20,
                fg_color="transparent", hover_color="#AA0000", text_color=("#D2691E","#CD5C5C"),
                command=lambda p=file_path, w=chat_item_frame: self.delete_chat(p, w)
            )
            delete_button.grid(row=0, column=1, padx=(0,5))

    def prompt_chat_title(self, default=""):
        title = simpledialog.askstring("Save Chat", "Enter a title for this chat:", initialvalue=default, parent=self)
        return title

    def save_current_chat(self):
        if not self.api_ready or not self.chat or not self.chat.history:
             messagebox.showinfo("Cannot Save", "No chat history to save.", parent=self)
             return
        first_user_message = next((msg.parts[0].text for msg in self.chat.history if msg.role == 'user' and msg.parts), None)
        suggested_title = ""
        if first_user_message:
            suggested_title = "".join(c for c in first_user_message[:30] if c.isalnum() or c in (' ', '_')).strip()
        if not suggested_title: suggested_title = f"Chat_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        filename_to_save = os.path.basename(self.current_chat_file) if self.current_chat_file else None
        title_to_use = os.path.splitext(filename_to_save)[0] if filename_to_save else suggested_title
        user_title = self.prompt_chat_title(default=title_to_use)
        if not user_title: return
        safe_filename = "".join(c for c in user_title if c.isalnum() or c in (' ', '_', '-')).strip()
        if not safe_filename: safe_filename = f"Chat_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        safe_filename += ".json"
        file_path = os.path.join(CHATS_DIR, safe_filename)
        if os.path.exists(file_path) and file_path != self.current_chat_file:
             if not messagebox.askyesno("Overwrite?", f"Overwrite '{user_title}'?", parent=self): return
        if save_chat_to_file(self.chat.history, file_path):
            self.current_chat_file = file_path
            self.chat_is_dirty = False
            self.update_status("Chat saved.")
            self.load_chat_list()
        else: self.update_status("Save failed.")

    def _confirm_discard_changes(self):
        if self.chat_is_dirty:
            return messagebox.askyesno("Unsaved Changes", "Discard unsaved changes?", icon='warning', parent=self)
        return True

    def load_chat(self, file_path):
        if not self._confirm_discard_changes(): return
        self.update_status(f"Loading {os.path.basename(file_path)}...")
        loaded_history = load_chat_from_file(file_path)
        if loaded_history is not None:
            self.chat_display.configure(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.configure(state=tk.DISABLED)
            if self.api_ready and self.model:
                try:
                     formatted_history_for_api = []
                     for item in loaded_history:
                         if 'content' in item: formatted_history_for_api.append({'role': item['role'], 'parts': [{'text': item['content']}]})
                         else: formatted_history_for_api.append(item)
                     self.chat = self.model.start_chat(history=formatted_history_for_api)
                except Exception as e:
                     messagebox.showerror("Load Error", f"Could not restart chat session: {e}", parent=self)
                     self.new_chat(confirm_discard=False)
                     return
                self.chat_display.configure(state=tk.NORMAL)
                for msg in self.chat.history:
                     role = getattr(msg, 'role', 'unknown')
                     content = ""
                     try: content = "".join(part.text for part in msg.parts if hasattr(part, 'text'))
                     except AttributeError:
                         if isinstance(msg, dict) and 'content' in msg: content = msg['content']
                         elif isinstance(msg, dict) and 'parts' in msg: content = "".join(part.get('text', '') for part in msg['parts'] if isinstance(part, dict))
                     if content: self.display_message(content, tag=role, append_newlines=True)
                self.chat_display.configure(state=tk.DISABLED)
                self.current_chat_file = file_path
                self.chat_is_dirty = False
                self.update_status("Chat loaded.")
                self.input_entry.focus()
            else:
                self.update_status("API not ready.")
                self.display_message("API not ready. Cannot load context.", tag="error")
        else: self.update_status("Load failed.")

    def delete_chat(self, file_path, item_widget):
        filename = os.path.basename(file_path)
        if messagebox.askyesno("Delete Chat?", f"Delete '{filename}'?", icon='warning', parent=self):
            if delete_chat_file(file_path):
                item_widget.destroy()
                self.update_status(f"Deleted {filename}.")
                if self.current_chat_file == file_path:
                     self.new_chat(confirm_discard=False)
            else: self.update_status("Delete failed.")

    def new_chat(self, confirm_discard=True):
        if confirm_discard and not self._confirm_discard_changes(): return
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        self.last_bot_response = ""
        self.current_chat_file = None
        self.chat_is_dirty = False
        if self.api_ready and self.model:
            try:
                self.chat = self.model.start_chat(history=[])
                self.update_status("New chat started.")
            except Exception as e:
                 self.update_status("Error starting new chat.")
                 self.display_message("Error starting new chat session.", tag="error")
        else: self.update_status("New chat (API not ready).")
        self.input_entry.focus()

if __name__ == "__main__":
    ensure_config_dir()
    ensure_chats_dir()
    app = GeminiChatApp()
    app.mainloop()