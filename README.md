# Gemini Chat GUI 
A desktop application built with Python and CustomTkinter providing a user-friendly interface to interact with Google's Gemini AI models (like `gemini-1.5-flash` and `gemini-pro`). Features chat history management, streaming responses, and basic settings configuration.

![AI Chatbot GIF]([https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGhxbTdhajE0ZWlsb2x1NG5sM2N4ZzBkN2R2bnR4c3d4eXp4MnQzcyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/SSju4C1V5yN4A/giphy.gif))

---

## Features

*   **Modern UI:** Clean and responsive interface using CustomTkinter.
*   **Gemini Integration:** Connects directly to the Google Gemini API (`google-generativeai`).
*   **Streaming Responses:** See the AI's response appear token-by-token in real-time.
*   **Collapsible Sidebar:** Toggle the sidebar visibility for more chat space.
*   **Chat History Management:**
    * **Save:** Save your current conversation locally.
    * **Load:** Load previous chat sessions from the sidebar list.
    * **Delete:** Remove saved chats (with confirmation).
    * **Unsaved Indicator:** Status bar shows if the current chat has unsaved changes (`*`).
*   **Settings Panel:**
    *    View and update your Gemini API Key.
    *    Select the Gemini model to use (`gemini-1.5-flash`, `gemini-pro`).
    *    Choose Appearance Mode (Light/Dark/System).
    *    Select Color Theme (blue, green, dark-blue).
*   **API Key Management:** Prompts for API key on first run and stores it securely in a config file.
*   **Asynchronous API Calls:** GUI remains responsive while waiting for AI responses.
*   **Basic Error Handling:** Displays common API and file operation errors.
*   **Enter-to-Send:** Conveniently send messages by pressing Enter.
*   **Auto-Scrolling:** Chat window automatically scrolls to the latest message.

---

## Getting Started

### Prerequisites

*   **Python:** Version 3.8 or higher recommended.
*   **pip:** Python package installer.
*   **Google Gemini API Key:** Obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Installation

1.  **Clone the repository (or download the script):**
2.  **(Recommended) Create and activate a virtual environment:**
    ```bash
    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Windows (cmd)
    python -m venv venv
    venv\Scripts\activate.bat

    # Windows (PowerShell)
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
3.  **Install required libraries:**
    ```bash
    pip install customtkinter google-generativeai Pillow
    ```

---

##  Configuration

*   **API Key:** The first time you run the application, it will prompt you to enter your Google Gemini API Key if it's not found in the configuration file.
*   **Configuration File:** The API key and settings are stored in:
    *   `~/.config/gemini_chat_gui/config.ini` (Linux/macOS)
    *   `%USERPROFILE%/.config/gemini_chat_gui/config.ini` (Windows - path might vary slightly)
*   **Settings Panel:** You can view/edit the API key and other settings via the "Settings" button in the sidebar.

---

##  Usage

1.  **Run the application:**
    ```bash
    python gemini_pro_gui.py
    ```
    (Replace `gemini_pro_gui.py` with your script's filename).
---

## File Structure

The application stores its data in your user's configuration directory:

*   **Configuration (`config.ini`):** Stores API key and application settings.
    *   *Path:* `~/.config/gemini_chat_gui/config.ini`
*   **Saved Chats (`chats/`):** Contains individual chat history files saved as `.json`.
    *   *Path:* `~/.config/gemini_chat_gui/chats/`

---

## Future Ideas

*   More advanced AI settings (temperature, top_p, safety levels).
*   Copy-to-clipboard button for bot responses.
*   Search within chat history.
*   Export chats to different formats (e.g., Markdown).
*   Add custom system prompts/personas.
*   Replace placeholder icons with custom ones.

---

## License

available for anyone. no commercial use
