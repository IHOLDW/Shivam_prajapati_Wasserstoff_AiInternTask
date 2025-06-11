let cancel_query = null;
let upload_files = new Set();

document.getElementById("fileInput").addEventListener("change", function () {
    document.getElementById("uploadBtn").disabled = this.files.length === 0;
});

const progressBar = document.getElementById("progressBox");
const embedStatus = document.getElementById("embeddingStatus");

function uploadFiles() {
    const files = document.getElementById("fileInput").files;
    if (files.length === 0) return;

    document.getElementById("uploadBtn").disabled = true;
    const allowedExtensions = [".pdf", ".webp", ".jpeg", ".png", ".txt", ".jpg"];
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

    embedStatus.innerHTML = ' Uploading...';

    fetch("/api/upload", {
        method: "POST",
        body: formData
    }).then(() => {
        embedStatus.innerHTML = ' Processing...';
        progress_staus();
    }).catch((err) => {
        alert("Upload failed: " + err.message);
        document.getElementById("uploadBtn").disabled = false;
    });
}

// causing problem in multithreading maybe increse the time interval
// used to check live progress of files being processes
function progress_staus() {
    const interval = setInterval(() => {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const pct = data.total === 0 ? 0 : Math.floor((data.current / data.total) * 100);
                progressBar.style.width = pct + '%';

                if (data.processing) {
                    embedStatus.innerHTML = ` Processing ${data.current}/${data.total}`;
                    document.getElementById("uploadBtn").disabled = true;
                    document.getElementById("fileInput").disabled = true;
                } else {
                    clearInterval(interval);
                    progressBar.style.width = '100%';
                    embedStatus.innerHTML = data.error ? ` Error: ${data.error}` : '✅ Documents processed.';
                    document.getElementById("uploadBtn").disabled = false;
                    document.getElementById("fileInput").disabled = false;
                    document.getElementById("queryInput").disabled = false;
                    document.getElementById("queryBtn").disabled = false;

                    if (data.error) {
                        alert("Error while processing documents:\n" + data.error);
                    }

                    upload_files.clear();
                    fetch('/api/data')
                        .then(res => res.json())
                        .then(data => {
                            for (let file of data.files) {
                                upload_files.add(file);
                            }
                            show_files();
                        });
                }
            })
            .catch(err => {
                clearInterval(interval);
                alert("Failed to poll status: " + err.message);
                embedStatus.innerHTML = "Error checking status.";
            });
    }, 5000);
}

function source_area(response) {
    const sourcesPanel = document.getElementById('sourcesPanel');
    const files = response.file_name || [];
    const pages = response.page_number || [];

    if (!files.length) {
        sourcesPanel.innerHTML = "";
        return;
    }

    sourcesPanel.innerHTML = "<strong> Sources:</strong><ul>";

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const page = pages[i];
        const ext = file.split('.').pop().toLowerCase();
        let link = `/uploads/${file}`;

        if (ext === "pdf" && page) {
            link += `#page=${page}`;
        }

        sourcesPanel.innerHTML += `
            <li>
                <a href="${link}" target="_blank">
                    ${file}${page ? ` (Page ${page})` : ""}
                </a>
            </li>
        `;
    }

    sourcesPanel.innerHTML += "</ul>";
}

function show_files() {
    const container = document.getElementById("fileListContainer");
    container.innerHTML = "";
    upload_files.forEach(fname => {
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
            upload_files.delete(fname);
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
          show_files();
      });
}

function clearFolder() {
    fetch('/api/clear', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            embedStatus.innerHTML = '';
            progressBar.style.width = '0%';
            upload_files.clear();
            show_files();
        });
}

function sendQuery() {
    const query = document.getElementById("queryInput").value.trim();
    if (!query) return;

    const chatBox = document.getElementById("chatOutput");
    chatBox.innerHTML += `
        <div class="message user-message">
            <div class="bubble">${escapeHtml(query)}</div>
        </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    const loader = document.createElement("div");
    loader.className = "message bot-message";
    loader.innerHTML = `<div class="bubble"><em>Thinking...</em></div>`;
    chatBox.appendChild(loader);
    chatBox.scrollTop = chatBox.scrollHeight;

    document.getElementById("queryBtn").disabled = true;
    document.getElementById("cancelQueryBtn").style.display = "inline";
    cancel_query = new AbortController();

    fetch("/api/query", {
        method: "POST",
        body: new URLSearchParams({ query }),
        signal: cancel_query.signal,
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
        .then(res => res.json())
        .then(data => {
            if(data.success){
                loader.innerHTML = `<div class="bubble">${formatBotReply(data.answer)}</div>`;
                source_area(data);
            }else{
                loader.innerHTML = `<div class="bubble">${formatBotReply("error")}</div>`
                alert(data.error)
            }
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
    if (cancel_query) cancel_query.abort();
}

//remove this, if using it local machine
function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

function formatBotReply(text) {
    return escapeHtml(text)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<li>$1</li>")
        .replace(/\n/g, "<br>");
}
