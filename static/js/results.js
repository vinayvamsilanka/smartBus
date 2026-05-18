document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const origin = urlParams.get('origin') || 'Hyderabad';
    const dest = urlParams.get('dest') || 'Bangalore';
    const date = urlParams.get('date') || new Date().toISOString().split("T")[0];

    document.getElementById('search-overview').innerText = `${origin} ➔ ${dest} | Date: ${date}`;

    let fareChartInstance = null;
    let globalDataCache = null;

    try {
        const response = await fetch('/api/optimizer/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, dest, date })
        });
        const data = await response.json();
        globalDataCache = data;

        document.getElementById('loader').classList.add('hidden');
        const dash = document.getElementById('results-dashboard');
        dash.classList.remove('hidden');

        // Setup Chart
        document.getElementById('cheapest-date').innerText =
            `${data.optimizer.cheapest_date.date} (₹${data.optimizer.cheapest_date.fare})`;
        document.getElementById('ai-confidence').innerText = data.optimizer.ai_confidence;

        // Handle Timeline and split
        if (data.optimizer.split_journey.available) {
            document.getElementById('split-journey-box').style.display = 'flex';
            document.getElementById('split-via').innerText = data.optimizer.split_journey.via;
            document.getElementById('direct-fare').innerText = data.optimizer.split_journey.direct_fare;
            document.getElementById('split-fare').innerText = data.optimizer.split_journey.split_fare;
            document.getElementById('split-savings').innerText = data.optimizer.split_journey.savings;

            const timeline = data.optimizer.split_journey.route_timeline;
            document.querySelector('#tp-origin .label').innerText = timeline[0];
            document.querySelector('#tp-via .label').innerText = timeline[1];
            document.querySelector('#tp-dest .label').innerText = timeline[2];

            setTimeout(() => {
                const busStr = document.getElementById('animated-bus');
                if (busStr) {
                    busStr.style.animation = 'none';
                    busStr.offsetHeight;
                    busStr.style.animation = `driveBus 4s ease-in-out infinite`;
                }
            }, 100);
        }

        renderChart(data.optimizer.labels, data.optimizer.fares);
        renderBuses(data.buses);

        // Show cascade animation
        requestAnimationFrame(() => {
            dash.style.opacity = '1';
            dash.style.transform = 'translateY(0)';
        });

    } catch (err) {
        console.error(err);
        alert("Failed to connect to the backend API.");
        document.getElementById('loader').classList.add('hidden');
    }

    function renderBuses(buses) {
        const container = document.getElementById('buses-container');
        container.innerHTML = '';

        buses.forEach((bus, index) => {
            const cardHTML = `
                <div class="bus-card" style="animation: fadeUp 0.6s ease-out forwards; animation-delay: ${index * 0.1}s">
                    <div class="bus-card-header">
                        <div class="operator-info">
                            <h3>${bus.operator}</h3>
                            <div class="bus-type">
                                <i class="fa-solid fa-bus-simple"></i>
                                <span>${bus.type}</span>
                                ${bus.badge ? `<span class="badge" style="background: #eff6ff; color: #2563eb; margin-left:10px">${bus.badge}</span>` : ''}
                            </div>
                        </div>
                        <div class="smart-match-score" style="--score: ${bus.confidence}">
                            <svg viewBox="0 0 70 70">
                                <circle cx="35" cy="35" r="32" stroke-dasharray="200" stroke-dashoffset="${200 - (200 * bus.confidence) / 100}"></circle>
                            </svg>
                            <span class="match-value">${bus.confidence}%</span>
                            <span class="match-label">AI Match</span>
                        </div>
                    </div>
                    
                    <div class="journey-row">
                        <div class="journey-point">
                            <span class="point-time">${bus.departure_time}</span>
                            <span class="point-loc">${origin}</span>
                        </div>
                        <div class="journey-path">
                            <span class="path-duration">${bus.duration}</span>
                            <div class="path-line"></div>
                        </div>
                        <div class="journey-point" style="text-align: right;">
                            <span class="point-time">${bus.arrival_time}</span>
                            <span class="point-loc">${dest}</span>
                        </div>
                    </div>

                    <div class="price-booking">
                        <div class="fare-box">
                            <span class="fare-label">Total Fare</span>
                            <span class="fare-amount">₹${bus.fare}</span>
                        </div>
                        <div style="display: flex; gap: 1rem;">
                            <button class="btn-ai-insight" onclick="toggleReasoning('reasoning-${bus.id}')">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> AI Insight
                            </button>
                            <button class="btn-select-seat-new" onclick="proceedToDetails('${bus.id}')">
                                Select Seat <i class="fa-solid fa-arrow-right"></i>
                            </button>
                        </div>
                    </div>

                    <div id="reasoning-${bus.id}" class="ai-reasoning-panel-new hidden">
                        <div class="ai-icon-burst">
                            <i class="fa-solid fa-robot"></i>
                        </div>
                        <div class="ai-text">
                            <strong>AI Analysis:</strong> ${bus.ai_reasoning}
                        </div>
                    </div>

                    <div class="metrics-strip">
                        <div class="metric-badge">
                            <i class="fa-solid fa-leaf"></i>
                            <span>${bus.carbon_footprint.eco_score} Eco Score</span>
                        </div>
                        <div class="metric-badge">
                            <i class="fa-solid fa-shield-halved"></i>
                            <span>${bus.overall_safety}/100 Safety</span>
                        </div>
                        <div class="metric-badge">
                            <i class="fa-solid fa-clock"></i>
                            <span>${bus.delay.on_time_probability}% On-Time</span>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML += cardHTML;
        });
    }

    function renderChart(labels, data) {
        const ctx = document.getElementById('fareChart').getContext('2d');
        let gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.5)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

        fareChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predicted Fare (₹)',
                    data: data,
                    borderColor: '#38bdf8',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#fff',
                    pointRadius: 5,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }

    // Attach to window so onclick works
    window.toggleReasoning = function (id) {
        const panel = document.getElementById(id);
        if (panel.classList.contains('hidden')) {
            panel.classList.remove('hidden');
        } else {
            panel.classList.add('hidden');
        }
    };

    window.proceedToDetails = function (bus_id) {
        // Find bus
        const bus = globalDataCache.buses.find(b => b.id === bus_id);
        // Serialize its data via localstorage so details page can use it instantly without refetching the ML model dict
        localStorage.setItem('selectedBusData', JSON.stringify(bus));
        window.location.href = `/details`;
    };
});
