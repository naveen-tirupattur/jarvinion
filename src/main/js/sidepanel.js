// const signInButton = document.getElementById("signInButton");
// const signOutButton = document.getElementById("signOutButton");
const statusMessage = document.getElementById("statusMessage")
const summarizeButton = document.getElementById("summarizeButton")

// Helper function to update UI based on auth state
function updateUI(isAuthenticated) {
    if (isAuthenticated) {
        statusMessage.textContent = 'Authenticated!';
        // signInButton.style.display = "none";
        // signOutButton.style.display = "block";
    } else {
        statusMessage.textContent = 'Not Authenticated!';
        // signInButton.style.display = "block";
        // signOutButton.style.display = "none";
    }
}

function updateEmailList(emails) {
    const emailList = document.getElementById('emailList');
    emailList.innerHTML = '';
    emails.forEach(email => {
        const listItem = document.createElement('li');
        const parser = new DOMParser();
        const doc = parser.parseFromString(email.body, 'text/html');
        const article = new Readability(doc).parse();
        console.log(article.textContent);
        listItem.textContent = article.textContent;
        emailList.appendChild(listItem);
    });
    return Promise.resolve();
}

async function checkAuthState() {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ action: "getAuthState" }, function (response) {
            if (response && response.isAuthenticated) {
                resolve(true);
            } else {
                resolve(false)
            }
        });
    })
}
// Check authentication status on popup load
checkAuthState().then((isAuthenticated) => {
    updateUI(isAuthenticated)
})


// signInButton.addEventListener("click", () => {
//     chrome.runtime.sendMessage({ action: "authenticate" }, function (response) {
//         if (response && response.isAuthenticated) {
//             checkAuthState().then((isAuthenticated) => {
//                 updateUI(isAuthenticated)
//             })
//         } else {
//             statusMessage.textContent = 'Authentication failed!'
//         }
//     });
// });

// signOutButton.addEventListener("click", () => {
//     chrome.runtime.sendMessage({ action: "signout" }, function (response) {
//         if (response && response.status == "signedOut") {
//             checkAuthState().then((isAuthenticated) => {
//                 updateUI(isAuthenticated)
//             })
//         } else {
//             statusMessage.textContent = 'Could not sign out'
//         }
//     });
// });

summarizeButton.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "summarize" }, function (response) {
        if (response && response.status == "summaryGenerated") {
            updateUI(response.summary)
        } else {
            statusMessage.textContent = 'Could not generate summary'
        }
    });
});

chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    switch (request.action) {
        case "emailFetched":
            console.log("Emails fetched: ", request.emails);
            updateEmailList(request.emails).then(() => {
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

