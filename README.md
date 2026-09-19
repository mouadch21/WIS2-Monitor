# 🌍 WIS2 Monitoring System

<p align="center">
  <strong>Real-Time Monitoring and Intelligent Analysis of WIS2 Events</strong>
</p>

<p align="center">
  A monitoring solution for collecting, validating, visualizing, and analyzing WIS2 events through MQTT and Artificial Intelligence.
</p>

---

## 📌 About the Project

The **WIS2 Monitoring System** is a monitoring and analysis platform developed as part of my **Projet de Fin d'Année (PFA)** at the *Direction Générale de la Météorologie (DGM)*.

The main objective is to facilitate the supervision of the WIS2 network by collecting monitoring events from the Global Broker MQTT, validating WME messages, storing the data, and providing interactive visualizations and intelligent analysis.

---

## 🏗️ System Architecture

The system is built around three main components:

### 🔄 1. MQTT Collector

- Connection to the Global Broker MQTT.
- Subscription to WIS2 monitoring topics.
- Real-time reception of WME messages.
- Validation according to WME compliance rules.
- Storage of events in an SQLite database.

### 📊 2. Streamlit Dashboard

- Interactive data visualizations.
- Multi-criteria filtering.
- Filtering by WIS2 Centre, severity, and date.
- Key Performance Indicators (KPIs).
- CSV data export.
- Interactive world map using Plotly.
- Monitoring statistics and event analysis.

### 🤖 3. WIS2 AI Assistant

- Natural language interaction.
- Intelligent search through monitoring events.
- Incident explanations and contextual analysis.
- Integration with Ollama and Gemma 3.
- Generation of contextualized responses.

---

## 🔗 System Workflow

```text
Global Broker MQTT
        │
        ▼
   Python Collector
        │
        ▼
   WME Validation
        │
        ▼
     SQLite
        │
        ├──────────────► Streamlit Dashboard
        │
        └──────────────► WIS2 AI Assistant
```

---

## 🛠️ Technologies Used

| Category | Technologies |
|----------|-------------|
| Programming Language | Python 3.10+ |
| MQTT Communication | Paho-MQTT |
| Database | SQLite |
| Data Processing | Pandas |
| Dashboard | Streamlit |
| Data Visualization | Plotly |
| Local AI | Ollama |
| Language Model | Gemma 3 |
| Communication Protocol | MQTT 3.1.1 / 5.0 |
| Data Standards | WIS2, WME, CloudEvents |

---

## ✨ Key Features

- 📡 Real-time monitoring of WIS2 events.
- ✅ WME message validation.
- 💾 Persistent storage using SQLite.
- 📈 Interactive monitoring dashboard.
- 🌍 Global map of WIS2 monitoring events.
- 🚨 Severity-based incident analysis.
- 🤖 AI-powered natural language assistant.
- 📊 Data export in CSV format.

---

## 📂 Project Structure

```text
WIS2_Monitor/
│
├── wis2_monitor.py       # MQTT collector and event management
├── dashboard.py          # Streamlit dashboard
├── wis2_monitor.db       # SQLite database (generated locally)
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── .gitignore            # Git ignored files
```

---

## ⚙️ Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/WIS2_Monitor.git
cd WIS2_Monitor
```

### 2️⃣ Create a virtual environment

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

Configure the MQTT connection using environment variables:

```env
MQTT_HOST=globalbroker.meteo.fr
MQTT_PORT=1883
MQTT_TOPIC=monitor/a/wis2/#
MQTT_TLS=false
DB_PATH=wis2_monitor.db
```

> ⚠️ Make sure that your MQTT credentials and connection settings are correctly configured.

---

## 🚀 Usage

### Initialize the database

```bash
python wis2_monitor.py initdb
```

### Start the MQTT collector

```bash
python wis2_monitor.py listen
```

### Launch the dashboard

```bash
streamlit run dashboard.py
```

### Start the AI assistant

Make sure that Ollama is installed and that the Gemma 3 model is available locally.

```bash
ollama pull gemma3
```

Then launch the Streamlit dashboard and access the AI assistant.

---

## 🤖 Artificial Intelligence

The WIS2 AI Assistant uses **Ollama** and **Gemma 3** to interpret natural language queries and provide contextualized information about monitoring events.

Example questions:

```text
How many CRITICAL events were recorded today?

Which WIS2 Centres generated ERROR events?

Explain the most recent critical incident.

Show the monitoring events for cn-cma.
```

---

## 🔒 Security and Reliability

- MQTT communication support.
- Automatic reconnection mechanism.
- WME message validation.
- Parameterized SQL queries.
- Data integrity through SQLite.
- Monitoring of validation errors.

> For production deployment, secure MQTT communication using TLS and appropriate authentication is recommended.

---

## 🎯 Project Objectives

- Improve the monitoring of the WIS2 network.
- Facilitate incident detection and analysis.
- Centralize monitoring events.
- Provide interactive and accessible visualizations.
- Integrate Artificial Intelligence into meteorological data monitoring.

---

