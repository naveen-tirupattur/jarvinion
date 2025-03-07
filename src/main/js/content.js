console.log('Jarvinion content script loaded');

window.onload = function () {
    console.log('Window onload triggered');
    let jarvinionIcon = document.createElement('img');
    jarvinionIcon.src = chrome.runtime.getURL('images/icons-200.png');
    jarvinionIcon.style.padding = '15px';
    jarvinionIcon.title = 'Banana!';
    jarvinionIcon.classList.add('jarvinion-icon');

    // Find the element where we want to inject the button
    let inboxToolsBar = document.querySelector('div.ajl.aib.aZ6');
    if (inboxToolsBar) {
        inboxToolsBar.appendChild(jarvinionIcon);
        console.log("Button was successfully inserted.");
    } else {
        console.log('Inbox tools could not be found.');
    }

    // Function to get selected message ids
    function getSelectedEmailMessageIds() {
        const selectedEmails = document.querySelectorAll('tr.zA.yO.x7');
        const gmailApiIds = [];
        selectedEmails.forEach(emailRow => {

            // Get the thread id from the data-thread-id attribute
            const threadIdElement = emailRow.querySelector('[data-legacy-thread-id]');
            if (threadIdElement) {
                const threadId = threadIdElement.getAttribute('data-legacy-thread-id');
                // if thread id exists, extract messageId
                if (threadId) {
                    const messageId = threadId.split(':').pop();
                    gmailApiIds.push(messageId)
                }
            }
        });
        return gmailApiIds;
    }


    let lastMessageIds = [];

    function sendMessage(messageIds) {
        if (!messageIds || messageIds.length === 0) return;
        if (JSON.stringify(lastMessageIds) == JSON.stringify(messageIds)) return;
        lastMessageIds = messageIds;
        console.log("Sending message ids to background: ", messageIds);
        chrome.runtime.sendMessage({ action: "fetchEmails", messageIds: messageIds }, function (response) {
            if (response && response.status === "fetching selected emails") {
                console.log(response.status);
            }
        });
    }

    function handleSelectionChanges() {
        const selectedMessages = getSelectedEmailMessageIds();
        if (selectedMessages.length === 0) {
            chrome.runtime.sendMessage({ action: 'clearSidePanel' }, function (response) {
                if (response && response.status == "side panel cleared") {
                    console.log(response.status);
                }
            });
        } else {
            sendMessage(selectedMessages);
        }
    }

    // Initial check
    handleSelectionChanges();

    // Observe the changes on the inbox
    let inboxContainer = document.querySelector('div[role="main"]');
    if (inboxContainer) {
        let observer = new MutationObserver(handleSelectionChanges);
        observer.observe(inboxContainer, {
            childList: true,
            subtree: true,
            attributes: true
        });
    }


    // Add event listener to the icon
    jarvinionIcon.addEventListener('click', () => {
        handleSelectionChanges();
        chrome.runtime.sendMessage({ action: 'openSidePanel' }, function (response) {
            if (response && response.status == "side panel opened") {
                console.log(response.status);
            }
        });
        // const messageId = document.querySelector('[data-message-id]').getAttribute('data-legacy-message-id')
        // console.log("Selected message: ", messageId);
        // // Sends message to background script, and waits for reply
        // chrome.runtime.sendMessage({ action: "processEmail", messageId: messageId }, function (response) {
        //     if (response && response.status == "processing email") {
        //         console.log("Processing email...")
        //     }
        // });
    });

    // Style the icon
    let style = document.createElement('style');
    style.innerHTML = `
    .jarvinion-icon {
      height: 24px; /* Adjust as needed */
      width: 24px;
      title: 'Jarvinion';
      margin-left: 10px; /* Adjust as needed */
      margin-right: 10px; /* Adjust as needed */
      vertical-align: middle;
      cursor: pointer;
    }
  `;
    document.head.appendChild(style);
};
