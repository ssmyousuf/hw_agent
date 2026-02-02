const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const uploadStatus = document.getElementById('upload-status');
const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const filePreview = document.getElementById('file-preview');
const statsSection = document.getElementById('stats-section');
const statsGrid = document.getElementById('stats-grid');

// State
let uploadedFiles = [];
let currentStats = null;

// File Upload Logic
browseBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

async function handleFiles(files) {
    if (files.length === 0) return;

    // Validate all files
    for (let file of files) {
        const lowerName = file.name.toLowerCase();
        if (!(lowerName.endsWith('.csv') || lowerName.endsWith('.pdf'))) {
            uploadStatus.innerText = `❌ Invalid file: "${file.name}". Only .csv and .pdf allowed.`;
            uploadStatus.style.color = "red";
            return;
        }
    }

    const formData = new FormData();
    uploadedFiles = Array.from(files);

    for (let file of files) {
        formData.append('files', file);
    }

    const password = document.getElementById('pdf-password').value;
    if (password) {
        formData.append('password', password);
    }

    uploadStatus.innerText = "Uploading...";
    uploadStatus.style.color = "#4ade80";

    try {
        const res = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            uploadStatus.innerText = `✅ ${data.message}`;
            updateFilePreview(uploadedFiles, data.rows);
            updateStats(data);
            enableChat();
        } else {
            uploadStatus.innerText = `❌ Error: ${data.detail}`;
            uploadStatus.style.color = "red";
        }
    } catch (e) {
        uploadStatus.innerText = `❌ Upload failed: ${e.message}`;
        uploadStatus.style.color = "red";
    }
}

function updateFilePreview(files, totalRows) {
    filePreview.innerHTML = '';
    const rowsPerFile = Math.floor(totalRows / files.length);

    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <span class="file-icon">${file.name.endsWith('.pdf') ? '📄' : '📊'}</span>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">~${rowsPerFile} transactions</div>
                </div>
            </div>
            <button class="delete-btn" onclick="removeFile(${index})">🗑️</button>
        `;
        filePreview.appendChild(fileItem);
    });
}

function updateStats(data) {
    currentStats = data;
    statsSection.style.display = 'block';
    statsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.rows}</div>
            <div class="stat-label">Transactions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${uploadedFiles.length}</div>
            <div class="stat-label">Files</div>
        </div>
    `;
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    if (uploadedFiles.length === 0) {
        filePreview.innerHTML = '';
        statsSection.style.display = 'none';
        disableChat();
        // Notify user that they need to re-upload
        uploadStatus.innerText = '🔄 Files cleared. Upload new statements to continue.';
        uploadStatus.style.color = '#fbbf24';
    } else {
        updateFilePreview(uploadedFiles, currentStats.rows);
        // Note: Server still has the combined data until new upload
        uploadStatus.innerText = `ℹ️ Removed locally. Server data unchanged until re-upload.`;
        uploadStatus.style.color = '#60a5fa';
    }
}

function enableChat() {
    userInput.disabled = false;
    sendBtn.disabled = false;
    appendMessage('ai', "✨ I've analyzed your statement. What would you like to know?");
}

function disableChat() {
    userInput.disabled = true;
    sendBtn.disabled = true;
}

// Chat Logic
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Quick Actions
document.querySelectorAll('.action-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        userInput.value = query;
        sendMessage();
    });
});

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage('user', text);
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();

        removeTypingIndicator(typingId);

        if (res.ok) {
            appendMessage('ai', data.response);
            if (data.debug_logs) {
                renderDebugLogs(data.debug_logs);
            }
        } else {
            appendMessage('system', `❌ Error: ${data.detail}`);
        }
    } catch (e) {
        removeTypingIndicator(typingId);
        appendMessage('system', `❌ Connection error: ${e.message}`);
    }

    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
}

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Parse Markdown images: ![alt](url)
    const imgRegex = /!\[(.*?)\]\((.*?)\)/g;
    const htmlWithImages = text.replace(imgRegex, '<img src="$2" alt="$1" style="max-width: 100%; border-radius: 8px; margin-top: 10px;">');

    bubble.innerHTML = htmlWithImages;

    // Add copy button for AI messages
    if (role === 'ai') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = '📋 Copy';
        copyBtn.onclick = () => copyToClipboard(text, copyBtn);
        bubble.appendChild(copyBtn);
    }

    div.appendChild(bubble);

    // Add timestamp
    if (role !== 'system') {
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
        div.appendChild(timestamp);
    }

    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div;
}

function showTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'message ai';
    div.id = 'typing-' + Date.now();

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    bubble.appendChild(indicator);
    div.appendChild(bubble);
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    return div.id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function copyToClipboard(text, button) {
    // Remove markdown image syntax for clipboard
    const cleanText = text.replace(/!\[.*?\]\(.*?\)/g, '[Image]');

    navigator.clipboard.writeText(cleanText).then(() => {
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Initialize
console.log('💳 Agentic Analyst loaded successfully');

function toggleDebugger() {
    const consoleDiv = document.getElementById('debug-console');
    consoleDiv.classList.toggle('hidden');

    // Scroll logs to bottom when opened
    if (!consoleDiv.classList.contains('hidden')) {
        const content = document.getElementById('debug-logs');
        content.scrollTop = content.scrollHeight;
    }
}

function renderDebugLogs(logs) {
    const debugContent = document.getElementById('debug-logs');
    if (!debugContent) return;

    debugContent.innerHTML = ''; // Clear previous logs

    if (!logs || logs.length === 0) {
        debugContent.innerHTML = '<div class="debug-placeholder">No logs available.</div>';
        return;
    }

    logs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = `log-entry log-type-${log.type}`;

        let icon = '🟦';
        if (log.type === 'tool_call') icon = '🛠️';
        if (log.type === 'tool_result') icon = '✅';
        if (log.type === 'error') icon = '❌';
        if (log.type === 'thinking') icon = '🧠';
        if (log.type === 'success') icon = '🏁';
        if (log.type === 'system') icon = '⚙️';
        if (log.type === 'warning') icon = '⚠️';
        if (log.type === 'nudge') icon = '👉';

        const detailsHtml = log.details ? `<div class="log-details">${escapeHtml(log.details)}</div>` : '';

        entry.innerHTML = `
            <div class="log-step">Step ${log.step} • ${log.type.toUpperCase()}</div>
            <div class="log-content">${icon} ${escapeHtml(log.content)}</div>
            ${detailsHtml}
        `;

        debugContent.appendChild(entry);
    });

    // Scroll to bottom
    debugContent.scrollTop = debugContent.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
