# GTA VI Intelligence & Change Monitoring System (Real-time Tracker)

## Overview

This repository implements an advanced automated monitoring system for real-time intelligence gathering on Grand Theft Auto VI development and announcements. The system performs comprehensive monitoring of key gaming platforms and official channels to detect updates, analyze content changes, and track service availability.

Track Grand Theft Auto VI development through official channels including Rockstar Newswire, PlayStation and Xbox Store listings. Our real-time monitoring system provides comprehensive intelligence on GTA VI updates and announcements.

## Features

- Multi-platform monitoring of gaming services and official channels
- Real-time content change detection using SHA-256 hashing
- Advanced latency analysis (DNS, TCP, transfer time breakdown)
- Content health verification through keyword analysis
- Security headers compliance checking
- Historical data retention with automatic log rotation
- Automated dashboard generation with real-time metrics
- GitHub Actions automation for scheduled intelligence updates
- Incident detection and alerting system

## Repository Layout

```
gta-vi-tracker/
├── monitor.py              # Main monitoring script with intelligence analysis
├── workflow.sh             # Automated workflow execution script
├── .github/workflows/      # GitHub Actions workflows for scheduled monitoring
├── index.html              # Static dashboard with real-time intelligence data
├── assets/
│   ├── style.css           # Dashboard styling and visualization
│   └── script.js           # Dashboard interactivity and charting
├── history.json            # Historical monitoring data and intelligence logs
├── uptime-badge.json       # Status badge configuration
├── data/
│   └── status.json         # Current service status snapshot
├── blog.html               # Static blog with intelligence updates
├── blog/                   # Individual blog post files
│   ├── update-*.html       # Individual intelligence update posts
│   └── update-*.json       # Blog post metadata
├── robots.txt              # Search engine configuration
├── sitemap.xml             # Site map for search engines
└── README.md               # System documentation
```

## Monitored Services

The system actively monitors the following critical gaming platforms:

- **GTA VI Official**: Rockstar Games official GTA VI page (https://www.rockstargames.com/VI/)
- **Rockstar Newswire**: Official Rockstar Games news announcements (https://www.rockstargames.com/newswire)
- **PlayStation Store**: GTA VI listing and information (https://www.playstation.com/en-us/games/grand-theft-auto-vi/)
- **Xbox Store**: GTA VI listing and information (https://www.xbox.com/en-US/games/store/grand-theft-auto-vi/9NL3WWNZLZZN)

## Intelligence Analysis Features

### Content Monitoring
- SHA-256 hash-based change detection for silent website updates
- HTML content size analysis to track page modifications
- Keyword presence verification for content integrity
- Page title and meta description tracking for SEO monitoring

### SEO & Visibility

Our GTA VI monitoring system uses advanced cryptographic hashing (SHA-256) to detect silent changes on Rockstar Games' official website. This ensures you never miss important updates to GTA VI development announcements, trailer releases, or store listing changes. The system tracks:

- **Silent Content Changes**: Detects modifications that don't trigger traditional alerts
- **Development Timeline Tracking**: Monitors progress through official channels
- **Store Listing Updates**: Tracks PlayStation and Xbox Store changes for release information
- **News Wire Monitoring**: Real-time tracking of Rockstar Newswire announcements

This comprehensive approach makes our monitoring system one of the most reliable sources for GTA VI intelligence and change detection.

### Performance Metrics
- DNS resolution time measurement
- TCP connection establishment timing
- HTTP transfer time analysis
- Total response time calculation
- Peak usage hour identification

### Security Analysis
- HTTPS enforcement verification
- Content-Type security headers
- Content Security Policy presence
- Frame options and referrer policy compliance

### Historical Intelligence
- 90-day automatic log rotation
- SLA calculations (24h, 7d, 30d)
- Incident detection and duration tracking
- Performance trend analysis

## System Architecture

1. **Intelligence Gathering**: `monitor.py` performs comprehensive HTTP checks with detailed timing and content analysis
2. **Data Processing**: Results are processed with advanced metrics calculation and change detection
3. **Historical Storage**: Intelligence data is stored in `history.json` with automatic rotation
4. **Dashboard Generation**: Real-time metrics are embedded into `index.html` for immediate visualization
5. **Automated Updates**: GitHub Actions executes monitoring on schedule and updates repository

## Configuration

### Environment Variables

The system requires the following environment variable for GitHub API authentication:

- `GITHUB_TOKEN`: GitHub Personal Access Token for API requests

### GitHub Repository Secrets

For automated workflow execution, configure the following repository secret:

- `PAT_SHARK`: GitHub Personal Access Token with repository permissions for automated PR creation and merging

### Service Configuration

Monitored services are defined in `monitor.py` under the `SERVICES` dictionary with the following parameters:
- URL endpoints for monitoring
- Service identification and classification
- Keyword lists for content verification
- Security header requirements

## GitHub Actions Workflows

### main.yml
- **Schedule**: Hourly execution (`0 * * * *`)
- **Function**: Primary monitoring workflow with automated PR creation
- **Authentication**: Uses `PAT_SHARK` secret for repository operations

### uptime.yml
- **Schedule**: Hourly execution (`0 * * * *`)
- **Function**: Comprehensive monitoring with detailed metrics collection
- **Features**: Advanced performance analysis and security header verification

Both workflows include:
- Python environment setup
- Dependency installation
- Monitoring execution
- Change detection and commit
- Automated pull request creation and merging

## Local Execution

### Prerequisites

- Python 3.8 or later
- Git version control system
- GitHub CLI (optional, for local testing)

### Installation

```bash
pip install requests
```

### Manual Execution

```bash
# Run monitoring script
python monitor.py

# Execute automated workflow
bash workflow.sh
```

### Continuous Monitoring

For continuous operation, configure system cron:

```bash
# Edit crontab configuration
crontab -e

# Add monitoring execution every hour
0 * * * * cd /path/to/uptime-monitor && python monitor.py && bash workflow.sh
```

## Data Management

### Historical Data
- **File**: `history.json`
- **Retention**: 90 days with automatic cleanup
- **Records**: Maximum 500 entries per service
- **Content**: Complete monitoring history with detailed metrics

### Current Status
- **File**: `data/status.json`
- **Purpose**: Latest service status for dashboard rendering
- **Update**: Real-time updates during monitoring cycles

### Intelligence Metrics
- **File**: `uptime-badge.json`
- **Format**: Shields.io compatible badge data
- **Content**: Current uptime percentage and status

## Security Considerations

- All HTTP requests use secure connections (HTTPS)
- GitHub tokens are handled through environment variables
- Repository secrets provide secure credential storage
- Automated workflows use minimal required permissions
- Temporary branches prevent main branch conflicts

## Performance Optimization

- Randomized execution intervals prevent service overload
- Connection timeouts prevent hanging operations
- Efficient data structures for historical storage
- Optimized dashboard rendering for real-time updates
- Automatic cleanup prevents repository bloat

## Monitoring Output

### Status Classification
- **ONLINE**: Service responding normally with expected content
- **DEGRADED**: Service responding but with performance issues
- **CONTENT_ERROR**: Service responding but content verification failed
- **INTELLIGENCE_UPDATE**: Content changes detected requiring attention
- **OFFLINE**: Service not responding or returning errors

### Alert Conditions
- Performance degradation detection
- Content change notifications
- Service availability issues
- Security header compliance problems

## Integration Guidelines

### Dashboard Customization
The `index.html` dashboard can be customized by modifying:
- Chart configurations in `assets/script.js`
- Visual styling in `assets/style.css`
- Data presentation logic in the embedded JavaScript

### Additional Services
To monitor additional services:
1. Add service configuration to `SERVICES` dictionary in `monitor.py`
2. Define monitoring parameters and keywords
3. Update dashboard visualization if needed

### Alert Integration
The system can be extended to integrate with external alerting systems by:
1. Modifying the alert detection logic in `monitor.py`
2. Adding webhook calls for external notifications
3. Implementing custom alert routing

## Maintenance

### Regular Tasks
- Monitor GitHub Actions execution logs
- Review historical data retention
- Verify service availability and response times
- Update monitored service configurations as needed

### Troubleshooting
- Check GitHub Actions workflow logs for execution issues
- Verify PAT_SHARK secret configuration
- Monitor system resource usage during execution
- Review error logs in monitoring output

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support and Maintenance

For system support and maintenance inquiries:

Patrick Araujo | Software Engineer
- GitHub: [PkLavc](https://github.com/PkLavc)
- Repository: [uptime-monitor](https://github.com/PkLavc/uptime-monitor)

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20me-%23ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/PkLavc)

## Version History

### Current Version Features
- Enhanced intelligence monitoring for GTA VI platforms
- Advanced content change detection using cryptographic hashing
- Comprehensive performance metrics and security analysis
- Automated GitHub Actions workflows with scheduled execution
- Professional dashboard with real-time intelligence visualization
- Updated to US-based gaming platform URLs
- English language documentation
