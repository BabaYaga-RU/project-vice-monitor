import requests
import datetime
import json
import os
import sys
import socket
import time
import re
import random
import hashlib
from urllib.parse import urlparse

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# GTA VI Real-Time Intelligence Monitoring
SERVICES = {
    "gta_vi_official": {
        "url": "https://www.rockstargames.com/VI/",
        "name": "GTA VI Official",
        "type": "website",
        "keywords": ["Grand Theft Auto", "GTA VI", "Rockstar"],
        "security_headers": ["strict-transport-security", "x-content-type-options"]
    },
    "rockstar_newswire": {
        "url": "https://www.rockstargames.com/newswire",
        "name": "Rockstar Newswire",
        "type": "website",
        "keywords": ["Rockstar", "News", "GTA"],
        "security_headers": ["strict-transport-security", "x-content-type-options"]
    },
    "playstation_store": {
        "url": "https://www.playstation.com/en-us/games/grand-theft-auto-vi/",
        "name": "PlayStation Store - GTA VI",
        "type": "website",
        "keywords": ["Grand Theft Auto", "GTA VI", "PlayStation"],
        "security_headers": ["strict-transport-security", "x-content-type-options"]
    },
    "xbox_store": {
        "url": "https://www.xbox.com/en-US/games/store/grand-theft-auto-vi/9NL3WWNZLZZN",
        "name": "Xbox Store - GTA VI",
        "type": "website",
        "keywords": ["Grand Theft Auto", "GTA VI", "Xbox"],
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
        # Handle encoding issues
        content = response.text
        if content:
            content = content.lower()
        else:
            content = ""
        
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

def calculate_content_hash(content):
    """Calculate SHA-256 hash of HTML content"""
    try:
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    except Exception:
        return None

def detect_intelligence_update(history, service_key, new_hash):
    """Detect if content hash changed - indicates Intelligence Update"""
    if not history or "services" not in history:
        return False, None
    
    records = history["services"].get(service_key, [])
    
    if not records:
        return False, None
    
    # Get the last record's hash if it exists
    last_record = records[-1]
    previous_hash = last_record.get("content_hash")
    
    if previous_hash and previous_hash != new_hash:
        return True, f"Hash changed: {previous_hash[:8]}... → {new_hash[:8]}..."
    
    return False, None

def generate_blog_entry(record, service_config):
    """Generate a blog entry for INTELLIGENCE_UPDATE"""
    try:
        # Create blog directory if it doesn't exist
        blog_dir = "blog"
        if not os.path.exists(blog_dir):
            os.makedirs(blog_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.fromisoformat(record["timestamp"])
        filename = f"update-{timestamp.strftime('%Y-%m-%d-%H')}.md"
        filepath = os.path.join(blog_dir, filename)
        
        # Determine security status
        security_status = "SECURE" if record.get("status") == "INTELLIGENCE_UPDATE" else "WARNING"
        
        # Generate blog content
        blog_content = f"""# Intelligence Update - {timestamp.strftime('%B %d, %Y at %H:%M UTC')}

**Date:** {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
**URL Monitored:** {service_config['url']}
**Service:** {service_config['name']}
**Hash SHA-256:** `{record.get('content_hash', 'N/A')}`
**Security Status:** {security_status}

## Summary

Content change detected on {service_config['name']}. The page content has been modified, indicating a potential update or change in the monitored service.

## Details

- **Detection Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **Service Type:** {service_config['type']}
- **Keywords Monitored:** {', '.join(service_config['keywords'])}
- **Content Size:** {record.get('html_size_kb', 0)} KB
- **Response Time:** {record.get('total_time_ms', 0)} ms

## Security Analysis

The change has been flagged as **{security_status}** based on the monitoring system's assessment.

## Next Steps

Monitor this service for any additional changes or updates that may follow this intelligence update.

---

*This entry was automatically generated by the Project Vice Monitor system.*
"""
        
        # Write the blog entry
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        
        print(f"[INFO] Blog entry created: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"[ERROR] Failed to create blog entry: {e}")
        return None

def is_service_healthy(status):
    """Health classification layer for services.
    
    Returns True if service is considered healthy for monitoring purposes.
    This helps eliminate false-positive incidents by treating DEGRADED as healthy.
    """
    return status in ["ONLINE", "DEGRADED", "INTELLIGENCE_UPDATE"]

def safe_request(url, headers=None, timeout=15, max_retries=3):
    """HTTP request with retry and exponential backoff"""
    session = requests.Session()
    session.headers.update({'User-Agent': 'UptimeMonitor/1.0'})
    if GITHUB_TOKEN:
        session.headers.update({'Authorization': f'token {GITHUB_TOKEN}'})
    
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Attempt {attempt + 1} for {url}")
            response = session.get(url, timeout=timeout)
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"[ERROR] All {max_retries} attempts failed for {url}: {e}")
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"[WARN] Request failed attempt {attempt + 1}, retrying in {delay:.2f}s")
            time.sleep(delay)
    
    return None

def check_service(service_key, service_config, history=None):
    """Perform advanced monitoring with detailed metrics"""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        # Detailed timing measurements
        dns_time = measure_dns_resolution(service_config["url"])
        
        start_total = time.time()
        headers = {'User-Agent': 'UptimeMonitor/1.0'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        response = safe_request(
            service_config["url"], 
            headers=headers,
            timeout=15,
            max_retries=3
        )
        
        if response is None:
            print(f"[ERROR] Failed to get response for {service_config['name']}")
            return {
                "timestamp": timestamp,
                "url": service_config["url"],
                "status": "ERROR",
                "http_code": 0,
                "total_time_ms": 0,
                "dns_time_ms": dns_time,
                "tcp_time_ms": 0,
                "transfer_time_ms": 0,
                "content_ok": False,
                "found_keywords": [],
                "security_headers": {},
                "error": "No response received",
                "engagement": {}
            }
        
        total_time = (time.time() - start_total) * 1000
        
        tcp_time = measure_tcp_connection(service_config["url"])
        transfer_time = max(0, total_time - dns_time - tcp_time)  # Ensure non-negative
        
        # Improved HTTP status handling - treat these as healthy
        healthy_status_codes = [200, 204, 301, 302, 304]
        if response.status_code in healthy_status_codes:
            status = "ONLINE"
        else:
            status = f"OFFLINE ({response.status_code})"
        
        # Handle GitHub API rate limiting
        if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
            status = "DEGRADED"
            print(f"[WARN] GitHub API rate limited for {service_config['name']}")
        
        # Deep health check for websites
        content_ok = True
        found_keywords = []
        security_headers = {}
        content_hash = None
        html_size_kb = 0
        intelligence_update = False
        
        if service_config["type"] == "website":
            content_ok, found_keywords = deep_health_check(
                service_config["url"], response, service_config["keywords"]
            )
            if not content_ok:
                status = "CONTENT_ERROR"
            elif total_time > 2000:  # Latency > 2000ms
                status = "DEGRADED"

            # Calculate content hash and detect intelligence updates
            content_hash = calculate_content_hash(response.content)
            
            # Check for intelligence updates
            if history:
                is_update, update_msg = detect_intelligence_update(history, service_key, content_hash)
                if is_update:
                    intelligence_update = True
                    status = "INTELLIGENCE_UPDATE"
                    print(f"[ALERT] Intelligence Update on {service_config['name']}: {update_msg}")
                    
                    # Generate blog entry for intelligence update
                    try:
                        # Create a temporary record with the intelligence update info
                        temp_record = {
                            "timestamp": timestamp,
                            "content_hash": content_hash,
                            "status": "INTELLIGENCE_UPDATE",
                            "total_time_ms": round(total_time, 2),
                            "html_size_kb": html_size_kb if html_size_kb is not None else 0
                        }
                        generate_blog_entry(temp_record, service_config)
                    except Exception as e:
                        print(f"[WARN] Failed to generate blog entry: {e}")

            # HTML size analysis
            html_size_kb = round(len(response.content) / 1024, 2)
            num_images = len(re.findall(r'<img\b', response.text, re.I))
            num_links = len(re.findall(r'<a\b', response.text, re.I))
            num_scripts = len(re.findall(r'<script\b', response.text, re.I))
            num_stylesheets = len(re.findall(r"<link[^>]+rel=['\"]stylesheet['\"]", response.text, re.I))

            title_match = re.search(r'<title>(.*?)</title>', response.text, re.I | re.S)
            page_title = title_match.group(1).strip() if title_match else None

            meta_desc = re.search(r"<meta\s+name=['\"]description['\"]\s+content=['\"](.*?)['\"]", response.text, re.I)
            meta_description = meta_desc.group(1).strip() if meta_desc else None

        # Security analysis with additional headers
        if response.status_code in healthy_status_codes:
            security_headers = analyze_security_headers(response, service_config)
            # Additional security headers check
            additional_headers = ["content-security-policy", "x-frame-options", "referrer-policy"]
            for header in additional_headers:
                security_headers[header] = header.lower() in response.headers
        
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
            "engagement": {},  # For GitHub API compatibility
            "content_hash": content_hash,
            "intelligence_update": intelligence_update,
            "html_size_kb": html_size_kb if service_config["type"] == "website" else 0,
            "num_images": num_images if service_config["type"] == "website" else 0,
            "num_links": num_links if service_config["type"] == "website" else 0,
            "num_scripts": num_scripts if service_config["type"] == "website" else 0,
            "num_stylesheets": num_stylesheets if service_config["type"] == "website" else 0,
            "page_title": page_title if service_config["type"] == "website" else None,
            "meta_description": meta_description if service_config["type"] == "website" else None
        }
        
    except requests.exceptions.ConnectTimeout:
        print(f"[WARN] Connection timeout for {service_config['name']}")
        record = {
            "timestamp": timestamp,
            "url": service_config["url"],
            "status": "DEGRADED",
            "http_code": 0,
            "total_time_ms": 0,
            "dns_time_ms": dns_time,
            "tcp_time_ms": 0,
            "transfer_time_ms": 0,
            "content_ok": False,
            "found_keywords": [],
            "security_headers": {},
            "error": "Connection timeout",
            "engagement": {}
        }
    except requests.exceptions.ReadTimeout:
        print(f"[WARN] Read timeout for {service_config['name']}")
        record = {
            "timestamp": timestamp,
            "url": service_config["url"],
            "status": "DEGRADED",
            "http_code": 0,
            "total_time_ms": 0,
            "dns_time_ms": dns_time,
            "tcp_time_ms": 0,
            "transfer_time_ms": 0,
            "content_ok": False,
            "found_keywords": [],
            "security_headers": {},
            "error": "Read timeout",
            "engagement": {}
        }
    except Exception as e:
        print(f"[ERROR] Service check failed for {service_config['name']}: {e}")
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
    """Calculate uptime percentage for a set of records using health classification"""
    if not records:
        return 0
    
    # Filter records if needed
    if time_filter:
        filtered_records = [r for r in records if parse_timestamp(r["timestamp"]) >= time_filter]
    else:
        filtered_records = records
    
    if not filtered_records:
        return 0
    
    # Use health classification to count healthy services (ONLINE + DEGRADED)
    healthy_records = [r for r in filtered_records if is_service_healthy(r.get("status", ""))]
    return (len(healthy_records) / len(filtered_records)) * 100

def calculate_performance_metrics(records, time_filter=None):
    """Calculate detailed performance metrics using health classification"""
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
    
    # Use health classification to include both ONLINE and DEGRADED services
    healthy_records = [r for r in filtered_records if is_service_healthy(r.get("status", "")) and r.get("total_time_ms", 0) > 0]
    
    if not healthy_records:
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
    latencies = [r["total_time_ms"] for r in healthy_records]
    dns_times = [r["dns_time_ms"] for r in healthy_records if r.get("dns_time_ms", 0) > 0]
    tcp_times = [r["tcp_time_ms"] for r in healthy_records if r.get("tcp_time_ms", 0) > 0]
    transfer_times = [r["transfer_time_ms"] for r in healthy_records if r.get("transfer_time_ms", 0) > 0]
    
    # Peak hour (highest latency)
    peak_record = max(healthy_records, key=lambda x: x["total_time_ms"])
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
    """Generate incident log from history - only log truly unhealthy services"""
    incidents = []
    
    for service_key in SERVICES.keys():
        records = history["services"][service_key]
        if not records:
            continue
        
        current_incident = None
        
        for record in records:
            status = record["status"]
            timestamp = record["timestamp"]
            
            # Only start incident for truly unhealthy services (not DEGRADED)
            if not is_service_healthy(status) and current_incident is None:
                # Start of incident
                current_incident = {
                    "service": service_key,
                    "start_time": timestamp,
                    "end_time": None,
                    "status": status,
                    "duration": "Em andamento"
                }
            elif is_service_healthy(status) and current_incident is not None:
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
    # Use the first service as reference for uptime calculation
    first_service_key = list(SERVICES.keys())[0]
    service_records = history["services"][first_service_key]
    if not service_records:
        uptime = 0
    else:
        time_filters = get_time_filters()
        uptime = calculate_uptime_percentage(service_records, time_filters["last_24h"])
    
    badge_data = {
        "schemaVersion": 1,
        "label": "Uptime",
        "message": f"{uptime:.1f}%",
        "color": "brightgreen" if uptime >= 99.0 else "yellow" if uptime >= 95.0 else "red"
    }
    
    with open(SHIELDS_BADGE_FILE, 'w') as f:
        json.dump(badge_data, f, indent=2)
    
    return badge_data

def inject_data_into_html(history, summary=None):
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
        "page_size_history": history.get("page_size_history", []),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": summary or {}
    }
    
    # Use ensure_ascii=False to properly handle Unicode characters
    json_data = json.dumps(dashboard_data, indent=2, ensure_ascii=False)
    
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

def save_dashboard_data_to_json(history, summary=None):
    """Save dashboard data to a separate JSON file for static hosting"""
    # Processa os dados exatamente como o script.js espera
    processed_data = {}
    for service_key in SERVICES.keys():
        processed_data[service_key] = process_service_data(history, service_key)
    
    dashboard_data = {
        "services": processed_data,
        "incident_log": generate_incident_log(history),
        "badge": generate_shields_badge(history),
        "history": history["services"],
        "page_size_history": history.get("page_size_history", []),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": summary or {}
    }
    
    # Save to data/dashboard-data.json
    data_file_path = "data/dashboard-data.json"
    try:
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        print(f"Dashboard data saved to {data_file_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save dashboard data to JSON: {e}")
        return False

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
    start_time = datetime.datetime.now(datetime.timezone.utc)

    try:
        # Load history
        history = load_history()
        print(f"Loaded history with {len(history.get('services', {}))} services")
    except Exception as e:
        print(f"ERROR: Failed to load history: {e}")
        sys.exit(1)

    # Monitora cada serviço
    service_results = {}
    for service_key, service_config in SERVICES.items():
        print(f"Monitorando {service_config['name']}...")
        try:
            record = check_service(service_key, service_config, history)
            add_record_to_history(history, service_key, record)
            service_results[service_key] = record

            status_symbol = "+" if record["status"] == "ONLINE" else "-"
            latency_str = f"{record.get('total_time_ms', 0)}ms" if record["status"] == "ONLINE" else "N/A"
            print(f"  {status_symbol} {service_config['name']}: {record['status']} - {latency_str}")
        except Exception as e:
            print(f"ERROR: Failed to monitor {service_config['name']}: {e}")
            # Create error record
            error_record = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
            add_record_to_history(history, service_key, error_record)
            service_results[service_key] = error_record
    
    # Cleanup old records
    print("Performing old record cleanup...")
    try:
        cleanup_old_records(history)
    except Exception as e:
        print(f"WARNING: Cleanup failed: {e}")
    
    try:
        save_history(history)
    except Exception as e:
        print(f"ERROR: Failed to save history: {e}")
        sys.exit(1)

    # Build a summary object for the dashboard
    time_filters = get_time_filters()
    summary = {
        "run_duration_seconds": round((datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds(), 2),
        "incidents_last_24h": {},
        "avg_latency_last_24h": {},
        "intelligence_updates": []
    }

    for service_key in SERVICES.keys():
        try:
            records = history["services"][service_key]
            last_24h = [r for r in records if parse_timestamp(r["timestamp"]) >= time_filters["last_24h"]]
            summary["incidents_last_24h"][service_key] = len([r for r in last_24h if r.get("status") not in ["ONLINE", "INTELLIGENCE_UPDATE"]])
            
            # Track intelligence updates
            intelligence_updates = [r for r in last_24h if r.get("intelligence_update", False)]
            if intelligence_updates:
                summary["intelligence_updates"].append({
                    "service": service_key,
                    "count": len(intelligence_updates),
                    "latest": intelligence_updates[-1]["timestamp"]
                })

            perf = calculate_performance_metrics(records, time_filters["last_24h"])
            summary["avg_latency_last_24h"][service_key] = int(perf.get("avg_latency", 0)) if perf and perf.get("avg_latency", 0) else 0
        except Exception as e:
            print(f"WARNING: Failed to process data for {service_key}: {e}")
            summary["incidents_last_24h"][service_key] = 0
            summary["avg_latency_last_24h"][service_key] = 0

    # Save data to JSON file for static hosting
    print("Saving dashboard data to JSON file...")
    try:
        if save_dashboard_data_to_json(history, summary):
            print("Dashboard data saved to JSON successfully!")
        else:
            print("Failed to save dashboard data to JSON")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to save dashboard data to JSON: {e}")
        sys.exit(1)
    
    # Inject data into HTML (for backward compatibility)
    print("Updating observability dashboard...")
    try:
        if inject_data_into_html(history, summary):
            print("Dashboard updated successfully!")
        else:
            print("Failed to update dashboard")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to inject data into HTML: {e}")
        sys.exit(1)
    
    # Check if alert is needed
    try:
        if should_alert_services(history) or (summary and summary.get("intelligence_updates", [])):
            print("ALERT: Incident or Intelligence Update detected!")
        else:
            print("Monitoring completed successfully - all services online")
    except Exception as e:
        print(f"WARNING: Failed to check alerts: {e}")
        print("Monitoring completed - check logs for details")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
