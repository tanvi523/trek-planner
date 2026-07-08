"""
==============================================================================
  Trek Planner Agent — Flask + IBM Watsonx.ai (Granite)
==============================================================================
  AGENT_INSTRUCTIONS
  ------------------
  Customise every aspect of the agent's behaviour here.  No other file needs
  to change.

  TONE
      "professional"  → formal, data-driven, concise
      "friendly"      → warm, encouraging, conversational (default)
      "adventurous"   → bold, inspiring, hype-driven

  TREK_SPECIALIZATION
      Choose one or more from:
          "Himalayan"       – High-altitude treks (5 000 m+), technical routes
          "Western Ghats"   – Moderate subtropical forest treks (Karnataka/Kerala)
          "Sahyadri"        – Maharashtra hill-forts and ridge walks
          "Pan-India"       – All regions (default)

  SAFETY_RULES
      Free-text list that is injected verbatim into the system prompt so the
      agent always surfaces safety guidance.

  ALTITUDE_SICKNESS_WARNING
      Toggle the automatic AMS/HACE/HAPE advisory for treks above the
      configured threshold.

  COST_CURRENCY
      ISO 4217 code — all cost estimates will use this currency symbol.

  MAX_GROUP_SIZE
      Agent will warn if a requested group exceeds this limit.
==============================================================================
"""

AGENT_INSTRUCTIONS = {
    # ── Personality ──────────────────────────────────────────────────────────
    "TONE": "friendly",                      # "friendly" | "professional" | "adventurous"

    # ── Specialisation ───────────────────────────────────────────────────────
    "TREK_SPECIALIZATION": "Pan-India",      # "Himalayan" | "Western Ghats" | "Sahyadri" | "Pan-India"

    # ── Safety ───────────────────────────────────────────────────────────────
    "SAFETY_RULES": [
        "Always advise trekkers to carry a first-aid kit and emergency whistle.",
        "Recommend hiring a certified local guide for Grade 4+ treks.",
        "Stress the importance of Leave No Trace (LNT) principles.",
        "Advise checking weather forecasts 48 hours before departure.",
        "Recommend travel insurance that covers high-altitude evacuation.",
    ],

    # ── Altitude sickness advisory ────────────────────────────────────────────
    "ALTITUDE_SICKNESS_WARNING": True,       # True | False
    "ALTITUDE_WARNING_THRESHOLD_M": 3500,    # metres — warn above this elevation

    # ── Cost estimates ────────────────────────────────────────────────────────
    "COST_CURRENCY": "INR",                  # ISO 4217 code
    "MAX_GROUP_SIZE": 20,                    # warn if group > this number

    # ── Model parameters ─────────────────────────────────────────────────────
    "MODEL_ID": "meta-llama/llama-3-3-70b-instruct",
    "MAX_NEW_TOKENS": 2048,
    "TEMPERATURE": 0.7,
    "TOP_P": 0.9,
    "REPETITION_PENALTY": 1.1,
}

# ==============================================================================
#  Standard imports — do not edit below unless you know what you are doing
# ==============================================================================
import os
import json
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
CORS(app)

# ==============================================================================
#  Watsonx.ai client initialisation
# ==============================================================================
def _build_model() -> ModelInference:
    api_key    = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        raise EnvironmentError(
            "IBM_API_KEY and IBM_PROJECT_ID must be set in your .env file."
        )

    credentials = Credentials(url=url, api_key=api_key)
    params = {
        GenParams.MAX_NEW_TOKENS:    AGENT_INSTRUCTIONS["MAX_NEW_TOKENS"],
        GenParams.TEMPERATURE:       AGENT_INSTRUCTIONS["TEMPERATURE"],
        GenParams.TOP_P:             AGENT_INSTRUCTIONS["TOP_P"],
        GenParams.REPETITION_PENALTY: AGENT_INSTRUCTIONS["REPETITION_PENALTY"],
        GenParams.STOP_SEQUENCES:    ["<|endoftext|>"],
    }
    return ModelInference(
        model_id=AGENT_INSTRUCTIONS["MODEL_ID"],
        credentials=credentials,
        project_id=project_id,
        params=params,
    )


try:
    model = _build_model()
    log.info("Watsonx.ai model initialised: %s", AGENT_INSTRUCTIONS["MODEL_ID"])
except Exception as exc:
    model = None
    log.warning("Watsonx.ai model NOT initialised — running in demo mode. Reason: %s", exc)


# ==============================================================================
#  System prompt builder  (driven entirely by AGENT_INSTRUCTIONS)
# ==============================================================================
TONE_PERSONAS = {
    "professional": (
        "You are a professional mountain guide and trek consultant. "
        "Your responses are precise, data-driven, and concise."
    ),
    "friendly": (
        "You are an enthusiastic and caring trek planner who loves helping "
        "adventurers discover India's best trails. Be warm, encouraging, and thorough."
    ),
    "adventurous": (
        "You are a bold, seasoned mountaineer who has summited peaks across the "
        "Himalayas and trekked every ridge in the Western Ghats. "
        "Your answers are inspiring, vivid, and energise trekkers to take the leap."
    ),
}


def build_system_prompt() -> str:
    ai = AGENT_INSTRUCTIONS
    tone_text  = TONE_PERSONAS.get(ai["TONE"], TONE_PERSONAS["friendly"])
    spec_text  = (
        f"Your primary trek specialisation is: {ai['TREK_SPECIALIZATION']} treks."
    )
    safety_list = "\n".join(f"  • {r}" for r in ai["SAFETY_RULES"])
    safety_text = f"Always incorporate the following safety guidelines:\n{safety_list}"

    altitude_text = ""
    if ai["ALTITUDE_SICKNESS_WARNING"]:
        altitude_text = (
            f"\nFor any trek above {ai['ALTITUDE_WARNING_THRESHOLD_M']} m, "
            "always include a dedicated section on Altitude Mountain Sickness (AMS), "
            "HACE, and HAPE: symptoms, prevention (acclimatisation schedule, Diamox), "
            "and emergency descent protocol."
        )

    cost_text = (
        f"\nProvide all cost estimates in {ai['COST_CURRENCY']}. "
        f"If a group exceeds {ai['MAX_GROUP_SIZE']} people, warn that special "
        "permits and larger logistics will significantly increase costs."
    )

    return f"""{tone_text}

{spec_text}

{safety_text}{altitude_text}{cost_text}

You can help with:
1. Personalised trek recommendations based on fitness, experience, and preferences.
2. Detailed day-wise itineraries with camp locations, distances, and elevation profiles.
3. Comprehensive gear and packing checklists tailored to the season and trek grade.
4. Group-size-based cost estimates (permits, guide, porter, accommodation, food).
5. Fitness and difficulty assessments.
6. General trekking Q&A.

When generating itineraries use this structure:
  Day N | <Camp/Location> | Distance: X km | Elevation gain/loss: ±Y m | Difficulty: <Easy/Moderate/Hard>

When generating packing checklists, group items into: Clothing, Navigation, Safety & First Aid, Food & Water, Camping Gear, Documents & Permits.

Respond in clear, well-formatted Markdown. Use headings, bullet points, and tables where appropriate.
"""


SYSTEM_PROMPT = build_system_prompt()


# ==============================================================================
#  Core generation helper
# ==============================================================================
def generate_response(user_message: str, history: list[dict]) -> str:
    """
    Call the Watsonx.ai Granite model and return the assistant reply.
    Falls back to a structured demo reply when the model is unavailable.
    """
    if model is None:
        return _demo_response(user_message)

    # Build a minimal chat-style prompt that Granite understands
    conversation = ""
    for turn in history[-6:]:          # keep last 3 exchanges for context
        role    = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "user":
            conversation += f"<|user|>\n{content}\n"
        else:
            conversation += f"<|assistant|>\n{content}\n"

    prompt = (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"{conversation}"
        f"<|user|>\n{user_message}\n"
        "<|assistant|>\n"
    )

    try:
        result = model.generate_text(prompt=prompt)
        return result.strip() if isinstance(result, str) else result# type: ignore
    except Exception as exc:
        log.error("Generation error: %s", exc)
        return (
            "⚠️ I encountered an issue connecting to the AI model. "
            "Please check your IBM credentials and try again."
        )


def _demo_response(message: str) -> str:
    """Structured demo reply when no model is available (for UI testing)."""
    msg = message.lower()
    if any(w in msg for w in ["recommend", "suggest", "trek", "trail"]):
        return (
            "## 🏔️ Trek Recommendations\n\n"
            "Here are three treks perfectly matched to a beginner–intermediate trekker:\n\n"
            "| Trek | Region | Duration | Max Altitude | Difficulty |\n"
            "|------|--------|----------|--------------|------------|\n"
            "| **Kedarkantha** | Uttarakhand | 6 days | 3 950 m | Easy–Moderate |\n"
            "| **Hampta Pass** | Himachal Pradesh | 5 days | 4 270 m | Moderate |\n"
            "| **Brahmatal** | Uttarakhand | 6 days | 3 800 m | Easy–Moderate |\n\n"
            "> ⚠️ *Demo mode — connect IBM Watsonx.ai for personalised AI responses.*"
        )
    if any(w in msg for w in ["itinerary", "day", "plan", "schedule"]):
        return (
            "## 📅 Sample 6-Day Kedarkantha Itinerary\n\n"
            "| Day | Camp | Distance | Elevation | Difficulty |\n"
            "|-----|------|----------|-----------|------------|\n"
            "| Day 1 | Sankri Base Camp | Drive | 1 950 m | Easy |\n"
            "| Day 2 | Juda Ka Talab | 4 km | 2 720 m | Easy |\n"
            "| Day 3 | Kedarkantha Base | 4 km | 3 200 m | Moderate |\n"
            "| Day 4 | **Summit → Hargaon** | 10 km | 3 950 m → 2 600 m | Hard |\n"
            "| Day 5 | Sankri | 8 km | 1 950 m | Easy |\n"
            "| Day 6 | Departure | — | — | — |\n\n"
            "> ⚠️ *Demo mode — connect IBM Watsonx.ai for AI-generated itineraries.*"
        )
    if any(w in msg for w in ["pack", "gear", "checklist", "equipment"]):
        return (
            "## 🎒 Packing Checklist\n\n"
            "### Clothing\n- Moisture-wicking base layers (×2)\n- Insulated jacket\n"
            "- Waterproof shell jacket & pants\n- Trekking trousers (×2)\n- Warm beanie & gloves\n\n"
            "### Navigation\n- Topographic map + compass\n- GPS device / downloaded offline maps\n\n"
            "### Safety & First Aid\n- First-aid kit (blister care, pain relief, ORS)\n"
            "- Emergency whistle & signal mirror\n- Headlamp + spare batteries\n\n"
            "### Food & Water\n- 3-litre water capacity (bottles + reservoir)\n"
            "- Water purification tablets\n- High-calorie snacks (nuts, energy bars)\n\n"
            "### Camping Gear\n- 3-season sleeping bag (−10 °C rated)\n"
            "- Trekking poles\n- Gaiters\n\n"
            "### Documents & Permits\n- Government-issued ID (×2 photocopies)\n"
            "- Trek permit\n- Emergency contact card\n\n"
            "> ⚠️ *Demo mode — connect IBM Watsonx.ai for personalised checklists.*"
        )
    return (
        "## 👋 Trek Planner Agent\n\n"
        "I'm your AI-powered trek companion! Ask me about:\n\n"
        "- 🏔️ **Trek recommendations** — *'Suggest a 7-day Himalayan trek for beginners'*\n"
        "- 📅 **Itinerary planning** — *'Create a day-wise plan for Hampta Pass'*\n"
        "- 🎒 **Packing checklists** — *'What gear do I need for a winter trek?'*\n"
        "- 💪 **Fitness assessment** — *'Am I fit enough for Roopkund?'*\n"
        "- 💰 **Cost estimates** — *'How much will Stok Kangri cost for 6 people?'*\n\n"
        "> ⚠️ *Demo mode — add IBM Watsonx.ai credentials to `.env` for live AI responses.*"
    )


# ==============================================================================
#  Flask routes
# ==============================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(force=True)
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Empty message"}), 400

    response = generate_response(message, history)
    return jsonify({"response": response})


@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True)
    fitness     = data.get("fitness", "moderate")
    experience  = data.get("experience", "beginner")
    duration    = data.get("duration", "5-7 days")
    region      = data.get("region", "any")
    season      = data.get("season", "any")
    group_size  = data.get("group_size", 4)

    prompt = (
        f"Generate exactly 3 personalised trek recommendations for a trekker with the "
        f"following profile:\n"
        f"- Fitness level: {fitness}\n"
        f"- Experience: {experience}\n"
        f"- Preferred duration: {duration}\n"
        f"- Region: {region}\n"
        f"- Season: {season}\n"
        f"- Group size: {group_size} people\n\n"
        f"For each trek provide: name, region, duration, max altitude, difficulty grade "
        f"(Grade 1–5), best season, highlights, and estimated cost in "
        f"{AGENT_INSTRUCTIONS['COST_CURRENCY']} per person. "
        f"Format as a Markdown table followed by brief descriptions."
    )
    response = generate_response(prompt, [])
    return jsonify({"response": response})


@app.route("/api/itinerary", methods=["POST"])
def itinerary():
    data      = request.get_json(force=True)
    trek_name = data.get("trek_name", "Kedarkantha")
    duration  = data.get("duration", "6 days")
    group     = data.get("group_size", 4)
    pace      = data.get("pace", "moderate")

    prompt = (
        f"Create a detailed day-wise itinerary for **{trek_name}** ({duration}) for a "
        f"group of {group} people trekking at a {pace} pace.\n\n"
        f"Include for each day: camp name, altitude (m), distance (km), elevation change (m), "
        f"approximate walking hours, key landmarks, and overnight stay type "
        f"(tent/guesthouse/hotel).\n\n"
        f"After the itinerary table add:\n"
        f"- **Acclimatisation notes** (if applicable)\n"
        f"- **Emergency exit points**\n"
        f"- **Total cost estimate** for the group in {AGENT_INSTRUCTIONS['COST_CURRENCY']}."
    )
    response = generate_response(prompt, [])
    return jsonify({"response": response})


@app.route("/api/checklist", methods=["POST"])
def checklist():
    data     = request.get_json(force=True)
    trek     = data.get("trek_name", "general high-altitude trek")
    season   = data.get("season", "summer")
    duration = data.get("duration", "7 days")
    altitude = data.get("max_altitude", 4000)

    prompt = (
        f"Generate a comprehensive packing checklist for **{trek}** in {season} season, "
        f"{duration} duration, max altitude {altitude} m.\n\n"
        f"Organise items into: Clothing, Navigation, Safety & First Aid, Food & Water, "
        f"Camping Gear, Electronics, Documents & Permits.\n"
        f"Mark essential items with ✅ and optional items with 🔵."
    )
    response = generate_response(prompt, [])
    return jsonify({"response": response})


@app.route("/api/fitness", methods=["POST"])
def fitness():
    data       = request.get_json(force=True)
    trek       = data.get("trek_name", "Stok Kangri")
    age        = data.get("age", 30)
    fitness_l  = data.get("fitness_level", "moderate")
    experience = data.get("experience", "1 previous trek")
    health     = data.get("health_conditions", "none")

    prompt = (
        f"Assess whether the following trekker is ready for **{trek}**:\n"
        f"- Age: {age}\n"
        f"- Fitness level: {fitness_l}\n"
        f"- Prior trekking experience: {experience}\n"
        f"- Health conditions: {health}\n\n"
        f"Provide:\n"
        f"1. **Readiness verdict** (Ready / Needs preparation / Not recommended)\n"
        f"2. **Gap analysis** — what fitness benchmarks they must meet\n"
        f"3. **8-week training plan** to prepare for this trek\n"
        f"4. **Medical checks** recommended before departure"
    )
    response = generate_response(prompt, [])
    return jsonify({"response": response})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": AGENT_INSTRUCTIONS["MODEL_ID"],
        "specialization": AGENT_INSTRUCTIONS["TREK_SPECIALIZATION"],
        "tone": AGENT_INSTRUCTIONS["TONE"],
        "model_available": model is not None,
    })


# ==============================================================================
#  Entry point
# ==============================================================================
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    log.info("Starting Trek Planner Agent on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
