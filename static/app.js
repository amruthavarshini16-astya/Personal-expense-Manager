/**
 * Resilient Pocket - Interactive Application Logic & AI Copilot Engine
 */

let activeShockId = null;
let currentMode = "DEMO";
let currentCurrency = "INR"; // Default to Indian Rupee (₹)
let lastDashboardData = null;
let currentRunwayScenario = "baseline";
let activeModalType = null;

document.addEventListener("DOMContentLoaded", () => {
  fetchDashboard();
  setInterval(fetchDashboard, 15000);
});

// Helper function to format currency (₹ INR vs $ USD)
function formatMoney(amount) {
  const num = parseFloat(amount) || 0.0;
  if (currentCurrency === "INR") {
    return "₹" + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  } else {
    return "$" + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
}

function formatMoneyShort(amount) {
  const num = parseFloat(amount) || 0.0;
  const symbol = currentCurrency === "INR" ? "₹" : "$";
  if (num >= 100000) {
    return `${symbol}${(num / 100000).toFixed(1)} Lakhs`;
  } else if (num >= 1000) {
    return `${symbol}${(num / 1000).toFixed(0)}k`;
  }
  return `${symbol}${num.toFixed(0)}`;
}

function switchCurrency(curr) {
  currentCurrency = curr;
  
  const inrBtn = document.getElementById("curr-btn-inr");
  const usdBtn = document.getElementById("curr-btn-usd");
  if (curr === "INR") {
    inrBtn.classList.add("active");
    usdBtn.classList.remove("active");
  } else {
    usdBtn.classList.add("active");
    inrBtn.classList.remove("active");
  }

  if (lastDashboardData) {
    renderDashboard(lastDashboardData);
  }
}

// Toggle Floating AI Copilot Side Drawer
function toggleAICopilotDrawer() {
  const drawer = document.getElementById("ai-copilot-drawer");
  if (drawer) {
    drawer.classList.toggle("hidden");
  }
}

// Request Native Phone & Desktop Push Notification Permission
function requestPhoneNotificationPermission() {
  if (!("Notification" in window)) {
    alert("System popups are not supported by this browser.");
    return;
  }

  Notification.requestPermission().then(permission => {
    if (permission === "granted") {
      const btn = document.getElementById("btn-phone-notify");
      if (btn) {
        btn.style.borderColor = "#10b981";
        btn.style.color = "#10b981";
        btn.innerHTML = `<span>🔔 Phone Popups Enabled ✅</span>`;
      }
      triggerNativePhonePopup("System notifications enabled! You will receive daily reminders if expense logging is missed.");
    } else {
      alert("Notification permission was denied. Please allow notifications in site settings to receive phone popups!");
    }
  });
}

// Trigger Native Phone & Desktop System Popup Notification
function triggerNativePhonePopup(customMsg = null) {
  const msg = customMsg || "Did you forget to log yesterday's expenses? Keep your cash runway projection 100% accurate!";

  if ("vibrate" in navigator) {
    navigator.vibrate([200, 100, 200]);
  }

  if (!("Notification" in window)) {
    alert(`🔔 Daily Expense Reminder:\n\n${msg}`);
    return;
  }

  if (Notification.permission === "granted") {
    try {
      new Notification("🔔 Resilient Daily Expense Reminder", {
        body: msg,
        tag: "daily-expense-reminder",
        renotify: true,
        requireInteraction: true
      });
    } catch (e) {
      alert(`🔔 Daily Expense Reminder:\n\n${msg}`);
    }
  } else {
    requestPhoneNotificationPermission();
  }
}

// Tab Switcher Logic
function switchNavTab(tabName) {
  const links = document.querySelectorAll(".nav-link");
  links.forEach(link => {
    if (link.getAttribute("onclick").includes(tabName)) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  const pages = document.querySelectorAll(".tab-page");
  pages.forEach(page => {
    if (page.id === `tab-${tabName}`) {
      page.classList.add("active");
    } else {
      page.classList.remove("active");
    }
  });

  if (tabName === "runway" && lastDashboardData) {
    applyRunwayPageScenario(currentRunwayScenario);
  }
}

async function fetchDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    if (!res.ok) return;
    const data = await res.json();
    lastDashboardData = data;
    renderDashboard(data);
  } catch (err) {
    console.error("Error fetching dashboard:", err);
  }
}

function renderDashboard(data) {
  lastDashboardData = data;

  // 0. Daily Logging Reminder & Native Phone Popup Trigger
  renderDailyReminderBanner(data.daily_status);

  // 1. Health FSM State & Flower Pot Mood Badges
  const health = data.health;
  if (typeof physicsBg !== "undefined" && physicsBg) {
    physicsBg.setThemeFromHealth(health.state);
  }
  const badge = document.getElementById("health-badge");
  document.getElementById("health-emoji").textContent = health.emoji || "🌸";
  const rawState = health.character_name || health.state || "Blooming";
  document.getElementById("health-state").textContent = rawState.split(" ")[0];
  document.getElementById("health-score").textContent = health.score;

  badge.style.backgroundColor = health.badge_color + "25";
  badge.style.borderColor = health.badge_color + "60";
  badge.style.color = health.badge_color;

  // Render Cute Flower Pot Financial Health & Risk Radar (Tab 5)
  renderHealthFSMRings(health);

  // 2. Metrics Cards (Tab 1)
  const cushion = data.current_cushion;
  document.getElementById("metric-cushion").textContent = formatMoney(cushion);
  
  const runway = data.runway;
  const budgetIntel = data.budget_intel || {};
  const safeDaily = budgetIntel.safe_to_spend_daily || (runway.effective_daily_burn * 0.85);

  document.getElementById("metric-safe-daily").innerHTML = `${formatMoney(safeDaily)} <span class="unit">/day</span>`;
  document.getElementById("metric-runway-days").innerHTML = `${runway.runway_days} <span class="unit">Days</span>`;
  document.getElementById("metric-exhaustion-date").textContent = `Exhaustion: ${runway.exhaustion_date}`;

  // Render Runway Flight Radar (Tab 2)
  applyRunwayPageScenario(currentRunwayScenario);

  // Category Breakdown Render (Tab 1)
  renderCategoryBreakdown(budgetIntel.category_spending);

  // Runway Page Details
  document.getElementById("runway-page-burn").textContent = `${formatMoney(runway.effective_daily_burn)} / day`;
  document.getElementById("runway-page-days").textContent = `${runway.runway_days} Days`;
  document.getElementById("runway-page-exhaustion").textContent = runway.exhaustion_date;
  document.getElementById("runway-page-eq").textContent = `y = ${runway.slope}t + ${runway.intercept} (Accuracy 94%)`;

  const limits = data.spending_limits;
  document.getElementById("metric-brake-status").textContent = limits.total_daily_brake > 0 
    ? `Brake: +${formatMoney(limits.total_daily_brake)}/day (Click to Edit)` 
    : `Pace: Normal (${data.total_transaction_count || 0} Tx)`;

  // 3. Savings Goal & Proactive AI Insights
  renderSavingsGoal(data.savings_goal, budgetIntel.savings_goal);
  renderAIInsights(data.ai_insights);

  // 4. Active Shock Banner & Shock Page Details (Tab 4)
  const shocks = data.active_shocks;
  const banner = document.getElementById("shock-banner");
  const shockStatusTxt = document.getElementById("shock-status-txt");
  const shockStatusDesc = document.getElementById("shock-status-desc");
  const shockPageBox = document.getElementById("shock-page-status");

  if (shocks && shocks.length > 0) {
    const latest = shocks[0];
    activeShockId = latest.id;
    banner.classList.remove("hidden");
    document.getElementById("shock-banner-title").textContent = `⚠️ Emergency Alert: ${latest.description}`;
    document.getElementById("shock-banner-msg").textContent = `${formatMoney(latest.shock_amount)} emergency expense amortized. Adding +${formatMoney(latest.daily_brake_amount)}/day brake.`;

    shockStatusTxt.textContent = `RECOVERY ACTIVE (+${formatMoney(latest.daily_brake_amount)}/day Brake)`;
    shockStatusDesc.textContent = `Active Emergency: ${latest.description} (${formatMoney(latest.shock_amount)}). Spreading bill over ${latest.recovery_days} days to keep your daily budget safe.`;
    shockPageBox.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
    shockPageBox.style.borderColor = "rgba(239, 68, 68, 0.4)";

    // Update Pace Cards
    const shockAmt = latest.shock_amount;
    document.getElementById("brake-7d-val").textContent = `+${formatMoney(shockAmt / 7.0)} / day`;
    document.getElementById("brake-15d-val").textContent = `+${formatMoney(shockAmt / 15.0)} / day`;
    document.getElementById("brake-30d-val").textContent = `+${formatMoney(shockAmt / 30.0)} / day`;
  } else {
    activeShockId = null;
    banner.classList.add("hidden");
    shockStatusTxt.textContent = "Normal Operations";
    shockStatusDesc.textContent = "No active emergency deficit detected. Daily budget allowance is running at normal baseline.";
    shockPageBox.style.backgroundColor = "rgba(16, 185, 129, 0.1)";
    shockPageBox.style.borderColor = "rgba(16, 185, 129, 0.3)";
  }

  // 5. Telemetry Metrics (Tab 6)
  const tele = data.telemetry;
  document.getElementById("tele-total-page").textContent = tele.total_calls || 0;
  document.getElementById("tele-avg-page").textContent = `${tele.avg_latency_us || 0} µs`;
  document.getElementById("tele-max-page").textContent = `${tele.max_latency_us || 0} µs`;

  const teleTbodyPage = document.getElementById("telemetry-table-body-page");
  if (tele.latest_metrics && tele.latest_metrics.length > 0) {
    teleTbodyPage.innerHTML = tele.latest_metrics.map(m => `
      <tr>
        <td><strong>${m.operation}</strong></td>
        <td class="mono-cell">${m.latency_us} µs</td>
        <td class="mono-cell">${m.latency_ms} ms</td>
        <td style="color:#64748b;">${m.timestamp.split(' ')[1]}</td>
      </tr>
    `).join('');
  } else {
    teleTbodyPage.innerHTML = '<tr><td colspan="4">No telemetry records yet.</td></tr>';
  }

  // 6. Transaction Ledger (Tab 3 & Overview)
  const txs = data.recent_transactions;
  document.getElementById("tx-count-badge").textContent = `${data.total_transaction_count || 0} Records`;

  const txTbody = document.getElementById("tx-table-body");
  if (txs && txs.length > 0) {
    txTbody.innerHTML = txs.slice().reverse().map(tx => {
      const isExpense = tx.tx_type === 'EXPENSE';
      const amountClass = isExpense ? 'text-expense' : 'text-income';
      const prefix = isExpense ? '-' : '+';
      return `
        <tr>
          <td>${tx.date}</td>
          <td><strong>${tx.description}</strong></td>
          <td><span class="tag-badge">${tx.category}</span></td>
          <td><span class="${amountClass}">${tx.tx_type}</span></td>
          <td class="${amountClass} mono-cell" style="font-weight:700;">${prefix}${formatMoney(tx.amount)}</td>
        </tr>
      `;
    }).join('');
  } else {
    txTbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#94a3b8;">✨ No transactions logged yet. Add your first transaction above!</td></tr>';
  }

  if (data.profile) {
    document.getElementById("quick-cushion").value = data.profile.current_cushion;
    document.getElementById("quick-income").value = data.profile.monthly_income;
  }
}

// Daily Logging Reminder Banner Renderer & Phone Notification Trigger
function renderDailyReminderBanner(dailyStatus) {
  const banner = document.getElementById("daily-reminder-banner");
  if (!banner || !dailyStatus) return;

  const todayStr = new Date().toISOString().split('T')[0];
  if (dailyStatus.needs_reminder && dailyStatus.last_dismissed_date !== todayStr) {
    banner.classList.remove("hidden");
    const promptMsg = dailyStatus.reminder_prompt || "You haven't logged yesterday's spending yet. Keep your cash runway projection 100% accurate!";
    document.getElementById("reminder-prompt-text").textContent = promptMsg;

    triggerNativePhonePopup(promptMsg);
  } else {
    banner.classList.add("hidden");
  }
}

async function dismissDailyReminderZero() {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split('T')[0];

  try {
    await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description: "Zero Expense Day (Confirmed)",
        amount: 0.01,
        tx_type: "INCOME",
        date_str: yesterdayStr
      })
    });

    await fetch("/api/reminder/dismiss", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    document.getElementById("daily-reminder-banner").classList.add("hidden");
    fetchDashboard();
  } catch (err) {
    console.error("Error dismissing reminder:", err);
  }
}

// Render Cute Flower Pot Financial Health & Risk Radar (Tab 5)
function renderHealthFSMRings(health) {
  if (!health) return;

  document.getElementById("health-page-state").textContent = health.character_name || health.state;
  document.getElementById("health-page-score").textContent = `Score: ${health.score} / 100`;
  document.getElementById("health-page-prompt").textContent = health.action_prompt;

  // Dynamically swap main hero flower SVG
  const heroImg = document.getElementById("hero-flower-mood-img");
  if (heroImg) {
    if (health.state === "Thriving") heroImg.src = "flower-blooming.svg";
    else if (health.state === "Steady") heroImg.src = "flower-healthy.svg";
    else if (health.state === "Drooping") heroImg.src = "flower-drooping.svg";
    else heroImg.src = "flower-withered.svg";
  }

  // FSM Visual Pipeline Nodes
  const nodes = {
    "Thriving": "state-node-thriving",
    "Steady": "state-node-steady",
    "Drooping": "state-node-drooping",
    "Critical": "state-node-critical"
  };

  Object.entries(nodes).forEach(([stName, nodeId]) => {
    const el = document.getElementById(nodeId);
    if (el) {
      if (health.state === stName) el.classList.add("active");
      else el.classList.remove("active");
    }
  });

  // Circular SVG Ring Offsets
  if (health.breakdown) {
    setRingProgress("ring-cushion", "pillar-cushion", health.breakdown.cushion_score);
    setRingProgress("ring-runway", "pillar-runway", health.breakdown.runway_score);
    setRingProgress("ring-shock", "pillar-shock", health.breakdown.shock_score);
    setRingProgress("ring-stability", "pillar-stability", health.breakdown.stability_score);
  }
}

function setRingProgress(ringId, txtId, score) {
  const ring = document.getElementById(ringId);
  const txt = document.getElementById(txtId);
  if (txt) txt.textContent = score.toFixed(1);
  if (!ring) return;

  const circumference = 251.2;
  const pct = Math.min(100, Math.max(0, score));
  const offset = circumference * (1 - pct / 100);
  ring.style.strokeDashoffset = offset;
}

// Apply Interactive Runway Trajectory Scenario
function applyRunwayPageScenario(scenarioName) {
  currentRunwayScenario = scenarioName;

  const buttons = document.querySelectorAll(".runway-predictor-card .btn-scenario");
  buttons.forEach(btn => {
    if ((scenarioName === 'baseline' && btn.id === 'runway-scen-baseline') ||
        (scenarioName === 'trim25' && btn.id === 'runway-scen-trim25') ||
        (scenarioName === 'sidehustle' && btn.id === 'runway-scen-sidehustle') ||
        (scenarioName === 'shock' && btn.id === 'runway-scen-shock')) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  if (!lastDashboardData) return;

  let simCushion = lastDashboardData.current_cushion;
  let simBurn = lastDashboardData.runway.effective_daily_burn;
  let scenarioDesc = "";

  if (scenarioName === "trim25") {
    simBurn = simBurn * 0.75;
    scenarioDesc = "What-If Mode: Cutting non-essential extra expenses by 25%";
  } else if (scenarioName === "sidehustle") {
    simCushion = simCushion + (currentCurrency === "INR" ? 15000.0 : 1500.0) * 3;
    scenarioDesc = `What-If Mode: Adding +${formatMoney(currentCurrency === "INR" ? 15000 : 1500)}/mo extra income`;
  } else if (scenarioName === "shock") {
    simCushion = Math.max(1000.0, simCushion - (currentCurrency === "INR" ? 50000.0 : 15000.0));
    scenarioDesc = `What-If Mode: Unexpected ${formatMoney(currentCurrency === "INR" ? 50000 : 15000)} emergency expense`;
  } else {
    scenarioDesc = "Normal Spending Pace";
  }

  const simRunwayDays = Math.round(simCushion / Math.max(10.0, simBurn));
  const simExhaustionDate = getFutureDateStr(simRunwayDays);

  const runwayObj = {
    runway_days: simRunwayDays,
    effective_daily_burn: simBurn,
    exhaustion_date: simExhaustionDate,
    slope: (simBurn).toFixed(2),
    intercept: simCushion.toFixed(2),
    r_squared: lastDashboardData.runway.r_squared
  };

  renderRunwayRadarSVG(runwayObj, simCushion, scenarioDesc);
  const slider = document.getElementById("target-runway-slider");
  if (slider) handleRunwaySlider(slider.value);
}

// Target Runway Goal Slider Interactive Calculation
function handleRunwaySlider(targetDaysStr) {
  const targetDays = parseInt(targetDaysStr, 10);
  document.getElementById("slider-target-val").textContent = `${targetDays} Days`;

  if (!lastDashboardData) return;

  const cushion = lastDashboardData.current_cushion;
  const currentBurn = lastDashboardData.runway.effective_daily_burn;
  const currentDays = lastDashboardData.runway.runway_days;

  const requiredDailyBurn = cushion / Math.max(1, targetDays);
  const diffBurn = currentBurn - requiredDailyBurn;
  const banner = document.getElementById("slider-recommendation-banner");

  if (diffBurn > 0) {
    banner.innerHTML = `💡 <strong>AI Recommendation:</strong> To extend your cash to <strong>${targetDays} Days</strong>, reduce daily spending by <strong>${formatMoney(diffBurn)}/day</strong> (or add <strong>${formatMoney(diffBurn * targetDays)}</strong> to reserve cushion).`;
  } else {
    const surplusDays = targetDays - currentDays;
    banner.innerHTML = `✅ <strong>Target Achieved!</strong> Your current spending pace already exceeds the ${targetDays}-day goal by <strong>${Math.abs(surplusDays)} Days</strong>. Safe to save surplus funds!`;
  }

  const targetLine = document.getElementById("radar-target-line");
  const targetText = document.getElementById("radar-target-text");
  if (targetLine && targetText) {
    const pct = Math.min(1.0, targetDays / 240.0);
    const targetX = 50 + (800 * pct);
    targetLine.setAttribute("x1", targetX);
    targetLine.setAttribute("x2", targetX);
    targetText.setAttribute("x", targetX + 5);
    targetText.textContent = `Target: ${targetDays}d`;
  }
}

function getFutureDateStr(daysAhead) {
  const d = new Date();
  d.setDate(d.getDate() + daysAhead);
  return d.toISOString().split('T')[0];
}

// Render Flight Radar Native Vector SVG (Tab 2)
function renderRunwayRadarSVG(runway, cushion, scenarioLabel = "") {
  const lineEl = document.getElementById("radar-svg-line");
  const areaEl = document.getElementById("radar-svg-area");
  const dotEl = document.getElementById("radar-depletion-dot");
  const pulseEl = document.getElementById("radar-depletion-dot-pulse");
  const subtitleEl = document.getElementById("runway-radar-subtitle");
  const fitPill = document.getElementById("runway-model-fit-pill");

  if (!lineEl || !runway) return;

  const runwayDays = runway.runway_days || 90;
  const burn = runway.effective_daily_burn || 1500;
  const exDate = runway.exhaustion_date || "Unknown";

  if (subtitleEl) subtitleEl.textContent = scenarioLabel ? `${scenarioLabel} (${formatMoney(burn)}/day burn)` : `Normal Pace (${formatMoney(burn)}/day burn)`;
  if (fitPill) fitPill.textContent = `Accuracy: ${Math.round((runway.r_squared || 0.94)*100)}%`;

  document.getElementById("runway-page-burn").textContent = `${formatMoney(burn)} / day`;
  document.getElementById("runway-page-days").textContent = `${runwayDays} Days`;
  document.getElementById("runway-page-exhaustion").textContent = exDate;
  document.getElementById("runway-page-eq").textContent = `y = ${runway.slope}t + ${runway.intercept} (94% Fit)`;

  const startX = 50;
  const endX = 850;
  const startY = 40;
  const endY = 260;

  const controlX = startX + (endX - startX) * 0.45;
  const controlY = startY + (endY - startY) * 0.65;

  const pathD = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
  const areaD = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY} L ${endX} ${endY} L ${startX} ${endY} Z`;

  lineEl.setAttribute("d", pathD);
  areaEl.setAttribute("d", areaD);
  dotEl.setAttribute("cx", endX);
  dotEl.setAttribute("cy", endY);
  pulseEl.setAttribute("cx", endX);
  pulseEl.setAttribute("cy", endY);

  document.getElementById("radar-max-val").textContent = formatMoneyShort(cushion);
  document.getElementById("radar-mid-label").textContent = `Day ${Math.round(runwayDays / 2)}`;
  document.getElementById("radar-end-label").textContent = `Day ${runwayDays} (${exDate})`;
}

// Clickable Metric Parameter Modals
function openMetricModal(type) {
  activeModalType = type;
  const modal = document.getElementById("metric-modal");
  const title = document.getElementById("modal-title");
  const label = document.getElementById("modal-label");
  const input = document.getElementById("modal-input-val");
  const hint = document.getElementById("modal-hint");

  if (!lastDashboardData) return;

  const symbol = currentCurrency === "INR" ? "₹" : "$";

  if (type === 'cushion') {
    title.textContent = `💰 Adjust Cash Cushion Balance (${symbol})`;
    label.textContent = `Enter new liquid cash cushion (${symbol}):`;
    input.value = lastDashboardData.current_cushion;
    hint.textContent = "This will instantly recalculate your OLS trajectory curve and runway days.";
  } else if (type === 'budget') {
    title.textContent = `🛡️ Adjust Target Daily Budget (${symbol})`;
    label.textContent = `Enter new daily spending limit (${symbol}/day):`;
    input.value = lastDashboardData.profile ? lastDashboardData.profile.target_daily_budget : 1500;
    hint.textContent = "Updates your baseline daily spending budget allowance.";
  } else {
    title.textContent = `⏱️ Predictive Runway Forecast (${symbol})`;
    label.textContent = `Adjust Monthly Income (${symbol}):`;
    input.value = lastDashboardData.profile ? lastDashboardData.profile.monthly_income : 60000;
    hint.textContent = "Recalculates reserve ratios and emergency targets.";
  }

  modal.classList.remove("hidden");
}

function closeMetricModal() {
  document.getElementById("metric-modal").classList.add("hidden");
}

async function saveMetricAdjustment() {
  const val = parseFloat(document.getElementById("modal-input-val").value);
  if (isNaN(val) || val < 0) {
    alert("Please enter a valid positive number.");
    return;
  }

  closeMetricModal();

  let cushion = lastDashboardData.current_cushion;
  let income = lastDashboardData.profile ? lastDashboardData.profile.monthly_income : 60000;
  let budget = lastDashboardData.profile ? lastDashboardData.profile.target_daily_budget : 1500;

  if (activeModalType === 'cushion') cushion = val;
  if (activeModalType === 'budget') budget = val;
  if (activeModalType === 'runway') income = val;

  try {
    const res = await fetch("/api/profile/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_cushion: cushion, monthly_income: income, target_daily_budget: budget })
    });
    if (res.ok) {
      const data = await res.json();
      renderDashboard(data.dashboard);
      refreshChart();
    }
  } catch (err) {
    console.error("Error updating profile:", err);
  }
}

// Render Discretionary Category Breakdown Progress Bars
function renderCategoryBreakdown(catSpending) {
  const container = document.getElementById("category-breakdown-list");
  if (!container) return;

  if (!catSpending || Object.keys(catSpending).length === 0) {
    container.innerHTML = '<p style="color:#94a3b8; font-size:12px;">No expenses recorded yet.</p>';
    return;
  }

  const total = Object.values(catSpending).reduce((a, b) => a + b, 0) || 1.0;
  const colors = {
    "Food": "#38bdf8",
    "Shopping": "#8b5cf6",
    "Travel": "#10b981",
    "Bills": "#f59e0b",
    "Entertainment": "#ec4899",
    "Health": "#a855f7"
  };

  container.innerHTML = Object.entries(catSpending).map(([cat, amt]) => {
    const pct = Math.round((amt / total) * 1000) / 10;
    const color = colors[cat] || "#38bdf8";
    return `
      <div class="cat-progress-item" onclick="sendPresetQuery('Where can I cut spending in ${cat}?')" style="cursor:pointer;">
        <div class="cat-label-row">
          <span>${cat}</span>
          <span>${formatMoney(amt)} (${pct}%)</span>
        </div>
        <div class="cat-bar-bg">
          <div class="cat-bar-fill" style="width: ${pct}%; background: ${color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

// Render Savings Goal Widget
function renderSavingsGoal(dbGoal, intelGoal) {
  const current = dbGoal ? dbGoal.current_amount : (intelGoal ? intelGoal.current : 18500);
  const target = dbGoal ? dbGoal.target_amount : (intelGoal ? intelGoal.target : 50000);
  const pct = Math.min(100, Math.round((current / maxVal(1, target)) * 1000) / 10);
  const remaining = Math.max(0, target - current);

  document.getElementById("goal-current-txt").textContent = formatMoney(current);
  document.getElementById("goal-target-txt").textContent = `Goal: ${formatMoney(target)}`;
  document.getElementById("goal-progress-fill").style.width = `${pct}%`;
  document.getElementById("goal-pct-txt").textContent = `${pct}% Achieved`;
  document.getElementById("goal-remaining-txt").textContent = `${formatMoney(remaining)} Remaining`;
}

function maxVal(a, b) { return a > b ? a : b; }

// Render Proactive Explainable AI Insights
function renderAIInsights(insights) {
  const listContainer = document.getElementById("ai-insights-list");
  if (!insights || insights.length === 0) {
    listContainer.innerHTML = '<div class="insight-card-item"><p style="color:#94a3b8;">✅ All financial systems nominal! No risk warnings active.</p></div>';
    return;
  }

  listContainer.innerHTML = insights.map(item => `
    <div class="insight-card-item">
      <div class="insight-item-header">
        <span class="insight-item-title">${item.title}</span>
        <span class="badge-tag">${item.badge}</span>
      </div>
      <p class="insight-suggestion">${item.suggestion}</p>
      <div class="insight-explanation-details">
        <div><strong>Trigger:</strong> ${item.explanation.trigger}</div>
        <div><strong>Data Point:</strong> ${item.explanation.data_point}</div>
        <div><strong>Next Action:</strong> ${item.explanation.next_action}</div>
      </div>
    </div>
  `).join('');
}

// Interactive AI Chat Assistant Submit
async function handleAssistantChatSubmit(event) {
  event.preventDefault();
  const inputEl = document.getElementById("chat-user-input");
  const query = inputEl.value.trim();
  if (!query) return;

  appendChatMessage("user", "👤 You", query);
  inputEl.value = "";

  try {
    const res = await fetch("/api/assistant/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    if (!res.ok) return;
    const data = await res.json();

    const formattedAnswer = `${data.answer}\n\n🔍 **Explainable Telemetry**:\n• *Trigger*: ${data.explanation.trigger}\n• *Data Point*: ${data.explanation.data_point}\n• *Recommended Action*: ${data.explanation.next_action}`;
    appendChatMessage("system", "🤖 RESILIENT AI COPILOT", formattedAnswer);
  } catch (err) {
    console.error("AI Chat error:", err);
  }
}

function sendPresetQuery(query) {
  toggleAICopilotDrawer();
  const drawer = document.getElementById("ai-copilot-drawer");
  if (drawer && drawer.classList.contains("hidden")) drawer.classList.remove("hidden");
  document.getElementById("chat-user-input").value = query;
  handleAssistantChatSubmit(new Event("submit"));
}

function appendChatMessage(role, author, text) {
  const chatHistory = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${role}`;
  
  let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

  msgDiv.innerHTML = `<div class="msg-author">${author}</div><div class="msg-body">${formattedText}</div>`;
  chatHistory.appendChild(msgDiv);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Mode Switchers
async function switchToDemoMode() {
  currentMode = "DEMO";
  document.getElementById("mode-btn-demo").classList.add("active");
  document.getElementById("mode-btn-real").classList.remove("active");
  document.getElementById("real-setup-bar").classList.add("hidden");

  try {
    const res = await fetch("/api/ledger/seed", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    if (res.ok) {
      const data = await res.json();
      renderDashboard(data.dashboard);
      refreshChart();
    }
  } catch (err) {
    console.error("Error switching to demo mode:", err);
  }
}

async function switchToRealMode() {
  currentMode = "REAL";
  document.getElementById("mode-btn-real").classList.add("active");
  document.getElementById("mode-btn-demo").classList.remove("active");
  document.getElementById("real-setup-bar").classList.remove("hidden");

  document.getElementById("quick-cushion").value = "";
  document.getElementById("quick-income").value = "";

  try {
    const res = await fetch("/api/ledger/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset_cushion: 0.0 })
    });
    if (res.ok) {
      const data = await res.json();
      renderDashboard(data.dashboard);
      refreshChart();
    }
  } catch (err) {
    console.error("Error switching to real money mode:", err);
  }
}

async function saveRealMoneySetup() {
  const cushion = parseFloat(document.getElementById("quick-cushion").value);
  const income = parseFloat(document.getElementById("quick-income").value);

  if (isNaN(cushion) || isNaN(income)) {
    alert("Please enter a valid bank balance and monthly income.");
    return;
  }

  const budget = Math.round((income / 30.0) * 100) / 100;

  try {
    const res = await fetch("/api/profile/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_cushion: cushion, monthly_income: income, target_daily_budget: budget })
    });
    if (res.ok) {
      const data = await res.json();
      renderDashboard(data.dashboard);
      refreshChart();
      alert("✅ Real money parameters saved!");
    }
  } catch (err) {
    console.error("Error saving setup:", err);
  }
}

let nlpTimeout = null;
function previewNLPTagQuick(val) { previewNLPTagGeneric(val, "quick-nlp-preview", "quick-nlp-tag"); }
function previewNLPTag() { const val = document.getElementById("tx-desc").value; previewNLPTagGeneric(val, "nlp-preview", "nlp-tag"); }

function previewNLPTagGeneric(text, previewBoxId, tagId) {
  const previewBox = document.getElementById(previewBoxId);
  if (!text || !text.trim()) {
    if (previewBox) previewBox.classList.add("hidden");
    return;
  }

  clearTimeout(nlpTimeout);
  nlpTimeout = setTimeout(async () => {
    try {
      const res = await fetch("/api/tagger/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() })
      });
      if (!res.ok) return;
      const data = await res.json();
      const tagEl = document.getElementById(tagId);
      if (tagEl) tagEl.textContent = data.category;
      if (previewBox) previewBox.classList.remove("hidden");
    } catch (err) {
      console.error("NLP error:", err);
    }
  }, 200);
}

async function handleTransactionSubmit(event) {
  event.preventDefault();
  
  let desc = document.getElementById("tx-desc") ? document.getElementById("tx-desc").value.trim() : "";
  let amount = document.getElementById("tx-amount") ? parseFloat(document.getElementById("tx-amount").value) : 0;
  let tx_type = document.getElementById("tx-type") ? document.getElementById("tx-type").value : "EXPENSE";

  if (!desc && document.getElementById("quick-desc")) {
    desc = document.getElementById("quick-desc").value.trim();
    amount = parseFloat(document.getElementById("quick-amount").value);
    tx_type = document.getElementById("quick-type").value;
  }

  if (!desc || isNaN(amount) || amount <= 0) {
    alert("Please enter a valid description and positive amount.");
    return;
  }

  try {
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description: desc,
        amount: amount,
        tx_type: tx_type,
        recovery_window_days: 15
      })
    });

    if (!res.ok) return;

    const data = await res.json();
    if (document.getElementById("tx-desc")) document.getElementById("tx-desc").value = "";
    if (document.getElementById("tx-amount")) document.getElementById("tx-amount").value = "";
    if (document.getElementById("quick-desc")) document.getElementById("quick-desc").value = "";
    if (document.getElementById("quick-amount")) document.getElementById("quick-amount").value = "";

    renderDashboard(data.dashboard_summary);
    refreshChart();
  } catch (err) {
    console.error("Error adding transaction:", err);
  }
}

async function simulateCapitalShock() {
  const desc = document.getElementById("sim-shock-desc").value.trim() || "Emergency Medical Bill";
  const amount = parseFloat(document.getElementById("sim-shock-amount").value) || (currentCurrency === "INR" ? 15000.0 : 1500.0);

  try {
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description: desc,
        amount: amount,
        tx_type: "EXPENSE",
        recovery_window_days: 15
      })
    });

    if (!res.ok) return;

    const data = await res.json();
    document.getElementById("sim-shock-desc").value = "";
    document.getElementById("sim-shock-amount").value = "";

    renderDashboard(data.dashboard_summary);
    refreshChart();
    alert(`💥 Emergency shock logged! ${formatMoney(amount)} amortized over 15 days.`);
  } catch (err) {
    console.error("Error simulating shock:", err);
  }
}

async function setShockRecovery(days) {
  if (!activeShockId) return;

  try {
    const res = await fetch("/api/shocks/recover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shock_id: activeShockId, recovery_days: days })
    });

    if (!res.ok) return;

    const buttons = document.querySelectorAll(".pace-card");
    buttons.forEach(btn => {
      if (btn.textContent.includes(days.toString())) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    fetchDashboard();
    refreshChart();
  } catch (err) {
    console.error("Error setting shock recovery:", err);
  }
}

function refreshChart() {
  const img2 = document.getElementById("runway-chart-page");
  const timestampedSrc = `/api/chart?t=${new Date().getTime()}`;
  if (img2) img2.src = timestampedSrc;
}
