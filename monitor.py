#!/usr/bin/env python3
"""
Project Vice Monitor - HTML Edition
Real-time monitoring system that edits index.html directly instead of using JSON files
"""

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
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
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
        # Handle encoding issues more robustly
        try:
            content = response.text
        except UnicodeDecodeError:
            # Fallback to encoding-safe content extraction
            content = response.content.decode('utf-8', errors='ignore')
        
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

def generate_static_blog():
    """Generate static blog.html with embedded intelligence updates"""
    try:
        # Load history data
        with open('history.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Generate blog entries
        blog_entries = []
        
        # Process each service
        for service_key, service_config in SERVICES.items():
            records = history.get('services', {}).get(service_key, [])
            
            # Filter for intelligence updates
            intelligence_updates = [
                record for record in records 
                if record.get('status') == 'INTELLIGENCE_UPDATE' or record.get('intelligence_update') == True
            ]
            
            for update in intelligence_updates:
                # Parse timestamp with regex for compatibility
                import re
                match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', update['timestamp'])
                if match:
                    date_part = match.group(1)
                    time_parts = match.group(2, 3, 4)
                    formatted_date = f"{date_part} {time_parts[0]}:{time_parts[1]}:{time_parts[2]} UTC"
                else:
                    # Fallback for simple format
                    formatted_date = update['timestamp'].replace('T', ' ').replace('+00:00', ' UTC')
                
                security_status = 'SECURE' if update.get('status') == 'INTELLIGENCE_UPDATE' else 'WARNING'
                status_class = 'status-secure' if security_status == 'SECURE' else 'status-warning'
                
                blog_entry = {
                    'timestamp': formatted_date,
                    'service_name': service_config['name'],
                    'service_url': service_config['url'],
                    'security_status': security_status,
                    'status_class': status_class,
                    'total_time_ms': update.get('total_time_ms', 0),
                    'html_size_kb': update.get('html_size_kb', 0),
                    'content_hash': update.get('content_hash', 'N/A')
                }
                blog_entries.append(blog_entry)
        
        # Sort by timestamp (newest first)
        blog_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Generate static HTML content
        blog_posts_html = ''
        
        if not blog_entries:
            blog_posts_html = '''
                <div class="empty-state">
                    <h3>No Intelligence Updates Found</h3>
                    <p>Currently no content changes have been detected. Monitoring is active and will log updates as they occur.</p>
                </div>
            '''
        else:
            for entry in blog_entries:
                blog_posts_html += f'''
                <div class="blog-card">
                    <div class="blog-meta">
                        <span class="blog-meta-item">
                            <span class="status-badge {entry['status_class']}">{entry['security_status']}</span>
                        </span>
                        <span class="blog-meta-item">
                            <span style="color: var(--accent-color)">•</span> {entry['timestamp']}
                        </span>
                        <span class="blog-meta-item">
                            <span style="color: var(--accent-color)">•</span> {entry['total_time_ms']}ms response
                        </span>
                    </div>
                    
                    <div class="service-tag">{entry['service_name']}</div>
                    
                    <h2 class="blog-title">Content Change Detected - {entry['service_name']}</h2>
                    
                    <div class="blog-content">
                        <p><strong>Summary:</strong> Content change detected on {entry['service_name']}. The page content has been modified, indicating a potential update or change in the monitored service.</p>
                        
                        <p><strong>Security Analysis:</strong> The change has been flagged as <strong>{entry['security_status']}</strong> based on the monitoring system's assessment.</p>
                        
                        <p><strong>Next Steps:</strong> Monitor this service for any additional changes or updates that may follow this intelligence update.</p>
                    </div>
                    
                    <div class="blog-details">
                        <div class="detail-item">
                            <span class="detail-label">Detection Time</span>
                            <span class="detail-value">{entry['timestamp']}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Service Type</span>
                            <span class="detail-value">Website</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Content Size</span>
                            <span class="detail-value">{entry['html_size_kb']} KB</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Response Time</span>
                            <span class="detail-value">{entry['total_time_ms']} ms</span>
                        </div>
                    </div>
                    
                    <div class="detail-item">
                        <span class="detail-label">Hash SHA-256</span>
                        <div class="hash-value">{entry['content_hash']}</div>
                    </div>
                    
                    <div class="blog-meta" style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                        <span class="blog-meta-item">
                            <span style="color: var(--accent-color)">URL:</span> {entry['service_url']}
                        </span>
                    </div>
                </div>
                '''
        
        # Read current blog.html template
        with open('blog.html', 'r', encoding='utf-8') as f:
            blog_content = f.read()
        
        # Replace the blog posts section
        new_blog_content = blog_content.replace(
            '<div class="blog-grid" id="blog-posts">\n            <!-- Blog entries will be loaded here -->\n        </div>',
            f'<div class="blog-grid">\n{blog_posts_html}\n        </div>'
        )
        
        # Remove the JavaScript loading script
        new_blog_content = new_blog_content.replace(
            '''<script>
        // Load and display intelligence updates from history.json
        async function loadIntelligenceUpdates() {
            try {
                let history;
                
                // Try multiple approaches to load the data
                try {
                    // Approach 1: Direct fetch
                    const response = await fetch('history.json');
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    history = await response.json();
                } catch (fetchError) {
                    console.warn('Fetch failed, trying alternative approach:', fetchError);
                    
                    // Approach 2: Try with cache busting
                    const response = await fetch('history.json?' + Date.now());
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    history = await response.json();
                }
                const blogPostsContainer = document.getElementById('blog-posts');
                const intelligenceUpdates = [];
                
                // Extract intelligence updates from all services
                for (const [serviceKey, serviceConfig] of Object.entries({
                    'gta_vi_official': { name: 'GTA VI Official', url: 'https://www.rockstargames.com/VI/' },
                    'rockstar_newswire': { name: 'Rockstar Newswire', url: 'https://www.rockstargames.com/newswire' },
                    'playstation_store': { name: 'PlayStation Store', url: 'https://www.playstation.com/en-us/games/grand-theft-auto-vi/' },
                    'xbox_store': { name: 'Xbox Store', url: 'https://www.xbox.com/en-US/games/store/grand-theft-auto-vi/9NL3WWNZLZZN' }
                })) {
                    const records = history.services[serviceKey] || [];
                    
                    // Filter for intelligence updates
                    const updates = records.filter(record => 
                        record.status === 'INTELLIGENCE_UPDATE' || 
                        record.intelligence_update === true
                    );
                    
                    updates.forEach(record => {
                        intelligenceUpdates.push({
                            ...record,
                            serviceKey,
                            serviceName: serviceConfig.name,
                            serviceUrl: serviceConfig.url
                        });
                    });
                }
                
                // Sort by timestamp (newest first)
                intelligenceUpdates.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                
                // Clear loading message
                blogPostsContainer.innerHTML = '';
                
                if (intelligenceUpdates.length === 0) {
                    blogPostsContainer.innerHTML = `
                        <div class="empty-state">
                            <h3>No Intelligence Updates Found</h3>
                            <p>Currently no content changes have been detected. Monitoring is active and will log updates as they occur.</p>
                        </div>
                    `;
                    return;
                }
                
                        // Generate blog posts
                intelligenceUpdates.forEach(update => {
                    const timestamp = new Date(update.timestamp);
                    const formattedDate = timestamp.toLocaleString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        timeZoneName: 'short'
                    });
                    
                    const securityStatus = update.status === 'INTELLIGENCE_UPDATE' ? 'SECURE' : 'WARNING';
                    const statusClass = securityStatus === 'SECURE' ? 'status-secure' : 'status-warning';
                    
                    const blogPost = document.createElement('div');
                    blogPost.className = 'blog-card';
                    blogPost.innerHTML = `
                        <div class="blog-meta">
                            <span class="blog-meta-item">
                                <span class="status-badge ${statusClass}">${securityStatus}</span>
                            </span>
                            <span class="blog-meta-item">
                                <span style="color: var(--accent-color)">•</span> ${formattedDate}
                            </span>
                            <span class="blog-meta-item">
                                <span style="color: var(--accent-color)">•</span> ${update.total_time_ms || 0}ms response
                            </span>
                        </div>
                        
                        <div class="service-tag">${update.serviceName}</div>
                        
                        <h2 class="blog-title">Content Change Detected - ${update.serviceName}</h2>
                        
                        <div class="blog-content">
                            <p><strong>Summary:</strong> Content change detected on ${update.serviceName}. The page content has been modified, indicating a potential update or change in the monitored service.</p>
                            
                            <p><strong>Security Analysis:</strong> The change has been flagged as <strong>${securityStatus}</strong> based on the monitoring system's assessment.</p>
                            
                            <p><strong>Next Steps:</strong> Monitor this service for any additional changes or updates that may follow this intelligence update.</p>
                        </div>
                        
                        <div class="blog-details">
                            <div class="detail-item">
                                <span class="detail-label">Detection Time</span>
                                <span class="detail-value">${formattedDate}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Service Type</span>
                                <span class="detail-value">Website</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Content Size</span>
                                <span class="detail-value">${update.html_size_kb || 0} KB</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Response Time</span>
                                <span class="detail-value">${update.total_time_ms || 0} ms</span>
                            </div>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Hash SHA-256</span>
                            <div class="hash-value">${update.content_hash || 'N/A'}</div>
                        </div>
                        
                        <div class="blog-meta" style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                            <span class="blog-meta-item">
                                <span style="color: var(--accent-color)">URL:</span> ${update.serviceUrl}
                            </span>
                        </div>
                    `;
                    
                    blogPostsContainer.appendChild(blogPost);
                });
                
            } catch (error) {
                console.error('Error loading intelligence updates:', error);
                document.getElementById('blog-posts').innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Updates</h3>
                        <p>Failed to load intelligence updates. Please check if history.json exists and is accessible.</p>
                        <p style="font-size: 0.9rem; color: var(--warning-color); margin-top: 1rem;">Error: ${error.message}</p>
                    </div>
                `;
            }
        }

        // Initialize blog
        document.addEventListener('DOMContentLoaded', () => {
            loadIntelligenceUpdates();
            
            // Refresh every 5 minutes
            setInterval(loadIntelligenceUpdates, 5 * 60 * 1000);
        });
    </script>''',
            ''
        )
        
        # Write updated blog.html
        with open('blog.html', 'w', encoding='utf-8') as f:
            f.write(new_blog_content)
            
        print(f"Static blog.html generated with {len(blog_entries)} intelligence updates")
        
    except Exception as e:
        print(f"Error generating static blog: {e}")

def generate_blog_entry(record, service_config):
    """Generate a blog entry for INTELLIGENCE_UPDATE"""
    try:
        # Create blog directory if it doesn't exist
        blog_dir = "blog"
        if not os.path.exists(blog_dir):
            os.makedirs(blog_dir)
        
        # Generate filename with timestamp
        # Parse timestamp with regex for compatibility
        import re
        match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', record["timestamp"])
        if match:
            date_part = match.group(1)
            time_parts = match.group(2, 3, 4)
            filename = f"update-{date_part}-{time_parts[0]}-{time_parts[1]}-{time_parts[2]}.html"
        else:
            # Fallback for simple format
            filename = f"update-{record['timestamp'].replace('T', '-').replace(':', '-').replace('+00:00', '')}.html"
        filepath = os.path.join(blog_dir, filename)
        
        # Parse timestamp for blog generation
        # Parse timestamp with regex for compatibility
        import re
        match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', record["timestamp"])
        if match:
            date_part = match.group(1)
            time_parts = match.group(2, 3, 4)
            timestamp_str = f"{date_part} {time_parts[0]}:{time_parts[1]}:{time_parts[2]} UTC"
            timestamp_formatted = f"{date_part} {time_parts[0]}:{time_parts[1]} UTC"
        else:
            # Fallback for simple format
            timestamp_str = record["timestamp"].replace('T', ' ').replace('+00:00', ' UTC')
            timestamp_formatted = timestamp_str
        
        # Determine security status
        security_status = "SECURE" if record.get("status") == "INTELLIGENCE_UPDATE" else "WARNING"
        
        # Generate blog content
        blog_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intelligence Update - {service_config['name']}</title>
    <link rel="stylesheet" href="../assets/style.css">
    <style>
        .blog-post {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .post-header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 2rem;
            margin-bottom: 2rem;
        }}
        
        .post-meta {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            color: var(--text-tertiary);
            font-size: 0.9rem;
        }}
        
        .post-title {{
            color: var(--text-primary);
            margin-bottom: 1rem;
        }}
        
        .status-badge {{
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .status-secure {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        
        .status-warning {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }}
        
        .post-content {{
            line-height: 1.6;
            color: var(--text-secondary);
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}
        
        .metric-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            border-radius: 8px;
        }}
        
        .metric-label {{
            color: var(--text-tertiary);
            font-size: 0.8rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value {{
            color: var(--text-primary);
            font-size: 1.2rem;
            font-weight: bold;
        }}
        
        .back-link {{
            margin-top: 2rem;
            display: inline-block;
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            text-decoration: none;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        
        .back-link:hover {{
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-content">
                <div class="logo">
                    <span class="logo-icon">🔍</span>
                    <span class="logo-text">Project Vice Monitor</span>
                </div>
                <nav class="nav">
                    <a href="../index.html" class="nav-link">Dashboard</a>
                    <a href="../blog.html" class="nav-link active">Intelligence Blog</a>
                </nav>
            </div>
        </header>

        <main class="main">
            <div class="blog-post">
                <div class="post-header">
                    <div class="post-meta">
                        <span class="status-badge status-secure">SECURE</span>
                        <span>📅 {timestamp_str}</span>
                        <span>🌐 {service_config['name']}</span>
                    </div>
                    <h1 class="post-title">Intelligence Update - {timestamp_formatted}</h1>
                    <p class="post-subtitle">Content change detected on {service_config['name']}</p>
                </div>

                <div class="post-content">
                    <h2>Summary</h2>
                    <p>Content change detected on {service_config['name']}. The page content has been modified, indicating a potential update or change in the monitored service.</p>

                    <h2>Details</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Detection Time</div>
                            <div class="metric-value">{timestamp_str}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Service Type</div>
                            <div class="metric-value">Website</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Content Size</div>
                            <div class="metric-value">{record.get('html_size_kb', 0)} KB</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Response Time</div>
                            <div class="metric-value">{record.get('total_time_ms', 0)} ms</div>
                        </div>
                    </div>

                    <h3>Keywords Monitored</h3>
                    <p>{', '.join(service_config['keywords'])}</p>

                    <h2>Security Analysis</h2>
                    <p>The change has been flagged as <strong>{security_status}</strong> based on the monitoring system's assessment.</p>

                    <h2>Next Steps</h2>
                    <p>Monitor this service for any additional changes or updates that may follow this intelligence update.</p>

                    <div style="margin-top: 2rem; padding: 1rem; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px;">
                        <strong>Note:</strong> This entry was automatically generated by the Project Vice Monitor system.
                    </div>
                </div>

                <div style="margin-top: 3rem; display: flex; gap: 1rem;">
                    <a href="../blog.html" class="back-link">← Back to Blog</a>
                    <a href="{service_config['url']}" class="back-link" target="_blank">Visit Service →</a>
                </div>
            </div>
        </main>

        <footer class="footer">
            <div class="footer-content">
                <p>&copy; 2026 Project Vice Monitor. Real-time intelligence monitoring system.</p>
            </div>
        </footer>
    </div>
</body>
</html>"""
        
        # Salva arquivo HTML
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        
        # Create JSON with event date
        json_data = {
            "date": timestamp_str,
            "service": service_config['name'],
            "url": service_config['url'],
            "status": security_status,
            "content_size_kb": record.get('html_size_kb', 0),
            "response_time_ms": record.get('total_time_ms', 0)
        }
        
        json_filepath = filepath.replace('.html', '.json')
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Blog entry created: {filepath}")
        print(f"[INFO] JSON data saved: {json_filepath}")
        
        # Update blog.html to include the new entry at the top
        update_blog_html(record, service_config, timestamp, filename)
        
        return filepath
        
    except Exception as e:
        print(f"[ERROR] Failed to create blog entry: {e}")
        return None

def update_blog_html(record, service_config, timestamp, filename):
    """Update blog.html to include the new entry at the top of the list"""
    try:
        # Parse timestamp for blog update
        # Parse timestamp with regex for compatibility
        import re
        match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', record["timestamp"])
        if match:
            date_part = match.group(1)
            time_parts = match.group(2, 3, 4)
            timestamp_str = f"{date_part} {time_parts[0]}:{time_parts[1]}:{time_parts[2]} UTC"
            timestamp_formatted = f"{date_part} {time_parts[0]}:{time_parts[1]} UTC"
        else:
            # Fallback for simple format
            timestamp_str = record["timestamp"].replace('T', ' ').replace('+00:00', ' UTC')
            timestamp_formatted = timestamp_str
        
        # Read current blog.html
        with open('blog.html', 'r', encoding='utf-8') as f:
            blog_content = f.read()
        
        # Create new blog entry HTML
        new_entry = f'''
                    <div class="blog-card">
                        <div class="blog-meta">
                            <span class="status-pill status-secure">SECURE</span>
                            <span>📅 {timestamp_str}</span>
                            <span>🌐 {service_config['name']}</span>
                        </div>
                        <h3 class="blog-title">Intelligence Update - {timestamp_formatted}</h3>
                        <p class="blog-excerpt">
                            Content change detected on {service_config['name']}. 
                            Response time: {record.get('total_time_ms', 0)}ms, 
                            Content size: {record.get('html_size_kb', 0)} KB
                        </p>
                        <div class="blog-actions">
                            <a href="blog/{filename}" class="btn">Read Full Report</a>
                            <a href="{service_config['url']}" class="btn" target="_blank">Visit Service</a>
                        </div>
                    </div>'''
        
        # Find the position to insert the new entry (after the opening blog-list div)
        insert_marker = '                <div class="blog-list">'
        insert_pos = blog_content.find(insert_marker)
        
        if insert_pos != -1:
            # Find the end of the opening div tag
            insert_pos = blog_content.find('>', insert_pos) + 1
            
            # Insert the new entry at the beginning of the list
            updated_content = blog_content[:insert_pos] + new_entry + blog_content[insert_pos:]
            
            # Save the updated blog.html
            with open('blog.html', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"[INFO] Blog.html updated with new entry: {filename}")
        else:
            print("[WARN] Could not find blog-list marker in blog.html")
            
    except Exception as e:
        print(f"[ERROR] Failed to update blog.html: {e}")

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
                    
                    # Generate static blog entry for intelligence update
                    try:
                        generate_static_blog()
                    except Exception as e:
                        print(f"[WARN] Failed to generate static blog: {e}")

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
            "engagement": {},
            "html_size_kb": 0,
            "num_images": 0,
            "num_links": 0,
            "num_scripts": 0,
            "page_title": "--",
            "meta_description": "--"
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
    
    # Extract website metrics from last record
    website_metrics = {
        "html_size_kb": last_record.get("html_size_kb", 0) if last_record else 0,
        "num_images": last_record.get("num_images", 0) if last_record else 0,
        "num_links": last_record.get("num_links", 0) if last_record else 0,
        "num_scripts": last_record.get("num_scripts", 0) if last_record else 0,
        "page_title": last_record.get("page_title", "--") if last_record else "--",
        "meta_description": last_record.get("meta_description", "--") if last_record else "--"
    }
    
    return {
        "current_status": current_status,
        "sla_24h": round(sla_24h, 2),
        "sla_7d": round(sla_7d, 2),
        "sla_30d": round(sla_30d, 2),
        "performance": performance,
        "last_check": last_check,
        "engagement": engagement,
        **website_metrics
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

def update_html_dashboard(data):
    """Atualiza o index.html com os dados do monitoramento"""
    try:
        # Lê o template HTML
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Atualiza dados globais
        html_content = update_html_global_data(html_content, data)
        
        # Atualiza dados de serviços
        html_content = update_html_service_data(html_content, data)
        
        # Atualiza gráficos
        html_content = update_html_charts(html_content, data)
        
        # Atualiza logs de incidentes
        html_content = update_html_incidents(html_content, data)
        
        # Atualiza resumo
        html_content = update_html_summary(html_content, data)
        
        # Salva o HTML atualizado
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print("index.html atualizado com os dados do monitoramento")
        
    except Exception as e:
        print(f"✗ Erro ao atualizar HTML: {e}")

def update_html_global_data(html_content, data):
    """Atualiza dados globais no HTML"""
    # Status global
    gta6_status = data['services']['gta_vi_official']['current_status']
    news_status = data['services']['rockstar_newswire']['current_status']
    ps_status = data['services']['playstation_store']['current_status']
    xbox_status = data['services']['xbox_store']['current_status']
    
    all_statuses = [gta6_status, news_status, ps_status, xbox_status]
    
    if all(s == 'ONLINE' for s in all_statuses):
        global_status = 'SYSTEM MONITORED'
        status_class = 'online'
    elif any(s == 'INTELLIGENCE_UPDATE' for s in all_statuses):
        global_status = 'UPDATE DETECTED'
        status_class = 'warning'
    else:
        global_status = 'INCIDENT DETECTED'
        status_class = 'offline'
    
    # Atualiza o status global
    html_content = html_content.replace(
        'id="global-status">LOADING...',
        f'id="global-status" class="badge {status_class}">{global_status}'
    )
    
    # Atualiza data de última atualização
    update_time = datetime.datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
    html_content = html_content.replace(
        'id="last-update-badge">Carregando...',
        f'id="last-update-badge">{update_time}'
    )
    
    return html_content

def update_html_service_data(html_content, data):
    """Atualiza dados de serviços no HTML"""
    services = {
        'gta-vi-official': data['services']['gta_vi_official'],
        'rockstar-newswire': data['services']['rockstar_newswire'],
        'playstation-store': data['services']['playstation_store'],
        'xbox-store': data['services']['xbox_store']
    }
    
    for service_id, service_data in services.items():
        # Atualiza status
        status_class = 'online' if service_data['current_status'] == 'ONLINE' else 'warning' if service_data['current_status'] == 'INTELLIGENCE_UPDATE' else 'offline'
        status_text = service_data['current_status']
        
        html_content = html_content.replace(
            f'id="{service_id}-status"></div>',
            f'id="{service_id}-status" class="status-indicator {status_class}"></div>'
        )
        
        html_content = html_content.replace(
            f'id="{service_id}-badge">ONLINE',
            f'id="{service_id}-badge" class="badge {status_class}">{status_text}'
        )
        
        # Atualiza SLA
        sla_24h = service_data.get('sla_24h', 0)
        sla_7d = service_data.get('sla_7d', 0)
        sla_30d = service_data.get('sla_30d', 0)
        
        html_content = html_content.replace(
            f'id="{service_id}-sla-24h">--',
            f'id="{service_id}-sla-24h">{sla_24h}%'
        )
        html_content = html_content.replace(
            f'id="{service_id}-sla-7d">--',
            f'id="{service_id}-sla-7d">{sla_7d}%'
        )
        html_content = html_content.replace(
            f'id="{service_id}-sla-30d">--',
            f'id="{service_id}-sla-30d">{sla_30d}%'
        )
        
        # Atualiza latência
        avg_latency = service_data.get('performance', {}).get('avg_latency', 0)
        html_content = html_content.replace(
            f'id="{service_id}-latency">--',
            f'id="{service_id}-latency">{int(avg_latency)}ms'
        )
        
        # Atualiza tempos de resposta
        perf = service_data.get('performance', {})
        dns_time = perf.get('avg_dns_time', 0)
        tcp_time = perf.get('avg_tcp_time', 0)
        transfer_time = perf.get('avg_transfer_time', 0)
        
        html_content = html_content.replace(
            f'id="{service_id}-dns">--',
            f'id="{service_id}-dns">{int(dns_time)}ms'
        )
        html_content = html_content.replace(
            f'id="{service_id}-tcp">--',
            f'id="{service_id}-tcp">{int(tcp_time)}ms'
        )
        html_content = html_content.replace(
            f'id="{service_id}-transfer">--',
            f'id="{service_id}-transfer">{int(transfer_time)}ms'
        )
        
        # Atualiza hora de pico
        peak_hour = perf.get('peak_hour', '--')
        html_content = html_content.replace(
            f'id="{service_id}-peak">--',
            f'id="{service_id}-peak">{peak_hour}'
        )
        
        # Atualiza métricas de página (para serviços específicos)
        if service_id == 'gta-vi-official':
            html_content = html_content.replace(
                'id="gta-vi-official-html-size">--',
                f'id="gta-vi-official-html-size">{service_data.get("html_size_kb", 0) if service_data else 0} KB'
            )
            html_content = html_content.replace(
                'id="gta-vi-official-images">--',
                f'id="gta-vi-official-images">{service_data.get("num_images", 0) if service_data else 0}'
            )
            html_content = html_content.replace(
                'id="gta-vi-official-links">--',
                f'id="gta-vi-official-links">{service_data.get("num_links", 0) if service_data else 0}'
            )
            html_content = html_content.replace(
                'id="gta-vi-official-scripts">--',
                f'id="gta-vi-official-scripts">{service_data.get("num_scripts", 0) if service_data else 0}'
            )
            html_content = html_content.replace(
                'id="gta-vi-official-title">--',
                f'id="gta-vi-official-title">{service_data.get("page_title", "--") if service_data else "--"}'
            )
            html_content = html_content.replace(
                'id="gta-vi-official-description">--',
                f'id="gta-vi-official-description">{service_data.get("meta_description", "--") if service_data else "--"}'
            )
    
    return html_content

def update_html_charts(html_content, data):
    """Atualiza dados dos gráficos no HTML"""
    # Para gráficos temporais, precisamos manter histórico
    # Vamos criar um arquivo de histórico para os gráficos
    chart_history = load_chart_history()
    
    # Adiciona dados atuais ao histórico
    current_time = datetime.datetime.now().strftime('%H:%M')
    
    # Latência histórica
    gta6_latency = data['services']['gta_vi_official']['performance']['avg_latency']
    news_latency = data['services']['rockstar_newswire']['performance']['avg_latency']
    ps_latency = data['services']['playstation_store']['performance']['avg_latency']
    xbox_latency = data['services']['xbox_store']['performance']['avg_latency']
    
    chart_history['latency_labels'].append(current_time)
    chart_history['gta6_latency'].append(gta6_latency)
    chart_history['news_latency'].append(news_latency)
    chart_history['ps_latency'].append(ps_latency)
    chart_history['xbox_latency'].append(xbox_latency)
    
    # Mantém apenas últimas 24 horas
    if len(chart_history['latency_labels']) > 24:
        chart_history['latency_labels'] = chart_history['latency_labels'][-24:]
        chart_history['gta6_latency'] = chart_history['gta6_latency'][-24:]
        chart_history['news_latency'] = chart_history['news_latency'][-24:]
        chart_history['ps_latency'] = chart_history['ps_latency'][-24:]
        chart_history['xbox_latency'] = chart_history['xbox_latency'][-24:]
    
    # Salva histórico
    save_chart_history(chart_history)
    
    # Atualiza dados no HTML (substitui placeholders)
    html_content = html_content.replace(
        'labels: []',
        f'labels: {chart_history["latency_labels"]}'
    )
    html_content = html_content.replace(
        'data: []',
        f'data: {chart_history["gta6_latency"]}'
    )
    
    return html_content

def update_html_incidents(html_content, data):
    """Atualiza logs de incidentes no HTML"""
    # Filtra incidentes de erro
    incidents = []
    for service_name, history in data['history'].items():
        service_incidents = [item for item in history if item['status'] == 'ERROR']
        for incident in service_incidents:
            incidents.append({
                'service': service_name.replace('_', ' ').title(),
                'timestamp': incident['timestamp'],
                'error': incident.get('error', 'Unknown error')
            })
    
    # Ordena por data
    incidents.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Gera HTML da tabela
    if incidents:
        incident_rows = ''
        for incident in incidents[:10]:  # Mostra últimos 10 incidentes
            incident_rows += f'''
            <tr>
                <td>{incident['service']}</td>
                <td><span class="status-pill status-offline">ERROR</span></td>
                <td>{incident['timestamp']}</td>
                <td>Resolved</td>
                <td>{incident['error'][:50]}...</td>
            </tr>
            '''
    else:
        incident_rows = '''
        <tr>
            <td colspan="5" style="text-align: center; color: var(--text-tertiary); padding: 2rem;">
                No incidents recorded
            </td>
        </tr>
        '''
    
    # Substitui a tabela de incidentes
    start_marker = '<tbody id="incident-table-body">'
    end_marker = '</tbody>'
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        new_content = html_content[:start_idx + len(start_marker)] + incident_rows + html_content[end_idx:]
        html_content = new_content
    
    return html_content

def update_html_summary(html_content, data):
    """Atualiza resumo no HTML"""
    summary = data.get('summary', {})
    
    # Duração da execução
    run_duration = summary.get('run_duration_seconds', 0)
    minutes = int(run_duration // 60)
    seconds = int(run_duration % 60)
    duration_text = f"{minutes}m {seconds}s"
    
    html_content = html_content.replace(
        'id="run-duration">--',
        f'id="run-duration">{duration_text}'
    )
    
    # Tamanho da página (último valor)
    page_size = summary.get('page_size', {}).get('current_kb', 0)
    html_content = html_content.replace(
        'id="page-size">--',
        f'id="page-size">{page_size} KB'
    )
    
    # Variação de tamanho
    size_change = summary.get('page_size', {}).get('percent_change', 0)
    html_content = html_content.replace(
        'id="page-size-change">--',
        f'id="page-size-change">{size_change:.1f}%'
    )
    
    # Incidentes nas últimas 24h
    incidents_24h = summary.get('incidents_last_24h', {})
    total_incidents = sum(incidents_24h.values())
    html_content = html_content.replace(
        'id="incidents-24h">--',
        f'id="incidents-24h">{total_incidents}'
    )
    
    return html_content

def load_chart_history():
    """Carrega histórico de gráficos"""
    try:
        with open('data/chart_history.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'latency_labels': [],
            'gta6_latency': [],
            'news_latency': [],
            'ps_latency': [],
            'xbox_latency': []
        }

def save_chart_history(history):
    """Salva histórico de gráficos"""
    try:
        with open('data/chart_history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar histórico de gráficos: {e}")

def save_dashboard_data(data):
    """Salva dados do dashboard (mantido para compatibilidade)"""
    try:
        # Salva dados completos
        with open('data/dataset.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Salva apenas dados resumidos para o badge
        badge_data = {
            "schemaVersion": 1,
            "label": "Uptime",
            "message": f"{data['services']['gta_vi_official']['sla_24h']:.1f}%",
            "color": "brightgreen" if data['services']['gta_vi_official']['sla_24h'] > 95 else "yellow" if data['services']['gta_vi_official']['sla_24h'] > 80 else "red"
        }
        
        with open('uptime-badge.json', 'w', encoding='utf-8') as f:
            json.dump(badge_data, f, indent=2, ensure_ascii=False)
            
        print("Dados salvos em data/dataset.json e uptime-badge.json")
        
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")

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
    # Configure UTF-8 encoding for console output
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
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
            summary["avg_latency_last_24h"][service_key] = int(perf.get("avg_latency", 0)) if perf and perf.get("avg_latency") is not None else 0
        except Exception as e:
            print(f"WARNING: Failed to process data for {service_key}: {e}")
            summary["incidents_last_24h"][service_key] = 0
            summary["avg_latency_last_24h"][service_key] = 0

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
        "summary": summary
    }
    
    # Atualiza o HTML diretamente
    print("Updating HTML dashboard...")
    try:
        update_html_dashboard(dashboard_data)
        print("HTML dashboard updated successfully!")
    except Exception as e:
        print(f"ERROR: Failed to update HTML dashboard: {e}")
        sys.exit(1)
    
    # Salva dados para compatibilidade
    print("Saving data files for compatibility...")
    try:
        save_dashboard_data(dashboard_data)
    except Exception as e:
        print(f"WARNING: Failed to save data files: {e}")
    
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