// =============================================
// BPOM Lubuklinggau Chatbot - Frontend JS
// =============================================

const messagesContainer = document.getElementById('messagesContainer');
const messagesWrapper   = document.getElementById('messagesWrapper');
const userInput         = document.getElementById('userInput');
const sendBtn           = document.getElementById('sendBtn');
const typingIndicator   = document.getElementById('typingIndicator');
const resetBtn          = document.getElementById('resetBtn');
const sidebarToggle     = document.getElementById('sidebarToggle');
const sidebar           = document.querySelector('.sidebar');
const overlay           = document.getElementById('overlay');

// Scroll-to-bottom button
const scrollBtn = document.createElement('button');
scrollBtn.className = 'scroll-btn';
scrollBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>`;
document.querySelector('.chat-container').appendChild(scrollBtn);

// =============================================
// MARKDOWN-LITE PARSER
// =============================================

function parseMarkdown(text) {
    if (!text) return '';

    // Escape HTML first
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Bold **text** or __text__
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic *text* (not bold)
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

    // Convert newlines to <br>
    html = html.replace(/\n/g, '<br>');

    return html;
}

// =============================================
// RENDER MESSAGE
// =============================================

const BOT_SVG = `
<svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="18" cy="18" r="18" fill="#E8F5E9"/>
    <circle cx="18" cy="14" r="6" fill="#007B5E"/>
    <path d="M6 30c0-6.627 5.373-12 12-12s12 5.373 12 12" fill="#007B5E" fill-opacity="0.6"/>
</svg>`;

function renderBotMessage(data) {
    const row = document.createElement('div');
    row.className = 'message-row bot';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = BOT_SVG;

    const wrapper = document.createElement('div');
    wrapper.className = 'bubble-wrapper';

    // CARD TYPE
    if (data.type === 'card' && data.card) {
        const card = buildInfoCard(data.card);
        const time = buildTimestamp(data.timestamp);
        wrapper.appendChild(card);
        wrapper.appendChild(time);
    }
    // TEXT MESSAGE
    else {
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.innerHTML = parseMarkdown(data.message || '');

        const time = buildTimestamp(data.timestamp);
        wrapper.appendChild(bubble);
        wrapper.appendChild(time);
    }

    // Quick replies (below bubble)
    if (data.quick_replies && data.quick_replies.length > 0) {
        const qrContainer = buildQuickReplies(data.quick_replies);
        row.appendChild(avatar);
        row.appendChild(wrapper);
        messagesContainer.appendChild(row);
        messagesContainer.appendChild(qrContainer);
        return; // early exit since appended already
    }

    row.appendChild(avatar);
    row.appendChild(wrapper);
    messagesContainer.appendChild(row);
}

function renderUserMessage(text, timestamp) {
    const row = document.createElement('div');
    row.className = 'message-row user';

    const wrapper = document.createElement('div');
    wrapper.className = 'bubble-wrapper';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    const time = buildTimestamp(timestamp, true);

    wrapper.appendChild(bubble);
    wrapper.appendChild(time);
    row.appendChild(wrapper);
    messagesContainer.appendChild(row);
}

function buildTimestamp(ts, isUser = false) {
    const el = document.createElement('span');
    el.className = 'msg-time';
    el.textContent = ts || getCurrentTime();
    return el;
}

function buildInfoCard(card) {
    const div = document.createElement('div');
    div.className = 'info-card-msg';

    const header = document.createElement('div');
    header.className = 'info-card-header';
    header.innerHTML = `<p>${card.title || ''}</p>`;

    const body = document.createElement('div');
    body.className = 'info-card-body';

    (card.items || []).forEach(item => {
        const row = document.createElement('div');
        row.className = 'info-card-item';
        row.innerHTML = `
            <span class="ic-icon">${item.icon || ''}</span>
            <div>
                <p class="ic-label">${item.label || ''}</p>
                <p class="ic-value">${item.value || ''}</p>
            </div>`;
        body.appendChild(row);
    });

    div.appendChild(header);
    div.appendChild(body);
    return div;
}

function buildQuickReplies(replies) {
    const container = document.createElement('div');
    container.className = 'quick-replies';

    replies.forEach(reply => {
        const btn = document.createElement('button');
        btn.className = 'qr-btn';
        btn.textContent = reply.text;
        btn.dataset.action = reply.id;

        btn.addEventListener('click', () => {
            // Remove all quick reply rows when one is clicked
            document.querySelectorAll('.quick-replies').forEach(el => {
                el.style.opacity = '0.5';
                el.style.pointerEvents = 'none';
            });
            sendMessage(reply.text);
        });

        container.appendChild(btn);
    });

    return container;
}

// =============================================
// DATE SEPARATOR
// =============================================

function addDateSeparator() {
    const sep = document.createElement('div');
    sep.className = 'date-separator';

    const now = new Date();
    const opts = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    const dateStr = now.toLocaleDateString('id-ID', opts);

    sep.innerHTML = `<span>Hari ini, ${dateStr}</span>`;
    messagesContainer.appendChild(sep);
}

// =============================================
// SCROLL HANDLING
// =============================================

function scrollToBottom(smooth = true) {
    messagesWrapper.scrollTo({
        top: messagesWrapper.scrollHeight,
        behavior: smooth ? 'smooth' : 'instant'
    });
}

function isScrolledToBottom() {
    return messagesWrapper.scrollHeight - messagesWrapper.scrollTop - messagesWrapper.clientHeight < 80;
}

messagesWrapper.addEventListener('scroll', () => {
    const atBottom = isScrolledToBottom();
    scrollBtn.classList.toggle('visible', !atBottom);
});

scrollBtn.addEventListener('click', () => scrollToBottom());

// =============================================
// TYPING INDICATOR
// =============================================

function showTyping() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

// =============================================
// SEND MESSAGE
// =============================================

function getCurrentTime() {
    return new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

async function sendMessage(text) {
    const message = text || userInput.value.trim();
    if (!message) return;

    // Disable input temporarily
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Render user message
    renderUserMessage(message, getCurrentTime());
    scrollToBottom();

    // Show typing
    await delay(300);
    showTyping();
    scrollToBottom();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await res.json();

        // Simulate typing delay for natural feel
        const typingTime = Math.min(600 + message.length * 8, 1800);
        await delay(typingTime);

        hideTyping();

        // FIX: Jika response adalah "waiting", coba dapatkan jawaban bot langsung
        if (data.type === 'waiting') {
            // Tampilkan pesan tunggu HANYA jika tidak ada quick reply dari bot
            const botRes = await fetch('/api/chat_direct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            if (botRes.ok) {
                const botData = await botRes.json();
                if (botData && botData.message) {
                    renderBotMessage(botData);
                    scrollToBottom();
                    userInput.disabled = false;
                    sendBtn.disabled = false;
                    userInput.focus();
                    return;
                }
            }
            // Fallback: tampilkan pesan tunggu
            renderBotMessage(data);
        } else {
            renderBotMessage(data);
        }
        scrollToBottom();

    } catch (err) {
        hideTyping();
        renderBotMessage({
            type: 'text_with_menu',
            message: '⚠️ Maaf, terjadi gangguan koneksi. Silakan coba lagi.',
            timestamp: getCurrentTime(),
        });
        scrollToBottom();
    }

    // Re-enable input
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================
// SUBMENU JENIS LAYANAN
// =============================================

function toggleSubmenu() {

    const submenu = document.getElementById('submenu-layanan');

    if (submenu.style.display === 'none') {
        submenu.style.display = 'block';
    } else {
        submenu.style.display = 'none';
    }
}

function sendMenu(menu) {

    // gunakan fungsi asli chatbot
    sendMessage(menu);
}

// =============================================
// EVENT LISTENERS
// =============================================

sendBtn.addEventListener('click', () => sendMessage());

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Reset conversation
resetBtn.addEventListener('click', async () => {
    await fetch('/api/reset', { method: 'POST' });
    messagesContainer.innerHTML = '';
    loadWelcome();
});

// Sidebar toggle (mobile)
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
});

overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
});

// Nav items
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const action = item.dataset.action;
        if (!action) return;

        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        // Close sidebar on mobile
        sidebar.classList.remove('open');
        overlay.classList.remove('show');

        if (action === 'home') {
            resetBtn.click();
        } else {
            sendMessage(action);
        }
    });
});

// =============================================
// INIT - LOAD WELCOME MESSAGE
// =============================================

async function loadWelcome() {
    addDateSeparator();

    try {
        const res = await fetch('/api/welcome');
        const data = await res.json();
        await delay(400);
        renderBotMessage(data);
        scrollToBottom(false);
    } catch (err) {
        renderBotMessage({
            type: 'text_with_menu',
            message: '👋 Selamat datang di Chatbot BPOM Lubuklinggau! Silakan pilih menu atau ketik pertanyaan Anda.',
            timestamp: getCurrentTime(),
        });
    }
}

// Start the app
loadWelcome();
