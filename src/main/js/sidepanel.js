const sidePanelContent = document.getElementById('emailList');

function updateSidePanelContentWithEmails(emails) {
    sidePanelContent.innerHTML = '';
    emails.forEach(email => {
        const listItem = document.createElement('li');
        listItem.classList.add('email-content'); // Add the class here

        const parser = new DOMParser();
        if (!email.body) return;
        const doc = parser.parseFromString(email.body, 'text/html');
        const emailBody = new Readability(doc).parse();
        if (!emailBody.textContent) return;
        console.log(emailBody.textContent);

        // Create a span element for the loading indicator
        const loadingSpan = document.createElement('span');
        loadingSpan.textContent = 'Summarizing...';
        loadingSpan.classList.add('loading-message'); // Add the class for loading message
        listItem.appendChild(loadingSpan);
        sidePanelContent.appendChild(listItem);

        fetch('http://0.0.0.0:11434/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: "llama3.2",
                system: "You are a smart assistant who is a combination of Jarvis from Ironman and Kevin from Minions.\
                Summarize this email as Kevin and suggest follow up items as Jarvis that might be relevant to me as the recipient.\
                Keep it concise and to the point. Be sure to extract links and other relevant info. Be funny but no yapping!",
                prompt: emailBody.textContent,
                stream: false
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                loadingSpan.remove();
                const html = marked.parse(data.response);
                listItem.innerHTML = html;
            })
            .catch(error => {
                loadingSpan.remove();
                listItem.innerHTML = 'Error summarizing email. Try again later!';
                console.error('Error:', error);
            });
        sidePanelContent.appendChild(listItem);
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

