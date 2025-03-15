
# Jarvinion - Your Sophisticated-Yet-Goofy Email Assistant for Gmail

## Description

Jarvinion is a Chrome extension that helps you manage your Gmail inbox more efficiently by providing intelligent summaries and highlighting key concepts in your emails. Inspired by both Jarvis from Iron Man and the Minions, Jarvinion combines cutting-edge AI with a touch of humor to make email management less of a chore.

## Features

- 🤖 Smart summarization of lengthy emails and threads, extracting key information
- 📋 Displays summaries and contextual suggestions in a convenient side panel within Gmail.
- 🎭 Playful interface combining Jarvis and Kevin's personalities
- ⚡ Real-time processing with streaming responses
- 🔄 Seamless Gmail integration
- 🔒 Securely connects to your Gmail account using Google's OAuth 2.0 protocol.
- ✉️ Detects when you select an email and retrieves its metadata automatically.
- 🏠 Uses local language models via Ollama for enhanced privacy and performance. This ensures that your data stays on your machine.


## Installation

```zsh

# Clone the repository
git clone https://github.com/yourusername/jarvinion.git
cd jarvinion

```

1.  Open Chrome and navigate to `chrome://extensions`.
2.  Enable "Developer mode" in the top right corner.
3.  Click "Load unpacked" and select the directory where you extracted the extension files.

### Ollama Setup

* Requires [Ollama](https://ollama.com/download) to be installed and running locally.
* Ensure the Llama3 model is installed with command ```ollama pull llama3```
* You may need to change the system prompt in javascript to align with another model.
* Start ollama server ```OLLAMA_ORIGINS=chrome-extension://* ollama serve``` to bypass CORS policy

### Google Cloud Project Setup (Required for Authentication)

Before using Jarvinion, you need to set up a Google Cloud project and configure OAuth 2.0 credentials.

1.  **Create a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Click on the project dropdown at the top and select "New Project".
    *   Enter a project name and click "Create".

2.  **Enable the Gmail API:**
    *   In your Google Cloud project, navigate to "APIs & Services" > "Library".
    *   Search for "Gmail API" and click on it.
    *   Click "Enable".

3.  **Configure OAuth 2.0 Credentials:**
    *   Navigate to "APIs & Services" > "Credentials".
    *   Click "+ Create Credentials" and select "OAuth client ID".

      ![image](https://github.com/user-attachments/assets/12f55ad8-546a-44bc-8578-d81261bd3719)

    *   If you haven't configured the OAuth consent screen, you'll be prompted to do so:
        *   Click "Configure consent screen".
        *   Select "External" as the user type (unless you're only using this for users within your Google Workspace organization).
        *   Fill in the required information (App name, User support email, Developer contact information).
        *   Add the following scopes:
            * `https://www.googleapis.com/auth/gmail.readonly`
            *   `https://www.googleapis.com/auth/userinfo.profile`
        *   Save the consent screen configuration.
    *   Now, create the OAuth client ID:
        *   Select "Chrome Application" as the application type.
        *   Enter a name for your OAuth client.
        *   Click "Create".
          
          ![image](https://github.com/user-attachments/assets/ffcd9aef-f540-42a6-bef8-996de21cca3a)

    *   Note down the **Client ID**. You'll need this in the next steps.

4.  **Update `manifest.json`:**
    *   Open the `manifest.json` file in your Jarvinion extension directory.
    *   Replace `"YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"` with your actual Google Client ID.

```json
   "oauth2": {
        "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
        "scopes":[
           "https://www.googleapis.com/auth/gmail.readonly",
           "https://www.googleapis.com/auth/userinfo.profile"
        ]
    }
 ```

## Configuration

1.  After installation, open Gmail. You should see the Jarvinion icon in the toolbar.
2.  If you haven't already, click the "Authenticate" button in the extension's side panel to grant Jarvinion access to your Gmail account.
3.  Once authenticated, you can select an email to view its summary and key information in the side panel.

## Usage

1.  Open your Gmail inbox.
2.  Select one or more emails using the checkboxes in the inbox.
3.  The side panel will dynamically update with the data related to the email(s) that you have just selected.
4.  Click the Jarvinion icon to process the current email.


## Technical Details

*   **Manifest Version:** 3
*   **OAuth 2.0:** Uses `chrome.identity` API for secure authentication.
*   **Communication:** Uses `chrome.runtime.sendMessage` for communication between content scripts and background script.
*   **DOM Manipulation:** Uses `content.js` to inject elements and interact with the Gmail interface.

## Permissions

The extension requires the following permissions:

*   `identity`: To access Google's OAuth 2.0 service for authentication.
*   `storage`: To store extension settings and data.
*   `scripting`: To inject content scripts into web pages.
*   `activeTab`: To access the currently active tab.
*   `https://mail.google.com/*`: To access Gmail data and inject the content script.

## Known Issues

*  Gmail's DOM structure can change, potentially breaking the content script. We will try to keep up with any issues that might arise.
*  Rate limiting with the Gmail API can cause the app to stop working.
*  Lack of support for large emails (context window is 2048 tokens)

## Contributing

Contributions are welcome! Please feel free to submit bug reports, feature requests, or pull requests.

## License

This project is licensed under the GNU General Public License v3.0.

## Credits

*   This extension was inspired by the desire to make email management more efficient and enjoyable.
