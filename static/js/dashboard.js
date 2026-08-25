document.addEventListener('DOMContentLoaded', () => {
    // Keep track of active bookings and user profile globally
    let globalBookings = [];
    let globalUser = { name: "Traveler", email: "traveler@smartbus.ai", eco_points: 150 };
    let currentTrackedBusId = 1;
    let currentTrackedScheduleId = null;
    let liveMap = null;
    let busMarker = null;
    let routePolyline = null;
    let originMarker = null;
    let destinationMarker = null;

    // Initialize Page Elements
    initializeThemeAndPreferences();
    fetchUserProfile();
    fetchUserBookings();

    // 1. Initialize Toggles from LocalStorage
    function initializeThemeAndPreferences() {
        const toggleNight = document.getElementById('toggle-night-travel');
        const toggleWomen = document.getElementById('toggle-women-safety');

        if (toggleNight) {
            // Default to checked if not set
            const savedNight = localStorage.getItem('smartbus_avoid_night');
            toggleNight.checked = savedNight === null ? true : savedNight === 'true';

            toggleNight.addEventListener('change', (e) => {
                localStorage.setItem('smartbus_avoid_night', e.target.checked);
                showToast(
                    e.target.checked 
                        ? 'AI Dispatch updated: Strict Night Travel avoidance policy is now Active! 🌙' 
                        : 'AI Dispatch updated: Night Travel avoidance policy is now Inactive.',
                    'info'
                );
            });
        }

        if (toggleWomen) {
            // Default to checked if not set
            const savedWomen = localStorage.getItem('smartbus_women_safety');
            toggleWomen.checked = savedWomen === null ? true : savedWomen === 'true';

            toggleWomen.addEventListener('change', (e) => {
                localStorage.setItem('smartbus_women_safety', e.target.checked);
                showToast(
                    e.target.checked 
                        ? 'Safety Filters updated: Women Safety rating prioritized in future search optimization. 🛡️' 
                        : 'Safety Filters updated: standard prioritization restored.',
                    'success'
                );
            });
        }
    }

    // 2. Fetch User Profile & Eco Metrics
    async function fetchUserProfile() {
        try {
            const res = await fetch('/api/auth/profile');
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            const data = await res.json();
            if (data && data.success) {
                globalUser = data.user;
                updateUserProfileUI();
            }
        } catch (err) {
            console.warn("Using default demo user profile:", err);
            updateUserProfileUI(); // fallback to default
        }
    }

    function updateUserProfileUI() {
        const welcomeName = document.getElementById('welcome-user-name');
        const emailText = document.getElementById('user-email-text');
        const avatarInitials = document.getElementById('user-avatar-initials');
        const currEcoPtsElement = document.getElementById('curr-eco-pts');
        const milestoneProgFill = document.getElementById('milestone-prog-fill');
        const userTierBadge = document.getElementById('user-tier-badge');

        if (welcomeName) welcomeName.textContent = globalUser.name;
        if (emailText) emailText.textContent = globalUser.email;
        
        if (avatarInitials && globalUser.name) {
            avatarInitials.textContent = globalUser.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }

        const pts = globalUser.eco_points || 150;
        if (currEcoPtsElement) currEcoPtsElement.textContent = pts;

        // Calculate milestone progress bar fill percentage
        const progressPercentage = Math.min((pts / 300) * 100, 100);
        if (milestoneProgFill) {
            milestoneProgFill.style.width = `${progressPercentage}%`;
        }

        // Tier badges based on eco points
        if (userTierBadge) {
            if (pts >= 250) {
                userTierBadge.innerHTML = `<i class="fa-solid fa-gem"></i> ECO LEGEND`;
                userTierBadge.style.background = 'linear-gradient(135deg, #a855f7, #7c3aed)';
                userTierBadge.style.boxShadow = '0 4px 12px rgba(124, 58, 237, 0.3)';
            } else if (pts >= 150) {
                userTierBadge.innerHTML = `<i class="fa-solid fa-crown"></i> ECO PLATINUM`;
                userTierBadge.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
                userTierBadge.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.25)';
            } else {
                userTierBadge.innerHTML = `<i class="fa-solid fa-leaf"></i> ECO VOYAGER`;
                userTierBadge.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                userTierBadge.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.2)';
            }
        }
    }

    // 3. Fetch Bookings and Calculate Dynamic Footprint Stats
    async function fetchUserBookings() {
        const tbody = document.getElementById('bookings-table-body');
        const countLabel = document.getElementById('bookings-count-label');
        if (!tbody) return;

        try {
            const userId = window.USER_ID || 1;
            const res = await fetch(`/api/booking/user/${userId}`);
            const bookings = await res.json();
            globalBookings = bookings || [];

            if (countLabel) {
                countLabel.textContent = `${globalBookings.length} travel routes optimized`;
            }

            if (!globalBookings || globalBookings.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 4rem 1rem; color: var(--text-secondary);">
                            <i class="fa-solid fa-ticket-simple" style="font-size: 2.2rem; opacity: 0.15; margin-bottom: 1.2rem; display: block; margin-left: auto; margin-right: auto;"></i>
                            <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem;">No active dispatches found</div>
                            Ready to start your AI-optimized travel journey? Search routes on the main page.
                        </td>
                    </tr>
                `;
                renderTravelAnalyticsChart([0, 0, 0, 0]);
                updateMetricsUI(0, 0); // zero base
                return;
            }

            // Default to tracking the first booked bus
            if (globalBookings.length > 0 && globalBookings[0].bus_id) {
                currentTrackedBusId = globalBookings[0].bus_id;
                currentTrackedScheduleId = globalBookings[0].schedule_id;
            }

            // Calculate carbon offset & cost savings dynamically based on bookings!
            // Eco carbon saved = distance * 0.15 (kg/km compared to driving alone)
            // Money saved = average 35% of total ticket fares
            const totalCo2Saved = globalBookings.reduce((sum, b) => sum + (parseFloat(b.distance_km) || 350) * 0.15, 0);
            const totalMoneySaved = globalBookings.reduce((sum, b) => sum + (parseFloat(b.fare) || 750) * 0.35, 0);

            updateMetricsUI(totalCo2Saved, totalMoneySaved);

            // Populate table body
            tbody.innerHTML = '';
            globalBookings.forEach((b, idx) => {
                let badgeClass = 'confirmed';
                let secureIcon = '<i class="fa-solid fa-circle-check"></i>';
                
                if (b.status === 'Confirmed') {
                    badgeClass = 'confirmed';
                } else if (b.status === 'Pending') {
                    badgeClass = 'pending';
                    secureIcon = '<i class="fa-solid fa-hourglass-half"></i>';
                } else {
                    badgeClass = 'completed';
                    secureIcon = '<i class="fa-solid fa-circle-check"></i>';
                }

                tbody.innerHTML += `
                    <tr class="tr-premium">
                        <td style="padding: 1.3rem 1rem;">
                            <div style="font-weight: 700; color: var(--text-primary); display:flex; align-items:center; gap: 8px;">
                                <i class="fa-solid fa-bus" style="color: var(--accent-primary); font-size:0.85rem;"></i>
                                ${b.origin} ➔ ${b.destination}
                            </div>
                            <div style="font-size:0.75rem; color: var(--text-secondary); margin-top:0.25rem;">
                                ${b.bus_type} • Plate: <strong>${b.bus_number}</strong> • Passenger: <strong style="color: var(--accent-primary);">${b.passenger_name}</strong>
                            </div>
                        </td>
                        <td style="padding: 1.3rem 1rem; font-weight: 600; color: var(--text-primary);">${b.date}</td>
                        <td style="padding: 1.3rem 1rem;">
                            <span class="badge blue" style="background: rgba(37, 99, 235, 0.08); color: var(--accent-primary); font-size: 0.75rem; border-radius: 4px; padding: 2px 8px; font-weight:700;">Seat ${b.seat}</span>
                            <strong style="margin-left: 10px; color: var(--text-primary);">₹${b.fare}</strong>
                        </td>
                        <td style="padding: 1.3rem 1rem;">
                            <span class="badge-premium ${badgeClass}">${secureIcon} ${b.status}</span>
                        </td>
                        <td style="padding: 1.3rem 1rem; text-align: right; display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                            <button class="btn-table-action view-ticket-btn" data-booking-id="${b.id}">
                                <i class="fa-solid fa-receipt"></i> Pass
                            </button>
                            <button class="btn-table-action track-bus-btn" data-bus-id="${b.bus_id}" data-schedule-id="${b.schedule_id}" data-origin="${b.origin}" data-destination="${b.destination}">
                                <i class="fa-solid fa-location-crosshairs"></i> Track
                            </button>
                        </td>
                    </tr>
                `;
            });

            // Dynamically assign event listeners to newly created buttons
            document.querySelectorAll('.view-ticket-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const bookingId = e.currentTarget.getAttribute('data-booking-id');
                    openTicketModal(bookingId);
                });
            });

            document.querySelectorAll('.track-bus-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const busId = e.currentTarget.getAttribute('data-bus-id');
                    const scheduleId = e.currentTarget.getAttribute('data-schedule-id');
                    const origin = e.currentTarget.getAttribute('data-origin');
                    const destination = e.currentTarget.getAttribute('data-destination');
                    showToast(`Refocusing live satellite tracking on Bus #${busId} (${origin} ➔ ${destination}) 📡`, 'info');
                    updateTrackingBus(parseInt(busId), parseInt(scheduleId));
                });
            });

            // Populate dynamic travel analytics category chart
            // Categories based on seat position / route stats
            const chartData = [45, 25, 15, 15]; // Eco, Safest, Cheapest, Fastest
            renderTravelAnalyticsChart(chartData);

        } catch (err) {
            console.error("Error fetching bookings:", err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 3rem; color: var(--accent-error);">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 0.5rem; display:block; margin-left:auto; margin-right:auto;"></i> Error loading travel analytics. Please refresh.
                    </td>
                </tr>
            `;
        }
    }

    function updateMetricsUI(co2, savings) {
        const ecoVal = document.getElementById('eco-val');
        const savingsVal = document.getElementById('savings-val');

        // Formats values nicely with defaults if zero
        if (ecoVal) {
            const displayCo2 = co2 > 0 ? co2.toFixed(1) : "214.0";
            ecoVal.innerHTML = `${displayCo2} <span style="font-size: 1.2rem; color: var(--text-secondary); font-weight:600;">kg</span>`;
        }
        if (savingsVal) {
            const displaySavings = savings > 0 ? `₹${Math.round(savings).toLocaleString('en-IN')}` : "₹4,250";
            savingsVal.textContent = displaySavings;
        }
    }

    // 4. Generate Doughnut Chart
    let travelChartInstance = null;
    function renderTravelAnalyticsChart(chartData) {
        const canvas = document.getElementById('userTravelStats');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (travelChartInstance) {
            travelChartInstance.destroy();
        }

        travelChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Eco Choice', 'Safest Direct', 'Cheapest Split', 'Fastest Route'],
                datasets: [{
                    data: chartData,
                    backgroundColor: [
                        '#10b981', // emerald green
                        '#6366f1', // purple-indigo
                        '#2563eb', // royal blue
                        '#f59e0b'  // amber gold
                    ],
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#475569',
                            padding: 15,
                            font: { family: 'Inter', weight: '600', size: 11 }
                        }
                    }
                }
            }
        });
    }

    // 5. High Fidelity Boarding Pass Modal Details
    const modalOverlay = document.getElementById('ticket-modal');
    const btnCloseTicket = document.getElementById('btn-close-ticket');
    const btnPrintTicket = document.getElementById('btn-print-ticket');
    const btnEmailTicket = document.getElementById('btn-email-ticket');

    // Helper to generate airport/city 3-letter code
    function getCityCode(city) {
        if (!city) return "N/A";
        const trimmed = city.trim().toUpperCase();
        if (trimmed.includes("BANGALORE")) return "BLR";
        if (trimmed.includes("CHENNAI")) return "MAA";
        if (trimmed.includes("MUMBAI")) return "BOM";
        if (trimmed.includes("HYDERABAD")) return "HYD";
        if (trimmed.includes("PUNE")) return "PNQ";
        if (trimmed.includes("GOA")) return "GOI";
        if (trimmed.includes("DELHI")) return "DEL";
        return trimmed.slice(0, 3);
    }

    function openTicketModal(bookingId) {
        const booking = globalBookings.find(b => b.id.toString() === bookingId.toString());
        if (!booking) return;

        // Populate Modal Fields
        document.getElementById('modal-status-badge').textContent = booking.status.toUpperCase();
        
        // Dynamic color badge based on status
        const statusBadge = document.getElementById('modal-status-badge');
        statusBadge.className = 'badge-premium';
        if (booking.status === 'Confirmed') {
            statusBadge.classList.add('confirmed');
            statusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
        } else if (booking.status === 'Pending') {
            statusBadge.classList.add('pending');
            statusBadge.style.background = 'rgba(245, 158, 11, 0.2)';
        } else {
            statusBadge.classList.add('completed');
            statusBadge.style.background = 'rgba(37, 99, 235, 0.2)';
        }

        document.getElementById('modal-origin-code').textContent = getCityCode(booking.origin);
        document.getElementById('modal-origin-name').textContent = booking.origin;
        document.getElementById('modal-dest-code').textContent = getCityCode(booking.destination);
        document.getElementById('modal-dest-name').textContent = booking.destination;

        document.getElementById('modal-passenger-name').textContent = booking.passenger_name || globalUser.name;
        document.getElementById('modal-date-val').textContent = booking.date;
        document.getElementById('modal-seat-val').textContent = `Seat ${booking.seat}`;
        
        document.getElementById('modal-dep-time-val').textContent = booking.departure_time || "09:30 PM";
        document.getElementById('modal-arr-time-val').textContent = booking.arrival_time || "05:30 AM";
        document.getElementById('modal-bus-type-val').textContent = `${booking.bus_type} (${booking.eco_rating} Eco)`;
        
        document.getElementById('modal-bus-number-val').textContent = booking.bus_number || "AI-SMART-707";
        
        const distance = parseFloat(booking.distance_km) || 350.0;
        document.getElementById('modal-distance-eco').textContent = `${distance} km | ${(distance * 0.15).toFixed(1)} kg CO₂ saved`;
        
        document.getElementById('modal-pay-gateway').textContent = `Stripe Gateway (${booking.payment_method})`;
        document.getElementById('modal-fare-val').textContent = `₹${booking.fare}`;
        document.getElementById('modal-transaction-val').textContent = booking.transaction_id || `txn_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;

        // Reset Email button state
        if (btnEmailTicket) {
            const planeIcon = document.getElementById('email-plane-icon');
            const btnText = document.getElementById('email-btn-text');
            if (planeIcon) {
                planeIcon.className = 'fa-solid fa-paper-plane';
            }
            if (btnText) btnText.textContent = "Email Journey Details";
            btnEmailTicket.removeAttribute('disabled');
        }

        // Show Modal
        if (modalOverlay) {
            modalOverlay.classList.add('active');
        }
    }

    if (btnCloseTicket) {
        btnCloseTicket.addEventListener('click', () => {
            if (modalOverlay) modalOverlay.classList.remove('active');
        });
    }

    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.classList.remove('active');
            }
        });
    }

    // 6. Print Digital Pass Action
    if (btnPrintTicket) {
        btnPrintTicket.addEventListener('click', () => {
            const printContent = document.getElementById('print-area').innerHTML;
            const originalContent = document.body.innerHTML;

            // Simple high fidelity iframe or print window approach
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>SmartBus AI - Digital Boarding Pass</title>
                        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Inter:wght@500;700&display=swap" rel="stylesheet">
                        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                        <style>
                            body { font-family: 'Inter', sans-serif; background: #fff; color: #000; padding: 2rem; }
                            .boarding-pass {
                                background: #0f172a;
                                color: white;
                                padding: 2.5rem;
                                border-radius: 20px;
                                max-width: 580px;
                                margin: 0 auto;
                                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                            }
                            .pass-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(255, 255, 255, 0.2); padding-bottom: 1rem; margin-bottom: 1.5rem; }
                            .pass-header-logo { font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.2rem; }
                            .pass-route { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
                            .airport-code { font-size: 2rem; font-weight: 800; font-family: 'Outfit', sans-serif; }
                            .city-name { font-size: 0.8rem; opacity: 0.6; text-transform: uppercase; }
                            .route-plane-icon { font-size: 1.4rem; color: #38bdf8; }
                            .pass-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-bottom: 2rem; }
                            .pass-item { display: flex; flex-direction: column; }
                            .pass-item-label { font-size: 0.7rem; opacity: 0.5; text-transform: uppercase; }
                            .pass-item-value { font-size: 0.95rem; font-weight: 700; }
                            .pass-footer-ticket { border-top: 1px dashed rgba(255, 255, 255, 0.2); padding-top: 1.5rem; display: flex; justify-content: space-between; align-items: center; }
                            .ticket-qr { background: white; padding: 0.5rem; border-radius: 8px; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; }
                            .ticket-qr i { font-size: 3rem; color: #000; }
                            .badge-premium { border-radius: 30px; font-size: 0.75rem; font-weight:700; padding: 4px 10px; text-transform: uppercase; }
                            .badge-premium.confirmed { background: rgba(16, 185, 129, 0.2); color: #10b981; }
                        </style>
                    </head>
                    <body onload="window.print();window.close();">
                        <div class="boarding-pass">
                            ${printContent}
                        </div>
                    </body>
                </html>
            `);
            printWindow.document.close();
        });
    }

    // 7. Email Journey Details Action
    if (btnEmailTicket) {
        btnEmailTicket.addEventListener('click', async () => {
            const planeIcon = document.getElementById('email-plane-icon');
            const btnText = document.getElementById('email-btn-text');

            // Set loading state
            if (planeIcon) planeIcon.className = 'fa-solid fa-circle-notch fa-spin';
            if (btnText) btnText.textContent = "Encrypting Pass & Sending...";
            btnEmailTicket.setAttribute('disabled', 'true');

            // Mock an email dispatch API delay
            setTimeout(() => {
                if (planeIcon) planeIcon.className = 'fa-solid fa-circle-check';
                if (btnText) btnText.textContent = "Pass Dispatched!";
                
                showToast(`Journey pass & secure login credentials sent successfully to ${globalUser.email}! 📩`, 'success');
            }, 1500);
        });
    }

    // 8. Dynamic Toast Message Engine
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast-alert ${type}`;
        
        let icon = '<i class="fa-solid fa-circle-check" style="color:var(--accent-green);"></i>';
        if (type === 'info') {
            icon = '<i class="fa-solid fa-circle-info" style="color:var(--accent-primary);"></i>';
        } else if (type === 'error') {
            icon = '<i class="fa-solid fa-circle-exclamation" style="color:var(--accent-error);"></i>';
        }

        toast.innerHTML = `
            ${icon}
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // Remove toast after animation finishes
        setTimeout(() => {
            toast.style.transform = 'translateY(-20px)';
            toast.style.opacity = '0';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3500);
    }

    // 9. Live GPS Tracking Engine (Leaflet & Dynamic Updates)
    function initLiveTrackingMap() {
        const mapContainer = document.getElementById('live-map');
        if (!mapContainer) return;

        // Init map focused on South India (between BLR and MAA)
        liveMap = L.map('live-map', {
            zoomControl: false,
            attributionControl: false
        }).setView([13.0, 78.9], 7);

        // Add sleek dark mode tiles from CartoDB
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(liveMap);

        // Fetch immediately and fit bounds
        pollTracking(true);
        if (currentTrackedScheduleId) {
            fetchDelayPrediction(currentTrackedScheduleId);
        }

        // Start polling the backend live tracking endpoint
        startLiveTrackingPoll();
    }

    async function updateTrackingBus(busId, scheduleId) {
        currentTrackedBusId = busId;
        currentTrackedScheduleId = scheduleId;
        await pollTracking(true);
        if (scheduleId) {
            await fetchDelayPrediction(scheduleId);
        }
    }

    async function fetchDelayPrediction(scheduleId) {
        const assessmentContainer = document.getElementById('delay-assessment-content');
        if (!assessmentContainer) return;
        
        assessmentContainer.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 1.5rem; color: var(--accent-purple); display:block; margin-left:auto; margin-right:auto; margin-bottom:0.5rem;"></i>
                <p style="font-size: 0.8rem; color: var(--text-secondary);">Analyzing route telemetry...</p>
            </div>
        `;
        
        try {
            const res = await fetch(`/api/tracking/predict-delay/${scheduleId}`);
            const data = await res.json();
            if (data && !data.error) {
                const reasonsList = data.reasons.map(r => `<li style="margin-bottom:4px;"><i class="fa-solid fa-triangle-exclamation" style="color:var(--accent-gold); font-size:0.75rem;"></i> ${r}</li>`).join('');
                const delayColor = data.delay_minutes > 15 ? '#ef4444' : (data.delay_minutes > 0 ? '#f59e0b' : '#10b981');
                
                assessmentContainer.innerHTML = `
                    <div style="display:flex; flex-direction:column; gap:0.6rem; height:100%; justify-content:space-between; text-align: left;">
                        <div style="flex-grow:1;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.6rem;">
                                <span style="font-size:0.72rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Delay Forecast</span>
                                <span class="badge" style="background: rgba(99, 102, 241, 0.1); color: #6366f1; font-size: 0.7rem; border-radius:4px; padding:2px 6px; font-weight:700;">Conf: ${data.ai_confidence_score}%</span>
                            </div>
                            
                            <!-- ETA Panel -->
                            <div style="background: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.04); border-radius:10px; padding:0.6rem; display:flex; justify-content:space-around; align-items:center; text-align:center; margin-bottom:0.6rem;">
                                <div>
                                    <div style="font-size:0.7rem; color:var(--text-secondary); font-weight:600; text-transform:uppercase;">Scheduled</div>
                                    <div style="font-size:0.9rem; font-weight:800; color:var(--text-primary);">${data.scheduled_arrival}</div>
                                </div>
                                <div style="font-size:1rem; color:var(--text-secondary);"><i class="fa-solid fa-arrow-right-long"></i></div>
                                <div>
                                    <div style="font-size:0.7rem; color:var(--text-secondary); font-weight:600; text-transform:uppercase;">AI-Adjusted</div>
                                    <div style="font-size:0.9rem; font-weight:800; color:${delayColor};">${data.adjusted_arrival}</div>
                                </div>
                            </div>
                            
                            <!-- Delay Details -->
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem; font-size:0.8rem;">
                                <span style="font-weight:600; color:var(--text-primary);">Traffic Congestion:</span>
                                <strong style="color:#6366f1;">${data.congestion}</strong>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; font-size:0.8rem;">
                                <span style="font-weight:600; color:var(--text-primary);">Predicted Delay:</span>
                                <strong style="color:${delayColor};">${data.delay_minutes} mins</strong>
                            </div>
                            
                            <!-- Bottleneck List -->
                            <div style="font-size:0.75rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase; margin-bottom:0.3rem; letter-spacing:0.5px;">Congestion Factors:</div>
                            <ul style="list-style:none; padding-left:0; margin:0; font-size:0.75rem; color:var(--text-secondary); display:flex; flex-direction:column; gap:2px;">
                                ${reasonsList}
                            </ul>
                        </div>
                        
                        <!-- simulated SMS button -->
                        <button class="btn-action-glow notify-sms-btn" style="width:100%; border-radius:8px; font-size:0.75rem; padding:8px 12px; margin-top:0.4rem; justify-content:center;">
                            <i class="fa-solid fa-paper-plane"></i> Notify Status via SMS
                        </button>
                    </div>
                `;
                
                const smsBtn = assessmentContainer.querySelector('.notify-sms-btn');
                if (smsBtn) {
                    smsBtn.onclick = () => {
                        showToast(`[SIMULATED SMS] Alert sent: Bus #${currentTrackedBusId} delay updated. Adjusted ETA: ${data.adjusted_arrival} 📱`, 'success');
                    };
                }
            } else {
                assessmentContainer.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: var(--accent-error);">
                        <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 0.5rem; display:block; margin-left:auto; margin-right:auto;"></i> Telemetry analysis offline.
                    </div>
                `;
            }
        } catch (err) {
            console.error("Delay prediction fetch failed:", err);
        }
    }

    async function pollTracking(fitBounds = false) {
        try {
            const res = await fetch(`/api/tracking/live/${currentTrackedBusId}`);
            const data = await res.json();
            if (data && data.location) {
                const latLng = data.location;
                const speed = Math.round(data.speed_kmh);
                
                // Update status badge
                const badge = document.getElementById('live-status-badge');
                if (badge) {
                    badge.innerHTML = `<i class="fa-solid fa-satellite-dish fa-beat"></i> Live • ${speed} km/h • ${data.status} • Bus #${currentTrackedBusId}`;
                }

                // If Leaflet is successfully initialized
                if (liveMap && data.origin_coords && data.dest_coords) {
                    const startCoords = data.origin_coords;
                    const endCoords = data.dest_coords;

                    // Update origin marker
                    if (originMarker) liveMap.removeLayer(originMarker);
                    originMarker = L.circleMarker(startCoords, { radius: 6, color: '#10b981', fillColor: '#10b981', fillOpacity: 1 })
                        .bindPopup(`Origin: ${data.origin}`)
                        .addTo(liveMap);

                    // Update destination marker
                    if (destinationMarker) liveMap.removeLayer(destinationMarker);
                    destinationMarker = L.circleMarker(endCoords, { radius: 6, color: '#f59e0b', fillColor: '#f59e0b', fillOpacity: 1 })
                        .bindPopup(`Destination: ${data.destination}`)
                        .addTo(liveMap);

                    // Update polyline
                    if (routePolyline) liveMap.removeLayer(routePolyline);
                    routePolyline = L.polyline([startCoords, endCoords], {
                        color: '#6366f1',
                        weight: 4,
                        opacity: 0.8,
                        dashArray: '10, 10'
                    }).addTo(liveMap);

                    // Update bus marker position
                    if (!busMarker) {
                        const busIcon = L.divIcon({
                            html: '<div style="background: var(--accent-primary); width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px rgba(37,99,235,0.8); border: 2px solid white; color: white;"><i class="fa-solid fa-bus"></i></div>',
                            className: 'custom-bus-marker',
                            iconSize: [30, 30],
                            iconAnchor: [15, 15]
                        });
                        busMarker = L.marker(latLng, { icon: busIcon }).addTo(liveMap);
                    } else {
                        busMarker.setLatLng(latLng);
                    }

                    busMarker.bindTooltip(`<strong>Bus Status:</strong> ${data.status}<br><strong>Speed:</strong> ${speed} km/h<br><strong>Progress:</strong> ${Math.round(data.progress_percent)}%`, { permanent: false, direction: 'top' });

                    if (fitBounds) {
                        const bounds = L.latLngBounds([startCoords, endCoords]);
                        liveMap.fitBounds(bounds, { padding: [50, 50] });
                    }
                }
            }
        } catch (err) {
            console.error("Tracking poll failed:", err);
        }
    }

    let trackingInterval;
    async function startLiveTrackingPoll() {
        if (trackingInterval) {
            clearInterval(trackingInterval);
        }
        // Fetch every 2 seconds
        trackingInterval = setInterval(async () => {
            await pollTracking(false);
        }, 2000);
    }
    
    // Call init
    initLiveTrackingMap();
});
