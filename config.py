import os
from dotenv import load_dotenv

load_dotenv()

SERVICENOW_INSTANCE   = os.getenv("SERVICENOW_INSTANCE", "")
SERVICENOW_USERNAME   = os.getenv("SERVICENOW_USERNAME", "")
SERVICENOW_PASSWORD   = os.getenv("SERVICENOW_PASSWORD", "")
GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60))
