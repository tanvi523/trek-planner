# Trek Planner Agent 🏔️

An AI-powered trek planning web application built with **Python Flask** and **IBM Watsonx.ai** (Granite 3.3 8B Instruct). Provides personalised trek recommendations, day-wise itineraries, packing checklists, fitness assessments, and real-time cost estimates through a responsive chat-first UI.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 AI Chat | Real-time conversation with IBM Granite via Watsonx.ai |
| 🗺️ Trek Recommendations | Personalised suggestions based on fitness, season, region |
| 📅 Itinerary Generator | Day-wise plans with altitude, distance, camp details |
| 🎒 Packing Checklist | Gear lists tailored to trek, season, and altitude |
| 💪 Fitness Assessment | Readiness verdict + 8-week training plan |
| 💰 Cost Estimates | Group-size-based cost breakdowns in INR |
| ⛑️ Altitude Warnings | Automatic AMS/HACE/HAPE advisories above 3 500 m |
| 🌙 Dark / Light Mode | Full theme toggle with localStorage persistence |
| 📱 Mobile Responsive | Bootstrap 5 grid + custom breakpoints |

---

## 🗂️ Project Structure

```
trek-planner-agent/
├── app.py                 # Flask backend + AGENT_INSTRUCTIONS + all API routes
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template — copy to .env
├── README.md
├── templates/
│   └── index.html         # Single-page frontend (Bootstrap 5 + dark mode)
└── static/
    ├── css/
    │   └── style.css      # Custom CSS + animations
    └── js/
        └── app.js         # Frontend logic (chat, forms, markdown rendering)
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- An [IBM Cloud](https://cloud.ibm.com) account
- A [Watsonx.ai](https://dataplatform.cloud.ibm.com) project with Granite model access

### 2. Clone and set up the environment

```bash
# Clone the repository
git clone https://github.com/your-username/trek-planner-agent.git
cd trek-planner-agent

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` with your actual values:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=change_this_to_a_random_secret
FLASK_DEBUG=false
FLASK_PORT=5000
```

#### How to get IBM credentials

| Credential | Where to find it |
|-----------|-----------------|
| `IBM_API_KEY` | IBM Cloud Console → **Manage → Access (IAM)** → **API keys** → Create |
| `IBM_PROJECT_ID` | Watsonx.ai Studio → Your project → **Manage** tab → **General** → Project ID |
| `IBM_WATSONX_URL` | Depends on your region — see `.env.example` for options |

### 4. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## ⚙️ Customising Agent Behaviour (AGENT_INSTRUCTIONS)

All agent customisation is in the `AGENT_INSTRUCTIONS` dictionary at the top of [`app.py`](app.py). **No other file needs to change.**

```python
AGENT_INSTRUCTIONS = {
    # Tone: "friendly" | "professional" | "adventurous"
    "TONE": "friendly",

    # Specialisation: "Himalayan" | "Western Ghats" | "Sahyadri" | "Pan-India"
    "TREK_SPECIALIZATION": "Pan-India",

    # Safety rules injected into every prompt
    "SAFETY_RULES": [
        "Always advise trekkers to carry a first-aid kit and emergency whistle.",
        "Recommend hiring a certified local guide for Grade 4+ treks.",
        ...
    ],

    # Altitude sickness advisory
    "ALTITUDE_SICKNESS_WARNING": True,
    "ALTITUDE_WARNING_THRESHOLD_M": 3500,

    # Cost & group settings
    "COST_CURRENCY": "INR",
    "MAX_GROUP_SIZE": 20,

    # Granite model parameters
    "MODEL_ID": "ibm/granite-3-3-8b-instruct",
    "MAX_NEW_TOKENS": 2048,
    "TEMPERATURE": 0.7,
    "TOP_P": 0.9,
    "REPETITION_PENALTY": 1.1,
}
```

### Common customisation examples

**Himalayan specialist with professional tone:**
```python
"TONE": "professional",
"TREK_SPECIALIZATION": "Himalayan",
```

**Western Ghats guide in adventurous mode:**
```python
"TONE": "adventurous",
"TREK_SPECIALIZATION": "Western Ghats",
"ALTITUDE_SICKNESS_WARNING": False,   # low-altitude region
"ALTITUDE_WARNING_THRESHOLD_M": 2000,
```

**Use a different Granite model:**
```python
"MODEL_ID": "ibm/granite-3-8b-instruct",   # or granite-13b-instruct-v2
"MAX_NEW_TOKENS": 1024,
```

---

## 🌐 API Reference

All endpoints accept and return JSON.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve the frontend SPA |
| POST | `/api/chat` | Free-form chat with history context |
| POST | `/api/recommend` | Trek recommendations based on trekker profile |
| POST | `/api/itinerary` | Day-wise itinerary for a named trek |
| POST | `/api/checklist` | Packing checklist for a trek / season / altitude |
| POST | `/api/fitness` | Fitness assessment + training plan |
| GET | `/api/health` | Model status and agent configuration |

### Example — Chat

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Suggest a 7-day trek in Uttarakhand for beginners", "history": []}'
```

### Example — Recommend

```bash
curl -X POST http://localhost:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "fitness": "moderate",
    "experience": "beginner",
    "duration": "5-7 days",
    "region": "Himalayan",
    "season": "summer",
    "group_size": 4
  }'
```

---

## 🐳 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

```bash
# Build and run
docker build -t trek-planner-agent .
docker run -p 5000:5000 --env-file .env trek-planner-agent
```

---

## ☁️ Production Deployment (IBM Code Engine / Cloud Foundry)

### IBM Code Engine

```bash
# Install IBM Cloud CLI and Code Engine plugin first
ibmcloud login
ibmcloud ce project select --name my-project

ibmcloud ce app create \
  --name trek-planner-agent \
  --image icr.io/your-namespace/trek-planner-agent:latest \
  --env-from-secret trek-planner-secrets \
  --port 5000 \
  --min-scale 1
```

### Cloud Foundry

```yaml
# manifest.yml
applications:
- name: trek-planner-agent
  memory: 512M
  instances: 1
  buildpacks:
    - python_buildpack
  env:
    IBM_API_KEY: ((ibm_api_key))
    IBM_PROJECT_ID: ((project_id))
    IBM_WATSONX_URL: https://us-south.ml.cloud.ibm.com
```

```bash
ibmcloud cf push
```

---

## 🧪 Running Without IBM Credentials (Demo Mode)

If `IBM_API_KEY` or `IBM_PROJECT_ID` are not set, the agent runs in **demo mode** with pre-built structured responses. All UI features work — you just get sample data instead of live AI.

---

## 📋 Dependency Versions

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.3 | Web framework |
| flask-cors | 4.0.1 | Cross-origin requests |
| python-dotenv | 1.0.1 | `.env` file loading |
| ibm-watsonx-ai | 1.1.2 | IBM Watsonx.ai SDK |
| requests | 2.32.3 | HTTP client |
| gunicorn | 22.0.0 | Production WSGI server |

---

## ⚠️ Disclaimer

This application provides trek planning *assistance* only. Always verify trail conditions through official sources, carry appropriate safety equipment, and follow local regulations and advisories.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
