import requests
import datetime
import json
import os
import sys

# Configurações
SERVICES = {
    "github_io": {
        "url": "https://pklavc.github.io/",
        "name": "GitHub Pages"
    },
    "codepulse": {
        "url": "https://pklavc.github.io/codepulse-monorepo/",
        "name": "CodePulse Monorepo"
    }
}

HISTORY_FILE = "history.json"
INDEX_FILE = "index.html"
MAX_HISTORY_RECORDS = 10000  # Histórico maior para cálculos estatísticos

def load_history():
    """Carrega o histórico de monitoramento"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    return {
        "services": {key: [] for key in SERVICES.keys()},
        "created_at": datetime.datetime.now().isoformat()
    }

def save_history(history):
    """Salva o histórico de monitoramento"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def check_service(service_key, service_config):
    """Realiza o monitoramento de um serviço"""
    try:
        start = datetime.datetime.now()
        r = requests.get(service_config["url"], timeout=10)
        latency = (datetime.datetime.now() - start).total_seconds() * 1000
        status = "ONLINE" if r.status_code == 200 else f"OFFLINE ({r.status_code})"
        
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "url": service_config["url"],
            "status": status,
            "latency_ms": round(latency, 2),
            "http_code": r.status_code
        }
        
    except Exception as e:
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "url": service_config["url"],
            "status": "ERROR",
            "latency_ms": 0,
            "error": str(e)
        }
    
    return record

def add_record_to_history(history, service_key, record):
    """Adiciona um registro ao histórico"""
    history["services"][service_key].append(record)
    
    # Implementa log rotation (mantém apenas os últimos registros)
    if len(history["services"][service_key]) > MAX_HISTORY_RECORDS:
        history["services"][service_key] = history["services"][service_key][-MAX_HISTORY_RECORDS:]
    
    save_history(history)

def calculate_uptime_percentage(records, time_filter=None):
    """Calcula o uptime percentage para um conjunto de registros"""
    if not records:
        return 0
    
    # Filtra registros se necessário
    if time_filter:
        cutoff_time = time_filter
        filtered_records = [r for r in records if datetime.datetime.fromisoformat(r["timestamp"]) >= cutoff_time]
    else:
        filtered_records = records
    
    if not filtered_records:
        return 0
    
    online_records = [r for r in filtered_records if r.get("status") == "ONLINE"]
    return (len(online_records) / len(filtered_records)) * 100

def calculate_average_latency(records, time_filter=None):
    """Calcula a latência média para um conjunto de registros"""
    if not records:
        return 0
    
    # Filtra registros se necessário
    if time_filter:
        cutoff_time = time_filter
        filtered_records = [r for r in records if datetime.datetime.fromisoformat(r["timestamp"]) >= cutoff_time]
    else:
        filtered_records = records
    
    online_records = [r for r in filtered_records if r.get("status") == "ONLINE" and r.get("latency_ms", 0) > 0]
    if not online_records:
        return 0
    
    return sum(r["latency_ms"] for r in online_records) / len(online_records)

def get_time_filters():
    """Obtém os filtros de tempo para cálculos estatísticos"""
    now = datetime.datetime.now()
    
    # Últimas 24 horas
    last_24h = now - datetime.timedelta(hours=24)
    
    # Mês atual
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Últimos meses (últimos 30 dias)
    last_month_start = now - datetime.timedelta(days=30)
    
    return {
        "last_24h": last_24h,
        "current_month": current_month_start,
        "last_month": last_month_start
    }

def process_service_data(history, service_key):
    """Processa os dados de um serviço e calcula estatísticas"""
    records = history["services"][service_key]
    
    if not records:
        return {
            "current_status": "UNKNOWN",
            "uptime_monthly": 0,
            "uptime_current_month": 0,
            "uptime_24h": 0,
            "avg_latency": 0,
            "last_check": ""
        }
    
    # Obtém filtros de tempo
    time_filters = get_time_filters()
    
    # Calcula estatísticas
    uptime_monthly = calculate_uptime_percentage(records, time_filters["last_month"])
    uptime_current_month = calculate_uptime_percentage(records, time_filters["current_month"])
    uptime_24h = calculate_uptime_percentage(records, time_filters["last_24h"])
    avg_latency = calculate_average_latency(records, time_filters["current_month"])
    
    # Status atual
    last_record = records[-1]
    current_status = last_record["status"]
    last_check = last_record["timestamp"]
    
    return {
        "current_status": current_status,
        "uptime_monthly": round(uptime_monthly, 2),
        "uptime_current_month": round(uptime_current_month, 2),
        "uptime_24h": round(uptime_24h, 2),
        "avg_latency": round(avg_latency, 2),
        "last_check": last_check
    }

def inject_data_into_html(history):
    """Injeta os dados processados no index.html"""
    if not os.path.exists(INDEX_FILE):
        print(f"Erro: Arquivo {INDEX_FILE} não encontrado")
        return False
    
    # Processa dados de todos os serviços
    processed_data = {}
    for service_key in SERVICES.keys():
        processed_data[service_key] = process_service_data(history, service_key)
    
    # Prepara dados para injeção
    dashboard_data = {
        "github_io": processed_data["github_io"],
        "codepulse": processed_data["codepulse"],
        "history": history["services"],
        "generated_at": datetime.datetime.now().isoformat()
    }
    
    # Converte para JSON
    json_data = json.dumps(dashboard_data, indent=2)
    
    # Lê o HTML
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        # Tenta com encoding diferente se falhar
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
        # Se não existir, adiciona antes do fechamento do body
        if "</body>" in html_content:
            insertion_point = html_content.find("</body>")
            new_data_block = f"""    <!-- INICIO_DADOS_INJECAO -->
    <!-- Os dados serão injetados aqui pelo Python -->
    <script>
        // INICIO_LOGICA_DASHBOARD
        // Esta seção será preenchida pelo Python com os dados processados
        
        let dashboardData = {json_data};
        // FIM_LOGICA_DASHBOARD
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
    <!-- Os dados serão injetados aqui pelo Python -->
    <script>
        // INICIO_LOGICA_DASHBOARD
        // Esta seção será preenchida pelo Python com os dados processados
        
        let dashboardData = {json_data};
        // FIM_LOGICA_DASHBOARD
    </script>
    <!-- FIM_DADOS_INJECAO -->"""
        
        html_content = html_content[:injection_point] + new_data_block + html_content[injection_point:]
    
    # Salva o HTML atualizado
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return True

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
    """Função principal de monitoramento"""
    print("Iniciando monitoramento de serviços...")
    
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
        latency_str = f"{record.get('latency_ms', 0)}ms" if record["status"] == "ONLINE" else "N/A"
        print(f"  {status_symbol} {service_config['name']}: {record['status']} - {latency_str}")
    
    # Injeta dados no HTML
    print("Atualizando dashboard...")
    if inject_data_into_html(history):
        print("Dashboard atualizado com sucesso!")
    else:
        print("Falha ao atualizar dashboard")
        sys.exit(1)
    
    # Verifica necessidade de alerta
    if should_alert_services(history):
        print("ALERTA: Interrupção de serviço detectada!")
        sys.exit(1)
    else:
        print("Monitoramento concluído com sucesso - todos os serviços online")
        sys.exit(0)

if __name__ == "__main__":
    main()