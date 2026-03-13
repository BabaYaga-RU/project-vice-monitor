import requests
import datetime
import json
import os
import sys
import socket
import time
import re
from urllib.parse import urlparse

# Configurações avançadas
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
MAX_HISTORY_RECORDS = 500  # Log rotation: manter apenas 500 registros
CLEANUP_DAYS = 90  # Remover registros com mais de 90 dias

def load_history():
    """Carrega o histórico de monitoramento"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                
            # Compatibilidade com histórico antigo
            if "services" not in history:
                history = {
                    "services": {key: [] for key in SERVICES.keys()},
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "page_size_history": []
                }
            else:
                # Garante que todas as chaves de serviços existam
                for service_key in SERVICES.keys():
                    if service_key not in history["services"]:
                        history["services"][service_key] = []
                # Garante que page_size_history exista
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
    """Salva o histórico de monitoramento"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def measure_dns_resolution(url):
    """Mede o tempo de resolução DNS"""
    try:
        hostname = urlparse(url).hostname
        start_time = time.time()
        socket.gethostbyname(hostname)
        dns_time = (time.time() - start_time) * 1000
        return round(dns_time, 2)
    except Exception:
        return 0

def measure_tcp_connection(url):
    """Mede o tempo de conexão TCP"""
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
    """Verifica se o conteúdo HTML contém palavras-chave específicas"""
    try:
        content = response.text.lower()
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in content:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords
    except Exception:
        return False, []

def analyze_security_headers(response):
    """Analisa a presença de cabeçalhos de segurança"""
    security_checks = {}
    required_headers = SERVICES["github_pages"]["security_headers"]
    
    for header in required_headers:
        security_checks[header] = header.lower() in response.headers
        
    return security_checks

def check_service(service_key, service_config):
    """Realiza monitoramento avançado com métricas detalhadas"""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        # Medidas de tempo detalhadas
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
        
        # Verificações avançadas
        status = "ONLINE" if response.status_code == 200 else f"OFFLINE ({response.status_code})"
        
        # Deep health check para websites
        content_ok = True
        found_keywords = []
        security_headers = {}
        
        if service_config["type"] == "website":
            content_ok, found_keywords = deep_health_check(
                service_config["url"], response, service_config["keywords"]
            )
            if not content_ok:
                status = "CONTENT_ERROR"
        
        # Análise de segurança
        if response.status_code == 200:
            security_headers = analyze_security_headers(response)
        
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
            "engagement": {}  # Para API GitHub
        }
        
        # Extrai dados de engajamento para API GitHub
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
    """Adiciona um registro ao histórico com log rotation"""
    history["services"][service_key].append(record)
    
    # Implementa log rotation (mantém apenas os últimos registros)
    if len(history["services"][service_key]) > MAX_HISTORY_RECORDS:
        history["services"][service_key] = history["services"][service_key][-MAX_HISTORY_RECORDS:]
    
    save_history(history)

def parse_timestamp(ts_str):
    """Parse timestamp string, handling both naive and aware datetimes"""
    dt = datetime.datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        # Se for naive, assume UTC
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt

def cleanup_old_records(history):
    """Remove registros com mais de 90 dias para manter o repositório leve"""
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=CLEANUP_DAYS)
    
    for service_key in history["services"]:
        original_count = len(history["services"][service_key])
        history["services"][service_key] = [
            record for record in history["services"][service_key]
            if parse_timestamp(record["timestamp"]) >= cutoff_date
        ]
        removed_count = original_count - len(history["services"][service_key])
        if removed_count > 0:
            print(f"Limpeza: Removidos {removed_count} registros antigos do serviço {service_key}")

def calculate_uptime_percentage(records, time_filter=None):
    """Calcula o uptime percentage para um conjunto de registros"""
    if not records:
        return 0
    
    # Filtra registros se necessário
    if time_filter:
        filtered_records = [r for r in records if parse_timestamp(r["timestamp"]) >= time_filter]
    else:
        filtered_records = records
    
    if not filtered_records:
        return 0
    
    online_records = [r for r in filtered_records if r.get("status") == "ONLINE"]
    return (len(online_records) / len(filtered_records)) * 100

def calculate_performance_metrics(records, time_filter=None):
    """Calcula métricas de performance detalhadas"""
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
    
    # Filtra registros se necessário
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
    
    # Cálculos de latência
    latencies = [r["total_time_ms"] for r in online_records]
    dns_times = [r["dns_time_ms"] for r in online_records if r.get("dns_time_ms", 0) > 0]
    tcp_times = [r["tcp_time_ms"] for r in online_records if r.get("tcp_time_ms", 0) > 0]
    transfer_times = [r["transfer_time_ms"] for r in online_records if r.get("transfer_time_ms", 0) > 0]
    
    # Horário de pico (maior latência)
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
    """Obtém os filtros de tempo para cálculos estatísticos"""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Últimas 24 horas
    last_24h = now - datetime.timedelta(hours=24)
    
    # Últimos 7 dias
    last_7d = now - datetime.timedelta(days=7)
    
    # Últimos 30 dias
    last_30d = now - datetime.timedelta(days=30)
    
    return {
        "last_24h": last_24h,
        "last_7d": last_7d,
        "last_30d": last_30d
    }

def process_service_data(history, service_key):
    """Processa os dados de um serviço e calcula estatísticas avançadas"""
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
    
    # Obtém filtros de tempo
    time_filters = get_time_filters()
    
    # Calcula SLA para diferentes períodos
    sla_24h = calculate_uptime_percentage(records, time_filters["last_24h"])
    sla_7d = calculate_uptime_percentage(records, time_filters["last_7d"])
    sla_30d = calculate_uptime_percentage(records, time_filters["last_30d"])
    
    # Status atual (precisa ser definido antes da lógica de initial state)
    last_record = records[-1] if records else None
    current_status = last_record.get("status", "UNKNOWN") if last_record else "UNKNOWN"
    
    # Initial State Logic: Se histórico pequeno, assume 100% se teste atual OK
    if len(records) < 10:  # Menos de 10 registros
        if current_status == "ONLINE":
            sla_24h = sla_7d = sla_30d = 100.0
    
    # Calcula métricas de performance
    performance = calculate_performance_metrics(records, time_filters["last_24h"])
    
    # Status atual (já definido acima)
    last_check = last_record["timestamp"]
    
    # Engajamento (para API GitHub)
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
    """Gera log de incidentes a partir do histórico"""
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
                # Início de incidente
                current_incident = {
                    "service": service_key,
                    "start_time": timestamp,
                    "end_time": None,
                    "status": status,
                    "duration": "Em andamento"
                }
            elif status == "ONLINE" and current_incident is not None:
                # Fim de incidente
                current_incident["end_time"] = timestamp
                start_dt = parse_timestamp(current_incident["start_time"])
                end_dt = parse_timestamp(current_incident["end_time"])
                duration = end_dt - start_dt
                current_incident["duration"] = str(duration).split('.')[0]  # Remove milissegundos
                incidents.append(current_incident)
                current_incident = None
        
        # Se houver incidente em andamento
        if current_incident:
            incidents.append(current_incident)
    
    # Ordena por data (mais recentes primeiro)
    incidents.sort(key=lambda x: x["start_time"], reverse=True)
    return incidents

def generate_shields_badge(history):
    """Gera badge no padrão Shields.io"""
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
    """Injeta os dados processados no index.html"""
    if not os.path.exists(INDEX_FILE):
        print(f"Erro: Arquivo {INDEX_FILE} não encontrado")
        return False
    
    # Processa dados de todos os serviços
    processed_data = {}
    for service_key in SERVICES.keys():
        processed_data[service_key] = process_service_data(history, service_key)
    
    # Gera log de incidentes
    incident_log = generate_incident_log(history)
    
    # Gera badge Shields.io
    badge_data = generate_shields_badge(history)
    
    # Prepara dados para injeção
    dashboard_data = {
        "services": processed_data,
        "incident_log": incident_log,
        "badge": badge_data,
        "history": history["services"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    # Converte para JSON
    json_data = json.dumps(dashboard_data, indent=2)
    
    # Lê o HTML
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        with open(INDEX_FILE, 'r', encoding='latin-1') as f:
            html_content = f.read()
    
    # Remove bloco de dados existente se houver
    if "<!-- INICIO_DADOS_INJECAO -->" in html_content and "<!-- FIM_DADOS_INJECAO -->" in html_content:
        start_marker = "<!-- INICIO_DADOS_INJECAO -->"
        end_marker = "<!-- FIM_DADOS_INJECAO -->"
        start_pos = html_content.find(start_marker)
        end_pos = html_content.find(end_marker) + len(end_marker)
        html_content = html_content[:start_pos] + html_content[end_pos:]
    
    # Verifica se o marcador ainda existe (para injeção inicial)
    if "<!-- INICIO_DADOS_INJECAO -->" not in html_content:
        if "</body>" in html_content:
            insertion_point = html_content.find("</body>")
            new_data_block = f"""    <!-- INICIO_DADOS_INJECAO -->
    <!-- Dados de observabilidade injetados pelo monitor.py -->
    <script>
        window.dashboardData = {json_data};
    </script>
    <!-- FIM_DADOS_INJECAO -->

</body>"""
            html_content = html_content[:insertion_point] + new_data_block + html_content[insertion_point + len("</body>"):]
        else:
            print("Erro: Marcador de injeção não encontrado no HTML")
            return False
    else:
        # Insere novos dados
        injection_point = html_content.find("<!-- INICIO_DADOS_INJECAO -->")
        new_data_block = f"""<!-- INICIO_DADOS_INJECAO -->
    <!-- Dados de observabilidade injetados pelo monitor.py -->
    <script>
        window.dashboardData = {json_data};
    </script>
    <!-- FIM_DADOS_INJECAO -->"""
        
        html_content = html_content[:injection_point] + new_data_block + html_content[injection_point:]
    
    # Salva o HTML atualizado
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return True

def check_page_size(url="https://pklavc.github.io/codepulse-monorepo/"):
    """Verifica o tamanho da página do codepulse-monorepo"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            return round(size_kb, 2)
        return 0
    except Exception:
        return 0

def should_alert_services(history):
    """Verifica se algum serviço está com problemas"""
    for service_key in SERVICES.keys():
        records = history["services"][service_key]
        if not records:
            continue
        
        last_record = records[-1]
        if last_record["status"] != "ONLINE":
            return True
    
    return False

def main():
    """Função principal de monitoramento SRE"""
    print("Iniciando monitoramento SRE avançado...")
    
    # Carrega histórico
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
    
    # Limpeza de registros antigos
    print("Realizando limpeza de registros antigos...")
    cleanup_old_records(history)
    
    # Verifica tamanho da página
    print("Verificando tamanho da página do codepulse-monorepo...")
    current_size = check_page_size()
    if current_size > 0:
        history["page_size_history"].append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "size_kb": current_size
        })
        # Mantém apenas últimos 30 registros de page size
        if len(history["page_size_history"]) > 30:
            history["page_size_history"] = history["page_size_history"][-30:]
        
        # Verifica mudança significativa
        if len(history["page_size_history"]) > 1:
            previous_size = history["page_size_history"][-2]["size_kb"]
            change_percent = abs(current_size - previous_size) / previous_size * 100
            if change_percent > 20:  # Mudança > 20%
                print(f"ALERTA: Mudança significativa no tamanho da página detectada: {previous_size}KB -> {current_size}KB ({change_percent:.1f}%)")
                # Sinaliza para commit especial
                os.environ["MONITOR_EXIT_CODE"] = "1"
    
    save_history(history)
    
    # Injeta dados no HTML
    print("Atualizando dashboard de observabilidade...")
    if inject_data_into_html(history):
        print("Dashboard atualizado com sucesso!")
    else:
        print("Falha ao atualizar dashboard")
        sys.exit(1)
    
    # Verifica necessidade de alerta
    if should_alert_services(history):
        print("ALERTA: Incidente detectado!")
        sys.exit(1)
    else:
        print("Monitoramento concluído com sucesso - todos os serviços online")
        sys.exit(0)

if __name__ == "__main__":
    main()