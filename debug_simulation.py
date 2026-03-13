#!/usr/bin/env python3
"""
Script de simulação para debugar o dashboard
Este script simula a lógica do dashboard para identificar o problema
"""

import json
import os
from datetime import datetime, timedelta
import pytz

def simulate_dashboard_logic():
    """Simula a lógica do dashboard para identificar problemas"""
    
    print("Simulando logica do dashboard...")
    
    # 1. Verificar se o arquivo index.html existe
    if not os.path.exists('index.html'):
        print("❌ ERRO: index.html não encontrado")
        return False
    
    # 2. Verificar se o script.js existe
    if not os.path.exists('assets/script.js'):
        print("❌ ERRO: assets/script.js não encontrado")
        return False
    
    # 3. Verificar se o history.json existe
    if not os.path.exists('history.json'):
        print("❌ ERRO: history.json não encontrado")
        print("💡 O arquivo history.json é necessário para o dashboard funcionar")
        return False
    
    # 4. Carregar o history.json
    try:
        with open('history.json', 'r') as f:
            history_data = json.load(f)
        print("history.json carregado com sucesso")
    except Exception as e:
        print(f"ERRO ao carregar history.json: {e}")
        return False
    
    # 5. Verificar estrutura do history.json
    required_keys = ['services', 'created_at']
    for key in required_keys:
        if key not in history_data:
            print(f"❌ ERRO: history.json está faltando a chave '{key}'")
            return False
    
    # 6. Verificar serviços no history
    expected_services = ['github_pages', 'github_api']
    for service in expected_services:
        if service not in history_data['services']:
            print(f"ERRO: Servico '{service}' nao encontrado no history.json")
            return False
        print(f"Servico '{service}' encontrado no history.json")
    
    # 7. Verificar se há registros de histórico
    total_records = 0
    for service in expected_services:
        records = history_data['services'][service]
        total_records += len(records)
        print(f"{service}: {len(records)} registros")
    
    if total_records == 0:
        print("❌ ERRO: Nenhum registro de histórico encontrado")
        return False
    
    # 8. Simular a lógica de processamento do monitor.py
    print("\nSimulando processamento de dados...")
    
    def simulate_process_service_data(history, service_key):
        """Simula a função process_service_data do monitor.py"""
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
        
        # Último registro
        last_record = records[-1]
        current_status = last_record.get("status", "UNKNOWN")
        
        # Calcular SLA (simplificado)
        online_records = [r for r in records if r.get("status") == "ONLINE"]
        sla_24h = (len(online_records) / len(records)) * 100 if records else 0
        sla_7d = sla_24h  # Simplificado
        sla_30d = sla_24h  # Simplificado
        
        # Performance
        latencies = [r.get("total_time_ms", 0) for r in records if r.get("total_time_ms", 0) > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        performance = {
            "avg_latency": round(avg_latency, 2),
            "avg_dns_time": 0,
            "avg_tcp_time": 0,
            "avg_transfer_time": 0,
            "peak_hour": "00:00",
            "slowest_response": max(latencies) if latencies else 0,
            "fastest_response": min(latencies) if latencies else 0
        }
        
        return {
            "current_status": current_status,
            "sla_24h": round(sla_24h, 2),
            "sla_7d": round(sla_7d, 2),
            "sla_30d": round(sla_30d, 2),
            "performance": performance,
            "last_check": last_record.get("timestamp", ""),
            "engagement": last_record.get("engagement", {})
        }
    
    # Processar cada serviço
    processed_services = {}
    for service in expected_services:
        processed_services[service] = simulate_process_service_data(history_data, service)
        print(f"{service} processado:")
        print(f"   Status: {processed_services[service]['current_status']}")
        print(f"   SLA 24h: {processed_services[service]['sla_24h']}%")
        print(f"   Latência média: {processed_services[service]['performance']['avg_latency']}ms")
    
    # 9. Verificar a injeção de dados no HTML
    print("\nVerificando injecao de dados no HTML...")
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Verificar se há a tag script com ID dashboard-data
        if 'id="dashboard-data"' in html_content:
            print("Tag script 'dashboard-data' encontrada")
            
            # Verificar se os dados foram injetados
            if 'window.dashboardData' in html_content:
                print("Dados do dashboard injetados no HTML")
                
                # Extrair os dados injetados
                import re
                pattern = r'window\.dashboardData = (.*?);'
                match = re.search(pattern, html_content, re.DOTALL)
                
                if match:
                    try:
                        injected_data = json.loads(match.group(1))
                        print("Dados injetados válidos")
                        print(f"   Serviços injetados: {list(injected_data.get('services', {}).keys())}")
                        print(f"   Histórico injetado: {len(injected_data.get('history', {}))} serviços")
                    except json.JSONDecodeError as e:
                        print(f"ERRO: Dados injetados inválidos: {e}")
                        return False
                else:
                    print("ERRO: Não foi possível extrair os dados injetados")
                    return False
            else:
                print("ERRO: Dados do dashboard não injetados")
                return False
        else:
            print("ERRO: Tag script 'dashboard-data' não encontrada")
            return False
    
    except Exception as e:
        print(f"❌ ERRO ao ler index.html: {e}")
        return False
    
    # 10. Simular a lógica do JavaScript
    print("\nSimulando logica do JavaScript...")
    
    def simulate_js_logic():
        """Simula a lógica do script.js"""
        # Carregar os dados injetados
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        import re
        pattern = r'window\.dashboardData = (.*?);'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if not match:
            print("❌ ERRO: Não foi possível encontrar os dados no HTML")
            return False
        
        try:
            dashboard_data = json.loads(match.group(1))
        except json.JSONDecodeError:
            print("❌ ERRO: Dados JSON inválidos")
            return False
        
        # Verificar se os dados são válidos
        if not dashboard_data or 'services' not in dashboard_data:
            print("ERRO: Dados do dashboard inválidos ou incompletos")
            return False
        
        print("Dados do dashboard carregados corretamente")
        
        # Simular updateServiceCard
        for service_key in ['github-pages', 'github-api']:
            service_data = dashboard_data['services'].get(service_key.replace('-', '_'))
            if not service_data:
                print(f"ERRO: Dados do serviço {service_key} não encontrados")
                return False
            
            print(f"Serviço {service_key} tem dados válidos")
            print(f"   Status: {service_data.get('current_status', 'N/A')}")
            print(f"   SLA 24h: {service_data.get('sla_24h', 'N/A')}%")
        
        # Simular updateIncidentLog
        incident_log = dashboard_data.get('incident_log', [])
        print(f"Incident log: {len(incident_log)} incidentes")
        
        # Simular updateCharts
        history = dashboard_data.get('history', {})
        if not history:
            print("ERRO: Histórico não encontrado para os gráficos")
            return False
        
        print("Histórico disponível para gráficos")
        
        return True
    
    if not simulate_js_logic():
        return False
    
    print("\nSimulacao concluida com sucesso!")
    print("Todos os componentes estao funcionando corretamente")
    return True

def check_monitor_execution():
    """Verifica se o monitor.py foi executado recentemente"""
    print("\nVerificando execucao do monitor.py...")
    
    # Verificar se o history.json foi modificado recentemente
    if os.path.exists('history.json'):
        mod_time = datetime.fromtimestamp(os.path.getmtime('history.json'))
        now = datetime.now()
        time_diff = now - mod_time
        
        if time_diff.total_seconds() < 3600:  # Menos de 1 hora
            print(f"history.json foi modificado recentemente ({time_diff.total_seconds()/60:.1f} minutos atrás)")
        else:
            print(f"history.json está desatualizado ({time_diff.total_seconds()/3600:.1f} horas atrás)")
            print("Execute 'python monitor.py' para atualizar os dados")
    
    # Verificar se o index.html foi modificado recentemente
    if os.path.exists('index.html'):
        mod_time = datetime.fromtimestamp(os.path.getmtime('index.html'))
        now = datetime.now()
        time_diff = now - mod_time
        
        if time_diff.total_seconds() < 3600:  # Menos de 1 hora
            print(f"index.html foi modificado recentemente ({time_diff.total_seconds()/60:.1f} minutos atrás)")
        else:
            print(f"index.html está desatualizado ({time_diff.total_seconds()/3600:.1f} horas atrás)")
            print("Execute 'python monitor.py' para atualizar o dashboard")

def main():
    """Função principal"""
    print("Iniciando simulacao de debug do dashboard...")
    print("=" * 60)
    
    success = simulate_dashboard_logic()
    
    if success:
        check_monitor_execution()
        print("\nSimulacao concluida - dashboard deve estar funcionando")
    else:
        print("\nSimulacao falhou - ha problemas a serem resolvidos")
        print("\nPossiveis solucoes:")
        print("1. Execute 'python monitor.py' para gerar os dados")
        print("2. Verifique se o history.json existe e tem dados validos")
        print("3. Verifique se o index.html tem a tag script 'dashboard-data'")
    
    return success

if __name__ == "__main__":
    main()