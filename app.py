# app.py - Main Streamlit Application (Optimized for Speed)

import streamlit as st
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

from servicenow_client import ServiceNowClient
from groq_analyzer import GroqIncidentAnalyzer

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🤖 ServiceNow AI Incident Bot",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CACHED RESOURCES — Created once, reused always
# ─────────────────────────────────────────────
@st.cache_resource
def get_groq_client(api_key: str) -> Groq:
    """Create Groq client once and cache it."""
    return Groq(api_key=api_key)


@st.cache_resource
def get_snow_client(instance_url: str, username: str, password: str) -> ServiceNowClient:
    """Create ServiceNow client once and cache it."""
    return ServiceNowClient(instance_url, username, password)


# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
    }
    .stMetric {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────
def init_session_state():
    defaults = {
        "monitoring_active": False,
        "processed_incidents": set(),
        "analysis_log": [],
        "sn_client": None,
        "groq_analyzer": None,
        "connected": False,
        "total_analyzed": 0,
        "total_failed": 0,
        "last_scan_time": None,
        "last_monitor_run": None,
        "chat_history": [],
        "groq_api_key": "",
        "last_manual_result": None,
        "last_manual_incident": None,
        "sn_instance": "",
        "sn_username": "",
        "sn_password": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🤖 ServiceNow AI Incident Bot</h1>
    <p>Powered by Groq LLaMA-3.3-70B | Automated Incident Analysis & Work Note Generation</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR — CONFIGURATION
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    st.divider()

    st.subheader("🔧 ServiceNow")
    sn_instance = st.text_input(
        "Instance URL",
        value=st.session_state.sn_instance or os.getenv("SERVICENOW_INSTANCE", ""),
        placeholder="https://devXXXXX.service-now.com",
        key="sn_instance_input",
    )
    sn_username = st.text_input(
        "Username",
        value=st.session_state.sn_username or os.getenv("SERVICENOW_USERNAME", "admin"),
        key="sn_username_input",
    )
    sn_password = st.text_input(
        "Password",
        type="password",
        value=st.session_state.sn_password or os.getenv("SERVICENOW_PASSWORD", ""),
        key="sn_password_input",
    )

    st.divider()

    st.subheader("🧠 Groq AI")
    groq_api_key = st.text_input(
        "Groq API Key",
        type="password",
        value=st.session_state.get("groq_api_key") or os.getenv("GROQ_API_KEY", ""),
        placeholder="gsk_...",
        key="groq_key_input",
    )
    if groq_api_key:
        st.session_state.groq_api_key = groq_api_key
        masked = groq_api_key[:6] + "..." + groq_api_key[-4:]
        st.caption(f"🔑 Active: `{masked}`")
    else:
        st.caption("🔑 No key set.")

    st.divider()

    st.subheader("📡 Monitor Settings")
    poll_interval = st.slider("Poll Interval (seconds)", 30, 300, 60, 10)
    max_incidents = st.slider("Max Incidents per Scan", 1, 20, 5)
    look_back_minutes = st.slider("Look Back (minutes)", 5, 120, 30)

    st.divider()

    # ── CONNECT BUTTON ──
    if st.button("🔌 Connect & Test", type="primary", key="btn_connect"):
        missing = []
        if not sn_instance:
            missing.append("Instance URL")
        if not sn_username:
            missing.append("Username")
        if not sn_password:
            missing.append("Password")
        if not st.session_state.groq_api_key:
            missing.append("Groq API Key")

        if missing:
            st.warning(f"⚠️ Missing: {', '.join(missing)}")
        else:
            with st.spinner("Connecting..."):
                try:
                    # Save credentials to session state
                    st.session_state.sn_instance = sn_instance
                    st.session_state.sn_username = sn_username
                    st.session_state.sn_password = sn_password

                    # Use cached clients
                    client = get_snow_client(sn_instance, sn_username, sn_password)

                    if client.test_connection():
                        st.session_state.sn_client = client
                        st.session_state.groq_analyzer = GroqIncidentAnalyzer(
                            st.session_state.groq_api_key
                        )
                        st.session_state.connected = True
                        st.success("✅ Connected!")
                    else:
                        st.session_state.connected = False
                except Exception as e:
                    st.error(f"❌ Failed: {str(e)}")
                    st.session_state.connected = False

    st.divider()
    if st.session_state.connected:
        st.success("🟢 Connected")
        st.caption(f"`{sn_instance}`")
    else:
        st.error("🔴 Not Connected")

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🔍 Analyze Incident",
    "💬 Chatbot",
    "📋 Activity Log",
])

# ─────────────────────────────────────────────
# TAB 1: DASHBOARD
# ─────────────────────────────────────────────
with tab1:
    # ── METRICS ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ Analyzed", st.session_state.total_analyzed)
    with col2:
        st.metric("❌ Failed", st.session_state.total_failed)
    with col3:
        st.metric("📂 Tracked", len(st.session_state.processed_incidents))
    with col4:
        last_scan = st.session_state.last_scan_time
        st.metric("⏱️ Last Scan", str(last_scan)[:19] if last_scan else "Never")

    st.divider()

    # ── START / STOP ──
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button(
            "▶️ Start Monitoring",
            disabled=not st.session_state.connected or st.session_state.monitoring_active,
            type="primary",
            key="btn_start",
        ):
            st.session_state.monitoring_active = True
            st.session_state.last_monitor_run = None
            st.success("✅ Monitoring started!")
            st.rerun()

    with col_stop:
        if st.button(
            "⏹️ Stop Monitoring",
            disabled=not st.session_state.monitoring_active,
            key="btn_stop",
        ):
            st.session_state.monitoring_active = False
            st.warning("⏹️ Monitoring stopped.")
            st.rerun()

    # ── NON-BLOCKING MONITORING LOOP ──
    if st.session_state.monitoring_active and st.session_state.connected:
        now = datetime.now()
        last_run = st.session_state.last_monitor_run

        # Check if it's time to scan
        should_scan = (
            last_run is None or
            (now - last_run).total_seconds() >= poll_interval
        )

        if should_scan:
            st.session_state.last_monitor_run = now
            st.session_state.last_scan_time = now

            with st.status("🔄 Scanning for new incidents...", expanded=True) as scan_status:
                try:
                    since = (
                        now - timedelta(minutes=look_back_minutes)
                    ).strftime("%Y-%m-%d %H:%M:%S")

                    st.write("📡 Fetching incidents from ServiceNow...")
                    incidents = st.session_state.sn_client.get_new_incidents(
                        last_checked=since,
                        limit=max_incidents,
                    )

                    already_processed = st.session_state.sn_client.get_processed_incidents()
                    new_incidents = [
                        i for i in incidents
                        if i["sys_id"] not in st.session_state.processed_incidents
                        and i["sys_id"] not in already_processed
                    ]

                    if new_incidents:
                        st.write(f"🆕 Found {len(new_incidents)} new incident(s)")
                        for incident in new_incidents:
                            st.write(f"🤖 Analyzing {incident.get('number')}...")
                            result = st.session_state.groq_analyzer.analyze_incident(incident)
                            success = st.session_state.sn_client.add_work_note(
                                incident["sys_id"], result["work_note"]
                            )
                            if success:
                                st.write(f"✅ Work note posted: {incident.get('number')}")
                                st.session_state.total_analyzed += 1
                                st.session_state.processed_incidents.add(incident["sys_id"])
                                st.session_state.analysis_log.append({
                                    "time": now.strftime("%H:%M:%S"),
                                    "incident": incident.get("number"),
                                    "category": result["detected_category"],
                                    "status": "✅ Success",
                                })
                            else:
                                st.write(f"❌ Failed: {incident.get('number')}")
                                st.session_state.total_failed += 1
                                st.session_state.analysis_log.append({
                                    "time": now.strftime("%H:%M:%S"),
                                    "incident": incident.get("number"),
                                    "category": result["detected_category"],
                                    "status": "❌ Failed",
                                })
                        scan_status.update(
                            label=f"✅ Scan complete — {len(new_incidents)} incident(s) processed",
                            state="complete",
                        )
                    else:
                        st.write("🟢 No new incidents found.")
                        scan_status.update(
                            label="🟢 Scan complete — No new incidents",
                            state="complete",
                        )

                except Exception as e:
                    st.error(f"❌ Scan error: {str(e)}")
                    scan_status.update(label="❌ Scan failed", state="error")
                    st.session_state.monitoring_active = False

        else:
            # Show countdown without blocking
            elapsed = (now - last_run).total_seconds()
            remaining = int(poll_interval - elapsed)
            st.info(f"🟢 Monitoring active — next scan in **{remaining}s**")
            progress = elapsed / poll_interval
            st.progress(min(progress, 1.0))

        # Non-blocking rerun — only sleep 3 seconds
        time.sleep(3)
        st.rerun()

    elif not st.session_state.connected:
        st.warning("⚠️ Please connect to ServiceNow first using the sidebar.")

# ─────────────────────────────────────────────
# TAB 2: ANALYZE SPECIFIC INCIDENT
# ─────────────────────────────────────────────
with tab2:
    st.subheader("🔍 Analyze a Specific Incident")
    st.caption("Fetch any incident, analyze with AI, and post summary to work notes.")

    inc_number = st.text_input(
        "Incident Number",
        placeholder="INC0010001",
        key="manual_incident_input",
    )

    col_analyze, col_post = st.columns(2)

    with col_analyze:
        if st.button(
            "🤖 Analyze",
            disabled=not st.session_state.connected,
            key="btn_analyze",
        ):
            if inc_number.strip():
                with st.spinner("Analyzing..."):
                    incident = st.session_state.sn_client.get_incident_by_number(
                        inc_number.strip()
                    )
                    if incident:
                        result = st.session_state.groq_analyzer.analyze_incident(incident)
                        st.session_state.last_manual_result = result
                        st.session_state.last_manual_incident = incident
                        st.success(f"✅ Done! Analysis ready for {inc_number}")
                    else:
                        st.error(f"❌ Incident {inc_number} not found.")
            else:
                st.warning("⚠️ Enter an incident number.")

    with col_post:
        if st.button(
            "📤 Post to Work Notes",
            disabled=(
                not st.session_state.connected
                or st.session_state.last_manual_result is None
            ),
            key="btn_post",
        ):
            result = st.session_state.last_manual_result
            incident = st.session_state.last_manual_incident
            if result and incident:
                with st.spinner("Posting..."):
                    success = st.session_state.sn_client.add_work_note(
                        incident["sys_id"], result["work_note"]
                    )
                    if success:
                        st.success("✅ Work note posted!")
                        st.session_state.total_analyzed += 1
                        st.session_state.analysis_log.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "incident": result["incident_number"],
                            "category": result["detected_category"],
                            "status": "✅ Success",
                        })
                    else:
                        st.error("❌ Failed to post work note.")

    # ── RESULTS ──
    if st.session_state.last_manual_result:
        result = st.session_state.last_manual_result
        st.divider()

        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            st.info(f"📋 **{result['incident_number']}**")
        with col_i2:
            st.info(f"📂 **{result['detected_category'].upper()}**")
        with col_i3:
            st.info(f"📘 **{result['sop']['doc_id']}**")

        with st.expander("🤖 AI Analysis", expanded=True):
            st.markdown(result["ai_analysis"])

        with st.expander("📘 SOP Details"):
            sop = result["sop"]
            st.write(f"**Title:** {sop['title']}")
            st.write(f"**SLA:** {sop['sla']}")
            st.write(f"**Escalation:** {sop['escalation']}")
            for step in sop["steps"]:
                st.write(step)

        with st.expander("📄 Full Work Note Preview"):
            st.code(result["work_note"], language="text")

# ─────────────────────────────────────────────
# TAB 3: CHATBOT
# ─────────────────────────────────────────────
with tab3:
    st.subheader("💬 Incident Analysis Chatbot")
    st.caption("Ask anything about incidents, paste details, or request SOP guidance.")

    active_key = st.session_state.get("groq_api_key", "")
    if active_key:
        masked = active_key[:6] + "..." + active_key[-4:]
        st.success(f"🔑 Using Groq key: `{masked}`")
    else:
        st.warning("⚠️ No Groq API key. Enter it in the sidebar.")

    st.divider()

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about an incident..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            api_key = st.session_state.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")

            if not api_key:
                response = "⚠️ No Groq API key. Enter it in the sidebar."
                st.markdown(response)
            else:
                with st.spinner("Thinking..."):
                    try:
                        # Use cached Groq client
                        groq_client = get_groq_client(api_key)

                        system_prompt = """You are an expert IT Service Management (ITSM) bot
specializing in ServiceNow incident management.
You help with:
1. Analyzing incidents and identifying issue types
2. Recommending resolution steps
3. Mapping incidents to SOPs
4. SLA guidance and escalation recommendations
5. Generating work notes for ServiceNow tickets
Always be concise, actionable, and solution-focused."""

                        messages = [{"role": "system", "content": system_prompt}]
                        for h in st.session_state.chat_history[-10:]:
                            messages.append({"role": h["role"], "content": h["content"]})

                        chat_response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=messages,
                            temperature=0.4,
                            max_tokens=1000,
                        )
                        response = chat_response.choices[0].message.content
                        st.markdown(response)

                    except Exception as e:
                        response = f"❌ Error: {str(e)}"
                        st.markdown(response)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
            })

    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

# ─────────────────────────────────────────────
# TAB 4: ACTIVITY LOG
# ─────────────────────────────────────────────
with tab4:
    st.subheader("📋 Activity Log")

    if st.session_state.analysis_log:
        h1, h2, h3, h4 = st.columns([1, 2, 2, 1])
        with h1:
            st.markdown("**Time**")
        with h2:
            st.markdown("**Incident**")
        with h3:
            st.markdown("**Category**")
        with h4:
            st.markdown("**Status**")

        st.divider()

        for entry in reversed(st.session_state.analysis_log):
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            with c1:
                st.write(entry["time"])
            with c2:
                st.write(f"📋 {entry['incident']}")
            with c3:
                st.write(f"📂 {entry['category']}")
            with c4:
                st.write(entry["status"])

        st.divider()
        if st.button("🗑️ Clear Log", key="clear_log"):
            st.session_state.analysis_log = []
            st.rerun()
    else:
        st.info("📭 No activity yet. Start monitoring or analyze an incident.")
