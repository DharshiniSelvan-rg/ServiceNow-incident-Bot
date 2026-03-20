# servicenow_client.py - ServiceNow REST API Client (Full Updated Version)

import requests
import json
import certifi
import urllib3
from datetime import datetime
from typing import Optional
import streamlit as st

# Disable SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ServiceNowClient:
    def __init__(self, instance_url: str, username: str, password: str):
        self.instance_url = instance_url.strip().rstrip("/")
        self.auth = (username, password)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update(self.headers)
        self.session.verify = certifi.where()  # Use certifi SSL certs by default

    # ─────────────────────────────────────────────
    # INTERNAL: HANDLE HTTP RESPONSE CODES
    # ─────────────────────────────────────────────
    def _handle_response(self, response) -> bool:
        """Handle HTTP response codes with clear user-facing messages."""
        code = response.status_code
        st.info(f"📡 HTTP Status Code: `{code}`")

        if code == 200:
            count = len(response.json().get("result", []))
            st.success(f"✅ Connected successfully! Found {count} incident(s).")
            return True

        elif code == 401:
            st.error("❌ **401 Unauthorized** — Wrong username or password.")
            st.warning(
                "👉 Fix: Go to **developer.servicenow.com** → My Instance → "
                "Action → **Reset admin password**"
            )

        elif code == 403:
            st.error("❌ **403 Forbidden** — User does not have REST API access.")
            st.warning(
                "👉 Fix: In ServiceNow → System Security → Users → "
                "Find your user → Assign role: `rest_api_explorer` or `admin`"
            )

        elif code == 404:
            st.error("❌ **404 Not Found** — Instance URL is wrong or endpoint does not exist.")
            st.warning(
                "👉 Fix: Check your URL format exactly: `https://devXXXXX.service-now.com`"
            )

        elif code == 302 or code == 301:
            st.error(f"❌ **{code} Redirect** — URL may be incorrect or missing `https://`.")
            st.warning(
                f"👉 Redirected to: {response.headers.get('Location', 'unknown')}"
            )

        elif code == 407:
            st.error("❌ **407 Proxy Authentication Required** — A proxy is blocking the connection.")
            st.warning("👉 Fix: Configure proxy settings or connect from a different network.")

        elif code == 429:
            st.error("❌ **429 Too Many Requests** — Rate limit hit.")
            st.warning("👉 Fix: Wait a few minutes and try again.")

        elif code == 502:
            st.error("❌ **502 Bad Gateway** — Your ServiceNow developer instance is **hibernating**.")
            st.warning(
                "👉 Fix: Go to **developer.servicenow.com** → My Instance → "
                "Click **START** button → Wait **3–5 minutes** → Try again."
            )
            st.info(
                "💡 Developer instances go to sleep after inactivity. "
                "You must manually wake them up each time."
            )

        elif code == 503:
            st.error("❌ **503 Service Unavailable** — Instance is starting up or down.")
            st.info("⏳ Wait 2–3 minutes and try again.")

        else:
            st.error(f"❌ **Unexpected Status {code}**")
            try:
                st.code(response.text[:500], language="json")
            except Exception:
                pass

        return False

    # ─────────────────────────────────────────────
    # CONNECTION TEST (WITH FULL DEBUG + SSL FALLBACK)
    # ─────────────────────────────────────────────
    def test_connection(self) -> bool:
        """
        Test connection to ServiceNow instance.
        Tries 3 methods:
          1. With certifi SSL verification
          2. With SSL verification disabled (fallback)
          3. With HTTP instead of HTTPS (last resort)
        """
        url = f"{self.instance_url}/api/now/table/incident?sysparm_limit=1"
        st.info(f"🔗 Attempting connection to: `{url}`")

        # ── ATTEMPT 1: certifi SSL ──
        try:
            st.info("🔐 Try 1: Connecting with certifi SSL verification...")
            response = self.session.get(url, timeout=20, verify=certifi.where())
            result = self._handle_response(response)
            if result:
                self.session.verify = certifi.where()
                return True
            elif response.status_code not in (502, 503):
                return False  # Auth/permission error — no point retrying
        except requests.exceptions.SSLError as e:
            st.warning(f"⚠️ SSL Error on Try 1: `{str(e)[:200]}`")
        except requests.exceptions.ConnectionError as e:
            err = str(e)
            if "502" in err or "RemoteDisconnected" in err or "BadStatusLine" in err:
                st.error("❌ **502 / Remote Disconnected** — Instance is hibernating.")
                st.warning(
                    "👉 Go to **developer.servicenow.com** → My Instance → "
                    "Click **START** → Wait 3–5 minutes → Try again."
                )
                st.info("💡 Verify instance is awake by opening: "
                        f"`{self.instance_url}/login.do` in your browser.")
                return False
            elif "getaddrinfo failed" in err or "Name or service not known" in err:
                st.error("❌ **DNS Error** — Instance URL not found.")
                st.warning("👉 Check URL format: `https://devXXXXX.service-now.com`")
                return False
            st.warning(f"⚠️ Connection Error on Try 1: `{err[:200]}`")
        except requests.exceptions.Timeout:
            st.warning("⚠️ Timeout on Try 1.")
        except Exception as e:
            st.warning(f"⚠️ Try 1 failed: `{str(e)[:200]}`")

        # ── ATTEMPT 2: SSL verification disabled ──
        try:
            st.info("🔓 Try 2: Retrying without SSL verification (dev mode)...")
            response = self.session.get(url, timeout=20, verify=False)
            result = self._handle_response(response)
            if result:
                self.session.verify = False  # Keep disabled for future calls
                st.warning(
                    "⚠️ Connected with SSL verification **disabled**. "
                    "This is fine for development."
                )
                return True
            elif response.status_code == 502:
                st.error("❌ Still getting 502 — Instance is definitely hibernating.")
                st.warning(
                    "👉 **Action Required:** Go to developer.servicenow.com → "
                    "My Instance → Click **START** → Wait 3–5 min → Try again."
                )
                return False
            else:
                return False
        except requests.exceptions.ConnectionError as e:
            err = str(e)
            st.warning(f"⚠️ Try 2 Connection Error: `{err[:200]}`")
            if "502" in err or "RemoteDisconnected" in err:
                st.error("❌ **502 confirmed** — Instance is hibernating.")
                st.warning(
                    "👉 Go to developer.servicenow.com → "
                    "My Instance → Click **START** → Wait 3–5 minutes."
                )
                return False
        except requests.exceptions.Timeout:
            st.warning("⚠️ Timeout on Try 2.")
        except Exception as e:
            st.warning(f"⚠️ Try 2 failed: `{str(e)[:200]}`")

        # ── ATTEMPT 3: HTTP fallback ──
        try:
            http_url = url.replace("https://", "http://")
            st.info(f"🌐 Try 3: Attempting HTTP fallback → `{http_url}`")
            response = self.session.get(http_url, timeout=20, verify=False)
            result = self._handle_response(response)
            if result:
                self.instance_url = self.instance_url.replace("https://", "http://")
                st.warning("⚠️ Connected via HTTP (not HTTPS). Use only for dev/testing.")
                return True
        except Exception as e:
            st.warning(f"⚠️ Try 3 failed: `{str(e)[:200]}`")

        # ── ALL ATTEMPTS FAILED ──
        st.error("❌ All connection attempts failed.")
        st.info(
            "📋 **Checklist:**\n"
            "- [ ] Instance is awake on developer.servicenow.com\n"
            "- [ ] URL format: `https://devXXXXX.service-now.com`\n"
            "- [ ] Username is `admin`\n"
            "- [ ] Password is correct (reset if unsure)\n"
            "- [ ] Open `https://dev222665.service-now.com/login.do` in browser — does it load?"
        )
        return False

    # ─────────────────────────────────────────────
    # FETCH NEW / RECENT INCIDENTS
    # ─────────────────────────────────────────────
    def get_new_incidents(self, last_checked: Optional[str] = None, limit: int = 10) -> list:
        """
        Fetch new/recent incidents from ServiceNow.
        last_checked: datetime string 'YYYY-MM-DD HH:MM:SS'
        """
        url = f"{self.instance_url}/api/now/table/incident"

        query = "active=true^stateIN1,2"
        if last_checked:
            query += f"^sys_created_on>{last_checked}"
        query += "^ORDERBYDESCsys_created_on"

        params = {
            "sysparm_limit": limit,
            "sysparm_fields": (
                "sys_id,number,short_description,description,"
                "priority,urgency,impact,state,category,"
                "assigned_to,caller_id,opened_at,sys_created_on,"
                "assignment_group,cmdb_ci,work_notes"
            ),
            "sysparm_query": query,
            "sysparm_display_value": "true",
        }

        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json().get("result", [])

        except requests.exceptions.HTTPError:
            st.error(f"❌ HTTP {response.status_code} while fetching incidents.")
            return []
        except requests.exceptions.Timeout:
            st.error("❌ Timeout fetching incidents.")
            return []
        except Exception as e:
            st.error(f"❌ Error fetching incidents: {str(e)}")
            return []

    # ─────────────────────────────────────────────
    # FETCH INCIDENT BY NUMBER
    # ─────────────────────────────────────────────
    def get_incident_by_number(self, incident_number: str) -> Optional[dict]:
        """Fetch a specific incident by number e.g. INC0010001."""
        url = f"{self.instance_url}/api/now/table/incident"

        params = {
            "sysparm_query": f"number={incident_number.strip()}",
            "sysparm_fields": (
                "sys_id,number,short_description,description,"
                "priority,urgency,impact,state,category,"
                "assigned_to,caller_id,opened_at,sys_created_on,"
                "assignment_group,cmdb_ci,work_notes,close_notes,resolved_at"
            ),
            "sysparm_display_value": "true",
            "sysparm_limit": 1,
        }

        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            results = response.json().get("result", [])

            if not results:
                st.warning(f"⚠️ No incident found with number: `{incident_number}`")
                return None

            return results[0]

        except requests.exceptions.HTTPError:
            st.error(f"❌ HTTP {response.status_code} fetching incident {incident_number}.")
            return None
        except requests.exceptions.Timeout:
            st.error("❌ Timeout fetching incident.")
            return None
        except Exception as e:
            st.error(f"❌ Error fetching incident {incident_number}: {str(e)}")
            return None

    # ─────────────────────────────────────────────
    # POST WORK NOTE TO INCIDENT
    # ─────────────────────────────────────────────
    def add_work_note(self, sys_id: str, work_note: str) -> bool:
        """Add a work note to a specific incident by sys_id."""
        url = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        payload = {"work_notes": work_note}

        try:
            response = self.session.patch(url, json=payload, timeout=20)

            if response.status_code in (200, 201):
                return True
            elif response.status_code == 401:
                st.error("❌ 401 Unauthorized — Cannot post work note.")
            elif response.status_code == 403:
                st.error("❌ 403 Forbidden — No permission to update work notes.")
            elif response.status_code == 404:
                st.error(f"❌ 404 Not Found — sys_id `{sys_id}` not found.")
            else:
                st.error(f"❌ Failed to post work note. Status: {response.status_code}")
                try:
                    st.code(response.text[:300])
                except Exception:
                    pass
            return False

        except requests.exceptions.Timeout:
            st.error("❌ Timeout posting work note.")
            return False
        except Exception as e:
            st.error(f"❌ Error posting work note: {str(e)}")
            return False

    # ─────────────────────────────────────────────
    # GET ALREADY PROCESSED INCIDENTS
    # ─────────────────────────────────────────────
    def get_processed_incidents(self, tag: str = "[AI-BOT-ANALYZED]") -> list:
        """Return sys_ids of incidents already analyzed by the bot."""
        url = f"{self.instance_url}/api/now/table/incident"
        params = {
            "sysparm_query": f"work_notesCONTAINS{tag}^active=true",
            "sysparm_fields": "sys_id,number",
            "sysparm_limit": 200,
        }
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return [r["sys_id"] for r in response.json().get("result", [])]
        except Exception:
            return []

    # ─────────────────────────────────────────────
    # FETCH ALL OPEN INCIDENTS (for dashboard)
    # ─────────────────────────────────────────────
    def get_all_open_incidents(self, limit: int = 50) -> list:
        """Fetch all currently open/active incidents."""
        url = f"{self.instance_url}/api/now/table/incident"
        params = {
            "sysparm_limit": limit,
            "sysparm_fields": (
                "sys_id,number,short_description,priority,"
                "state,assigned_to,opened_at,category"
            ),
            "sysparm_query": "active=true^stateIN1,2,3^ORDERBYpriority",
            "sysparm_display_value": "true",
        }
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json().get("result", [])
        except Exception as e:
            st.error(f"❌ Error fetching open incidents: {str(e)}")
            return []

    # ─────────────────────────────────────────────
    # STATIC HELPERS
    # ─────────────────────────────────────────────
    @staticmethod
    def format_priority(priority: str) -> str:
        return {
            "1": "🔴 P1 - Critical",
            "2": "🟠 P2 - High",
            "3": "🟡 P3 - Medium",
            "4": "🟢 P4 - Low",
        }.get(str(priority), f"Priority {priority}")

    @staticmethod
    def format_state(state: str) -> str:
        return {
            "1": "🆕 New",
            "2": "🔄 In Progress",
            "3": "⏸️ On Hold",
            "4": "👤 Awaiting User Info",
            "6": "✅ Resolved",
            "7": "🔒 Closed",
        }.get(str(state), state)

    @staticmethod
    def get_current_timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
