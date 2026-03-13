# SRE Dashboard - Uptime Monitor System

## Overview

This repository implements an automated uptime monitoring system that:

- periodically checks one or more HTTP endpoints
- tracks uptime, latency, and performance metrics
- stores historical data in JSON
- updates a static dashboard (`index.html`) with the latest metrics
- creates and merges pull requests to keep the dashboard in sync via GitHub Actions

## Features

- Multi-service monitoring (example: GitHub Pages + GitHub API)
- Latency breakdown (DNS, TCP, transfer)
- Simple content health checking (keyword-based)
- Security header presence checks
- History retention with automatic pruning
- Automated dashboard generation (no backend required)
- GitHub Actions automation for scheduled updates

## Repository Layout

```
uptime-monitor/
├── monitor.py              # Main monitoring script
├── workflow.sh             # Local workflow runner (script-based automation)
├── .github/workflows/      # GitHub Actions workflows (scheduled updates)
├── index.html              # Static dashboard (renders JSON data)
├── assets/
│   ├── style.css           # Dashboard styles
│   └── script.js           # Dashboard charting logic
├── history.json            # Historical monitoring data
├── uptime-badge.json       # Shields.io badge configuration
└── README.md               # Documentation (this file)
```

## How It Works

1. `monitor.py` performs HTTP checks for configured services.
2. Results are appended to `history.json` and optionally rotated.
3. The latest status snapshot is embedded into `index.html` so the dashboard shows current metrics without a backend.
4. GitHub Actions runs the monitor on a schedule, commits any changes, and opens/merges a pull request using a PAT.

## Getting Started

### Requirements

- Python 3.8+
- Git
- (Optional) GitHub CLI (`gh`) for local workflow testing

### Run Locally

```sh
pip install requests
python monitor.py
```

## Configuration

### Monitored Services

The monitored endpoints are defined in `monitor.py` under the `SERVICES` dictionary.

### Secrets / Tokens

For GitHub Actions to create and merge PRs as your account, set a repository secret named `PAT_SHARK` with a Personal Access Token (PAT) that has `repo` permissions.

## GitHub Actions Workflow

A workflow in `.github/workflows/uptime.yml` is scheduled to run periodically (hourly by default). It:

1. Runs `monitor.py` to update metrics.
2. Compares the generated files (`data/status.json` and `README.md`) against the repo.
3. If changes exist, creates a new branch, commits the updated files, and pushes the branch.
4. Uses `gh` to create a pull request and merges it automatically.

> **Note:** The workflow relies on the `PAT_SHARK` secret and the GitHub CLI (`gh`) being available.

## Local Workflow (Optional)

You can run the helper script locally to emulate the same behavior as the GitHub Actions workflow:

```sh
bash workflow.sh
```

This script will:

- Sleep for a random short interval (to avoid accidental collisions)
- Run the monitor
- Commit any changes
- Push a branch
- Create and merge a PR via `gh`

## Data Files

- `history.json`: Full chronological history of monitored checks.
- `data/status.json`: Latest snapshot used by the dashboard for rendering.
- `uptime-badge.json`: Badge configuration for Shields.io.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Manual Run (Optional)

```bash
python monitor.py
bash workflow.sh
```

## Continuous Run (Cron)

To run the monitor continuously on a Unix-like system, add a cron entry:

```bash
# Edit crontab
crontab -e

# Example: run every 5 minutes
*/5 * * * * cd /path/to/uptime-monitor && python monitor.py && bash workflow.sh
```

## Log Format

The `uptime_log.txt` file contains entries like:

- **Timestamp**: When the check ran
- **URL**: The monitored endpoint
- **Status**: ONLINE/OFFLINE or HTTP error code
- **Latency**: Response time in milliseconds

Format: `[YYYY-MM-DD HH:MM:SS] URL | STATUS | LATENCYms`

## Safety Notes

- The script uses a 10-second timeout to avoid hanging.
- Exceptions are caught so failures are still recorded.
- Temporary branches are used to avoid conflicts on `main`.
- Pull requests are merged automatically only after they are created.

## Monitoring Details

This project monitors the following services by default:

- GitHub Pages (`https://pklavc.github.io/`)
- GitHub API (`https://api.github.com/repos/PkLavc/codepulse-monorepo`)

Checks include:

- HTTP availability (200 is ONLINE)
- Response latency
- Connection and timeout errors


## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add feature"`)
4. Push to your branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## Contact

Patrick Araujo | Software Engineer
- Email: patrickajm@gmail.com
- GitHub: [PkLavc](https://github.com/PkLavc)

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20me-%23ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/PkLavc)
