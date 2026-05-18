document.addEventListener('DOMContentLoaded', () => {
    // Generate simple Doughnut Chart
    const ctx = document.getElementById('userTravelStats').getContext('2d');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Eco Choice', 'Cheapest', 'Fastest', 'Safest'],
            datasets: [{
                data: [40, 30, 10, 20],
                backgroundColor: [
                    '#34d399', // green
                    '#38bdf8', // blue
                    '#fbbf24', // yellow
                    '#a78bfa'  // purple
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#cbd5e1', font: { family: 'Inter' } }
                }
            }
        }
    });

    // Fetch real bookings dynamically
    fetchUserBookings();

    async function fetchUserBookings() {
        const tbody = document.getElementById('bookings-table-body');
        if (!tbody) return;

        try {
            const userId = window.USER_ID || 1;
            const res = await fetch(`/api/booking/user/${userId}`);
            const bookings = await res.json();

            if (!bookings || bookings.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                            <i class="fa-solid fa-ticket-simple" style="font-size: 2rem; opacity: 0.15; margin-bottom: 1rem; display: block; margin-left: auto; margin-right: auto;"></i>
                            No tickets booked yet. Ready to start your AI-optimized journey?
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = '';
            bookings.forEach(b => {
                const badgeClass = b.status === 'Confirmed' ? 'green' : 'warning';
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.02); transition: 0.3s;" class="booking-row">
                        <td style="padding: 1.2rem 1rem; font-weight: 600; color: #fff;">${b.origin} ➔ ${b.destination}</td>
                        <td style="padding: 1.2rem 1rem; color: var(--text-secondary);">${b.date}</td>
                        <td style="padding: 1.2rem 1rem;">
                            <span class="badge blue" style="background: rgba(56, 189, 248, 0.15); color: var(--accent-primary); border-radius: 4px; padding: 2px 8px;">Seat ${b.seat}</span>
                            <strong style="margin-left: 10px; color: #fff;">₹${b.fare}</strong>
                        </td>
                        <td style="padding: 1.2rem 1rem;">
                            <span class="badge ${badgeClass}" style="border-radius: 30px; font-weight: 700;">${b.status}</span>
                        </td>
                    </tr>
                `;
            });

        } catch (err) {
            console.error(err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 2rem; color: #ef4444;">
                        <i class="fa-solid fa-triangle-exclamation"></i> Error loading profile data.
                    </td>
                </tr>
            `;
        }
    }
});
