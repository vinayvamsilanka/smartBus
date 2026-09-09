// Global state
let currentPointsBalance = 0;
let catalogProducts = [];
let activeFilter = 'All';

document.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
    loadRewardsCatalog();
    loadUserRedemptions();
});

// Load User Profile points & credentials
async function loadUserProfile() {
    try {
        const response = await fetch('/api/auth/profile');
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await response.json();
        
        if (data.success && data.user) {
            const user = data.user;
            currentPointsBalance = user.eco_points !== undefined ? user.eco_points : 150;
            
            // Welcome name
            const welcomeName = document.getElementById('welcome-user-name');
            if (welcomeName) welcomeName.textContent = user.name;
            
            // Avatar initials
            const avatarInitials = document.getElementById('user-avatar-initials');
            if (avatarInitials) {
                avatarInitials.textContent = user.name
                    .split(' ')
                    .map(n => n[0])
                    .join('')
                    .toUpperCase()
                    .slice(0, 2);
            }
            
            updatePointsMetrics(currentPointsBalance);
        }
    } catch (err) {
        console.error("Error loading user profile:", err);
        // Fallback for simulation
        currentPointsBalance = 150;
        updatePointsMetrics(currentPointsBalance);
    }
}

// Update UI metrics for points, progress and tiers
function updatePointsMetrics(pts) {
    const ptsElement = document.getElementById('curr-eco-pts');
    if (ptsElement) ptsElement.textContent = pts;
    
    const progFill = document.getElementById('milestone-prog-fill');
    const tierText = document.getElementById('user-tier-text');
    const tierBadge = document.getElementById('user-tier-badge');
    const descContent = document.getElementById('milestone-desc-content');
    
    // Tier mapping
    let tierName = "Eco Explorer";
    let badgeHtml = '<i class="fa-solid fa-seedling"></i> ECO EXPLORER';
    let badgeGradient = 'linear-gradient(135deg, #b45309, #d97706)';
    let badgeShadow = '0 4px 12px rgba(217, 119, 6, 0.25)';
    let nextTier = "Eco Champion";
    let nextTierPts = 150;
    
    if (pts >= 150 && pts < 250) {
        tierName = "Eco Champion";
        badgeHtml = '<i class="fa-solid fa-leaf"></i> ECO CHAMPION';
        badgeGradient = 'linear-gradient(135deg, #10b981, #059669)';
        badgeShadow = '0 4px 12px rgba(16, 185, 129, 0.25)';
        nextTier = "Eco Expert";
        nextTierPts = 250;
    } else if (pts >= 250 && pts < 350) {
        tierName = "Eco Expert";
        badgeHtml = '<i class="fa-solid fa-crown"></i> ECO EXPERT';
        badgeGradient = 'linear-gradient(135deg, #3b82f6, #2563eb)';
        badgeShadow = '0 4px 12px rgba(37, 99, 235, 0.25)';
        nextTier = "Eco Legend";
        nextTierPts = 350;
    } else if (pts >= 350) {
        tierName = "Eco Legend";
        badgeHtml = '<i class="fa-solid fa-gem"></i> ECO LEGEND';
        badgeGradient = 'linear-gradient(135deg, #a855f7, #7c3aed)';
        badgeShadow = '0 4px 12px rgba(124, 58, 237, 0.3)';
        nextTier = "Max Tier Unlocked!";
        nextTierPts = pts;
    }
    
    if (tierText) tierText.textContent = tierName;
    if (tierBadge) {
        tierBadge.innerHTML = badgeHtml;
        tierBadge.style.background = badgeGradient;
        tierBadge.style.boxShadow = badgeShadow;
    }
    
    // Progress calculation
    let progressPercentage = 0;
    if (pts >= 350) {
        progressPercentage = 100;
        if (descContent) {
            descContent.innerHTML = `<i class="fa-solid fa-star text-glow" style="color: var(--accent-gold);"></i> <span>You have reached the ultimate <strong>Eco Legend</strong> tier! Claim and show off your badges!</span>`;
        }
    } else {
        const currentTierBase = (pts >= 250) ? 250 : ((pts >= 150) ? 150 : 0);
        const range = nextTierPts - currentTierBase;
        progressPercentage = Math.min(((pts - currentTierBase) / range) * 100, 100);
        
        const ptsRemaining = nextTierPts - pts;
        if (descContent) {
            descContent.innerHTML = `<i class="fa-solid fa-sparkles text-glow" style="color: var(--accent-gold);"></i> <span>You are <strong>${ptsRemaining} Points</strong> away from unlocking <strong>${nextTier}</strong> status!</span>`;
        }
    }
    
    if (progFill) progFill.style.width = `${progressPercentage}%`;
}

// Fetch Rewards Catalog from Backend API
async function loadRewardsCatalog() {
    try {
        const response = await fetch('/api/rewards/products');
        const data = await response.json();
        
        if (data.success) {
            catalogProducts = data.products;
            renderCatalog();
        }
    } catch (err) {
        console.error("Error loading rewards catalog:", err);
        const grid = document.getElementById('products-catalog-grid');
        if (grid) {
            grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--accent-error);">
                <i class="fa-solid fa-circle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem; display:block; margin-left:auto; margin-right:auto;"></i>
                Failed to retrieve rewards catalog. Please check your connections.
            </div>`;
        }
    }
}

// Render Products Grid
function renderCatalog() {
    const grid = document.getElementById('products-catalog-grid');
    if (!grid) return;
    
    // Filter products
    const filtered = catalogProducts.filter(p => activeFilter === 'All' || p.category === activeFilter);
    
    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 4rem; color: var(--text-secondary);">
            No rewards found matching filter selection '${activeFilter}'.
        </div>`;
        return;
    }
    
    grid.innerHTML = filtered.map(p => {
        const isAffordable = currentPointsBalance >= p.points_cost;
        const outOfStock = p.stock <= 0;
        const btnDisabled = (!isAffordable || outOfStock) ? 'disabled' : '';
        
        let btnText = "Redeem Reward";
        if (outOfStock) {
            btnText = "Out of Stock";
        } else if (!isAffordable) {
            btnText = `Requires ${p.points_cost} Pts`;
        }
        
        return `
            <div class="product-card">
                <span class="prod-category-pill">${p.category}</span>
                <div class="prod-icon-wrapper">
                    <i class="fa-solid ${p.image_url || 'fa-gift'}"></i>
                </div>
                <h4 class="product-title">${p.name}</h4>
                <p class="product-desc">${p.description}</p>
                <div class="prod-footer">
                    <div class="prod-cost">
                        <span class="cost-value">${p.points_cost}</span>
                        <span class="cost-label">Green Miles</span>
                    </div>
                    <button class="btn-redeem" ${btnDisabled} onclick="redeemReward(${p.id})">
                        ${btnText}
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Filter Catalog Products
function filterCatalog(category) {
    activeFilter = category;
    
    // Update active pill styling
    const pills = document.querySelectorAll('.filter-pill');
    pills.forEach(pill => {
        if (pill.textContent.includes(category) || (category === 'All' && pill.textContent === 'All Rewards')) {
            pill.classList.add('active');
        } else {
            pill.classList.remove('active');
        }
    });
    
    renderCatalog();
}

// Trigger post redemption query to API
async function redeemReward(productId) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...`;
    
    try {
        const response = await fetch('/api/rewards/redeem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ product_id: productId })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast(`Redeemed successfully! Coupon code: ${data.coupon_code}`, 'success');
            
            // Reload user state, catalog and claims
            loadUserProfile();
            loadRewardsCatalog();
            loadUserRedemptions();
        } else {
            showToast(data.msg || "Redemption failed", 'error');
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (err) {
        console.error("Redemption error:", err);
        showToast("Network dispatch failed. Please retry.", 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Load Claims/Redemptions List from Database
async function loadUserRedemptions() {
    try {
        const response = await fetch('/api/rewards/user-redemptions');
        const data = await response.json();
        
        const tableBody = document.getElementById('claims-table-body');
        
        if (data.success) {
            const list = data.redemptions;
            
            // 1. Render Top-Medium Active Coupons Board
            renderActiveCouponsBoard(list.filter(r => r.status === 'Active'));
            
            // 2. Render Full Redemptions History Table
            if (!tableBody) return;
            
            if (list.length === 0) {
                tableBody.innerHTML = `<tr>
                    <td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                        You haven't claimed any eco-rewards yet. Travel green to earn miles!
                    </td>
                </tr>`;
                return;
            }
            
            tableBody.innerHTML = list.map(r => {
                const statusClass = r.status.toLowerCase();
                return `
                    <tr class="claim-row">
                        <td style="font-weight: 700;">${r.product_name}</td>
                        <td><span style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px; font-weight:600; color:var(--text-secondary);">${r.product_category}</span></td>
                        <td style="font-weight: 800; color: var(--accent-green);"><i class="fa-solid fa-leaf" style="font-size:0.8rem;"></i> ${r.points_spent}</td>
                        <td style="color: var(--text-secondary); font-size:0.82rem;">${r.redemption_date}</td>
                        <td>
                            <div class="coupon-badge">
                                <span>${r.coupon_code}</span>
                                <button class="btn-copy" onclick="copyCouponCode('${r.coupon_code}')" title="Copy Claim Code">
                                    <i class="fa-solid fa-copy"></i>
                                </button>
                            </div>
                        </td>
                        <td><span class="badge-status ${statusClass}">${r.status}</span></td>
                    </tr>
                `;
            }).join('');
        }
    } catch (err) {
        console.error("Error loading user redemptions:", err);
    }
}

// Render Top-Medium Active Coupons Board on Eco Travel Page
function renderActiveCouponsBoard(activeList) {
    const grid = document.getElementById('active-coupons-board-grid');
    const countBadge = document.getElementById('active-coupons-count-badge');
    if (!grid) return;

    if (countBadge) {
        countBadge.textContent = `${activeList.length} Active`;
        if (activeList.length > 0) {
            countBadge.style.background = 'rgba(16, 185, 129, 0.2)';
            countBadge.style.color = '#34d399';
            countBadge.style.border = '1px solid rgba(16, 185, 129, 0.5)';
        } else {
            countBadge.style.background = 'rgba(148, 163, 184, 0.1)';
            countBadge.style.color = 'var(--text-secondary)';
            countBadge.style.border = '1px solid rgba(255, 255, 255, 0.1)';
        }
    }

    if (activeList.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; background: rgba(15, 23, 42, 0.5); border: 1.5px dashed rgba(255,255,255,0.1); border-radius: 20px; padding: 2.2rem 1.5rem; text-align: center; color: var(--text-secondary);">
                <i class="fa-solid fa-ticket" style="font-size: 2rem; color: var(--accent-gold); opacity: 0.6; margin-bottom: 0.6rem; display: block; margin-left: auto; margin-right: auto;"></i>
                <p style="font-size: 1rem; font-weight: 700; color: #ffffff; margin-bottom: 6px;">No active unused coupons currently</p>
                <small style="color: var(--text-secondary); max-width: 500px; display: inline-block;">Redeem your Green Miles in the catalog below to generate discount coupons that will stay active here on screen until you use them for bus booking!</small>
            </div>
        `;
        return;
    }

    grid.innerHTML = activeList.map(item => {
        let discountTag = '10% OFF';
        if (item.product_name.includes('50%')) discountTag = '50% OFF';
        else if (item.product_name.toLowerCase().includes('lounge') || item.product_name.toLowerCase().includes('priority')) discountTag = 'FREE PASS';

        return `
            <div class="active-coupon-card">
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <span style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 0.72rem; font-weight: 800; padding: 3px 10px; border-radius: 20px; text-transform: uppercase;">
                            <i class="fa-solid fa-tag" style="margin-right: 4px;"></i> ${discountTag}
                        </span>
                        <span style="font-size: 0.72rem; color: #34d399; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                            <span class="pulse-dot"></span> ACTIVE UNTIL USED
                        </span>
                    </div>

                    <h4 style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-bottom: 6px; line-height: 1.3;">
                        ${item.product_name}
                    </h4>
                    <p style="font-size: 0.78rem; color: rgba(255,255,255,0.6); margin-bottom: 14px;">
                        Redeemed on ${item.redemption_date} · <i class="fa-solid fa-leaf" style="color:#10b981;"></i> ${item.points_spent} Green Miles
                    </p>

                    <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255, 255, 255, 0.12); padding: 10px 14px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
                        <span style="font-family: monospace; font-size: 1.05rem; font-weight: 800; letter-spacing: 1.5px; color: #38bdf8;">
                            ${item.coupon_code}
                        </span>
                        <button class="btn-copy" onclick="copyCouponCode('${item.coupon_code}')" style="background: rgba(56, 189, 248, 0.15); border: none; color: #38bdf8; padding: 6px 12px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.75rem; display: flex; align-items: center; gap: 4px;" title="Copy Code">
                            <i class="fa-solid fa-copy"></i> Copy
                        </button>
                    </div>
                </div>

                <button onclick="useCouponInBooking('${item.coupon_code}')" style="width: 100%; padding: 10px; border-radius: 12px; background: linear-gradient(135deg, #10b981, #059669); border: 1px solid #34d399; color: #ffffff; font-weight: 800; font-size: 0.82rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.25s;">
                    <i class="fa-solid fa-bus"></i> Use Code in Bus Booking
                </button>
            </div>
        `;
    }).join('');
}

function useCouponInBooking(code) {
    copyCouponCode(code);
    localStorage.setItem('autoApplyCoupon', code);
    showToast("Coupon copied! Opening bus search to apply discount...", "success");
    setTimeout(() => {
        window.location.href = '/results';
    }, 1200);
}

// Copy Voucher Claim Codes Helper
function copyCouponCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        showToast("Claim code copied to clipboard!", "success");
    }).catch(err => {
        console.error("Failed to copy code: ", err);
    });
}

// Show green/red floating notifications
function showToast(message, type = 'success') {
    const box = document.getElementById('toast-alerts-box');
    if (!box) return;
    
    const toast = document.createElement('div');
    toast.className = `toast-alert ${type}`;
    
    const icon = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
    const iconColor = type === 'success' ? 'var(--accent-green)' : 'var(--accent-error)';
    
    toast.innerHTML = `
        <i class="fa-solid ${icon}" style="color: ${iconColor}; font-size: 1.15rem;"></i>
        <span>${message}</span>
    `;
    
    box.appendChild(toast);
    
    // Animate removal after 4 seconds
    setTimeout(() => {
        toast.style.transform = 'translateY(10px)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
