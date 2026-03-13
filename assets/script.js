// Dashboard Logic
let charts = {}; // Store chart instances

function updateDashboard() {
    const data = window.dashboardData;

    if (!data || !data.services) {
        console.log('⚠️ Dashboard data not found - please run the monitoring script first');
        console.log('💡 Tip: Execute "python monitor.py" to generate the required data');
        return;
    }

        // Update Global Status
        const globalStatus = document.getElementById('global-status');
        const githubStatus = data.services.github_pages.current_status;
        const apiStatus = data.services.github_api.current_status;
        
        if (githubStatus === 'ONLINE' && apiStatus === 'ONLINE') {
            globalStatus.textContent = 'SYSTEMS OPERATIONAL';
            globalStatus.className = 'badge online';
        } else {
            globalStatus.textContent = 'INCIDENT DETECTED';
            globalStatus.className = 'badge offline';
        }

    // Update GitHub Pages
    updateServiceCard('github-pages', data.services.github_pages);

    // Update GitHub API
    updateServiceCard('github-api', data.services.github_api);

    // Update Incident Log
    updateIncidentLog(data.incident_log);

    // Update Charts
    updateCharts(data);

    // Update Last Update
    const lastUpdate = document.getElementById('last-update');
    const lastUpdateBadge = document.getElementById('last-update-badge');
    const updateTime = new Date(data.generated_at).toLocaleString('en-US');

    lastUpdate.textContent = `Last update: ${updateTime}`;
    lastUpdateBadge.textContent = updateTime;
}

function updateServiceCard(prefix, serviceData) {
    // Status Indicator
    const statusEl = document.getElementById(`${prefix}-status`);
    const badgeEl = document.getElementById(`${prefix}-badge`);

    if (serviceData.current_status === 'ONLINE') {
        statusEl.className = 'status-indicator';
        badgeEl.className = 'badge online';
        badgeEl.textContent = 'ONLINE';
    } else if (serviceData.current_status === 'OFFLINE') {
        statusEl.className = 'status-indicator offline';
        badgeEl.className = 'badge offline';
        badgeEl.textContent = 'OFFLINE';
    } else {
        statusEl.className = 'status-indicator warning';
        badgeEl.className = 'badge warning';
        badgeEl.textContent = 'WARNING';
    }

    // SLA Metrics
    const sla24h = serviceData.sla_24h || 0;
    const sla7d = serviceData.sla_7d || 0;
    const sla30d = serviceData.sla_30d || 0;

    document.getElementById(`${prefix}-sla-24h`).textContent = sla24h === 0 && data.history ? 'Calculating...' : `${sla24h}%`;
    document.getElementById(`${prefix}-sla-7d`).textContent = sla7d === 0 && data.history ? 'Calculating...' : `${sla7d}%`;
    document.getElementById(`${prefix}-sla-30d`).textContent = sla30d === 0 && data.history ? 'Calculating...' : `${sla30d}%`;

    // Performance Metrics
    const perf = serviceData.performance;
    if (perf) {
        document.getElementById(`${prefix}-latency`).textContent = `${perf.avg_latency || 0}ms`;
        document.getElementById(`${prefix}-dns`).textContent = `${perf.avg_dns_time || 0}ms`;
        document.getElementById(`${prefix}-tcp`).textContent = `${perf.avg_tcp_time || 0}ms`;
        document.getElementById(`${prefix}-transfer`).textContent = `${perf.avg_transfer_time || 0}ms`;
        document.getElementById(`${prefix}-peak`).textContent = perf.peak_hour || '--:--';
    }

    // Engagement Metrics (API only)
    if (prefix === 'github-api' && serviceData.engagement) {
        const eng = serviceData.engagement;
        document.getElementById('api-stars').textContent = eng.stars || 0;
        document.getElementById('api-forks').textContent = eng.forks || 0;
        document.getElementById('api-issues').textContent = eng.open_issues || 0;
    }
}

function updateIncidentLog(incidents) {
    const tbody = document.getElementById('incident-table-body');
    tbody.innerHTML = '';

    if (!incidents || incidents.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-tertiary); padding: 2rem;">
                    No incidents registered
                </td>
            </tr>
        `;
        return;
    }

    incidents.forEach(incident => {
        const row = document.createElement('tr');
        row.className = 'incident-row';

        const statusClass = incident.status === 'ONLINE' ? 'status-online' :
                          incident.status === 'OFFLINE' ? 'status-offline' : 'status-warning';

        row.innerHTML = `
            <td>${incident.service}</td>
            <td><span class="status-pill ${statusClass}">${incident.status}</span></td>
            <td>${new Date(incident.start_time).toLocaleString('en-US')}</td>
            <td>${incident.end_time ? new Date(incident.end_time).toLocaleString('en-US') : 'In Progress'}</td>
            <td>${incident.duration}</td>
        `;

        tbody.appendChild(row);
    });
}

function updateCharts(data) {
    if (!data.history) return;

    // Process history data for charts
    const githubHistory = data.history.github_pages || [];
    const apiHistory = data.history.github_api || [];

    // Uptime Chart (last 24 hours)
    updateUptimeChart(githubHistory, apiHistory);

    // Latency Chart
    updateLatencyChart(githubHistory, apiHistory);

    // Page Size Chart (if available)
    if (data.page_size_history) {
        updatePageSizeChart(data.page_size_history);
    }
}

function updateUptimeChart(githubHistory, apiHistory) {
    const ctx = document.getElementById('uptime-sla-chart');
    if (!ctx) return;

    // Get last 24 hours data
    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const githubData = githubHistory.filter(h => new Date(h.timestamp) > last24h);
    const apiData = apiHistory.filter(h => new Date(h.timestamp) > last24h);

    const labels = [];
    const githubUptime = [];
    const apiUptime = [];

    // Create hourly buckets
    for (let i = 23; i >= 0; i--) {
        const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
        labels.push(hour.getHours() + ':00');

        const githubChecks = githubData.filter(h => {
            const checkHour = new Date(h.timestamp).getHours();
            return checkHour === hour.getHours();
        });
        const apiChecks = apiData.filter(h => {
            const checkHour = new Date(h.timestamp).getHours();
            return checkHour === hour.getHours();
        });

        const githubRate = githubChecks.length > 0 ? (githubChecks.filter(c => c.status === 'ONLINE').length / githubChecks.length) * 100 : 100;
        const apiRate = apiChecks.length > 0 ? (apiChecks.filter(c => c.status === 'ONLINE').length / apiChecks.length) * 100 : 100;

        githubUptime.push(githubRate);
        apiUptime.push(apiRate);
    }

    if (charts.uptime) {
        charts.uptime.destroy();
    }

    charts.uptime = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'GitHub Pages',
                data: githubUptime,
                borderColor: 'var(--success-color)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                tension: 0.4
            }, {
                label: 'GitHub API',
                data: apiUptime,
                borderColor: 'var(--accent-color)',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: 'var(--text-primary)'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: 'var(--text-secondary)',
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                },
                x: {
                    ticks: {
                        color: 'var(--text-secondary)'
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                }
            }
        }
    });
}

function updateLatencyChart(githubHistory, apiHistory) {
    const ctx = document.getElementById('latency-trend-chart');
    if (!ctx) return;

    // Get last 24 hours data
    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const githubData = githubHistory.filter(h => new Date(h.timestamp) > last24h && h.latency_ms);
    const apiData = apiHistory.filter(h => new Date(h.timestamp) > last24h && h.latency_ms);

    const labels = [];
    const githubLatency = [];
    const apiLatency = [];

    // Create hourly buckets
    for (let i = 23; i >= 0; i--) {
        const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
        labels.push(hour.getHours() + ':00');

        const githubChecks = githubData.filter(h => {
            const checkHour = new Date(h.timestamp).getHours();
            return checkHour === hour.getHours();
        });
        const apiChecks = apiData.filter(h => {
            const checkHour = new Date(h.timestamp).getHours();
            return checkHour === hour.getHours();
        });

        const githubAvg = githubChecks.length > 0 ? githubChecks.reduce((sum, c) => sum + c.latency_ms, 0) / githubChecks.length : 0;
        const apiAvg = apiChecks.length > 0 ? apiChecks.reduce((sum, c) => sum + c.latency_ms, 0) / apiChecks.length : 0;

        githubLatency.push(githubAvg);
        apiLatency.push(apiAvg);
    }

    if (charts.latency) {
        charts.latency.destroy();
    }

    charts.latency = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'GitHub Pages',
                data: githubLatency,
                borderColor: 'var(--success-color)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                tension: 0.4
            }, {
                label: 'GitHub API',
                data: apiLatency,
                borderColor: 'var(--accent-color)',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: 'var(--text-primary)'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'var(--text-secondary)',
                        callback: function(value) {
                            return value + 'ms';
                        }
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                },
                x: {
                    ticks: {
                        color: 'var(--text-secondary)'
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                }
            }
        }
    });
}

function updatePageSizeChart(pageSizeHistory) {
    const ctx = document.getElementById('page-size-chart');
    if (!ctx) return;

    const labels = pageSizeHistory.map(p => new Date(p.timestamp).toLocaleDateString('en-US'));
    const sizes = pageSizeHistory.map(p => p.size_kb);

    if (charts.pageSize) {
        charts.pageSize.destroy();
    }

    charts.pageSize = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Tamanho da Página (KB)',
                data: sizes,
                borderColor: 'var(--warning-color)',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: 'var(--text-primary)'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'var(--text-secondary)',
                        callback: function(value) {
                            return value + ' KB';
                        }
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                },
                x: {
                    ticks: {
                        color: 'var(--text-secondary)'
                    },
                    grid: {
                        color: 'var(--grid-line)'
                    }
                }
            }
        }
    });
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    updateDashboard();
    // Update every 60 seconds
    setInterval(updateDashboard, 60000);
});