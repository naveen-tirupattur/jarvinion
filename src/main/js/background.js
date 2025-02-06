let isAuthenticated = false;

// Function to initiate authentication flow
async function authenticate() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ 'interactive': true }, function (token) {
      if (chrome.runtime.lastError) {
        console.log('Error getting auth token: ', chrome.runtime.lastError.message);
        reject(chrome.runtime.lastError.message);
        chrome.storage.local.remove("isAuthenticated", () => {
          // Resolve with the current status
          resolve({ isAuthenticated: false, status: "error", error: chrome.runtime.lastError.message });
        });
        chrome.storage.local.remove("token");
      } else {
        isAuthenticated = true;
        chrome.storage.local.set({ isAuthenticated: true, "token": token }, () => {
          console.log("Auth token acquired: " + token);
          // Resolve with the current status after storage is set
          resolve({ isAuthenticated: true, status: "authenticated", token: token });
        });
      }
    });
  });
}

// Function to sign out
async function signOut() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ 'interactive': false }, function (token) {
      if (token) {
        chrome.identity.removeCachedAuthToken({ token: token }, function () {
          console.log('Token removed. Signed out.');
          isAuthenticated = false
          chrome.storage.local.remove("isAuthenticated", () => {
            // Resolve only after remove is done
            resolve({ isAuthenticated: false, status: "signedOut" });
          });
        });
      } else {
        console.log('No token found. Already signed out.');
        isAuthenticated = false
        chrome.storage.local.remove("token");
        chrome.storage.local.remove("isAuthenticated", () => {
          // Resolve only after remove is done
          resolve({ isAuthenticated: false, status: "signedOut" });
        });
      }
    })
  });
}

// Function to periodically expire the token
function tokenExpirationCheck() {
  setInterval(async () => {
    console.log("Checking token state.")
    if (isAuthenticated) {
      chrome.identity.getAuthToken({ 'interactive': false }, function (token) {
        if (token) {
          console.log("Token is still valid.");
        } else {
          console.log("Token has expired, user needs to sign in.");
          isAuthenticated = false
          chrome.storage.local.remove('isAuthenticated');
        }

      })
    } else {
      console.log("Not authenticated.")
    }
  }, 600000) // Check every 10 minutes
}

// Listener for extension startup
chrome.runtime.onStartup.addListener(async () => {
  console.log('Extension started');
  const data = await chrome.storage.local.get(['isAuthenticated']);
  if (data && data.isAuthenticated) {
    isAuthenticated = true
  }
  console.log('Authenticated from startup:', isAuthenticated);
  tokenExpirationCheck()
});

// Listener for when the extension is installed
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Extension installed.');
  const data = await chrome.storage.local.get(['isAuthenticated']);
  if (data && data.isAuthenticated) {
    isAuthenticated = true
  }
  console.log('Authenticated from install:', isAuthenticated);
  tokenExpirationCheck()
});


chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
  if (request.action == "fetchEmails") {
    fetchEmailsAndThreads(request.messageIds)
    sendResponse({ status: "fetching selected emails" });
    // } else if (request.action == "authenticate") {
    //   authenticate().then((response) => {
    //     sendResponse(response);
    //   });
    //   return true;
    // } else if (request.action == "signout") {
    //   signOut().then((response) => {
    //     sendResponse(response);
    //   });
    //   return true;
  } else if (request.action == "getAuthState") {
    sendResponse({ isAuthenticated: isAuthenticated })
  } else if (request.action == "openSidePanel") {
    console.log(sender.tab.id);
    openSidePanel(sender).then((response) => {
      sendResponse({ status: "side panel opened" });
    });
  }
});

// Function to open the side panel
async function openSidePanel(sender) {
  try {
    // This will open a tab-specific side panel only on the current tab.
    chrome.sidePanel.setOptions({
      tabId: sender.tab.id,
      path: "src/main/ui/sidepanel.html",
      enabled: true
    });
    await chrome.sidePanel.open({ tabId: sender.tab.id });
  } catch (error) {
    console.error('Error opening side panel:', error);
  }
}

async function fetchEmailsAndThreads(messageIds) {
  if (!messageIds || messageIds.length === 0) {
    console.log("No emails selected.");
    return;
  }

  const fetchedEmails = []; // Use a proper array
  const fetchPromises = messageIds.map(async (messageId) => {
    try {
      console.log("processing message id: ", messageId);
      const message = await fetchEmail(messageId);
      if (message) {
        console.log('Message: ', message);
        if (message.threadId) {
          const threadMessages = await fetchThreadMessages(message.threadId);
          if (threadMessages) {
            console.log("Thread: ", threadMessages);
            threadMessages.forEach(threadMessage => {
              if (message.id != threadMessage.id && threadMessage.body) {
                message.body += "\n\n" + threadMessage.body;
              }
            });
          }
        }
        fetchedEmails.push(message);
      } else {
        console.log("No data for message id: ", messageId);
      }
    } catch (error) {
      console.error('Error processing email:', messageId, error);
    }
  });

  await Promise.all(fetchPromises); // Wait for all to complete

  console.log('Sending emails to side panel: ', fetchedEmails);

  chrome.runtime.sendMessage({ action: "emailFetched", emails: fetchedEmails }, function (response) {
    if (response && response.status == "emails updated") {
      console.log("emails updated");
    }
  });
}

// Function to fetch emails using the Gmail API
async function fetchEmail(messageId) {
  const authResponse = await authenticate()
  if (!authResponse.isAuthenticated) {
    console.log('Could not authenticate.')
    return;
  }
  console.log('Auth Response:', authResponse);
  const url = `https://gmail.googleapis.com/gmail/v1/users/me/messages/${messageId}?format=full&alt=json`;
  console.log('Fetching emails from: ', url);
  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${authResponse.token}`,
      },
    });
    console.log('Response: ', response);
    if (!response.ok) {
      console.log('Error fetching messages: ', response.statusText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    const processedData = await processEmailContent(data);
    return processedData
  } catch (error) {
    console.error('Error getting emails: ', error);
    return null;
  }
}

async function fetchThreadMessages(threadId) {
  if (!isAuthenticated) {
    console.log("User not authenticated");
    return;
  }
  const authResponse = await authenticate()
  if (!authResponse.isAuthenticated) {
    console.log('Could not authenticate.')
    return;
  }
  console.log('Auth Response:', authResponse);
  const url = `https://gmail.googleapis.com/gmail/v1/users/me/threads/${threadId}?format=full`;
  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${authResponse.token}`,
      },
    });
    console.log('Response: ', response);
    if (!response.ok) {
      console.log("Error fetching thread: ", response.statusText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    const processedData = await processThreadContent(data);
    return processedData;
  } catch (error) {
    console.error("Error getting thread: ", error);
    return null
  }
}

async function processThreadContent(thread) {
  if (!thread || !thread.messages) {
    console.log("No messages found on thread.");
    return null;
  }
  const processedMessages = [];
  for (const message of thread.messages) {
    const processedMessage = await processEmailContent(message)
    processedMessages.push(processedMessage);
  }
  return processedMessages;
}

async function processEmailContent(message) {
  if (!message) {
    console.log("No message found to process.");
    return null;
  }
  let body = "";
  if (message.payload) {
    if (message.payload.body && message.payload.body.data) {
      body = atob(message.payload.body.data.replace(/-/g, '+').replace(/_/g, '/'));
    } else if (message.payload.parts) {
      for (const part of message.payload.parts) {
        if (part.mimeType == 'text/plain' && part.body && part.body.data) {
          body = atob(part.body.data.replace(/-/g, '+').replace(/_/g, '/'));
          break;
        } else if (part.mimeType == 'text/html' && part.body && part.body.data) {
          body = atob(part.body.data.replace(/-/g, '+').replace(/_/g, '/'));
          break;
        }
      }
    }
  }
  return { ...message, body: body };
}