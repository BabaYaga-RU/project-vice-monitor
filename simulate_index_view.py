#!/usr/bin/env python3
"""
Script para simular a visualização do index.html
Este script simula exatamente o que o navegador faz ao carregar a página
"""

import json
import re
import os
from datetime import datetime

def simulate_index_view():
    """Simula a visualização do index.html como um navegador"""
    
    print("Simulando visualizacao do index.html...")
    print("=" * 60)
    
    # 1. Verificar se o index.html existe
    if not os.path.exists('index.html'):
        print("❌ ERRO: index.html não encontrado")
        return False
    
    # 2. Carregar o conteúdo do index.html
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        print("index.html carregado com sucesso")
    except Exception as e:
        print(f"ERRO ao carregar index.html: {e}")
        return False
    
    # 3. Simular a injeção de dados (como o monitor.py faz)
    print("\nVerificando injecao de dados...")
    
    # Verificar se há a tag script com ID dashboard-data
    if 'id="dashboard-data"' not in html_content:
        print("ERRO: Tag script 'dashboard-data' não encontrada")
        print("Isso significa que o monitor.py não foi executado")
        return False
    
    print("Tag script 'dashboard-data' encontrada")
    
    # Verificar se os dados foram injetados
    if 'window.dashboardData' not in html_content:
        print("ERRO: Dados do dashboard não injetados")
        return False
    
    print("Dados do dashboard injetados no HTML")
    
    # 4. Extrair os dados injetados (simulando o que o navegador faz)
    try:
        pattern = r'window\.dashboardData = (.*?);'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if not match:
            print("❌ ERRO: Não foi possível extrair os dados injetados")
            return False
        
        # Simular a execução do JavaScript (como o navegador faria)
        dashboard_data_str = match.group(1)
        dashboard_data = json.loads(dashboard_data_str)
        
        print("Dados JSON extraidos com sucesso")
        
    except json.JSONDecodeError as e:
        print(f"❌ ERRO: Dados JSON inválidos: {e}")
        return False
    
    # 5. Simular a lógica do JavaScript (como o script.js faz)
    print("\nSimulando logica do JavaScript...")
    
    # Verificar se os dados são válidos
    if not dashboard_data or 'services' not in dashboard_data:
        print("ERRO: Dados do dashboard inválidos ou incompletos")
        return False
    
    print("Dados do dashboard carregados corretamente")
    
    # 6. Simular updateDashboard() - a função principal do script.js
    print("\nSimulando updateDashboard()...")
    
    # Simular updateGlobalStatus
    github_status = dashboard_data['services']['github_pages']['current_status']
    api_status = dashboard_data['services']['github_api']['current_status']
    
    if github_status == 'ONLINE' and api_status == 'ONLINE':
        global_status = "SYSTEMS OPERATIONAL"
        print(f"Status Global: {global_status}")
    else:
        global_status = "INCIDENT DETECTED"
        print(f"Status Global: {global_status}")
    
    # 7. Simular updateServiceCard para GitHub Pages
    print("\nSimulando updateServiceCard (GitHub Pages)...")
    
    github_pages = dashboard_data['services']['github_pages']
    
    # Status
    if github_pages['current_status'] == 'ONLINE':
        print("Status: ONLINE")
    else:
        print(f"Status: {github_pages['current_status']}")
    
    # SLA Metrics
    sla_24h = github_pages.get('sla_24h', 0)
    sla_7d = github_pages.get('sla_7d', 0)
    sla_30d = github_pages.get('sla_30d', 0)
    
    print(f"SLA 24h: {sla_24h}%")
    print(f"SLA 7d: {sla_7d}%")
    print(f"SLA 30d: {sla_30d}%")
    
    # Performance Metrics
    performance = github_pages.get('performance', {})
    avg_latency = performance.get('avg_latency', 0)
    avg_dns = performance.get('avg_dns_time', 0)
    avg_tcp = performance.get('avg_tcp_time', 0)
    avg_transfer = performance.get('avg_transfer_time', 0)
    
    print(f"Latencia Media: {avg_latency}ms")
    print(f"DNS Time: {avg_dns}ms")
    print(f"TCP Time: {avg_tcp}ms")
    print(f"Transfer Time: {avg_transfer}ms")
    
    # 8. Simular updateServiceCard para GitHub API
    print("\nSimulando updateServiceCard (GitHub API)...")
    
    github_api = dashboard_data['services']['github_api']
    
    # Status
    if github_api['current_status'] == 'ONLINE':
        print("Status: ONLINE")
    else:
        print(f"Status: {github_api['current_status']}")
    
    # SLA Metrics
    sla_24h_api = github_api.get('sla_24h', 0)
    sla_7d_api = github_api.get('sla_7d', 0)
    sla_30d_api = github_api.get('sla_30d', 0)
    
    print(f"SLA 24h: {sla_24h_api}%")
    print(f"SLA 7d: {sla_7d_api}%")
    print(f"SLA 30d: {sla_30d_api}%")
    
    # Performance Metrics
    performance_api = github_api.get('performance', {})
    avg_latency_api = performance_api.get('avg_latency', 0)
    
    print(f"Latencia Media: {avg_latency_api}ms")
    
    # Engagement Metrics (GitHub API only)
    engagement = github_api.get('engagement', {})
    stars = engagement.get('stars', 0)
    forks = engagement.get('forks', 0)
    issues = engagement.get('open_issues', 0)
    
    print(f"Stars: {stars}")
    print(f"Forks: {forks}")
    print(f"Issues: {issues}")
    
    # 9. Simular updateIncidentLog
    print("\nSimulando updateIncidentLog...")
    
    incident_log = dashboard_data.get('incident_log', [])
    
    if not incident_log:
        print("Nenhum incidente registrado")
    else:
        print(f"{len(incident_log)} incidentes registrados:")
        for i, incident in enumerate(incident_log, 1):
            service = incident.get('service', 'Desconhecido')
            status = incident.get('status', 'Desconhecido')
            start_time = incident.get('start_time', 'Desconhecido')
            end_time = incident.get('end_time', 'Em andamento')
            duration = incident.get('duration', 'Desconhecido')
            
            print(f"   {i}. {service} - {status}")
            print(f"      Início: {start_time}")
            print(f"      Fim: {end_time}")
            print(f"      Duração: {duration}")
    
    # 10. Simular updateCharts (verificar se há dados para gráficos)
    print("\nSimulando updateCharts...")
    
    history = dashboard_data.get('history', {})
    
    if not history:
        print("ERRO: Historico nao encontrado para os graficos")
        return False
    
    print("Historico disponivel para graficos")
    
    # Verificar dados de histórico
    github_pages_history = history.get('github_pages', [])
    github_api_history = history.get('github_api', [])
    
    print(f"Historico GitHub Pages: {len(github_pages_history)} registros")
    print(f"Historico GitHub API: {len(github_api_history)} registros")
    
    # 11. Simular updateLastUpdate
    print("\nSimulando updateLastUpdate...")
    
    generated_at = dashboard_data.get('generated_at', 'Desconhecido')
    print(f"Ultima atualizacao: {generated_at}")
    
    # 12. Verificar se há algum problema que causaria "tudo zerado"
    print("\nVerificando possiveis causas de 'tudo zerado'...")
    
    issues_found = []
    
    # Verificar SLA muito baixo
    if sla_24h < 50 or sla_7d < 50 or sla_30d < 50:
        issues_found.append("SLA muito baixo - pode indicar problemas de monitoramento")
    
    # Verificar latência muito alta
    if avg_latency > 5000 or avg_latency_api > 5000:
        issues_found.append("Latência muito alta - pode indicar problemas de conexão")
    
    # Verificar histórico vazio
    if len(github_pages_history) == 0 or len(github_api_history) == 0:
        issues_found.append("Histórico vazio - o monitor.py pode não estar funcionando")
    
    # Verificar dados inconsistentes
    if sla_24h == 0 and len(github_pages_history) > 0:
        issues_found.append("SLA 0% com histórico existente - possível erro de cálculo")
    
    if issues_found:
        print("Possiveis problemas identificados:")
        for issue in issues_found:
            print(f"   - {issue}")
    else:
        print("Nenhum problema obvio identificado")
    
    print("\nSimulacao da visualizacao do index.html concluida!")
    print("O dashboard esta configurado corretamente")
    
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
            print(f"history.json foi modificado recentemente ({time_diff.total_seconds()/60:.1f} minutos atras)")
        else:
            print(f"history.json esta desatualizado ({time_diff.total_seconds()/3600:.1f} horas atras)")
            print("Execute 'python monitor.py' para atualizar os dados")
    
    # Verificar se o index.html foi modificado recentemente
    if os.path.exists('index.html'):
        mod_time = datetime.fromtimestamp(os.path.getmtime('index.html'))
        now = datetime.now()
        time_diff = now - mod_time
        
        if time_diff.total_seconds() < 3600:  # Menos de 1 hora
            print(f"index.html foi modificado recentemente ({time_diff.total_seconds()/60:.1f} minutos atras)")
        else:
            print(f"index.html esta desatualizado ({time_diff.total_seconds()/3600:.1f} horas atras)")
            print("Execute 'python monitor.py' para atualizar o dashboard")

def main():
    """Função principal"""
    print("Iniciando simulacao da visualizacao do index.html...")
    print("=" * 60)
    
    success = simulate_index_view()
    
    if success:
        check_monitor_execution()
        print("\nSimulacao concluida - o index.html deve estar funcionando")
        print("\nSe ainda estiver vazio, tente:")
        print("1. Abrir o index.html no navegador")
        print("2. Pressionar F12 para abrir o console do desenvolvedor")
        print("3. Verificar se há erros no console")
        print("4. Verificar se window.dashboardData está definido")
    else:
        print("\nSimulacao falhou - há problemas com a visualização do index.html")
        print("\nPossiveis solucoes:")
        print("1. Execute 'python monitor.py' para gerar os dados")
        print("2. Verifique se o history.json existe e tem dados válidos")
        print("3. Verifique se o index.html tem a tag script 'dashboard-data'")
    
    return success

if __name__ == "__main__":
    main()