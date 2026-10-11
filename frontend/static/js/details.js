document.addEventListener('DOMContentLoaded', async () => {
    const rawData = localStorage.getItem('selectedBusData');
    if (!rawData) {
        alert("No bus selected! Redirecting to home...");
        window.location.href = '/';
        return;
    }

    const bus = JSON.parse(rawData);

    // Multi-Seat State & Validation
    let selectedSeats = [];
    const passengerCount = parseInt(localStorage.getItem('passengerCount') || '1', 10);

    // Populate Header
    document.getElementById('bus-operator').innerText = bus.operator;
    document.getElementById('bus-type').innerText = bus.type;
    document.getElementById('bus-fare').innerText = `₹${bus.fare}`;

    if (bus.badge) {
        const badgeEl = document.getElementById('bus-badge');
        badgeEl.style.display = 'inline-block';
        badgeEl.innerText = bus.badge;
    }

    // Populate Eco
    document.getElementById('bus-co2').innerText = bus.carbon_footprint.bus_co2;
    document.getElementById('car-co2').innerText = bus.carbon_footprint.car_co2;
    document.getElementById('train-co2').innerText = bus.carbon_footprint.train_co2;
    document.getElementById('eco-badge').innerText = bus.carbon_footprint.badge;

    const eco_grade = bus.carbon_footprint.eco_score.toLowerCase();
    const chart = document.querySelector('.circular-chart');
    chart.className = `circular-chart ${eco_grade === 'high' ? 'green' : (eco_grade === 'medium' ? 'blue' : 'warning')}`;

    let pathElem = document.getElementById('eco-path');
    let ecoScoreVal = bus.carbon_footprint.eco_score === 'High' ? 85 : (bus.carbon_footprint.eco_score === 'Medium' ? 50 : 25);
    pathElem.setAttribute('stroke-dasharray', `${ecoScoreVal}, 100`);
    document.getElementById('eco-level').textContent = bus.carbon_footprint.eco_score;

    // Populate Safety
    document.getElementById('safety-overall').innerText = bus.overall_safety;
    animateProgress('driver', bus.safety_index.driver_reliability);
    animateProgress('maint', bus.safety_index.maintenance_score);
    animateProgress('night', bus.safety_index.night_travel_safety);
    animateProgress('women', bus.safety_index.women_safety_index);

    // Populate Delay
    document.getElementById('on-time-prob').innerText = bus.delay.on_time_probability;
    document.getElementById('sim-delay').innerText = bus.delay.simulated_delay_mins;

    const sparkline = document.getElementById('sparkline-container');
    sparkline.innerHTML = '';
    bus.delay.reliability_trend.forEach(v => {
        sparkline.innerHTML += `<div class="bar" style="height: ${v}%"></div>`;
    });

    renderDelayChart(bus.delay.reliability_trend);

    // Fetch Seat Map
    try {
        const res = await fetch(`/api/optimizer/seats?type=${encodeURIComponent(bus.type)}&schedule_id=${bus.schedule_id}`);
        const seats = await res.json();

        // Initialize Deck Management
        let currentDeck = 'Lower';
        const isSleeper = bus.type.toLowerCase().includes('sleeper');

        if (isSleeper) {
            setupDeckSelector((deck) => {
                currentDeck = deck;
                renderSeats(seats.filter(s => s.deck === currentDeck), bus.fare, isSleeper);
            });
            renderSeats(seats.filter(s => s.deck === 'Lower'), bus.fare, isSleeper);
        } else {
            renderSeats(seats, bus.fare, false);
        }
    } catch (err) {
        console.error("Failed to load seats", err);
    }

    function setupDeckSelector(onChange) {
        const wrapper = document.getElementById('bus-360-wrapper');
        const selectorHTML = `
            <div class="deck-selector" style="position: absolute; top: 100px; z-index: 100; transform: translateZ(20px);">
                <button class="deck-btn active" data-deck="Lower">Lower Deck</button>
                <button class="deck-btn" data-deck="Upper">Upper Deck</button>
            </div>
        `;
        wrapper.insertAdjacentHTML('afterbegin', selectorHTML);

        document.querySelectorAll('.deck-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.deck-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                onChange(btn.dataset.deck);
            });
        });
    }

    function renderSeats(seats, fare, isSleeper) {
        const container = document.getElementById('seats-container');
        container.innerHTML = '';

        if (isSleeper) {
            container.classList.add('sleeper-grid');
            container.style.gridTemplateColumns = '1fr 60px 1fr 1fr';
        } else {
            container.classList.remove('sleeper-grid');
            container.style.gridTemplateColumns = '1fr 1fr 60px 1fr 1fr';
        }

        let html = '';
        if (isSleeper) {
            // Group by row for sleeper
            const rows = {};
            seats.forEach(s => {
                const r = s.id.match(/\d+/)[0];
                if (!rows[r]) rows[r] = [];
                rows[r].push(s);
            });

            Object.keys(rows).sort((a, b) => a - b).forEach(r => {
                const rowSeats = rows[r];
                const left = rowSeats.find(s => s.align === 'left');
                const rightA = rowSeats.find(s => s.id.includes('RA'));
                const rightB = rowSeats.find(s => s.id.includes('RB'));

                html += generateSeatHTML(left, r, true);
                html += `<div style="width:100%; display:flex; align-items:center; justify-content:center;"><div style="width:2px; height:60%; background: rgba(56,189,248,0.1);"></div></div>`;
                html += generateSeatHTML(rightA, r, true);
                html += generateSeatHTML(rightB, r, true);
            });
        } else {
            let seatIndex = 0;
            for (let row = 0; row < 10; row++) {
                let rowSeats = seats.slice(seatIndex, seatIndex + 4);
                seatIndex += 4;
                if (!rowSeats[0]) continue;
                html += generateSeatHTML(rowSeats[0], row + 1, false);
                html += generateSeatHTML(rowSeats[1], row + 1, false);
                html += `<div style="width:100%; display:flex; align-items:center; justify-content:center;"><div style="width:2px; height:100%; background: rgba(56,189,248,0.1);"></div></div>`;
                html += generateSeatHTML(rowSeats[2], row + 1, false);
                html += generateSeatHTML(rowSeats[3], row + 1, false);
            }
        }

        container.innerHTML = html;

        // --- AI Seat Recommendation Engine ---
        seats.forEach(s => {
            s.ai_score = -9999;
            if (!s.available) return;

            let score = 0;
            // 1. Noise factor (lower is better, max ~80dB)
            score += (80 - (s.noise_db || 50)) * 1.5;

            // 2. Vibration comfort
            if (s.vibration === 'Low' || s.vibration === 'Ultra Smooth') score += 25;
            else if (s.vibration === 'Medium') score += 10;
            else score -= 20; // High vibration

            // 3. Journey duration / Distance heuristic
            // Longer journeys demand mid-cabin stability. Shorter ones prefer front cabin.
            const durationHours = bus.duration ? parseInt(bus.duration.split('h')[0]) : 5;
            if (durationHours > 5) {
                if (s.zone === 'Middle') score += 30; // Max stability
                else if (s.zone === 'Front') score += 10;
                else if (s.zone === 'Back') score -= 20; // Too bumpy for long trips
            } else {
                if (s.zone === 'Front') score += 30; // Quick exit
                else if (s.zone === 'Middle') score += 15;
                else if (s.zone === 'Back') score -= 10;
            }

            // 4. Seating preferences (Window/Single Berth gets a boost)
            if (s.type === 'Window') score += 20;
            if (s.type === 'Single Berth' || (s.align && s.align === 'left')) score += 25; // Solo travel preference

            s.ai_score = score;
        });

        let recommendedSeats = [];
        let bestGroupScore = -99999;
        let bestGroupIndex = -1;

        // Strategy 1: Find best adjacent cluster in the linear seat array
        for (let i = 0; i <= seats.length - passengerCount; i++) {
            let validGroup = true;
            let groupScore = 0;

            for (let j = 0; j < passengerCount; j++) {
                if (!seats[i + j].available) {
                    validGroup = false;
                    break;
                }
                groupScore += seats[i + j].ai_score;
            }

            if (validGroup && groupScore > bestGroupScore) {
                bestGroupScore = groupScore;
                bestGroupIndex = i;
            }
        }

        if (bestGroupIndex !== -1) {
            for (let j = 0; j < passengerCount; j++) {
                recommendedSeats.push(seats[bestGroupIndex + j]);
            }
        } else {
            // Strategy 2: Fallback to top individual seats if no contiguous block is available
            const availableScored = seats.filter(s => s.available).sort((a, b) => b.ai_score - a.ai_score);
            recommendedSeats = availableScored.slice(0, passengerCount);
        }

        if (recommendedSeats.length > 0 && selectedSeats.length === 0) {
            // Small delay to allow DOM to render
            setTimeout(() => {
                recommendedSeats.forEach(recSeat => {
                    const seatEl = document.querySelector(`[data-id="${recSeat.id}"]`);
                    if (seatEl) {
                        seatEl.style.boxShadow = '0 0 15px rgba(16, 185, 129, 0.8)';
                        seatEl.style.border = '2px solid #10b981';
                        seatEl.innerHTML += `<div style="position:absolute; top:-8px; right:-8px; background:#10b981; color:#000; border-radius:50%; width:20px; height:20px; font-size:10px; display:flex; align-items:center; justify-content:center; font-weight:bold; z-index: 5; box-shadow: 0 0 10px #10b981;" title="AI Group Pick: Best Comfort"><i class="fa-solid fa-wand-magic-sparkles"></i></div>`;
                    }
                });
            }, 300);
        }

        attachSeatEvents(seats, fare);
    }

    function attachSeatEvents(seats, fare) {
        const pHeading = document.getElementById('selected-seat-title');
        if (pHeading) {
            pHeading.innerHTML = `Select exactly <strong>${passengerCount}</strong> seat(s) (Selected: <span id="sel-count">${selectedSeats.length}</span>)`;
        }

        document.querySelectorAll('.seat-btn').forEach(seatEl => {
            if (seatEl.dataset.booked === 'true') return;

            // Restore visual style if the seat is already selected (e.g. after changing decks)
            const seatId = seatEl.dataset.id;
            const isSelected = selectedSeats.some(s => s.id === seatId);
            if (isSelected) {
                setSelectedSeatStyle(seatEl);
            } else {
                resetSeatStyle(seatEl);
            }

            // Click listener
            seatEl.addEventListener('click', () => {
                const seatData = seats.find(s => s.id === seatId);
                if (!seatData) return; // safety check

                const idx = selectedSeats.findIndex(s => s.id === seatId);
                if (idx > -1) {
                    // Already selected, deselect it
                    selectedSeats.splice(idx, 1);
                    resetSeatStyle(seatEl);
                } else {
                    // Not selected yet
                    if (selectedSeats.length >= passengerCount) {
                        // FIFO replacement: deselect oldest
                        const oldest = selectedSeats.shift();
                        if (oldest) {
                            const oldestEl = document.querySelector(`[data-id="${oldest.id}"]`);
                            if (oldestEl) resetSeatStyle(oldestEl);
                        }
                    }

                    selectedSeats.push(seatData);
                    setSelectedSeatStyle(seatEl);
                }

                updateSeatSelectionStatus(fare);
            });
        });

        // Initialize status on load/deck change
        updateSeatSelectionStatus(fare);
    }


    function animateProgress(idPrefix, value) {
        const el = document.getElementById(`${idPrefix}-score`);
        if (!el) return;
        el.innerText = `${value}%`;
        const bar = document.getElementById(`${idPrefix}-bar`);
        if (bar) {
            bar.style.width = '0%';
            setTimeout(() => { bar.style.width = `${value}%`; }, 500);
        }
    }

    function renderDelayChart(data) {
        const canvas = document.getElementById('reliabilityChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let gradient = ctx.createLinearGradient(0, 0, 0, 160);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)');
        gradient.addColorStop(0.5, 'rgba(56, 189, 248, 0.3)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Trip 1', 'Trip 2', 'Trip 3', 'Trip 4', 'Trip 5'],
                datasets: [{
                    label: 'On-Time %',
                    data: data,
                    borderColor: '#6366f1',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#6366f1',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, min: 50, max: 100, ticks: { color: 'rgba(255,255,255,0.4)' } },
                    x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.4)' } }
                }
            }
        });
    }

    function generateSeatHTML(seat, rowNum, isSleeper) {
        if (!seat) return '<div></div>';
        const isBooked = !seat.available;
        const isWindow = seat.type === 'Window' || (seat.align && (seat.align === 'left' || seat.id.includes('RB')));

        let iconHTML = '';
        if (isSleeper) {
            const isDouble = seat.type && seat.type.includes('Double');
            iconHTML = `<div style="font-size: 1.6rem; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5)); opacity: ${isBooked ? 0.3 : 0.95}; margin-bottom: 2px;">${isBooked ? '🔒' : (isDouble ? '🛏️' : '🛌')}</div>`;
        } else {
            iconHTML = `<div style="font-size: 1.3rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4)); opacity: ${isBooked ? 0.3 : 0.95}; margin-bottom: 2px;">${isBooked ? '🔒' : '💺'}</div>`;
        }

        const sleeperClass = isSleeper ? `berth-btn ${seat.type && seat.type.includes('Double') ? 'double-berth' : ''}` : 'seater-btn';

        return `<div class="seat-btn ${sleeperClass}"
            data-id="${seat.id}"
            data-booked="${isBooked}"
            title="${seat.id} · ${seat.type || 'Standard'} · Zone: ${seat.zone || 'Main'}"
            style="
                cursor: ${isBooked ? 'not-allowed' : 'pointer'};
                color: ${isBooked ? 'rgba(255,255,255,0.2)' : '#ffffff'};
            ">
            ${isWindow && !isBooked ? '<span style="position: absolute; top: 4px; right: 6px; font-size: 0.65rem; opacity: 0.7;" title="Window View">🪟</span>' : ''}
            ${iconHTML}
            <div style="font-weight: 800; font-size: 0.78rem; letter-spacing: 0.5px; z-index: 2;">${seat.id}</div>
            <div style="font-size: 0.58rem; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-top: 2px;">
                ${isBooked ? 'BOOKED' : (isSleeper ? (seat.type && seat.type.includes('Double') ? 'DBL BERTH' : 'SLEEPER') : (seat.type === 'Window' ? 'WINDOW' : 'AISLE'))}
            </div>
        </div>`;
    }

    // ── 360° View Engine ──────────────────────────────────────
    let rotY = 0, rotX = 0;
    const busView = document.getElementById('bus-360-view');

    const viewAngles = {
        front: { x: 45, y: 0, z: -100, cockpit: 1 },
        mid: { x: 15, y: -15, z: 0, cockpit: 0.8 },
        top: { x: 60, y: 0, z: 50, cockpit: 0.5 },
        side: { x: 0, y: 65, z: 100, cockpit: 0.2 }
    };

    window.setViewAngle = (angle) => {
        const target = viewAngles[angle];
        rotX = target.x;
        rotY = target.y;
        applyView();

        // Cockpit opacity animation
        const cockpit = document.getElementById('cockpit-view');
        if (cockpit) cockpit.style.opacity = target.cockpit;

        document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`[data-angle="${angle}"]`)?.classList.add('active');
    };

    window.rotateView = (degrees) => {
        rotY += degrees;
        applyView();
    };

    window.resetView = () => {
        rotX = 0; rotY = 0;
        applyView();
        document.querySelectorAll('.view-angle-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-angle="front"]')?.classList.add('active');
    };

    function applyView() {
        busView.style.transform = `perspective(1500px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-20px)`;
    }

    // Drag to rotate
    let isDragging = false, lastX = 0, lastY = 0;
    busView.addEventListener('mousedown', e => { isDragging = true; lastX = e.clientX; lastY = e.clientY; busView.style.cursor = 'grabbing'; });
    document.addEventListener('mouseup', () => { isDragging = false; busView.style.cursor = 'grab'; });
    document.addEventListener('mousemove', e => {
        if (!isDragging) return;
        rotY += (e.clientX - lastX) * 0.4;
        rotX -= (e.clientY - lastY) * 0.4;
        rotX = Math.max(-45, Math.min(45, rotX));
        lastX = e.clientX; lastY = e.clientY;
        applyView();
    });

    function resetSeatStyle(el) {
        el.style.background = '';
        el.style.borderColor = '';
        el.style.color = '#ffffff';
        el.style.transform = '';
        el.style.boxShadow = '';
        el.classList.remove('selected-seat-3d');
        el.classList.remove('seat-pop');
    }

    function setSelectedSeatStyle(el) {
        el.classList.add('selected-seat-3d');
        el.classList.remove('seat-pop');
        void el.offsetWidth; // Trigger reflow
        el.classList.add('seat-pop');
    }

    function updateSeatSelectionStatus(fare) {
        const countSpan = document.getElementById('sel-count');
        if (countSpan) countSpan.innerText = selectedSeats.length;

        const metricsDiv = document.getElementById('seat-metrics');
        const bookBtn = document.getElementById('btn-book');
        const titleEl = document.getElementById('selected-seat-title');

        if (selectedSeats.length === 0) {
            metricsDiv.style.opacity = '0.4';
            titleEl.innerHTML = `Select exactly <strong style="color:#38bdf8;">${passengerCount}</strong> seat(s)`;

            document.getElementById('seat-noise').innerText = '-- dB';
            document.getElementById('seat-vibe').innerText = '--';
            document.getElementById('seat-type').innerText = '--';
            document.getElementById('seat-zone').innerText = '--';

            bookBtn.disabled = true;
            bookBtn.classList.remove('pulse-glow');
            bookBtn.innerHTML = `<i class="fa-solid fa-lock"></i> Secure Seat`;
        } else {
            metricsDiv.style.opacity = '1';
            // Show latest seat info
            const latest = selectedSeats[selectedSeats.length - 1];
            titleEl.innerHTML = `Selected <strong style="color:#38bdf8;">${selectedSeats.length}/${passengerCount}</strong> Seat(s) <span style="background:linear-gradient(135deg, #2563eb, #1d4ed8);color:#fff;padding:4px 12px;border-radius:20px;font-size:0.8rem;margin-left:8px;box-shadow:0 4px 10px rgba(37,99,235,0.4);border:1px solid #60a5fa;">₹${fare * selectedSeats.length}</span>`;

            const noiseVal = latest.noise_db || (latest.zone === 'Front' ? 32 : (latest.zone === 'Back' ? 42 : 36));
            const vibeVal = latest.vibration || (latest.zone === 'Front' ? 'Ultra Smooth' : (latest.zone === 'Back' ? 'Engine Zone' : 'Medium'));

            document.getElementById('seat-noise').innerText = `${noiseVal} dB`;
            document.getElementById('seat-vibe').innerText = vibeVal;
            document.getElementById('seat-type').innerText = latest.type || 'Executive Pod';
            document.getElementById('seat-zone').innerText = `${latest.zone || 'Mid'} Cabin`;

            if (latest.zone === 'Back') {
                document.getElementById('seat-vibe').style.color = '#f87171';
            } else if (latest.zone === 'Front') {
                document.getElementById('seat-vibe').style.color = '#34d399';
            } else {
                document.getElementById('seat-vibe').style.color = '#38bdf8';
            }

            // Enable check out button only when exact seats count matched
            if (selectedSeats.length === passengerCount) {
                bookBtn.disabled = false;
                bookBtn.classList.add('pulse-glow');
                bookBtn.innerHTML = `<i class="fa-solid fa-lock"></i> Secure ${selectedSeats.length} Seat(s) · ₹${fare * selectedSeats.length}`;
            } else {
                bookBtn.disabled = true;
                bookBtn.classList.remove('pulse-glow');
                bookBtn.innerHTML = `<i class="fa-solid fa-lock"></i> Select ${passengerCount - selectedSeats.length} more seat(s)`;
            }
        }
    }

    // Interactive Checkout Modal
    const modal = document.getElementById('checkout-modal');
    const modalContent = document.getElementById('checkout-modal-content');
    const closeModalBtn = document.getElementById('close-checkout-modal');

    // Progress Indicators
    const step1Ind = document.getElementById('step-1-indicator');
    const step2Ind = document.getElementById('step-2-indicator');
    const step3Ind = document.getElementById('step-3-indicator');
    const line1 = document.getElementById('line-step-1');
    const line2 = document.getElementById('line-step-2');
    const lbl1 = document.getElementById('lbl-step-1');
    const lbl2 = document.getElementById('lbl-step-2');
    const lbl3 = document.getElementById('lbl-step-3');

    // Panels
    const stepAuth = document.getElementById('checkout-step-auth');
    const stepPassenger = document.getElementById('checkout-step-passenger');
    const stepPayment = document.getElementById('checkout-step-payment');
    const stepProcessing = document.getElementById('checkout-step-processing');
    const stepSuccess = document.getElementById('checkout-step-success');

    // Auth fields
    const emailInput = document.getElementById('modal-email-input');
    const passwordInput = document.getElementById('modal-password-input');
    const phoneInput = document.getElementById('modal-phone-input');

    const tabEmail = document.getElementById('modal-tab-email');
    const emailForm = document.getElementById('modal-auth-email-form');
    let currentAuthMode = 'email';


    if (closeModalBtn) {
        closeModalBtn.onclick = () => {
            modal.style.opacity = '0';
            modalContent.style.transform = 'scale(0.95)';
            setTimeout(() => {
                modal.style.display = 'none';
            }, 400);
        };
    }

    const btn = document.getElementById('btn-book');
    if (btn) {
        btn.onclick = () => {
            const seatsListStr = selectedSeats.map(s => s.id).join(', ');
            document.getElementById('modal-seat-id-1').innerText = seatsListStr;
            document.getElementById('modal-seat-id-3').innerText = seatsListStr;
            const totalFare = bus.fare * selectedSeats.length;
            document.getElementById('modal-fare-amount').innerText = `₹${totalFare}`;

            stepAuth.style.display = 'none';
            stepPassenger.style.display = 'none';
            stepPayment.style.display = 'none';
            stepProcessing.style.display = 'none';
            stepSuccess.style.display = 'none';
            document.getElementById('auth-modal-error').style.display = 'none';

            modal.style.display = 'flex';
            setTimeout(() => {
                modal.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }, 10);

            if (window.USER_ID) {
                goToPassengerStep();
            } else {
                stepAuth.style.display = 'block';
                updateStepProgress(1);
            }
        };
    }

    function updateStepProgress(step) {
        step1Ind.style.background = 'rgba(255,255,255,0.05)';
        step1Ind.style.color = 'rgba(255,255,255,0.4)';
        step1Ind.style.borderColor = 'rgba(255,255,255,0.1)';
        step1Ind.innerHTML = '1';

        step2Ind.style.background = 'rgba(255,255,255,0.05)';
        step2Ind.style.color = 'rgba(255,255,255,0.4)';
        step2Ind.style.borderColor = 'rgba(255,255,255,0.1)';
        step2Ind.innerHTML = '2';

        step3Ind.style.background = 'rgba(255,255,255,0.05)';
        step3Ind.style.color = 'rgba(255,255,255,0.4)';
        step3Ind.style.borderColor = 'rgba(255,255,255,0.1)';
        step3Ind.innerHTML = '3';

        line1.style.background = 'rgba(255,255,255,0.1)';
        line2.style.background = 'rgba(255,255,255,0.1)';

        lbl1.style.color = 'var(--text-secondary)';
        lbl2.style.color = 'var(--text-secondary)';
        lbl3.style.color = 'var(--text-secondary)';

        if (step === 1) {
            step1Ind.style.background = 'var(--accent-primary)';
            step1Ind.style.color = '#000';
            step1Ind.style.borderColor = 'var(--accent-primary)';
            lbl1.style.color = '#cbd5e1';
        } else if (step === 2) {
            step1Ind.style.background = 'rgba(16, 185, 129, 0.15)';
            step1Ind.style.color = '#10b981';
            step1Ind.style.borderColor = '#10b981';
            step1Ind.innerHTML = '✓';

            step2Ind.style.background = 'var(--accent-primary)';
            step2Ind.style.color = '#000';
            step2Ind.style.borderColor = 'var(--accent-primary)';
            line1.style.background = 'var(--accent-primary)';
            lbl2.style.color = '#cbd5e1';
        } else if (step === 3) {
            step1Ind.style.background = 'rgba(16, 185, 129, 0.15)';
            step1Ind.style.color = '#10b981';
            step1Ind.style.borderColor = '#10b981';
            step1Ind.innerHTML = '✓';

            step2Ind.style.background = 'rgba(16, 185, 129, 0.15)';
            step2Ind.style.color = '#10b981';
            step2Ind.style.borderColor = '#10b981';
            step2Ind.innerHTML = '✓';

            step3Ind.style.background = 'var(--accent-primary)';
            step3Ind.style.color = '#000';
            step3Ind.style.borderColor = 'var(--accent-primary)';
            line1.style.background = '#10b981';
            line2.style.background = 'var(--accent-primary)';
            lbl3.style.color = '#cbd5e1';
        }
    }

    function goToPassengerStep() {
        stepAuth.style.display = 'none';
        stepPassenger.style.display = 'block';
        updateStepProgress(2);

        const container = document.getElementById('passenger-forms-container');
        container.innerHTML = '';

        selectedSeats.forEach((seat, idx) => {
            container.innerHTML += `
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 15px;" class="passenger-form-item" data-seat="${seat.id}">
                    <h4 style="margin-top:0; margin-bottom:12px; font-size:0.95rem; color: var(--accent-primary); display:flex; align-items:center; gap:6px;">
                        <i class="fa-solid fa-circle-user"></i> Passenger ${idx + 1} (Seat ${seat.id})
                    </h4>
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 4px;">Passenger Full Name</label>
                        <input type="text" class="passenger-name-input" data-seat="${seat.id}" placeholder="e.g. Charan Kumar" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; outline: none; font-size:0.85rem; font-weight:600;" value="${idx === 0 ? (window.USER_NAME || '') : ''}">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <div style="flex: 1;">
                            <label style="display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 4px;">Age</label>
                            <input type="text" class="passenger-age-input" data-seat="${seat.id}" placeholder="Age" inputmode="numeric" maxlength="3" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; outline: none; font-size:0.85rem;" oninput="this.value = this.value.replace(/[^0-9]/g, '')">
                        </div>
                        <div style="flex: 1.2;">
                            <label style="display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 4px;">Gender</label>
                            <select class="passenger-gender-input" data-seat="${seat.id}" style="width: 100%; padding: 10px; background: rgba(30, 41, 59, 0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff; outline: none; cursor: pointer; font-size:0.85rem;">
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                    </div>
                </div>
            `;
        });
    }

    // Authenticate Button Click
    document.getElementById('modal-auth-submit').onclick = async () => {
        const errDiv = document.getElementById('auth-modal-error');
        errDiv.style.display = 'none';

        const email = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email || !password) {
            errDiv.innerText = 'Please enter both email and password.';
            errDiv.style.display = 'block';
            return;
        }

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                window.USER_ID = data.user.id;
                window.USER_NAME = data.user.name;
                fetchUserProfileNav();
                goToPassengerStep();
            } else {
                errDiv.innerText = data.message || 'Invalid email or password.';
                errDiv.style.display = 'block';
            }
        } catch (e) {
            errDiv.innerText = 'Server error during authentication.';
            errDiv.style.display = 'block';
        }
    };



    function fetchUserProfileNav() {
        fetch('/api/auth/profile').then(r => r.json()).then(d => {
            if (d.success) {
                const navLinks = document.querySelector('.nav-links');
                if (navLinks) {
                    const loginBtn = navLinks.querySelector('.btn-login-nav');
                    if (loginBtn) {
                        loginBtn.outerHTML = `
                            <span class="user-profile-badge" style="background: rgba(37, 99, 235, 0.08); color: var(--accent-primary); border: 1.5px solid rgba(37, 99, 235, 0.15); padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: flex; align-items: center; gap: 6px;">
                                <i class="fa-solid fa-circle-user"></i> Hi, ${d.user.name}
                            </span>
                            <a href="/logout" class="btn-logout-nav" style="background: rgba(239, 68, 68, 0.08); color: var(--accent-error); border: 1.5px solid rgba(239, 68, 68, 0.2); padding: 8px 16px; border-radius: 10px; font-weight: 700; font-size: 0.88rem; text-decoration: none; display: flex; align-items: center; gap: 6px; transition: all 0.2s;">
                                <i class="fa-solid fa-right-from-bracket"></i> Logout
                            </a>
                        `;
                        const adminNav = navLinks.querySelector('.btn-admin-nav');
                        if (adminNav) adminNav.remove();
                    }
                }
            }
        });
    }

    let passengersInfo = [];
    document.getElementById('passenger-details-submit').onclick = () => {
        passengersInfo = [];
        let valid = true;

        document.querySelectorAll('.passenger-form-item').forEach(form => {
            const seatId = form.dataset.seat;
            const nameVal = form.querySelector('.passenger-name-input').value.trim();
            const ageVal = form.querySelector('.passenger-age-input').value.trim();
            const genderVal = form.querySelector('.passenger-gender-input').value;

            if (!nameVal || !ageVal) {
                valid = false;
                return;
            }

            passengersInfo.push({
                seat_number: seatId,
                fare: bus.fare,
                passenger_name: nameVal,
                passenger_age: parseInt(ageVal, 10),
                passenger_gender: genderVal
            });
        });

        if (!valid) {
            alert('Please enter passenger name and age for all seats.');
            return;
        }

        stepPassenger.style.display = 'none';
        stepPayment.style.display = 'block';
        updateStepProgress(3);

        let totalFare = bus.fare * selectedSeats.length;
        window.CURRENT_FARE = totalFare;
        window.APPLIED_COUPON = null;

        document.getElementById('modal-fare-amount').innerText = `₹${totalFare}`;

        // Handle Coupon Application
        const applyBtn = document.getElementById('apply-coupon-btn');
        const codeInp = document.getElementById('checkout-coupon-code');

        if (applyBtn && codeInp) {
            applyBtn.onclick = async () => {
                const msg = document.getElementById('coupon-message');
                const code = codeInp.value.trim();
                if (!code) return;

                applyBtn.disabled = true;
                applyBtn.innerText = '...';

                try {
                    const res = await fetch('/api/rewards/validate-coupon', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ coupon_code: code })
                    });
                    const data = await res.json();

                    if (data.success) {
                        window.APPLIED_COUPON = code;
                        const newFare = window.CURRENT_FARE * (1.0 - data.discount_pct);
                        document.getElementById('modal-fare-amount').innerHTML = `<strike style="color:var(--text-secondary);font-size:0.8rem;">₹${window.CURRENT_FARE}</strike> ₹${newFare.toFixed(2)}`;
                        totalFare = newFare;
                        msg.style.display = 'block';
                        msg.style.color = 'var(--accent-green)';
                        msg.innerText = `Coupon Applied! You get ${data.discount_pct * 100}% off with ${data.product_name}`;

                        // Update UPI QR with new fare
                        const upiId = document.getElementById('payment-upi-id').innerText.trim() || '9390378365@axl';
                        const upiUrl = `upi://pay?pa=${upiId}&pn=SmartBus%20AI&am=${newFare.toFixed(2)}&cu=INR&tn=SmartBus%20Booking`;
                        document.getElementById('upi-qr-image').src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(upiUrl)}`;
                    } else {
                        msg.style.display = 'block';
                        msg.style.color = 'var(--accent-error)';
                        msg.innerText = data.msg || 'Invalid Coupon';
                        window.APPLIED_COUPON = null;
                        totalFare = window.CURRENT_FARE;
                        document.getElementById('modal-fare-amount').innerText = `₹${totalFare}`;
                    }
                } catch (e) {
                    msg.style.display = 'block';
                    msg.style.color = 'var(--accent-error)';
                    msg.innerText = 'Network error checking coupon';
                }
                applyBtn.disabled = false;
                applyBtn.innerText = 'Apply';
            };

            // Check if user clicked "Use in Bus Booking" from Eco Travel board
            const savedCoupon = localStorage.getItem('autoApplyCoupon');
            if (savedCoupon) {
                codeInp.value = savedCoupon;
                setTimeout(() => {
                    applyBtn.click();
                    localStorage.removeItem('autoApplyCoupon');
                }, 300);
            }
        }

        const upiId = document.getElementById('payment-upi-id').innerText.trim() || '9390378365@axl';
        const upiUrl = `upi://pay?pa=${upiId}&pn=SmartBus%20AI&am=${totalFare}&cu=INR&tn=SmartBus%20Booking`;
        document.getElementById('upi-qr-image').src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(upiUrl)}`;

        document.getElementById('card-preview-name').innerText = passengersInfo[0].passenger_name.toUpperCase();
    };

    // Payment Tab Switching
    let selectedPaymentMethod = 'UPI';
    const tabUpi = document.getElementById('pay-tab-upi');
    const tabCard = document.getElementById('pay-tab-card');
    const tabBank = document.getElementById('pay-tab-bank');

    const panelUpi = document.getElementById('pay-panel-upi');
    const panelCard = document.getElementById('pay-panel-card');
    const panelBank = document.getElementById('pay-panel-bank');

    if (tabUpi && tabCard && tabBank) {
        tabUpi.onclick = () => {
            tabUpi.classList.add('active-tab');
            tabCard.classList.remove('active-tab');
            tabBank.classList.remove('active-tab');
            panelUpi.style.display = 'block';
            panelCard.style.display = 'none';
            panelBank.style.display = 'none';
            selectedPaymentMethod = 'UPI';
        };

        tabCard.onclick = () => {
            tabCard.classList.add('active-tab');
            tabUpi.classList.remove('active-tab');
            tabBank.classList.remove('active-tab');
            panelCard.style.display = 'block';
            panelUpi.style.display = 'none';
            panelBank.style.display = 'none';
            selectedPaymentMethod = 'Card';
        };

        tabBank.onclick = () => {
            tabBank.classList.add('active-tab');
            tabUpi.classList.remove('active-tab');
            tabCard.classList.remove('active-tab');
            panelBank.style.display = 'block';
            panelUpi.style.display = 'none';
            panelCard.style.display = 'none';
            selectedPaymentMethod = 'Netbanking';
        };
    }

    // Card Input Formatting & Sync
    const cardNumInp = document.getElementById('card-number-input');
    const cardNameInp = document.getElementById('card-name-input');
    const cardExpInp = document.getElementById('card-expiry-input');
    const cardCvvInp = document.getElementById('card-cvv-input');
    const cardPreview = document.getElementById('credit-card-preview');

    if (cardNumInp) {
        cardNumInp.oninput = (e) => {
            let val = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            let formatted = '';
            for (let i = 0; i < val.length; i++) {
                if (i > 0 && i % 4 === 0) formatted += ' ';
                formatted += val[i];
            }
            e.target.value = formatted;
            document.getElementById('card-preview-number').innerText = formatted || '•••• •••• •••• ••••';
        };
    }

    if (cardNameInp) {
        cardNameInp.oninput = (e) => {
            document.getElementById('card-preview-name').innerText = e.target.value.toUpperCase() || 'CHARAN KUMAR';
        };
    }

    if (cardExpInp) {
        cardExpInp.oninput = (e) => {
            let val = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            if (val.length >= 2) {
                val = val.slice(0, 2) + '/' + val.slice(2, 4);
            }
            e.target.value = val;
            document.getElementById('card-preview-expiry').innerText = val || 'MM/YY';
        };
    }

    if (cardCvvInp) {
        cardCvvInp.onfocus = () => { cardPreview.classList.add('flipped'); };
        cardCvvInp.onblur = () => { cardPreview.classList.remove('flipped'); };
        cardCvvInp.oninput = (e) => {
            document.getElementById('card-preview-cvv').innerText = e.target.value || '•••';
        };
    }

    // Netbanking Bank Selection Buttons
    let selectedBankName = '';
    document.querySelectorAll('.bank-select-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.bank-select-btn').forEach(b => b.classList.remove('selected-bank'));
            btn.classList.add('selected-bank');
            selectedBankName = btn.dataset.bank;
            document.getElementById('bank-dropdown').value = '';
        };
    });

    const bankDropdown = document.getElementById('bank-dropdown');
    if (bankDropdown) {
        bankDropdown.onchange = (e) => {
            if (e.target.value) {
                document.querySelectorAll('.bank-select-btn').forEach(b => b.classList.remove('selected-bank'));
                selectedBankName = e.target.value;
            }
        };
    }

    function luhnCheck(val) {
        let sum = 0;
        for (let i = 0; i < val.length; i++) {
            let intVal = parseInt(val.substr(i, 1));
            if (i % 2 === val.length % 2) {
                intVal *= 2;
                if (intVal > 9) intVal -= 9;
            }
            sum += intVal;
        }
        return (sum % 10) === 0;
    }

    // Confirm Payment
    document.getElementById('payment-confirm-submit').onclick = async () => {
        let paymentData = {};
        if (selectedPaymentMethod === 'Card') {
            const rawCard = cardNumInp.value.replace(/\s+/g, '');
            if (!rawCard || !cardNameInp.value || !cardExpInp.value || !cardCvvInp.value) {
                alert('Please fill out all credit card fields.');
                return;
            }
            if (!luhnCheck(rawCard)) {
                alert('Invalid Card Number (Failed Luhn Check). Please use a valid card format.');
                return;
            }
            paymentData = {
                method: 'Card',
                card_number: rawCard,
                cvv: cardCvvInp.value,
                expiry: cardExpInp.value,
                amount: bus.fare * selectedSeats.length
            };
        } else if (selectedPaymentMethod === 'Netbanking') {
            if (!selectedBankName) {
                alert('Please select a bank to proceed.');
                return;
            }
            paymentData = { method: 'Netbanking', amount: bus.fare * selectedSeats.length };
        } else {
            paymentData = { method: 'UPI', upi_id: 'user@upi', amount: bus.fare * selectedSeats.length };
        }

        stepPayment.style.display = 'none';
        stepProcessing.style.display = 'block';

        const procTitle = document.getElementById('payment-processing-title');
        const procDesc = document.getElementById('payment-processing-desc');

        const messages = [
            { t: "Locking Seats...", d: "Securing temporary database locks for your seats..." },
            { t: "Processing Payment...", d: "Validating transaction with Secure Payment Gateway..." },
            { t: "Confirming Transaction...", d: "Committing booking status, logging ledger and updating footprint data..." }
        ];

        let msgIdx = 0;
        const msgInterval = setInterval(() => {
            if (msgIdx < messages.length) {
                procTitle.innerText = messages[msgIdx].t;
                procDesc.innerText = messages[msgIdx].d;
                msgIdx++;
            }
        }, 500);

        try {
            // Lock all selected seats
            for (let seat of selectedSeats) {
                await fetch('/api/booking/lock-seat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ schedule_id: bus.schedule_id, seat_number: seat.id })
                });
            }

            // Process secure payment handshake
            const payRes = await fetch('/api/booking/process-payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(paymentData)
            });
            const payResult = await payRes.json();

            if (!payRes.ok || !payResult.success) {
                clearInterval(msgInterval);
                alert('Payment Processing Failed: ' + (payResult.error || 'Gateway Error'));
                stepProcessing.style.display = 'none';
                stepPayment.style.display = 'block';
                return;
            }

            // Perform checkout
            const res = await fetch('/api/booking/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: window.USER_ID || 1,
                    schedule_id: bus.schedule_id,
                    payment_method: selectedPaymentMethod === 'Netbanking' ? `Netbanking (${selectedBankName})` : selectedPaymentMethod,
                    bookings: passengersInfo,
                    transaction_id: payResult.transaction_id,
                    card_number: selectedPaymentMethod === 'Card' ? cardNumInp.value.replace(/\s+/g, '') : undefined,
                    cvv: selectedPaymentMethod === 'Card' ? cardCvvInp.value : undefined,
                    expiry: selectedPaymentMethod === 'Card' ? cardExpInp.value : undefined,
                    upi_id: selectedPaymentMethod === 'UPI' ? 'user@upi' : undefined,
                    coupon_code: window.APPLIED_COUPON || undefined
                })
            });

            clearInterval(msgInterval);

            if (res.ok) {
                const checkoutResult = await res.json();

                setTimeout(() => {
                    stepProcessing.style.display = 'none';
                    stepSuccess.style.display = 'block';

                    const successContainer = document.getElementById('success-tickets-container');
                    successContainer.innerHTML = '';

                    if (checkoutResult.booking_ids && checkoutResult.booking_ids.length > 0) {
                        const dlBtn = document.getElementById('success-download-ticket');
                        if (dlBtn) {
                            dlBtn.onclick = () => {
                                window.open('/api/booking/download-ticket?ids=' + checkoutResult.booking_ids.join(','), '_blank');
                            };
                        }
                    }

                    const details = checkoutResult.payment.details || [];

                    details.forEach((ticket, idx) => {
                        const pass = passengersInfo[idx] || {};
                        successContainer.innerHTML += `
                            <div style="border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 12px; font-size:0.85rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                    <span style="color: var(--text-secondary);">Ticket ID</span>
                                    <strong style="color: #fff;">#TXN-${ticket.booking_id}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">Passenger</span>
                                    <strong style="color: #fff;">${pass.passenger_name} (${pass.passenger_age < 18 ? 'Child' : 'Adult'}, Age: ${pass.passenger_age}, ${pass.passenger_gender})</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">Seat Assigned</span>
                                    <strong style="color: var(--accent-primary);">Seat ${ticket.seat_number}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-secondary);">Amount Charged</span>
                                    <strong style="color: #fff;">₹${ticket.amount}</strong>
                                </div>
                            </div>
                        `;
                    });

                    successContainer.innerHTML += `
                        <div style="font-size:0.8rem; color: rgba(255,255,255,0.6); margin-top: 10px;">
                            Payment processed securely via <strong>${selectedPaymentMethod}</strong>.
                        </div>
                    `;
                }, 800);
            } else {
                const data = await res.json();
                stepProcessing.style.display = 'none';
                stepPayment.style.display = 'block';
                alert(`Booking error: ${data.error || data.msg}`);
            }

        } catch (err) {
            clearInterval(msgInterval);
            console.error(err);
            stepProcessing.style.display = 'none';
            stepPayment.style.display = 'block';
            alert('Booking failed due to a network or server error.');
        }
    };

    // Final Dashboard Redirect
    const dashboardRedirectBtn = document.getElementById('success-dashboard-redirect');
    const pendingLeg2Str = localStorage.getItem('pendingSplitLeg2');

    if (pendingLeg2Str) {
        dashboardRedirectBtn.innerText = 'Book Next Leg (Leg 2) →';
        dashboardRedirectBtn.style.background = 'linear-gradient(135deg, var(--accent-purple), #4f46e5)';
        dashboardRedirectBtn.onclick = () => {
            localStorage.setItem('selectedBusData', pendingLeg2Str);
            localStorage.removeItem('pendingSplitLeg2');
            window.location.reload();
        };
    } else {
        dashboardRedirectBtn.onclick = () => {
            window.location.href = '/dashboard';
        };
    }
});
