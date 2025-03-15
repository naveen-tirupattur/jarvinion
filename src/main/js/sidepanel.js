const sidePanelContent = document.getElementById('emailList');

function updateSidePanelContentWithEmails(emails) {
    sidePanelContent.innerHTML = '';
    emails.forEach(email => {
        const listItem = document.createElement('li');
        listItem.classList.add('email-content');

        const parser = new DOMParser();
        if (!email.body) return;
        const doc = parser.parseFromString(email.body, 'text/html');
        const emailBody = new Readability(doc).parse();
        if (!emailBody.textContent) return;

        // Create a container for the streaming content
        const contentContainer = document.createElement('div');
        contentContainer.classList.add('stream-content');

        // Create loading indicator
        const loadingSpan = document.createElement('span');
        loadingSpan.textContent = 'Summarizing...';
        loadingSpan.classList.add('loading-message');

        listItem.appendChild(loadingSpan);
        listItem.appendChild(contentContainer);
        sidePanelContent.appendChild(listItem);

        fetch('http://0.0.0.0:11434/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: "llama3.2",
                system: "You are a smart assistant who is a combination of Jarvis from Ironman and Kevin from Minions.\
-               Summarize this email in as Kevin and suggest follow up items as Jarvis that might be relevant to me as the recipient.\
                Keep it concise and to the point. Include emojis and relevant links. Be funny but no yapping!",
                prompt: emailBody.textContent,
                stream: true
            })
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                // Remove loading indicator once we start receiving data
                loadingSpan.remove();

                function processStream({ done, value }) {
                    if (done) {
                        if (buffer) {
                            contentContainer.innerHTML += buffer;
                        }
                        return;
                    }

                    // Decode the received chunk and add it to our buffer
                    buffer += decoder.decode(value, { stream: true });
                    let sentence = '';

                    // Process complete lines
                    while (buffer.includes('\n')) {
                        const lineEnd = buffer.indexOf('\n');
                        const line = buffer.slice(0, lineEnd);
                        buffer = buffer.slice(lineEnd + 1);

                        if (line.trim()) {
                            try {
                                const json = JSON.parse(line);
                                if (json.response) {
                                    contentContainer.innerHTML += json.response;
                                }
                            } catch (e) {
                                console.error('Error parsing JSON:', e);
                            }
                        }
                    }

                    // Continue reading
                    return reader.read().then(processStream);
                }

                return reader.read().then(processStream);
            })
            .catch(error => {
                loadingSpan.remove();
                listItem.innerHTML = `<div class="error-message">Error summarizing email: ${error.message}</div>`;
                console.error('Error:', error);
            });
    });
    return Promise.resolve();
}

chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    switch (request.action) {
        case "emailsFetched":
            console.log("Email fetched: ", request.emails);
            updateSidePanelContentWithEmails(request.emails).then(() => {
                sendResponse({ status: "emails updated" });
            });
            break;

        case "clearSidePanel":
            const emailList = document.getElementById('emailList');
            emailList.innerHTML = '';
            sendResponse({ status: "side panel cleared" });
            break;
    }
});

