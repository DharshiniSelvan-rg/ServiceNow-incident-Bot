# groq_analyzer.py - Groq AI-powered incident analysis

from groq import Groq
from sop_config import get_sop, detect_category
from datetime import datetime


class GroqIncidentAnalyzer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # ✅ Latest supported model

    def analyze_incident(self, incident: dict) -> dict:
        """
        Full incident analysis pipeline.
        Returns structured analysis with all required fields.
        """
        short_desc = incident.get("short_description", "No description")
        description = incident.get("description", "No details provided")
        category = incident.get("category", "")
        priority = incident.get("priority", "3")
        number = incident.get("number", "Unknown")
        opened_at = incident.get("opened_at", "Unknown")

        caller = incident.get("caller_id", {})
        caller_name = (
            caller.get("display_value", "Unknown")
            if isinstance(caller, dict)
            else str(caller)
        )

        assigned_to = incident.get("assigned_to", {})
        assigned_name = (
            assigned_to.get("display_value", "Unassigned")
            if isinstance(assigned_to, dict)
            else str(assigned_to)
        )

        # Auto-detect category if not set
        detected_category = (
            detect_category(short_desc, description)
            if not category
            else category
        )
        sop = get_sop(detected_category)

        # Build the AI prompt
        prompt = self._build_prompt(
            number=number,
            short_desc=short_desc,
            description=description,
            priority=priority,
            opened_at=opened_at,
            caller_name=caller_name,
            assigned_name=assigned_name,
            detected_category=detected_category,
        )

        # Call Groq API
        ai_response = self._call_groq(prompt)

        # Build final work note
        work_note = self._format_work_note(
            number=number,
            ai_analysis=ai_response,
            sop=sop,
            detected_category=detected_category,
            incident=incident,
        )

        return {
            "incident_number": number,
            "detected_category": detected_category,
            "sop": sop,
            "ai_analysis": ai_response,
            "work_note": work_note,
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _build_prompt(self, **kwargs) -> str:
        return f"""You are an expert IT incident analyst. Analyze the following ServiceNow incident and provide a structured analysis.

INCIDENT DETAILS:
- Incident Number  : {kwargs['number']}
- Short Description: {kwargs['short_desc']}
- Full Description : {kwargs['description']}
- Priority         : {kwargs['priority']}
- Category         : {kwargs['detected_category']}
- Reported By      : {kwargs['caller_name']}
- Assigned To      : {kwargs['assigned_name']}
- Opened At        : {kwargs['opened_at']}

Please analyze and respond EXACTLY in this format:

## ISSUE TYPE
[Classify: Network / Server / Application / Database / Security / Hardware / Other]
[Subcategory: Be specific, e.g., "Web Application - 500 Error", "Network - VPN Connectivity"]

## ROOT CAUSE ANALYSIS
[Provide likely root causes based on the description. List 2-3 possible causes with brief explanation]

## IMPACT ASSESSMENT
[Who is affected? How many users? What services are down? What is the business impact?]

## RESOLUTION STEPS
[Provide 5-7 specific actionable resolution steps based on the incident type]
1.
2.
3.
4.
5.

## RECOMMENDED ESCALATION
[Should this be escalated? To whom? Under what conditions?]

## ESTIMATED RESOLUTION TIME
[Based on priority and complexity, estimate resolution time]

## ADDITIONAL NOTES
[Any other important observations or recommendations]"""

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API with the analysis prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert ITSM analyst specializing in IT incident management. "
                            "You provide clear, actionable, technically accurate incident analyses. "
                            "Always be concise, structured, and solution-focused."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return response.choices[0].message.content

        except Exception as e:
            return (
                f"⚠️ AI Analysis Error: {str(e)}\n"
                "Please check your Groq API key and model availability."
            )

    def _format_work_note(
        self,
        number: str,
        ai_analysis: str,
        sop: dict,
        detected_category: str,
        incident: dict,
    ) -> str:
        """Format the complete work note to be posted to ServiceNow."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        priority_labels = {
            "1": "🔴 CRITICAL",
            "2": "🟠 HIGH",
            "3": "🟡 MEDIUM",
            "4": "🟢 LOW",
        }
        priority = incident.get("priority", "3")
        priority_label = priority_labels.get(str(priority), "🟡 MEDIUM")
        sop_steps = "\n".join(sop["steps"])

        work_note = f"""
[AI-BOT-ANALYZED]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AI INCIDENT ANALYSIS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Incident   : {number}
⏰ Analyzed At: {now}
🔴 Priority   : {priority_label}
📂 Category   : {detected_category.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{ai_analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📘 STANDARD OPERATING PROCEDURE (SOP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOP Reference : {sop['doc_id']} - {sop['title']}
SLA Target    : {sop['sla']}
Escalation To : {sop['escalation']}

SOP Steps:
{sop_steps}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️  Auto-generated by AI Incident Bot
    Model: LLaMA-3.3-70B | Powered by Groq
    ServiceNow Integration v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return work_note.strip()
