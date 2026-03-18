#!/usr/bin/env python3
import json

def generate_static_blog():
    # Carregar o history.json
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    # Configuração dos serviços
    services = {
        'gta_vi_official': { 'name': 'GTA VI Official', 'url': 'https://www.rockstargames.com/VI/' },
        'rockstar_newswire': { 'name': 'Rockstar Newswire', 'url': 'https://www.rockstargames.com/newswire' },
        'playstation_store': { 'name': 'PlayStation Store', 'url': 'https://www.playstation.com/en-us/games/grand-theft-auto-vi/' },
        'xbox_store': { 'name': 'Xbox Store', 'url': 'https://www.xbox.com/en-US/games/store/grand-theft-auto-vi/9NL3WWNZLZZN' }
    }

    # Extrair atualizações de inteligência
    intelligence_updates = []
    for service_key, service_config in services.items():
        records = history['services'].get(service_key, [])
        updates = [record for record in records if record.get('status') == 'INTELLIGENCE_UPDATE' or record.get('intelligence_update') == True]
        
        for record in updates:
            intelligence_updates.append({
                **record,
                'serviceKey': service_key,
                'serviceName': service_config['name'],
                'serviceUrl': service_config['url']
            })

    # Ordenar por timestamp (mais recente primeiro)
    intelligence_updates.sort(key=lambda x: x['timestamp'], reverse=True)

    # Gerar HTML estático
    blog_posts_html = ''

    if not intelligence_updates:
        blog_posts_html = '''
            <div class="empty-state">
                <h3>No Intelligence Updates Found</h3>
                <p>Currently no content changes have been detected. Monitoring is active and will log updates as they occur.</p>
            </div>
        '''
    else:
        for update in intelligence_updates:
            timestamp = update['timestamp']
            formatted_date = timestamp.replace('T', ' ').replace('+00:00', ' UTC')
            
            # Generate filename for individual post
            # Use regex to extract date components for better compatibility
            import re
            match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', timestamp)
            if match:
                date_part = match.group(1)
                time_parts = match.group(2, 3, 4)
                date_str = f"{date_part}-{time_parts[0]}-{time_parts[1]}-{time_parts[2]}+{match.group(5)}-{match.group(6)}"
            else:
                # Fallback for simple format
                date_str = timestamp.replace('T', '-').replace(':', '-').replace('+00:00', '')
            post_filename = f"update-{date_str}.html"
            
            security_status = 'SECURE' if update.get('status') == 'INTELLIGENCE_UPDATE' else 'WARNING'
            status_class = 'status-secure' if security_status == 'SECURE' else 'status-warning'
            
            blog_posts_html += f'''
            <div class="blog-card">
                <div class="blog-meta">
                    <span class="blog-meta-item">
                        <span class="status-badge {status_class}">{security_status}</span>
                    </span>
                    <span class="blog-meta-item">
                        <span style="color: var(--accent-color)">•</span> {formatted_date}
                    </span>
                    <span class="blog-meta-item">
                        <span style="color: var(--accent-color)">•</span> {update.get('total_time_ms', 0)}ms response
                    </span>
                </div>
                
                <div class="service-tag">{update['serviceName']}</div>
                
                <h2 class="blog-title"><a href="blog/{post_filename}" style="color: inherit; text-decoration: none;">Content Change Detected - {update['serviceName']}</a></h2>
                
                <div class="blog-content">
                    <p><strong>Summary:</strong> Content change detected on {update['serviceName']}. The page content has been modified, indicating a potential update or change in the monitored service.</p>
                    
                    <p><strong>Security Analysis:</strong> The change has been flagged as <strong>{security_status}</strong> based on the monitoring system's assessment.</p>
                    
                    <p><strong>Next Steps:</strong> Monitor this service for any additional changes or updates that may follow this intelligence update.</p>
                </div>
                
                <div class="blog-details">
                    <div class="detail-item">
                        <span class="detail-label">Detection Time</span>
                        <span class="detail-value">{formatted_date}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Service Type</span>
                        <span class="detail-value">Website</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Content Size</span>
                        <span class="detail-value">{update.get('html_size_kb', 0)} KB</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Response Time</span>
                        <span class="detail-value">{update.get('total_time_ms', 0)} ms</span>
                    </div>
                </div>
                
                <div class="detail-item">
                    <span class="detail-label">Hash SHA-256</span>
                    <div class="hash-value">{update.get('content_hash', 'N/A')}</div>
                </div>
                
                <div class="blog-meta" style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                    <span class="blog-meta-item">
                        <span style="color: var(--accent-color)">URL:</span> {update['serviceUrl']}
                    </span>
                </div>
                
                <div style="margin-top: 1rem; text-align: right;">
                    <a href="blog/{post_filename}" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.9rem;">Read Full Report →</a>
                </div>
            </div>
            '''

    # Substituir o blog.html com o HTML estático
    with open('blog.html', 'r', encoding='utf-8') as f:
        blog_content = f.read()

    # Substituir a seção de blog posts
    new_blog_content = blog_content.replace(
        '<div class="blog-grid" id="blog-posts">\n            <!-- Blog entries will be loaded here -->\n        </div>',
        f'<div class="blog-grid">\n{blog_posts_html}\n        </div>'
    )

    # Remover o script de carregamento
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

    # Salvar o blog.html atualizado
    with open('blog.html', 'w', encoding='utf-8') as f:
        f.write(new_blog_content)

    # Generate individual blog post files
    if intelligence_updates:
        # Read the template
        with open('blog-post-template.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        for update in intelligence_updates:
            timestamp = update['timestamp']
            formatted_date = timestamp.replace('T', ' ').replace('+00:00', ' UTC')
            
            # Generate filename for individual post
            # Use regex to extract date components for better compatibility
            import re
            match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})\+(\d{2}):(\d{2})', timestamp)
            if match:
                date_part = match.group(1)
                time_parts = match.group(2, 3, 4)
                date_str = f"{date_part}-{time_parts[0]}-{time_parts[1]}-{time_parts[2]}+{match.group(5)}-{match.group(6)}"
            else:
                # Fallback for simple format
                date_str = timestamp.replace('T', '-').replace(':', '-').replace('+00:00', '')
            post_filename = f"blog/update-{date_str}.html"
            
            security_status = 'SECURE' if update.get('status') == 'INTELLIGENCE_UPDATE' else 'WARNING'
            status_class = 'status-secure' if security_status == 'SECURE' else 'status-warning'
            
            # Replace template variables
            post_content = template_content.replace('{serviceName}', update['serviceName'])
            post_content = post_content.replace('{timestamp}', timestamp)
            post_content = post_content.replace('{timestamp_formatted}', formatted_date)
            post_content = post_content.replace('{response_time}', str(update.get('total_time_ms', 0)))
            post_content = post_content.replace('{content_size}', str(update.get('html_size_kb', 0)))
            post_content = post_content.replace('{service_url}', update['serviceUrl'])
            post_content = post_content.replace('{post_url}', f"../{post_filename}")
            
            # Update status badge class
            if security_status == 'SECURE':
                post_content = post_content.replace('class="status-badge status-secure"', f'class="status-badge {status_class}"')
                post_content = post_content.replace('SECURE', security_status)
            else:
                post_content = post_content.replace('class="status-badge status-secure"', f'class="status-badge {status_class}"')
                post_content = post_content.replace('SECURE', security_status)
            
            # Save individual post
            with open(post_filename, 'w', encoding='utf-8') as f:
                f.write(post_content)
            
            print(f'Generated: {post_filename}')

    print(f'Blog.html atualizado com {len(intelligence_updates)} atualizações de inteligência estáticas')
    print(f'Generated {len(intelligence_updates)} individual blog post files')

if __name__ == '__main__':
    generate_static_blog()