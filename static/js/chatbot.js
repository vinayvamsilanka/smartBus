document.addEventListener('DOMContentLoaded', () => {
    const chatBtn = document.getElementById('ai-chat-btn');
    const chatWindow = document.getElementById('ai-chat-window');
    const closeChat = document.getElementById('close-chat');
    const sendBtn = document.getElementById('send-chat');
    const inputField = document.getElementById('chat-input');
    const messagesBox = document.getElementById('chat-messages');

    if (!chatBtn || !chatWindow) return;

    chatBtn.addEventListener('click', () => {
        chatWindow.classList.remove('hidden');
        chatBtn.style.opacity = '0';
        chatBtn.style.pointerEvents = 'none';

        // Slight delay to allow focus after transition starts
        setTimeout(() => inputField.focus(), 100);
    });

    closeChat.addEventListener('click', () => {
        chatWindow.classList.add('hidden');
        chatBtn.style.opacity = '1';
        chatBtn.style.pointerEvents = 'all';
    });

    sendBtn.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    async function sendMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        appendMessage(text, 'user-message', false);
        inputField.value = '';

        // Add thinking animation dots
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message ai-message thinking';
        thinkingDiv.style.opacity = '0.7';
        thinkingDiv.innerHTML = '<span class="dot-blink">●</span> <span class="dot-blink" style="animation-delay: 0.2s;">●</span> <span class="dot-blink" style="animation-delay: 0.4s;">●</span>';
        messagesBox.appendChild(thinkingDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;

        try {
            const res = await fetch('/api/optimizer/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            
            // Remove thinking indicator
            thinkingDiv.remove();

            // Format markdown to HTML in response
            let formattedResponse = data.response
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');

            appendMessage(formattedResponse, 'ai-message', true);
            
            // Proactively highlight buses based on query keywords
            const query = text.toLowerCase();
            if (query.includes('safe')) highlightBuses('Safest');
            if (query.includes('cheap') || query.includes('under') || query.includes('deal')) highlightBuses('Value');
            if (query.includes('eco') || query.includes('green')) highlightBuses('Green');

        } catch (err) {
            console.error(err);
            thinkingDiv.remove();
            appendMessage("⚠️ SmartBus AI system is currently optimizing route loads. Please try again shortly.", 'ai-message', false);
        }
    }

    function appendMessage(msg, className, isHTML = false) {
        const div = document.createElement('div');
        div.className = `message ${className}`;
        if (isHTML) {
            div.innerHTML = msg;
        } else {
            div.textContent = msg;
        }
        messagesBox.appendChild(div);
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    function highlightBuses(keyword) {
        const cards = document.querySelectorAll('.bus-card');
        if (cards.length === 0) return;

        cards.forEach(c => {
            c.style.transition = 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
            if (c.textContent.toLowerCase().includes(keyword.toLowerCase())) {
                c.style.opacity = '1';
                c.style.transform = 'scale(1.02)';
                c.style.borderColor = 'var(--accent-primary)';
                c.style.boxShadow = '0 10px 25px rgba(37, 99, 235, 0.2)';
            } else {
                c.style.opacity = '0.4';
                c.style.transform = 'scale(0.98)';
                c.style.borderColor = 'transparent';
                c.style.boxShadow = 'none';
            }
        });
    }
});
