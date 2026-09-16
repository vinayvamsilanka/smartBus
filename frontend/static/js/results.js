document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const origin = urlParams.get('origin') || 'Hyderabad';
    const dest = urlParams.get('dest') || 'Bangalore';
    const date = urlParams.get('date') || new Date().toISOString().split("T")[0];
    const passengers = urlParams.get('passengers') || '1';
    localStorage.setItem('passengerCount', passengers);

    document.getElementById('search-overview').innerText = `${origin} ➔ ${dest} | Date: ${date}`;

    // New Dashboard fields
    const co = document.getElementById('chart-origin');
    if (co) co.innerText = origin;
    const cd = document.getElementById('chart-dest');
    if (cd) cd.innerText = dest;

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

            const originCity = timeline[0];
            const viaCity = timeline[1];
            const destCity = timeline[2];

            document.getElementById('leg1-text').innerText = `${originCity} ➔ ${viaCity}`;
            document.getElementById('leg2-text').innerText = `${viaCity} ➔ ${destCity}`;

            // Populate connecting leg details
            const leg1 = data.optimizer.split_journey.leg1_bus;
            const leg2 = data.optimizer.split_journey.leg2_bus;

            document.getElementById('leg1-route-detail').innerText = `${originCity} ➔ ${viaCity}`;
            document.getElementById('split-leg1-operator').innerText = `${leg1.operator} (${leg1.type})`;
            document.getElementById('split-leg1-dep').innerText = leg1.departure_datetime.split(' ')[1];
            document.getElementById('split-leg1-arr').innerText = leg1.arrival_datetime.split(' ')[1];
            document.getElementById('split-leg1-fare').innerText = `₹${leg1.fare}`;

            document.getElementById('leg2-route-detail').innerText = `${viaCity} ➔ ${destCity}`;
            document.getElementById('split-leg2-operator').innerText = `${leg2.operator} (${leg2.type})`;
            document.getElementById('split-leg2-dep').innerText = leg2.departure_datetime.split(' ')[1];
            document.getElementById('split-leg2-arr').innerText = leg2.arrival_datetime.split(' ')[1];
            document.getElementById('split-leg2-fare').innerText = `₹${leg2.fare}`;

            // Populate New Dark UI Elements
            const splitLeg1Dep = document.getElementById('split-leg1-dep').innerText;
            const splitLeg1Arr = document.getElementById('split-leg1-arr').innerText;
            const splitLeg2Arr = document.getElementById('split-leg2-arr').innerText;

            const routeTextNodes = document.getElementById('route-text-nodes');
            if (routeTextNodes) {
                routeTextNodes.innerText = `${originCity} (${splitLeg1Dep}) → ${viaCity} (${splitLeg1Arr}) → ${destCity} (${splitLeg2Arr})`;
            }

            const leg1Duration = document.getElementById('leg1-duration');
            if (leg1Duration) leg1Duration.innerText = leg1.duration;

            const leg2Duration = document.getElementById('leg2-duration');
            if (leg2Duration) leg2Duration.innerText = leg2.duration;

            function parseDurationStr(durArr) {
                let h = 0; let m = 0;
                durArr.forEach(d => {
                    const dh = d.match(/(\d+)\s*h/i);
                    const dm = d.match(/(\d+)\s*m/i);
                    if (dh) h += parseInt(dh[1]);
                    if (dm) m += parseInt(dm[1]);
                });
                h += Math.floor(m / 60);
                m = m % 60;
                return `${h}h ${m}m`;
            }
            const totalDur = document.getElementById('total-duration');
            if (totalDur) {
                totalDur.innerText = parseDurationStr([leg1.duration, leg2.duration, "0h 30m"]); // Adding 30m layover estimate
            }

            document.getElementById('btn-split-leg1').onclick = () => {
                localStorage.setItem('selectedBusData', JSON.stringify({
                    id: `bus_${leg1.bus_id}`,
                    schedule_id: leg1.schedule_id,
                    operator: leg1.operator,
                    type: leg1.type,
                    fare: leg1.fare,
                    badge: "Leg 1 of Split Journey",
                    confidence: leg1.confidence,
                    carbon_footprint: leg1.carbon_footprint,
                    safety_index: leg1.safety_index,
                    overall_safety: leg1.overall_safety,
                    delay: leg1.delay,
                    departure_time: leg1.departure_datetime,
                    arrival_time: leg1.arrival_datetime,
                    duration: leg1.duration,
                    ai_reasoning: "Selected as Leg 1 of your split journey."
                }));
                localStorage.setItem('passengerCount', passengers);
                window.location.href = `/details`;
            };

            document.getElementById('btn-split-leg2').onclick = () => {
                localStorage.setItem('selectedBusData', JSON.stringify({
                    id: `bus_${leg2.bus_id}`,
                    schedule_id: leg2.schedule_id,
                    operator: leg2.operator,
                    type: leg2.type,
                    fare: leg2.fare,
                    badge: "Leg 2 of Split Journey",
                    confidence: leg2.confidence,
                    carbon_footprint: leg2.carbon_footprint,
                    safety_index: leg2.safety_index,
                    overall_safety: leg2.overall_safety,
                    delay: leg2.delay,
                    departure_time: leg2.departure_datetime,
                    arrival_time: leg2.arrival_datetime,
                    duration: leg2.duration,
                    ai_reasoning: "Selected as Leg 2 of your split journey."
                }));
                localStorage.setItem('passengerCount', passengers);
                window.location.href = `/details`;
            };

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
        container.innerHTML = `
            <style>
                @keyframes slideBusAnim {
                    0% { left: 5%; opacity: 0; }
                    15% { opacity: 1; }
                    85% { opacity: 1; }
                    100% { left: 95%; opacity: 0; }
                }
            </style>
        `;

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
                    
                    <div class="journey-row" style="display: flex; align-items: center; justify-content: space-between; margin: 2rem 0;">
                        <div class="journey-point" style="text-align: left; display: flex; flex-direction: column;">
                            <span class="point-time" style="font-size: 2rem; font-weight: 800; color: var(--text-primary); line-height: 1.1;">${bus.departure_time.split(' ')[1] || bus.departure_time}</span>
                            <span style="font-size: 0.85rem; color: var(--text-secondary); font-weight: 600; margin-top: 4px; letter-spacing: 0.5px;">${bus.departure_time.split(' ')[0] || ''}</span>
                            <span class="point-loc" style="font-size: 1.1rem; font-weight: 700; margin-top: 8px;">${origin}</span>
                        </div>
                        <div class="journey-path" style="flex: 1; margin: 0 2.5rem; position: relative; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                            <span class="path-duration" style="position: absolute; top: -30px; left: 50%; transform: translateX(-50%); background: #f8fafc; padding: 6px 14px; border-radius: 20px; font-weight: 800; color: var(--text-primary); font-size: 1.05rem; letter-spacing: 1px; z-index: 3; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">${bus.duration}</span>
                            <div class="path-line" style="width: 100%; height: 2px; background: ${(bus.stops && bus.stops.length > 0) ? 'var(--accent-primary)' : 'repeating-linear-gradient(90deg, var(--border-light) 0, var(--border-light) 6px, transparent 6px, transparent 12px)'}; position: absolute; top: 50%; transform: translateY(-50%); opacity: 0.8; z-index: 1;">
                                ${(bus.stops && bus.stops.length > 0) ? bus.stops.map((stop, i) => `
                                    <div style="position: absolute; left: ${((i + 1) / (bus.stops.length + 1)) * 100}%; top: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; z-index: 1;">
                                        <div style="width: 12px; height: 12px; background: var(--accent-primary); border-radius: 50%; box-shadow: 0 0 0 3px white;"></div>
                                        <span style="position: absolute; top: 16px; font-size: 1.05rem; font-weight: 700; color: var(--text-primary); white-space: nowrap;">${stop}</span>
                                    </div>
                                `).join('') : ''}
                            </div>
                            
                            <i class="fa-solid fa-bus-simple" style="color: var(--accent-primary); font-size: 1.15rem; position: absolute; top: 50%; left: 0%; transform: translate(-50%, -50%); z-index: 2; opacity: 1; animation: slideBusAnim 5.5s ease-in-out infinite;"></i>
                        </div>
                        <div class="journey-point" style="text-align: right; display: flex; flex-direction: column; align-items: flex-end;">
                            <span class="point-time" style="font-size: 2rem; font-weight: 800; color: var(--text-primary); line-height: 1.1;">${bus.arrival_time.split(' ')[1] || bus.arrival_time}</span>
                            <span style="font-size: 0.85rem; color: var(--text-secondary); font-weight: 600; margin-top: 4px; letter-spacing: 0.5px;">${bus.arrival_time.split(' ')[0] || ''}</span>
                            <span class="point-loc" style="font-size: 1.1rem; font-weight: 700; margin-top: 8px;">${dest}</span>
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

        let strokeGradient = ctx.createLinearGradient(0, 0, 400, 0);
        strokeGradient.addColorStop(0, '#a855f7');
        strokeGradient.addColorStop(0.5, '#6366f1');
        strokeGradient.addColorStop(1, '#38bdf8');

        let fillGradient = ctx.createLinearGradient(0, 0, 0, 400);
        fillGradient.addColorStop(0, 'rgba(168, 85, 247, 0.4)');
        fillGradient.addColorStop(0.5, 'rgba(56, 189, 248, 0.1)');
        fillGradient.addColorStop(1, 'rgba(17, 24, 39, 0)');

        fareChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predicted Fare (₹)',
                    data: data,
                    borderColor: strokeGradient,
                    backgroundColor: fillGradient,
                    borderWidth: 4,
                    pointBackgroundColor: '#111827',
                    pointBorderColor: '#38bdf8',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#64748b' } },
                    x: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#64748b' } }
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
        localStorage.setItem('passengerCount', passengers);
        window.location.href = `/details`;
    };
});
