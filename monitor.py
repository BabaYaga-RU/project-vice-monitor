import requests
import datetime
import json
import os
import sys
import socket
import time
import re
from urllib.parse import urlparse

# Advanced configuration
SERVICES = {
    "github_pages": {
        "url": "https://pklavc.github.io/",
        "name": "GitHub Pages",
        "type": "website",
        "keywords": ["PkLavc", "Patrick", "Software Engineer"],
        "security_headers": ["strict-transport-security", "x-content-type-options"]
    },
    "github_api": {
        "url": "https://api.github.com/repos/PkLavc/codepulse-monorepo",
        "name": "GitHub API",
        "type": "api",
        "keywords": ["codepulse-monorepo"],
        "security_headers": ["strict-transport-security", "x-content-type-options"]
    }
}

HISTORY_FILE = "history.json"
INDEX_FILE = "index.html"
SHIELDS_BADGE_FILE = "uptime-badge.json"
MAX_HISTORY_RECORDS = 500  # Log rotation: keep only the most recent 500 records
CLEANUP_DAYS = 90  # Remove records older than 90 days

def load_history():
    """Load monitoring history"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                
            # Backward compatibility with older history format
            if "services" not in history:
                history = {
                    "services": {key: [] for key in SERVICES.keys()},
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "page_size_history": []
                }
            else:
                # Ensure all service keys exist
                for service_key in SERVICES.keys():
                    if service_key not in history["services"]:
                        history["services"][service_key] = []
                # Ensure page_size_history exists
                if "page_size_history" not in history:
                    history["page_size_history"] = []
            
            return history
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    return {
        "services": {key: [] for key in SERVICES.keys()},
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "page_size_history": []
    }

def save_history(history):
    """Save monitoring history"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def measure_dns_resolution(url):
    """Measure DNS resolution time"""
    try:
        hostname = urlparse(url).hostname
        start_time = time.time()
        socket.gethostbyname(hostname)
        dns_time = (time.time() - start_time) * 1000
        return round(dns_time, 2)
    except Exception:
        return 0

def measure_tcp_connection(url):
    """Measure TCP connection time"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((hostname, port))
        sock.close()
        tcp_time = (time.time() - start_time) * 1000
        return round(tcp_time, 2)
    except Exception:
        return 0

def deep_health_check(url, response, keywords):
    """Check if HTML content contains specified keywords"""
    try:
        content = response.text.lower()
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in content:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords
    except Exception:
        return False, []

def analyze_security_headers(response, service_config):
    """Analyze presence of security headers"""
    security_checks = {}
    required_headers = service_config["security_headers"]
    
    for header in required_headers:
        security_checks[header] = header.lower() in response.headers
        
    return security_checks

def check_service(service_key, service_config):
    """Perform advanced monitoring with detailed metrics"""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        # Detailed timing measurements
        dns_time = measure_dns_resolution(service_config["url"])
        
        start_total = time.time()
        response = requests.get(
            service_config["url"], 
            timeout=10,
            headers={'User-Agent': 'UptimeMonitor/1.0'}
        )
        total_time = (time.time() - start_total) * 1000
        
        tcp_time = measure_tcp_connection(service_config["url"])
        transfer_time = total_time - dns_time - tcp_time
        
        # Advanced checks
        status = "ONLINE" if response.status_code == 200 else f"OFFLINE ({response.status_code})"
        
        # Deep health check for websites
        content_ok = True
        found_keywords = []
        security_headers = {}
        
        if service_config["type"] == "website":
            content_ok, found_keywords = deep_health_check(
                service_config["url"], response, service_config["keywords"]
            )
            if not content_ok:
                status = "CONTENT_ERROR"
        
        # Security analysis
        if response.status_code == 200:
            security_headers = analyze_security_headers(response, service_config)
        
        record = {
            "timestamp": timestamp,
            "url": service_config["url"],
            "status": status,
            "http_code": response.status_code,
            "total_time_ms": round(total_time, 2),
            "dns_time_ms": dns_time,
            "tcp_time_ms": tcp_time,
            "transfer_time_ms": round(transfer_time, 2),
            "content_ok": content_ok,
            "found_keywords": found_keywords,
            "security_headers": security_headers,
            "engagement": {}  # For GitHub API
        }
        
        # Extract engagement data for CodePulse API
        if service_key == "github_api" and response.status_code == 200:
            try:
                data = response.json()
                record["engagement"] = {
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "open_issues": data.get("open_issues_count", 0)
                }
            except:
                pass
        
    except Exception as e:
        record = {
            "timestamp": timestamp,
            "url": service_config["url"],
            "status": "ERROR",
            "http_code": 0,
            "total_time_ms": 0,
            "dns_time_ms": 0,
            "tcp_time_ms": 0,
            "transfer_time_ms": 0,
            "content_ok": False,
            "found_keywords": [],
            "security_headers": {},
            "error": str(e),
            "engagement": {}
        }
    
    return record

def add_record_to_history(history, service_key, record):
    """Add a record to history with log rotation"""
    history["services"][service_key].append(record)
    
    # Implement log rotation (keep only the most recent records)
    if len(history["services"][service_key]) > MAX_HISTORY_RECORDS:
        history["services"][service_key] = history["services"][service_key][-MAX_HISTORY_RECORDS:]
    
    save_history(history)

def parse_timestamp(ts_str):
    """Parse timestamp string, handling both naive and aware datetimes"""
    dt = datetime.datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        # If naive, assume UTC
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt

def cleanup_old_records(history):
    """Remove records older than 90 days to keep the repository lean"""
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=CLEANUP_DAYS)
    
    for service_key in history["services"]:
        original_count = len(history["services"][service_key])
        history["services"][service_key] = [
            record for record in history["services"][service_key]
            if parse_timestamp(record["timestamp"]) >= cutoff_date
        ]
        removed_count = original_count - len(history["services"][service_key])
        if removed_count > 0:
            print(f"Cleanup: Removed {removed_count} old records for service {service_key}")

def calculate_uptime_percentage(records, time_filter=None):
    """Calculate uptime percentage for a set of records"""
    if not records:
        return 0
    
    # Filter records if needed
    if time_filter:
        filtered_records = [r for r in records if parse_timestamp(r["timestamp"]) >= time_filter]
    else:
        filtered_records = records
    
    if not filtered_records:
        return 0
    
    online_records = [r for r in filtered_records if r.get("status") == "ONLINE"]
    return (len(online_records) / len(filtered_records)) * 100

def calculate_performance_metrics(records, time_filter=None):
    """Calculate detailed performance metrics"""
    if not records:
        return {
            "avg_latency": 0,
            "avg_dns_time": 0,
            "avg_tcp_time": 0,
            "avg_transfer_time": 0,
            "peak_hour": None,
            "slowest_response": 0,
            "fastest_response": 0
        }
    
    # Filter records if needed
    if time_filter:
        filtered_records = [r for r in records if parse_timestamp(r["timestamp"]) >= time_filter]
    else:
        filtered_records = records
    
    online_records = [r for r in filtered_records if r.get("status") == "ONLINE" and r.get("total_time_ms", 0) > 0]
    
    if not online_records:
        return {
            "avg_latency": 0,
            "avg_dns_time": 0,
            "avg_tcp_time": 0,
            "avg_transfer_time": 0,
            "peak_hour": None,
            "slowest_response": 0,
            "fastest_response": 0
        }
    
    # Latency calculations
    latencies = [r["total_time_ms"] for r in online_records]
    dns_times = [r["dns_time_ms"] for r in online_records if r.get("dns_time_ms", 0) > 0]
    tcp_times = [r["tcp_time_ms"] for r in online_records if r.get("tcp_time_ms", 0) > 0]
    transfer_times = [r["transfer_time_ms"] for r in online_records if r.get("transfer_time_ms", 0) > 0]
    
    # Peak hour (highest latency)
    peak_record = max(online_records, key=lambda x: x["total_time_ms"])
    peak_hour = parse_timestamp(peak_record["timestamp"]).strftime("%H:%M")
    
    return {
        "avg_latency": round(sum(latencies) / len(latencies), 2),
        "avg_dns_time": round(sum(dns_times) / len(dns_times), 2) if dns_times else 0,
        "avg_tcp_time": round(sum(tcp_times) / len(tcp_times), 2) if tcp_times else 0,
        "avg_transfer_time": round(sum(transfer_times) / len(transfer_times), 2) if transfer_times else 0,
        "peak_hour": peak_hour,
        "slowest_response": max(latencies),
        "fastest_response": min(latencies)
    }

def get_time_filters():
    """Get time filters for statistical calculations"""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Last 24 hours
    last_24h = now - datetime.timedelta(hours=24)
    
    # Last 7 days
    last_7d = now - datetime.timedelta(days=7)
    
    # Last 30 days
    last_30d = now - datetime.timedelta(days=30)
    
    return {
        "last_24h": last_24h,
        "last_7d": last_7d,
        "last_30d": last_30d
    }

def process_service_data(history, service_key):
    """Process service data and calculate advanced statistics"""
    records = history["services"][service_key]
    
    if not records:
        return {
            "current_status": "UNKNOWN",
            "sla_24h": 0,
            "sla_7d": 0,
            "sla_30d": 0,
            "performance": {},
            "last_check": "",
            "engagement": {}
        }
    
    # Get time filters
    time_filters = get_time_filters()
    
    # Calculate SLA for different periods
    sla_24h = calculate_uptime_percentage(records, time_filters["last_24h"])
    sla_7d = calculate_uptime_percentage(records, time_filters["last_7d"])
    sla_30d = calculate_uptime_percentage(records, time_filters["last_30d"])
    
    # Status atual (precisa ser definido antes da lógica de initial state)
    last_record = records[-1] if records else None
    current_status = last_record.get("status", "UNKNOWN") if last_record else "UNKNOWN"
    
    # Initial State Logic: Se histórico pequeno, assume 100% se teste atual OK
    if len(records) < 10:  # Less than 10 records
        if current_status == "ONLINE":
            sla_24h = sla_7d = sla_30d = 100.0
    
    # Calculate performance metrics
    performance = calculate_performance_metrics(records, time_filters["last_24h"])
    
    # Status atual (já definido acima)
    last_check = last_record["timestamp"] if last_record else ""
    
    # Engagement (for GitHub API)
    engagement = last_record.get("engagement", {})
    
    return {
        "current_status": current_status,
        "sla_24h": round(sla_24h, 2),
        "sla_7d": round(sla_7d, 2),
        "sla_30d": round(sla_30d, 2),
        "performance": performance,
        "last_check": last_check,
        "engagement": engagement
    }

def generate_incident_log(history):
    """Generate incident log from history"""
    incidents = []
    
    for service_key in SERVICES.keys():
        records = history["services"][service_key]
        if not records:
            continue
        
        current_incident = None
        
        for record in records:
            status = record["status"]
            timestamp = record["timestamp"]
            
            if status != "ONLINE" and current_incident is None:
                # Start of incident
                current_incident = {
                    "service": service_key,
                    "start_time": timestamp,
                    "end_time": None,
                    "status": status,
                    "duration": "Em andamento"
                }
            elif status == "ONLINE" and current_incident is not None:
                # End of incident
                current_incident["end_time"] = timestamp
                start_dt = parse_timestamp(current_incident["start_time"])
                end_dt = parse_timestamp(current_incident["end_time"])
                duration = end_dt - start_dt
                current_incident["duration"] = str(duration).split('.')[0]  # Remove milliseconds
                incidents.append(current_incident)
                current_incident = None
        
        # If there is an ongoing incident
        if current_incident:
            incidents.append(current_incident)
    
    # Sort by date (most recent first)
    incidents.sort(key=lambda x: x["start_time"], reverse=True)
    return incidents

def generate_shields_badge(history):
    """Generate a Shields.io badge"""
    github_records = history["services"]["github_pages"]
    if not github_records:
        uptime = 0
    else:
        time_filters = get_time_filters()
        uptime = calculate_uptime_percentage(github_records, time_filters["last_24h"])
    
    badge_data = {
        "schemaVersion": 1,
        "label": "Uptime",
        "message": f"{uptime:.1f}%",
        "color": "brightgreen" if uptime >= 99.0 else "yellow" if uptime >= 95.0 else "red"
    }
    
    with open(SHIELDS_BADGE_FILE, 'w') as f:
        json.dump(badge_data, f, indent=2)
    
    return badge_data

def inject_data_into_html(history):
    """Injeta os dados diretamente no script do index.html"""
    if not os.path.exists(INDEX_FILE):
        return False
    
    # Processa os dados exatamente como o script.js espera
    processed_data = {}
    for service_key in SERVICES.keys():
        processed_data[service_key] = process_service_data(history, service_key)
    
    dashboard_data = {
        "services": processed_data,
        "incident_log": generate_incident_log(history),
        "badge": generate_shields_badge(history),
        "history": history["services"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    json_data = json.dumps(dashboard_data, indent=2)
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitui o conteúdo da tag script com ID 'dashboard-data'
    pattern = r'<script id="dashboard-data">.*?</script>'
    replacement = f'<script id="dashboard-data">window.dashboardData = {json_data};</script>'
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        # Se a tag não existir, insere antes do fechamento do body
        new_content = content.replace('</body>', f'{replacement}\n</body>')
        
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def check_page_size(url="https://pklavc.github.io/codepulse-monorepo/"):
    """Check codepulse-monorepo page size"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            return round(size_kb, 2)
        return 0
    except Exception:
        return 0

def should_alert_services(history):
    """Check if any service is experiencing problems"""
    for service_key in SERVICES.keys():
        records = history["services"][service_key]
        if not records:
            continue
        
        last_record = records[-1]
        if last_record["status"] != "ONLINE":
            return True
    
    return False

def main():
    """Main SRE monitoring function"""
    print("Starting advanced SRE monitoring...")
    
    # Load history
    history = load_history()
    
    # Monitora cada serviço
    service_results = {}
    for service_key, service_config in SERVICES.items():
        print(f"Monitorando {service_config['name']}...")
        record = check_service(service_key, service_config)
        add_record_to_history(history, service_key, record)
        service_results[service_key] = record
        
        status_symbol = "+" if record["status"] == "ONLINE" else "-"
        latency_str = f"{record.get('total_time_ms', 0)}ms" if record["status"] == "ONLINE" else "N/A"
        print(f"  {status_symbol} {service_config['name']}: {record['status']} - {latency_str}")
    
    # Cleanup old records
    print("Performing old record cleanup...")
    cleanup_old_records(history)
    
    # Check page size
    print("Checking codepulse-monorepo page size...")
    current_size = check_page_size()
    if current_size > 0:
        history["page_size_history"].append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "size_kb": current_size
        })
        # Keep only the last 30 page size records
        if len(history["page_size_history"]) > 30:
            history["page_size_history"] = history["page_size_history"][-30:]
        
        # Check for significant change
        if len(history["page_size_history"]) > 1:
            previous_size = history["page_size_history"][-2]["size_kb"]
            change_percent = abs(current_size - previous_size) / previous_size * 100
            if change_percent > 20:  # Change > 20%
                print(f"ALERT: Significant page size change detected: {previous_size}KB -> {current_size}KB ({change_percent:.1f}%)")
                # Flag for special commit
                os.environ["MONITOR_EXIT_CODE"] = "1"
    
    save_history(history)
    
    # Inject data into HTML
    print("Updating observability dashboard...")
    if inject_data_into_html(history):
        print("Dashboard updated successfully!")
    else:
        print("Failed to update dashboard")
        sys.exit(1)
    
    # Check if alert is needed
    if should_alert_services(history):
        print("ALERT: Incident detected!")
        sys.exit(1)
    else:
        print("Monitoring completed successfully - all services online")
        sys.exit(0)

if __name__ == "__main__":
    main()