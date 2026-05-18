/**
 * chat_ws_patch.js
 * ─────────────────────────────────────────────────────────────
 * Tambahkan file ini sebagai <script> SETELAH chat.js di index.html:
 *
 *   <script src="{{ url_for('static', filename='js/chat.js') }}"></script>
 *   <script src="{{ url_for('static', filename='js/chat_ws_patch.js') }}"></script>
 *
 * File ini menambahkan WebSocket real-time KE ATAS HTTP fallback yang
 * sudah ada di chat.js — tanpa mengubah chat.js sama sekali.
 * ─────────────────────────────────────────────────────────────
 */

(function () {
    // Pastikan Socket.IO sudah dimuat (oleh CDN di template)
    if (typeof io === "undefined") {
        console.warn("[WS Patch] Socket.IO tidak ditemukan — WebSocket tidak aktif, HTTP fallback tetap jalan.");
        return;
    }

    /* ── Koneksi Socket.IO ───────────────────────────────────── */
    const socket = io({ transports: ["websocket", "polling"] });

    /* ── Ambil session_id — sync dengan Flask session ─────────── */
    // Ambil dari meta tag yang akan kita tambahkan di index.html
    // atau gunakan sessionStorage sebagai fallback
    let sessionId = document.querySelector('meta[name="bpom-session-id"]')?.content
        || sessionStorage.getItem("bpom_ws_session_id");

    if (!sessionId) {
        // Buat baru dan simpan — akan dipakai konsisten selama tab terbuka
        sessionId = "web_" + Math.random().toString(36).slice(2, 10) + Date.now();
        sessionStorage.setItem("bpom_ws_session_id", sessionId);
    }

    /* ── Event: terkoneksi ───────────────────────────────────── */
    socket.on("connect", () => {
        socket.emit("join_user", { session_id: sessionId });
        console.info("[WS Patch] WebSocket terhubung, session:", sessionId);
    });

    /* ── Event: balasan bot via WebSocket ────────────────────── */
    socket.on("bot_reply", (data) => {
        // Cegah duplikat — jika HTTP sudah merespons, abaikan WS
        // (keduanya tidak akan aktif bersamaan karena sendMessageWS intercept)
        if (data._ws_handled) return;
        data._ws_handled = true;

        // Sembunyikan typing indicator (didefinisikan di chat.js)
        if (typeof hideTyping === "function") hideTyping();

        // Tambahkan pesan bot ke UI (didefinisikan di chat.js)
        if (typeof renderBotMessage === "function") {
            renderBotMessage(data); if (typeof scrollToBottom === "function") scrollToBottom();
        } else {
            // Fallback: emit event agar chat.js bisa handle
            window.dispatchEvent(new CustomEvent("bpom:ws_reply", { detail: data }));
        }
    });

    /* ── Event: typing start/stop ────────────────────────────── */
    socket.on("typing_start", () => {
        if (typeof showTyping === "function") showTyping();
    });

    socket.on("typing_stop", () => {
        if (typeof hideTyping === "function") hideTyping();
    });

    /* ── Event: balasan dari admin dashboard ─────────────────── */
    socket.on("admin_reply", (data) => {
        console.info("[WS] admin_reply diterima:", data);
        const adminMsg = {
            type: "text",
            message: "👨‍💼 *Admin BPOM Lubuklinggau:*\n" + data.message,
            timestamp: data.timestamp,
            quick_replies: [],
        };
        // FIX: nama fungsi di chat.js adalah renderBotMessage
        if (typeof renderBotMessage === "function") {
            renderBotMessage(adminMsg);
            if (typeof scrollToBottom === "function") scrollToBottom();
        } else {
            console.error("[WS] renderBotMessage tidak ditemukan!");
        }
        _flashTitle("📩 Admin BPOM membalas!");
    });

    /* ── Override pengiriman pesan untuk gunakan WebSocket ─────
       Kita intercept klik tombol Send & Enter SETELAH chat.js
       memasangnya — caranya: tambahkan listener kedua yang
       mencegah HTTP call jika WS connected.
    ─────────────────────────────────────────────────────────── */
    let wsInterceptActive = false;

    function activateWsIntercept() {
        if (wsInterceptActive) return;
        wsInterceptActive = true;

        const input = document.getElementById("userInput");
        const sendBtn = document.getElementById("sendBtn");
        if (!input || !sendBtn) return;

        function sendViaWS(e) {
            if (!socket.connected) return;   // jika WS putus, biarkan chat.js handle via HTTP
            const text = input.value.trim();
            if (!text) return;

            // Intercept — kita yang kirim, bukan HTTP
            e.stopImmediatePropagation();

            input.value = "";
            input.style.height = "auto";

            // Tampilkan bubble user (fungsi dari chat.js)
            if (typeof renderUserMessage === "function") renderUserMessage(text, new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }));
            if (typeof showTyping === "function") showTyping();

            socket.emit("chat_message_ws", {
                session_id: sessionId,
                message: text,
            });
        }

        sendBtn.addEventListener("click", sendViaWS, true);   // capture phase
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) sendViaWS(e);
        }, true);

        console.info("[WS Patch] Intercept aktif — pesan dikirim via WebSocket.");
    }

    socket.on("joined", () => activateWsIntercept());

    /* ── Helper: flash judul tab ─────────────────────────────── */
    let _flashInterval = null;
    function _flashTitle(msg) {
        if (_flashInterval) return;
        const orig = document.title;
        let show = true;
        _flashInterval = setInterval(() => {
            document.title = show ? msg : orig;
            show = !show;
        }, 900);
        setTimeout(() => {
            clearInterval(_flashInterval);
            _flashInterval = null;
            document.title = orig;
        }, 5000);
    }

    /* ── Indikator status WS di hint bar ─────────────────────── */
    function updateHint() {
        const hint = document.querySelector(".input-hint");
        if (!hint) return;
        if (socket.connected) {
            hint.innerHTML = '🟢 Real-time aktif &nbsp;•&nbsp; Tekan Enter untuk mengirim &nbsp;•&nbsp; Dikelola BPOM Lubuklinggau';
        } else {
            hint.innerHTML = '🟡 Menghubungkan… &nbsp;•&nbsp; Tekan Enter untuk mengirim';
        }
    }

    socket.on("connect",    updateHint);
    socket.on("disconnect", updateHint);

    // Expose socket ke global jika perlu debug
    window._bpomSocket = socket;
    window._bpomSessionId = sessionId;
})();