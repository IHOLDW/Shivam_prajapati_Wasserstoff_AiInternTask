let queryController = null;
let uploadedFiles = new Set();

document.getElementById("fileInput").addEventListener("change", function () {
    document.getElementById("uploadBtn").disabled = this.files.length === 0;
});

const progressBar = document.getElementById("progressBox");
const embedStatus = document.getElementById("embeddingStatus");

function uploadFiles() {
    const files = document.getElementById("fileInput").files;
    if (files.length === 0) return;

    document.getElementById("uploadBtn").disabled = true;
    const allowedExtensions = [".pdf", ".webp", ".jpeg", ".png", ".txt"];
    const formData = new FormData();

    for (let file of files) {
        const ext = file.name.toLowerCase().split('.').pop();
        if (!allowedExtensions.includes("." + ext)) {
            alert(`${file.name} has unsupported file type.`);
            document.getElementById("uploadBtn").disabled = false;
            return;
        }
        if (file.size > 25 * 1024 * 1024) {
            alert(`${file.name} exceeds 25MB limit.`);
            document.getElementById("uploadBtn").disabled = false;
            return;
        }
        formData.append("files[]", file);
    }

    embedStatus.innerHTML = '⏳ Uploading...';

    fetch("/api/upload", {
        method: "POST",
        body: formData
    }).then(() => {
        embedStatus.innerHTML = '⏳ Processing...';
        startPollingStatus();
    }).catch((err) => {
        alert("Upload failed: " + err.message);
        document.getElementById("uploadBtn").disabled = false;
    });
}

function startPollingStatus() {
    const interval = setInterval(() => {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const pct = data.total === 0 ? 0 : Math.floor((data.current / data.total) * 100);
                progressBar.style.width = pct + '%';

                if (data.processing) {
                    embedStatus.innerHTML = `⏳ Processing ${data.current}/${data.total}`;
                    document.getElementById("uploadBtn").disabled = true;
                    document.getElementById("fileInput").disabled = true;
                } else {
                    clearInterval(interval);
                    progressBar.style.width = '100%';
                    embedStatus.innerHTML = data.error ? `❌ Error: ${data.error}` : '✅ Documents processed.';
                    document.getElementById("uploadBtn").disabled = false;
                    document.getElementById("fileInput").disabled = false;
                    document.getElementById("queryInput").disabled = false;
                    document.getElementById("queryBtn").disabled = false;

                    if (data.error) {
                        alert("Error while processing documents:\n" + data.error);
                    }

                    // ✅ Fetch and update file list
                    uploadedFiles.clear();
                    fetch('/api/data')
                        .then(res => res.json())
                        .then(data => {
                            for (let file of data.files) {
                                uploadedFiles.add(file);
                            }
                            renderFileList();
                        });
                }
            })
            .catch(err => {
                clearInterval(interval);
                alert("Failed to poll status: " + err.message);
                embedStatus.innerHTML = "❌ Error checking status.";
            });
    }, 1000);
}

function renderFileList() {
    const container = document.getElementById("fileListContainer");
    container.innerHTML = "";
    uploadedFiles.forEach(fname => {
        const li = document.createElement("li");
        li.innerHTML = `
            <label>
                <input type="checkbox" checked data-fname="${fname}">
                ${fname}
            </label>`;
        container.appendChild(li);
    });
}


function updateFiles() {
    const checkboxes = document.querySelectorAll("#fileListContainer input[type='checkbox']");
    const filesToDelete = [];

    checkboxes.forEach(cb => {
        const fname = cb.getAttribute("data-fname");
        if (!cb.checked) {
            filesToDelete.push(fname);
            uploadedFiles.delete(fname);
        }
    });

    if (filesToDelete.length === 0) return alert("No files selected for removal.");

    fetch('/api/modify_learning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: filesToDelete })
    }).then(res => res.json())
      .then(data => {
          alert(data.message || 'Files updated.');
          renderFileList();
      });
}


function clearFolder() {
    fetch('/api/clear', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            embedStatus.innerHTML = '';
            progressBar.style.width = '0%';
            uploadedFiles.clear();
            renderFileList();
        });
}

function renderSources(fileNames = [], pageNumbers = []) {
    const panel = document.getElementById("sourcesPanel");
    if (!fileNames.length) {
        panel.innerHTML = '';
        return;
    }

    const sources = fileNames.map((fname, i) => {
        const page = pageNumbers[i] !== undefined ? ` — Page ${pageNumbers[i]}` : '';
        return `<li><strong>${fname}</strong>${page}</li>`;
    });

    panel.innerHTML = `
        <h4>📚 Sources</h4>
        <ul>${sources.join('')}</ul>
    `;
}

function sendQuery() {
    const query = document.getElementById("queryInput").value.trim();
    if (!query) return;

    const chatBox = document.getElementById("chatOutput");

    // User message
    chatBox.innerHTML += `
        <div class="message user-message">
            <div class="bubble">${escapeHtml(query)}</div>
        </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    // Bot is thinking
    const loader = document.createElement("div");
    loader.className = "message bot-message";
    loader.innerHTML = `<div class="bubble"><em>Thinking...</em></div>`;
    chatBox.appendChild(loader);
    chatBox.scrollTop = chatBox.scrollHeight;

    document.getElementById("queryBtn").disabled = true;
    document.getElementById("cancelQueryBtn").style.display = "inline";

    queryController = new AbortController();

    fetch("/api/query", {
        method: "POST",
        body: new URLSearchParams({ query }),
        signal: queryController.signal,
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
        .then(res => res.json())
        .then(data => {
            loader.innerHTML = `<div class="bubble">${formatBotReply(data.answer)}</div>`;
            renderSources(data.file_name, data.page_number);
        })
        .catch(() => {
            loader.innerHTML = `<div class="bubble"><strong>Bot:</strong> Query was cancelled.</div>`;
        })
        .finally(() => {
            document.getElementById("queryBtn").disabled = false;
            document.getElementById("cancelQueryBtn").style.display = "none";
        });
}

function cancelQuery() {
    if (queryController) queryController.abort();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

function formatBotReply(text) {
    return escapeHtml(text)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
        .replace(/\*(.*?)\*/g, "<li>$1</li>")             // List item
        .replace(/\n/g, "<br>");                          // Line breaks
}


