document.addEventListener('DOMContentLoaded', async () => {
    const rawData = localStorage.getItem('selectedBusData');
    if (!rawData) {
        alert("No bus selected! Redirecting to home...");
        window.location.href = '/';
        return;
    }

    const bus = JSON.parse(rawData);

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
            
            Object.keys(rows).sort((a,b) => a-b).forEach(r => {
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
        attachSeatEvents(seats, fare);
    }

    function attachSeatEvents(seats, fare) {
        document.querySelectorAll('.seat-btn').forEach(seatEl => {
            if (seatEl.dataset.booked === 'true') return;
            seatEl.addEventListener('click', () => {
                document.querySelectorAll('.seat-btn').forEach(s => {
                    const booked = s.dataset.booked === 'true';
                    s.style.background = booked ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.8)';
                    s.style.borderColor = booked ? 'transparent' : 'rgba(0,0,0,0.05)';
                    s.style.color = booked ? 'rgba(0,0,0,0.1)' : 'rgba(15, 23, 42, 0.6)';
                    s.style.transform = 'translateZ(0)';
                    s.classList.remove('selected-seat-3d');
                });
                
                seatEl.style.background = 'var(--accent-primary)';
                seatEl.style.borderColor = 'var(--accent-primary)';
                seatEl.style.color = '#fff';
                seatEl.classList.add('selected-seat-3d');
                seatEl.style.boxShadow = '0 10px 25px rgba(37, 99, 235, 0.3)';

                const seatId = seatEl.dataset.id;
                const seatData = seats.find(s => s.id === seatId);
                showSeatDetails(seatData, fare);
            });
        });
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
        let gradient = ctx.createLinearGradient(0, 0, 0, 100);
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.4)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Trip 1', 'Trip 2', 'Trip 3', 'Trip 4', 'Trip 5'],
                datasets: [{
                    label: 'On-Time %',
                    data: data,
                    borderColor: 'var(--accent-primary)',
                    backgroundColor: gradient,
                    borderWidth: 2,
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
        let icon = seat.type === 'Window' ? '🪟' : '💺';
        if (isSleeper) {
            icon = seat.type.includes('Double') ? '🛌🛌' : '🛌';
        }
        
        return `<div class="seat-btn ${isSleeper ? 'berth-btn' : ''}"
            data-id="${seat.id}"
            data-booked="${isBooked}"
            title="${seat.id} · ${seat.type} · ${seat.zone}"
            style="
                background: ${isBooked ? 'rgba(0,0,0,0.02)' : 'rgba(255,255,255,0.8)'};
                border: 1.5px solid ${isBooked ? 'transparent' : 'rgba(0,0,0,0.05)'};
                border-radius: ${isSleeper ? '15px' : '12px'};
                padding: 12px 6px;
                text-align: center;
                cursor: ${isBooked ? 'not-allowed' : 'pointer'};
                transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
                color: ${isBooked ? 'rgba(0,0,0,0.1)' : 'rgba(15, 23, 42, 0.7)'};
                font-size: 0.75rem;
                font-weight: 700;
                user-select: none;
                position: relative;
                transform-style: preserve-3d;
                box-shadow: ${isBooked ? 'none' : '0 4px 10px rgba(0,0,0,0.05)'};
            ">
            <div style="font-size: ${isSleeper ? '1.8rem' : '1.4rem'}; margin-bottom: 6px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1)); transform: translateZ(10px);">${isBooked ? '🚫' : icon}</div>
            <div style="transform: translateZ(5px); transition: 0.3s; color: inherit;">${seat.id}</div>
            ${isSleeper && !isBooked ? '<div style="position:absolute; bottom:5px; left:50%; transform:translateX(-50%); font-size:0.5rem; opacity:0.6; letter-spacing:1px; color: var(--text-secondary);">SLEEPER</div>' : ''}
        </div>`;
    }

    // ── 360° View Engine ──────────────────────────────────────
    let rotY = 0, rotX = 0;
    const busView = document.getElementById('bus-360-view');

    const viewAngles = {
        front: { x: 45, y: 0,  z: -100, cockpit: 1 },
        mid:   { x: 15, y: -15, z: 0, cockpit: 0.8 },
        top:   { x: 60, y: 0,  z: 50, cockpit: 0.5 },
        side:  { x: 0,  y: 65, z: 100, cockpit: 0.2 }
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

    function showSeatDetails(seat, fare) {
        document.getElementById('seat-metrics').style.opacity = '1';
        document.getElementById('selected-seat-title').innerHTML =
            `Seat <strong>${seat.id}</strong> <span style="background:#2563eb;color:#fff;padding:2px 10px;border-radius:20px;font-size:0.8rem;margin-left:6px;">₹${fare}</span>`;
        document.getElementById('seat-noise').innerText = `${seat.noise_db} dB`;
        document.getElementById('seat-vibe').innerText = seat.vibration;
        document.getElementById('seat-type').innerText = seat.type;
        document.getElementById('seat-zone').innerText = seat.zone;

        if (seat.zone === 'Back') {
            document.getElementById('seat-vibe').style.color = '#ef4444';
        } else if (seat.zone === 'Front') {
            document.getElementById('seat-vibe').style.color = '#10b981';
        } else {
            document.getElementById('seat-vibe').style.color = '';
        }

        const btn = document.getElementById('btn-book');
        btn.disabled = false;
        btn.classList.add('pulse-glow');
        btn.innerHTML = `<i class="fa-solid fa-lock"></i> Secure Seat ${seat.id}`;

        // Multi-Step Checkout Modal Setup
        const modal = document.getElementById('checkout-modal');
        const modalContent = document.getElementById('checkout-modal-content');
        const closeModalBtn = document.getElementById('close-checkout-modal');
        
        // Progress elements
        const step1Ind = document.getElementById('step-1-indicator');
        const step2Ind = document.getElementById('step-2-indicator');
        const step3Ind = document.getElementById('step-3-indicator');
        const line1 = document.getElementById('line-step-1');
        const line2 = document.getElementById('line-step-2');
        const lbl1 = document.getElementById('lbl-step-1');
        const lbl2 = document.getElementById('lbl-step-2');
        const lbl3 = document.getElementById('lbl-step-3');

        // Containers
        const stepAuth = document.getElementById('checkout-step-auth');
        const stepPassenger = document.getElementById('checkout-step-passenger');
        const stepPayment = document.getElementById('checkout-step-payment');
        const stepProcessing = document.getElementById('checkout-step-processing');
        const stepSuccess = document.getElementById('checkout-step-success');

        // Inputs
        const emailInput = document.getElementById('modal-email-input');
        const passwordInput = document.getElementById('modal-password-input');
        const phoneInput = document.getElementById('modal-phone-input');
        const passengerNameInput = document.getElementById('passenger-name-input');
        const passengerAgeInput = document.getElementById('passenger-age-input');
        const passengerGenderInput = document.getElementById('passenger-gender-input');

        // Tabs
        const tabEmail = document.getElementById('modal-tab-email');
        const tabOtp = document.getElementById('modal-tab-otp');
        const emailForm = document.getElementById('modal-auth-email-form');
        const otpForm = document.getElementById('modal-auth-otp-form');
        let currentAuthMode = 'email';

        // Tab Switching
        tabEmail.onclick = () => {
            tabEmail.classList.add('active-tab');
            tabOtp.classList.remove('active-tab');
            emailForm.style.display = 'block';
            otpForm.style.display = 'none';
            currentAuthMode = 'email';
        };
        tabOtp.onclick = () => {
            tabOtp.classList.add('active-tab');
            tabEmail.classList.remove('active-tab');
            otpForm.style.display = 'block';
            emailForm.style.display = 'none';
            currentAuthMode = 'otp';
        };

        // OTP inputs autofocus hopping
        const digits = document.querySelectorAll('.modal-otp-digit');
        digits.forEach((digit, idx) => {
            digit.oninput = () => {
                if (digit.value && idx < digits.length - 1) {
                    digits[idx + 1].focus();
                }
            };
            digit.onkeydown = (e) => {
                if (e.key === 'Backspace' && !digit.value && idx > 0) {
                    digits[idx - 1].focus();
                }
            };
        });

        // Close modal
        closeModalBtn.onclick = () => {
            modal.style.opacity = '0';
            modalContent.style.transform = 'scale(0.95)';
            setTimeout(() => {
                modal.style.display = 'none';
            }, 400);
        };

        // Click secure button
        btn.onclick = () => {
            // Setup seat and fare parameters
            document.getElementById('modal-seat-id-1').innerText = seat.id;
            document.getElementById('modal-seat-id-2').innerText = seat.id;
            document.getElementById('modal-seat-id-3').innerText = seat.id;
            document.getElementById('modal-fare-amount').innerText = `₹${bus.fare}`;

            // Reset containers
            stepAuth.style.display = 'none';
            stepPassenger.style.display = 'none';
            stepPayment.style.display = 'none';
            stepProcessing.style.display = 'none';
            stepSuccess.style.display = 'none';
            document.getElementById('auth-modal-error').style.display = 'none';

            // Show Modal with animation
            modal.style.display = 'flex';
            setTimeout(() => {
                modal.style.opacity = '1';
                modalContent.style.transform = 'scale(1)';
            }, 10);

            if (window.USER_ID) {
                // User is already logged in, proceed to passenger details directly
                goToPassengerStep();
            } else {
                // Show Auth verification step
                stepAuth.style.display = 'block';
                updateStepProgress(1);
            }
        };

        function updateStepProgress(step) {
            // Reset indicators
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
            passengerNameInput.value = window.USER_NAME || '';
        }

        // Authenticate Button Click
        document.getElementById('modal-auth-submit').onclick = async () => {
            const errDiv = document.getElementById('auth-modal-error');
            errDiv.style.display = 'none';

            if (currentAuthMode === 'email') {
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
                        // Dynamically update main navbar profile if present
                        const navLoginBtn = document.getElementById('navbar-login-btn') || document.querySelector('.navbar-end .glass-panel');
                        if (navLoginBtn) {
                            navLoginBtn.innerHTML = `<span style="color: var(--accent-primary);"><i class="fa-solid fa-user-check"></i> Hi, ${data.user.name}</span>`;
                        }
                        goToPassengerStep();
                    } else {
                        errDiv.innerText = data.message || 'Invalid email or password.';
                        errDiv.style.display = 'block';
                    }
                } catch (e) {
                    errDiv.innerText = 'Server error during authentication.';
                    errDiv.style.display = 'block';
                }
            } else {
                // OTP Mobile Mode
                const phone = phoneInput.value.trim();
                let otp = '';
                digits.forEach(d => otp += d.value);

                if (phone.length < 10 || otp.length < 4) {
                    errDiv.innerText = 'Please enter a valid 10-digit phone number and 4-digit OTP.';
                    errDiv.style.display = 'block';
                    return;
                }

                // Simulating seamless OTP checkout by logging in Charan Kumar backend credentials!
                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: 'charan@example.com', password: 'password123' })
                    });
                    const data = await res.json();
                    if (res.ok && data.success) {
                        window.USER_ID = data.user.id;
                        window.USER_NAME = data.user.name;
                        const navLoginBtn = document.getElementById('navbar-login-btn') || document.querySelector('.navbar-end .glass-panel');
                        if (navLoginBtn) {
                            navLoginBtn.innerHTML = `<span style="color: var(--accent-primary);"><i class="fa-solid fa-user-check"></i> Hi, ${data.user.name}</span>`;
                        }
                        goToPassengerStep();
                    } else {
                        errDiv.innerText = 'OTP Verification failed.';
                        errDiv.style.display = 'block';
                    }
                } catch (e) {
                    errDiv.innerText = 'Server error during OTP verification.';
                    errDiv.style.display = 'block';
                }
            }
        };

        // Passenger Form Submit
        document.getElementById('passenger-details-submit').onclick = () => {
            const name = passengerNameInput.value.trim();
            const age = passengerAgeInput.value.trim();

            if (!name || !age) {
                alert('Please enter passenger name and age.');
                return;
            }

            document.getElementById('credit-card-holder-name').innerText = name.toUpperCase();
            
            // Go to step 3 (Payment)
            stepPassenger.style.display = 'none';
            stepPayment.style.display = 'block';
            updateStepProgress(3);
        };

        // Payment Submit (Pay & Confirm)
        document.getElementById('payment-confirm-submit').onclick = async () => {
            stepPayment.style.display = 'none';
            stepProcessing.style.display = 'block';

            try {
                // 1. Lock the seat
                await fetch('/api/booking/lock-seat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ schedule_id: bus.schedule_id, seat_number: seat.id })
                });

                // 2. Perform the database checkout!
                const res = await fetch('/api/booking/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: window.USER_ID,
                        schedule_id: bus.schedule_id,
                        seat_number: seat.id,
                        fare: bus.fare
                    })
                });

                const data = await res.json();
                
                // Add simulated glowing delay for absolute premium payment experience
                setTimeout(() => {
                    if (res.ok) {
                        stepProcessing.style.display = 'none';
                        stepSuccess.style.display = 'block';

                        // Fill success summary card details
                        document.getElementById('success-ticket-id').innerText = `#TXN-${data.booking_id}`;
                        document.getElementById('success-passenger-name').innerText = passengerNameInput.value.trim();
                        document.getElementById('success-seat-id').innerText = `Seat ${seat.id}`;
                        document.getElementById('success-fare-amount').innerText = `₹${bus.fare}`;
                    } else {
                        stepProcessing.style.display = 'none';
                        stepPayment.style.display = 'block';
                        alert(`Double booking or transaction error: ${data.error || data.msg}`);
                    }
                }, 1800);

            } catch (err) {
                console.error(err);
                stepProcessing.style.display = 'none';
                stepPayment.style.display = 'block';
                alert('Booking failed due to a network or server error.');
            }
        };

        // Final Dashboard Redirect
        document.getElementById('success-dashboard-redirect').onclick = () => {
            window.location.href = '/dashboard';
        };
    }
});
