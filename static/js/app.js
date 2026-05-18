document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
        dateInput.min = new Date().toISOString().split("T")[0];
    }

    const form = document.getElementById('search-form');
    let fareChartInstance = null;
    let currentSeats = [];

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const origin = document.getElementById('origin').value;
        const dest = document.getElementById('dest').value;
        const date = document.getElementById('date').value;

        // Show loader
        document.getElementById('dashboard').classList.add('hidden');
        document.getElementById('loader').classList.remove('hidden');

        try {
            const response = await fetch('/api/optimizer/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ origin, dest, date })
            });
            const data = await response.json();

            // Populate UI with data
            updateDashboard(data);

            // Hide loader show dashboard
            setTimeout(() => {
                document.getElementById('loader').classList.add('hidden');
                document.getElementById('dashboard').classList.remove('hidden');

                // Add fade in effect
                requestAnimationFrame(() => {
                    document.querySelector('.dashboard-grid').classList.add('show');
                });

            }, 800); // Simulate slightly longer AI processing time for UX

        } catch (err) {
            console.error(err);
            alert('Failed to connect to the AI Engine. Is the backend running?');
            document.getElementById('loader').classList.add('hidden');
        }
    });

    function updateDashboard(data) {
        // 1. Optimizer & Chart
        document.getElementById('cheapest-date').innerText =
            `${data.optimizer.cheapest_date.date} (₹${data.optimizer.cheapest_date.fare})`;

        document.getElementById('ai-confidence').innerText = data.optimizer.ai_confidence;

        if (data.optimizer.split_journey.available) {
            document.getElementById('split-journey-box').style.display = 'flex';
            document.getElementById('split-via').innerText = data.optimizer.split_journey.via;
            document.getElementById('direct-fare').innerText = data.optimizer.split_journey.direct_fare;
            document.getElementById('split-fare').innerText = data.optimizer.split_journey.split_fare;
            document.getElementById('split-savings').innerText = data.optimizer.split_journey.savings;

            // Motion Timeline Logic
            const timeline = data.optimizer.split_journey.route_timeline;
            document.querySelector('#tp-origin .label').innerText = timeline[0];
            document.querySelector('#tp-via .label').innerText = timeline[1];
            document.querySelector('#tp-dest .label').innerText = timeline[2];

            // Trigger animation
            setTimeout(() => {
                const busStr = document.getElementById('animated-bus');
                if (busStr) {
                    busStr.style.animation = 'none';
                    busStr.offsetHeight; // trigger reflow
                    busStr.style.animation = `driveBus 4s ease-in-out infinite`;
                }
            }, 100);

        } else {
            document.getElementById('split-journey-box').style.display = 'none';
        }

        renderChart(data.optimizer.labels, data.optimizer.fares);

        // 2. Green Card
        document.getElementById('bus-co2').innerText = data.carbon_footprint.bus_co2;
        document.getElementById('car-co2').innerText = data.carbon_footprint.car_co2;
        document.getElementById('train-co2').innerText = data.carbon_footprint.train_co2;
        document.getElementById('eco-badge').innerText = data.carbon_footprint.badge;
        document.querySelector('.stat-circle').className = `stat-circle ${data.carbon_footprint.eco_score.toLowerCase()}`;

        let pathElem = document.querySelector('.stat-circle .circle');
        let ecoScoreVal = data.carbon_footprint.eco_score === 'High' ? 15 : (data.carbon_footprint.eco_score === 'Medium' ? 50 : 85);
        pathElem.setAttribute('stroke-dasharray', `${100 - ecoScoreVal}, 100`);
        document.querySelector('.stat-circle .percentage').textContent = data.carbon_footprint.eco_score;

        // 3. Safety Index
        document.getElementById('safety-overall').innerText = data.safety_index.overall_score;
        animateProgress('driver', data.safety_index.driver_reliability);
        animateProgress('maint', data.safety_index.maintenance_score);
        animateProgress('night', data.safety_index.night_travel_safety);
        animateProgress('women', data.safety_index.women_safety_index);

        // 4. Delay & On-Time
        document.getElementById('on-time-prob').innerText = data.delay.on_time_probability;
        document.getElementById('sim-delay').innerText = data.delay.simulated_delay_mins;

        // 5. Seats
        currentSeats = data.seats;
        renderSeats(data.seats);
    }

    function animateProgress(idPrefix, value) {
        document.getElementById(`${idPrefix}-score`).innerText = `${value}%`;
        const bar = document.getElementById(`${idPrefix}-bar`);
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = `${value}%`;
        }, 500);
    }

    function renderChart(labels, data) {
        const ctx = document.getElementById('fareChart').getContext('2d');

        if (fareChartInstance) {
            fareChartInstance.destroy();
        }

        // Gradient for line
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
                    pointHoverRadius: 8,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(30, 41, 59, 0.9)',
                        titleFont: { family: 'Inter', size: 14 },
                        bodyFont: { family: 'Inter', size: 14, weight: 'bold' },
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    function renderSeats(seats) {
        const container = document.getElementById('seats-container');
        container.innerHTML = '';

        // We know there are 40 seats (10 rows, 4 cols)
        let html = '';

        let seatIndex = 0;
        for (let row = 0; row < 10; row++) {

            // W1, A1, aisle, A2, W2
            let rowSeats = seats.slice(seatIndex, seatIndex + 4);
            seatIndex += 4;

            // W1
            html += generateSeatHTML(rowSeats[0]);
            // A1
            html += generateSeatHTML(rowSeats[1]);
            // Aisle
            html += `<div class="seat aisle-space"></div>`;
            // A2
            html += generateSeatHTML(rowSeats[2]);
            // W2
            html += generateSeatHTML(rowSeats[3]);
        }

        container.innerHTML = html;

        // Add event listeners
        document.querySelectorAll('.seat:not(.booked):not(.aisle-space)').forEach(seatEl => {
            seatEl.addEventListener('click', () => {
                document.querySelectorAll('.seat').forEach(s => s.classList.remove('selected'));
                seatEl.classList.add('selected');

                const seatId = seatEl.dataset.id;
                const seatData = currentSeats.find(s => s.id === seatId);
                showSeatDetails(seatData);
            });
        });
    }

    function generateSeatHTML(seat) {
        let classes = 'seat';
        if (!seat.available) classes += ' booked';
        let icon = seat.type === 'Window' ? 'fa-window-maximize' : 'fa-chair';

        return `<div class="${classes}" data-id="${seat.id}" title="${seat.id} (${seat.type})">
            ${seat.id}
        </div>`;
    }

    function showSeatDetails(seat) {
        document.getElementById('seat-metrics').style.opacity = '1';
        document.getElementById('selected-seat-title').innerHTML = `Seat ${seat.id} Selected <span class="badge blue">₹${document.getElementById('direct-fare').innerText || '---'}</span>`;
        document.getElementById('seat-noise').innerText = `${seat.noise_db} dB`;
        document.getElementById('seat-vibe').innerText = seat.vibration;
        document.getElementById('seat-type').innerText = seat.type;
        document.getElementById('seat-zone').innerText = seat.zone;

        const btn = document.getElementById('btn-book');
        btn.disabled = false;
        btn.innerText = `Proceed to Book Seat ${seat.id}`;

        // Warning if back seat
        if (seat.zone === 'Back') {
            document.getElementById('seat-vibe').style.color = '#f87171'; // red
        } else {
            document.getElementById('seat-vibe').style.color = '';
        }
    }
});
