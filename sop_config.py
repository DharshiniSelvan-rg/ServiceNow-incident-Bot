# sop_config.py - Standard Operating Procedures mapping

SOP_DATABASE = {
    "network": {
        "title": "Network Incident SOP",
        "doc_id": "SOP-NET-001",
        "steps": [
            "1. Verify network connectivity using ping/traceroute",
            "2. Check firewall rules and ACLs",
            "3. Review network device logs (switches/routers)",
            "4. Check for recent network changes in CMDB",
            "5. Escalate to Network Team if unresolved in 30 mins",
        ],
        "escalation": "Network Operations Team",
        "sla": "P2: 4 hours resolution",
    },
    "server": {
        "title": "Server/Infrastructure SOP",
        "doc_id": "SOP-SRV-002",
        "steps": [
            "1. Check server health metrics (CPU, Memory, Disk)",
            "2. Review system logs (/var/log or Event Viewer)",
            "3. Verify running services and processes",
            "4. Check recent deployments or patches",
            "5. Restart services if safe to do so",
            "6. Escalate to Infrastructure Team if hardware issue",
        ],
        "escalation": "Infrastructure Team",
        "sla": "P1: 1 hour / P2: 4 hours",
    },
    "application": {
        "title": "Application Incident SOP",
        "doc_id": "SOP-APP-003",
        "steps": [
            "1. Identify affected application and version",
            "2. Check application logs for errors/exceptions",
            "3. Verify database connectivity and queries",
            "4. Check recent code deployments or config changes",
            "5. Test in staging environment if possible",
            "6. Escalate to Application Dev Team",
        ],
        "escalation": "Application Development Team",
        "sla": "P2: 4 hours / P3: 8 hours",
    },
    "database": {
        "title": "Database Incident SOP",
        "doc_id": "SOP-DB-004",
        "steps": [
            "1. Check database service status and connectivity",
            "2. Review database error logs",
            "3. Check for long-running queries or locks",
            "4. Verify disk space and tablespace usage",
            "5. Check backup status and replication lag",
            "6. Escalate to DBA Team immediately",
        ],
        "escalation": "Database Administration Team",
        "sla": "P1: 1 hour critical / P2: 4 hours",
    },
    "security": {
        "title": "Security Incident SOP",
        "doc_id": "SOP-SEC-005",
        "steps": [
            "1. IMMEDIATELY isolate affected systems",
            "2. Preserve logs and evidence",
            "3. Notify Security Team and Management",
            "4. Document all actions taken with timestamps",
            "5. Conduct forensic analysis",
            "6. Follow incident response playbook",
        ],
        "escalation": "Security Operations Center (SOC)",
        "sla": "P1: Immediate response",
    },
    "hardware": {
        "title": "Hardware Failure SOP",
        "doc_id": "SOP-HW-006",
        "steps": [
            "1. Identify failed hardware component",
            "2. Check warranty and support contract",
            "3. Initiate failover if available",
            "4. Contact hardware vendor for replacement",
            "5. Schedule maintenance window",
            "6. Update CMDB after replacement",
        ],
        "escalation": "Hardware Support / Vendor",
        "sla": "P1: 2 hours / P2: Next business day",
    },
    "general": {
        "title": "General Incident SOP",
        "doc_id": "SOP-GEN-000",
        "steps": [
            "1. Acknowledge and assess incident impact",
            "2. Identify affected users/systems",
            "3. Gather initial information and symptoms",
            "4. Search knowledge base for similar incidents",
            "5. Attempt standard troubleshooting steps",
            "6. Escalate if not resolved within SLA",
        ],
        "escalation": "Level 2 Support",
        "sla": "Based on priority",
    },
}


def get_sop(category: str) -> dict:
    """Get SOP based on incident category."""
    return SOP_DATABASE.get(category.lower(), SOP_DATABASE["general"])


def detect_category(short_description: str, description: str) -> str:
    """Auto-detect incident category from description."""
    text = f"{short_description} {description}".lower()

    keywords = {
        "network": ["network", "connectivity", "firewall", "vpn", "dns", "routing", "bandwidth", "latency", "switch", "router"],
        "server": ["server", "cpu", "memory", "disk", "ram", "linux", "windows", "vm", "virtual machine", "reboot", "crash"],
        "application": ["application", "app", "software", "web", "portal", "api", "service", "microservice", "deployment", "error 500"],
        "database": ["database", "db", "sql", "oracle", "mysql", "postgres", "mongodb", "query", "table", "deadlock"],
        "security": ["security", "breach", "hack", "unauthorized", "malware", "ransomware", "phishing", "vulnerability", "attack"],
        "hardware": ["hardware", "disk failure", "physical", "nic", "raid", "ups", "power supply", "cable"],
    }

    scores = {category: 0 for category in keywords}
    for category, words in keywords.items():
        for word in words:
            if word in text:
                scores[category] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"
