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
            let res;
            let data;
            try {
                res = await fetch('/api/optimizer/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                data = await res.json();
            } catch (firstErr) {
                // Quick retry in case server was reloading
                console.warn('First request attempt interrupted, retrying...', firstErr);
                await new Promise(r => setTimeout(r, 600));
                res = await fetch('/api/optimizer/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                data = await res.json();
            }

            // Remove thinking indicator
            if (thinkingDiv && thinkingDiv.parentNode) {
                thinkingDiv.remove();
            }

            const rawResponse = (data && typeof data.response === 'string')
                ? data.response
                : (data && data.msg) || "We are in the year 2026. How can I assist you with your travel plans today?";

            // Format markdown to HTML in response
            let formattedResponse = rawResponse
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');

            appendMessage(formattedResponse, 'ai-message', true);

            // New Feature: Rich UI Cards in Chat!
            if (data.rich_cards && data.rich_cards.length > 0) {
                let cardsHTML = '<div class="chat-rich-cards-container" style="display:flex; flex-direction:column; gap:12px; margin-top:12px;">';
                data.rich_cards.forEach((c, i) => {
                    cardsHTML += `
                        <div class="chat-rich-card" style="
                            background: linear-gradient(145deg, #ffffff, #f8fafc);
                            border: 1px solid rgba(56, 189, 248, 0.25);
                            border-radius: 14px; 
                            padding: 14px; 
                            color: #1e293b; 
                            box-shadow: 0 8px 20px rgba(0,0,0,0.06); 
                            display: flex; 
                            flex-direction: column; 
                            gap: 10px;
                            opacity: 0;
                            animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                            animation-delay: ${i * 0.15}s;
                            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px) scale(1.02)'; this.style.boxShadow='0 12px 25px rgba(37, 99, 235, 0.12)';" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 8px 20px rgba(0,0,0,0.06)';">
                            
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 6px;">
                                <div style="flex: 1; min-width: 140px;">
                                    <div style="font-weight: 800; font-size: 0.95rem; color: #0f172a; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-family: 'Outfit', sans-serif;">
                                        ${c.origin} <i class="fa-solid fa-arrow-right" style="color: #3b82f6; font-size: 0.8rem;"></i> ${c.destination}
                                    </div>
                                    <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">
                                        <i class="fa-solid fa-bolt" style="margin-right: 4px; color: #fbbf24;"></i> ${c.title}
                                    </div>
                                </div>
                                <div style="background: rgba(139, 92, 246, 0.1); color: #7c3aed; font-size: 0.65rem; padding: 4px 8px; border-radius: 20px; font-weight: 800; border: 1px solid rgba(139, 92, 246, 0.25); text-transform: uppercase;">
                                    ${c.type}
                                </div>
                            </div>
                            
                            <div style="display: flex; gap: 12px; color: #334155; font-size: 0.75rem; font-weight: 700; background: #f1f5f9; padding: 10px; border-radius: 10px; margin: 2px 0;">
                                <div style="display: flex; align-items: center; gap: 6px;"><i class="fa-solid fa-route" style="color: #3b82f6; font-size: 0.9rem;"></i> ${c.distance} km</div>
                                <div style="display: flex; align-items: center; gap: 6px;"><i class="fa-solid fa-stopwatch" style="color: #10b981; font-size: 0.9rem;"></i> ${c.time}</div>
                            </div>

                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                                <div>
                                    <span style="font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 2px;">Smart Fare</span>
                                    <div style="font-size: 1.25rem; font-weight: 900; color: #2563eb; letter-spacing: -0.5px; font-family: 'Outfit', sans-serif; line-height: 1;">₹${c.fare}</div>
                                </div>
                                <a href="${c.bookLink}" style="
                                    background: linear-gradient(135deg, #2563eb, #1d4ed8); 
                                    color: white; 
                                    border: none; 
                                    padding: 8px 14px; 
                                    border-radius: 8px; 
                                    font-size: 0.8rem; 
                                    font-weight: 800; 
                                    text-decoration: none; 
                                    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
                                    transition: all 0.25s ease;
                                    display: flex;
                                    align-items: center;
                                    gap: 6px;
                                " onmouseover="this.style.boxShadow='0 6px 15px rgba(37, 99, 235, 0.45)'; this.style.transform='translateY(-2px)';" onmouseout="this.style.boxShadow='0 4px 10px rgba(37, 99, 235, 0.3)'; this.style.transform='translateY(0)';">
                                    Secure <i class="fa-solid fa-arrow-right"></i>
                                </a>
                            </div>
                        </div>
                    `;
                });
                cardsHTML += '<style>@keyframes slideUpFade { 0% { opacity: 0; transform: translateY(30px) scale(0.95); } 100% { opacity: 1; transform: translateY(0) scale(1); } }</style>';
                cardsHTML += '</div>';
                appendMessage(cardsHTML, 'ai-message', true);
            }

            // Proactively highlight buses based on query keywords
            const query = text.toLowerCase();
            if (query.includes('safe')) highlightBuses('Safest');
            if (query.includes('cheap') || query.includes('under') || query.includes('deal')) highlightBuses('Value');
            if (query.includes('eco') || query.includes('green')) highlightBuses('Green');

        } catch (err) {
            console.error('Chatbot error:', err);
            if (thinkingDiv && thinkingDiv.parentNode) {
                thinkingDiv.remove();
            }
            appendMessage("We are in **2026**! I am your SmartBus AI Travel Concierge. Please ask me about your travel route or date!", 'ai-message', true);
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
