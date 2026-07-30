# 🌿 Resilient Pocket | Intelligent Personal Expense Manager

[![Live Demo](https://img.shields.io/badge/Render-Live_Demo-00C7B7?style=for-the-badge&logo=render&logoColor=white)](https://resilient-pocket.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)]()

**Resilient Pocket** is a modular, data-driven personal financial management and expense tracking application built in Python. Beyond basic transaction logging, it provides intelligent budget analytics, financial stress testing (shock analysis), and dynamic financial runway forecasting.

🚀 **Live Application:** [https://resilient-pocket.onrender.com](https://resilient-pocket.onrender.com)

---

## ✨ Key Features

* **📊 Budget Intelligence & Analytics:** Categorizes spending, tracks recurring costs, and provides dynamic health scoring.
* **📉 Financial Runway Forecasting:** Calculates estimated survival runway based on net spending velocity and liquid reserves.
* **⚡ Shock Resistance Testing:** Simulates real-world financial stress scenarios to test budget resilience.
* **🎨 Interactive Visual Dashboard:** Features dynamic visual state indicators (growing/drooping flower states) based on financial health and custom canvas physics.
* **🏷️ Automated Smart Tagging:** Automatically parses and tags transactions for accurate category breakdown.
* **⚡ Modern Web Interface:** Clean HTML/CSS/JS frontend communicating with a custom Python HTTP backend engine.

---

## 🛠️ Tech Stack

* **Backend:** Python 3, SQLite, Pandas, Matplotlib
* **Frontend:** HTML5, CSS3, Modern JavaScript (ES6+), HTML Canvas Physics
* **Deployment:** Render

---

## 📂 Project Structure

```text
.
├── app.py                   # Core application interface
├── assistant.py             # Financial assistant logic
├── budget_intelligence.py   # Spending intelligence & category logic
├── config.py                # Configuration & threshold settings
├── core.py                  # Primary application orchestrator
├── db.py                    # Database models and SQLite handler
├── health.py                # Financial health scoring engine
├── runway.py                # Financial runway forecasting models
├── shock.py                 # Financial shock resistance testing
├── tagger.py                # Smart transaction tagger engine
├── telemetry.py             # Internal system telemetry & metrics
├── web_server.py            # HTTP web server & API endpoints
├── static/                  # Frontend assets
│   ├── index.html           # Main Web UI
│   ├── styles.css           # Styling
│   ├── app.js               # Frontend integration script
│   ├── canvas_physics.js    # Interactive canvas physics engine
│   └── *.svg                # Dynamic state SVG assets
└── requirements.txt         # Dependencies for production build
