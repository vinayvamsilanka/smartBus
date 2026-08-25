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

            // New Feature: Rich UI Cards in Chat!
            if (data.rich_cards && data.rich_cards.length > 0) {
                let cardsHTML = '<div class="chat-rich-cards-container" style="display:flex; flex-direction:column; gap:10px; margin-top:10px;">';
                data.rich_cards.forEach(c => {
                    cardsHTML += `
                        <div class="chat-rich-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; color: #1e293b; box-shadow: 0 4px 15px rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 6px;">
                            <div style="font-weight: 800; font-size: 1.1rem; color: #020617; display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                                ${c.origin} <i class="fa-solid fa-arrow-right" style="color: #3b82f6; font-size: 0.9rem;"></i> ${c.destination}
                            </div>
                            <div style="font-size: 0.85rem; color: #64748b; font-weight: 500;">
                                ${c.title}
                            </div>
                            <div style="background: #f1f5f9; color: #8b5cf6; font-size: 0.70rem; padding: 4px 10px; border-radius: 20px; font-weight: 600; width: fit-content; display: inline-flex; align-items: center; margin-bottom: 8px; margin-top: 2px;">
                                Eco ${c.type}
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 8px; color: #475569; font-size: 0.85rem; font-weight: 600;">
                                <div style="display: flex; align-items: center; gap: 8px;"><i class="fa-solid fa-road" style="color: #475569;"></i> ${c.distance} km</div>
                                <div style="display: flex; align-items: center; gap: 8px;"><i class="fa-regular fa-clock" style="color: #475569;"></i> ${c.time}</div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; border-top: 1px solid #f1f5f9; padding-top: 15px;">
                                <div style="font-size: 1.4rem; font-weight: 900; color: #2563eb; letter-spacing: -0.5px;">₹${c.fare}</div>
                                <a href="${c.bookLink}" onmouseover="this.style.background='#eff6ff';" onmouseout="this.style.background='white';" style="background: white; color: #2563eb; border: 1px solid #3b82f6; padding: 6px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 500; text-decoration: none; transition: all 0.2s ease;">Select Path</a>
                            </div>
                        </div>
                    `;
                });
                cardsHTML += '</div>';
                appendMessage(cardsHTML, 'ai-message', true);
            }

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
