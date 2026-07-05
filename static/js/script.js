/**
 * script.js
 * ----------
 * Frontend logic for the AI Chatbot UI:
 *  - Sending / receiving messages via fetch()
 *  - Typing indicator animation
 *  - Auto-scroll & timestamps
 *  - Dark / light mode toggle (persisted in-memory for the session)
 *  - Voice input (Web Speech API) + speech output (SpeechSynthesis)
 *  - Emoji picker
 *  - Chat export (TXT)
 *  - Clear chat / history loading
 *  - Character counter
 */

(function () {
    "use strict";

    // ---------------------------------------------------------------------
    // State
    // ---------------------------------------------------------------------
    const state = {
        theme: "light",
        isBotTyping: false,
        messages: [], // {sender, text, time}
    };

    // ---------------------------------------------------------------------
    // DOM references
    // ---------------------------------------------------------------------
    const landing = document.getElementById("landing");
    const openChatBtn = document.getElementById("open-chat-btn");
    const floatingBtn = document.getElementById("floating-chat-btn");
    const chatWindow = document.getElementById("chat-window");
    const minimizeBtn = document.getElementById("minimize-btn");
    const chatMessages = document.getElementById("chat-messages");
    const messageInput = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    const exportBtn = document.getElementById("export-btn");
    const themeToggle = document.getElementById("theme-toggle");
    const themeToggleLanding = document.getElementById("theme-toggle-landing");
    const typingIndicator = document.getElementById("typing-indicator");
    const charCounter = document.getElementById("char-counter");
    const voiceBtn = document.getElementById("voice-btn");
    const emojiBtn = document.getElementById("emoji-btn");
    const emojiPicker = document.getElementById("emoji-picker");
    const notificationSound = document.getElementById("notification-sound");
    const statusText = document.getElementById("status-text");

    // ---------------------------------------------------------------------
    // Theme handling
    // ---------------------------------------------------------------------
    function applyTheme(theme) {
        state.theme = theme;
        document.documentElement.setAttribute("data-theme", theme);
        const icon = theme === "dark" ? "☀️" : "🌙";
        if (themeToggle) themeToggle.textContent = icon;
        if (themeToggleLanding) themeToggleLanding.textContent = icon;
    }

    function toggleTheme() {
        applyTheme(state.theme === "light" ? "dark" : "light");
    }

    // Respect system preference on load
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        applyTheme("dark");
    }

    themeToggle?.addEventListener("click", toggleTheme);
    themeToggleLanding?.addEventListener("click", toggleTheme);

    // ---------------------------------------------------------------------
    // Open / close chat window
    // ---------------------------------------------------------------------
    function openChat() {
        chatWindow.classList.add("open");
        messageInput.focus();
        loadHistory();
    }

    function closeChat() {
        chatWindow.classList.remove("open");
    }

    openChatBtn?.addEventListener("click", openChat);
    floatingBtn?.addEventListener("click", () => {
        chatWindow.classList.contains("open") ? closeChat() : openChat();
    });
    minimizeBtn?.addEventListener("click", closeChat);

    // ---------------------------------------------------------------------
    // Message rendering
    // ---------------------------------------------------------------------
    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function appendMessage(sender, text, time) {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${sender}-message`;

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = sender === "bot" ? "🤖" : "🧑";

        const content = document.createElement("div");
        content.className = "message-content";

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = text;

        const timestamp = document.createElement("span");
        timestamp.className = "timestamp";
        timestamp.textContent = time || formatTime(new Date());

        content.appendChild(bubble);
        content.appendChild(timestamp);
        wrapper.appendChild(avatar);
        wrapper.appendChild(content);

        chatMessages.appendChild(wrapper);
        scrollToBottom();

        state.messages.push({ sender, text, time: timestamp.textContent });
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping() {
        state.isBotTyping = true;
        typingIndicator.style.display = "flex";
        scrollToBottom();
    }

    function hideTyping() {
        state.isBotTyping = false;
        typingIndicator.style.display = "none";
    }

    // ---------------------------------------------------------------------
    // Sending messages
    // ---------------------------------------------------------------------
    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text) return;

        appendMessage("user", text);
        messageInput.value = "";
        updateCharCounter();
        sendBtn.disabled = true;
        showTyping();

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });

            const data = await response.json();
            hideTyping();

            if (data.success) {
                appendMessage("bot", data.response);
                playNotificationSound();
                speak(data.response);
            } else {
                appendMessage("bot", data.error || "Something went wrong. Please try again.");
            }
        } catch (error) {
            hideTyping();
            appendMessage("bot", "⚠️ Network error — please check your connection and try again.");
            console.error("Chat request failed:", error);
        } finally {
            sendBtn.disabled = false;
        }
    }

    sendBtn?.addEventListener("click", sendMessage);
    messageInput?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });

    // ---------------------------------------------------------------------
    // Character counter
    // ---------------------------------------------------------------------
    function updateCharCounter() {
        const len = messageInput.value.length;
        charCounter.textContent = `${len}/500`;
    }
    messageInput?.addEventListener("input", updateCharCounter);

    // ---------------------------------------------------------------------
    // Clear chat
    // ---------------------------------------------------------------------
    async function clearChat() {
        try {
            await fetch("/clear", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
        } catch (error) {
            console.error("Failed to clear history on server:", error);
        }

        chatMessages.innerHTML = "";
        state.messages = [];
        appendMessage("bot", "Chat cleared! How can I help you now?");
    }
    clearBtn?.addEventListener("click", clearChat);

    // ---------------------------------------------------------------------
    // Load history on open
    // ---------------------------------------------------------------------
    async function loadHistory() {
        try {
            const response = await fetch("/history");
            const data = await response.json();
            if (data.success && Array.isArray(data.history) && data.history.length && chatMessages.children.length <= 1) {
                chatMessages.innerHTML = "";
                data.history.forEach((record) => {
                    appendMessage("user", record.user_message);
                    appendMessage("bot", record.bot_response);
                });
            }
        } catch (error) {
            console.error("Failed to load history:", error);
        }
    }

    // ---------------------------------------------------------------------
    // Export chat as TXT
    // ---------------------------------------------------------------------
    function exportChat() {
        if (!state.messages.length) return;
        const lines = state.messages.map(
            (m) => `[${m.time}] ${m.sender === "bot" ? "DialogBot" : "You"}: ${m.text}`
        );
        const blob = new Blob([lines.join("\n")], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `chat-export-${Date.now()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
    exportBtn?.addEventListener("click", exportChat);

    // ---------------------------------------------------------------------
    // Emoji picker
    // ---------------------------------------------------------------------
    emojiBtn?.addEventListener("click", () => {
        emojiPicker.style.display = emojiPicker.style.display === "grid" ? "none" : "grid";
    });
    emojiPicker?.querySelectorAll("span").forEach((el) => {
        el.addEventListener("click", () => {
            messageInput.value += el.textContent;
            updateCharCounter();
            messageInput.focus();
        });
    });

    // ---------------------------------------------------------------------
    // Voice input (Web Speech API)
    // ---------------------------------------------------------------------
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.interimResults = false;

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            messageInput.value = transcript;
            updateCharCounter();
            sendMessage();
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            statusText.textContent = "Online";
        };

        recognition.onend = () => {
            statusText.textContent = "Online";
        };
    }

    voiceBtn?.addEventListener("click", () => {
        if (!recognition) {
            appendMessage("bot", "Voice input isn't supported in this browser.");
            return;
        }
        statusText.textContent = "Listening...";
        recognition.start();
    });

    // ---------------------------------------------------------------------
    // Speech output (SpeechSynthesis)
    // ---------------------------------------------------------------------
    function speak(text) {
        if (!("speechSynthesis" in window)) return;
        // Speech output is opt-in-friendly: keep it short and non-intrusive.
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 0; // Muted by default; set to 1 to enable audible replies.
        window.speechSynthesis.speak(utterance);
    }

    // ---------------------------------------------------------------------
    // Notification sound
    // ---------------------------------------------------------------------
    function playNotificationSound() {
        try {
            notificationSound.currentTime = 0;
            notificationSound.play().catch(() => {
                /* Autoplay might be blocked until user interacts — safe to ignore. */
            });
        } catch (error) {
            /* no-op */
        }
    }

    // ---------------------------------------------------------------------
    // Online / offline indicator
    // ---------------------------------------------------------------------
    function updateOnlineStatus() {
        if (navigator.onLine) {
            statusText.textContent = "Online";
        } else {
            statusText.textContent = "Offline";
        }
    }
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    updateOnlineStatus();

    // ---------------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------------
    updateCharCounter();
})();
