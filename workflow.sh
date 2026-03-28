#!/bin/bash
set -e 

CURRENT_TIME=$(date -u -d "-3 hours" +"%H%M")
DATE_SEED=$(date -u -d "-3 hours" +"%Y%m%d")

RANDOM_OFFSET=$(echo "$DATE_SEED" | awk '{print ($1 % 60)}')

STOP_LIMIT=$(( 2235 + RANDOM_OFFSET ))
START_LIMIT=$(( 0600 + RANDOM_OFFSET ))

echo "Current: $CURRENT_TIME | Today's Stop: $STOP_LIMIT | Today's Start: $START_LIMIT"

if [ "$CURRENT_TIME" -ge "$STOP_LIMIT" ] || [ "$CURRENT_TIME" -lt "$START_LIMIT" ]; then
    echo "Sleeping hours. Skipping update to mimic human behavior."
    exit 0
fi

sleep $(( ( RANDOM % 600 ) + 300 ))

git config user.name "PkLavc"
git config user.email "patrickajm@gmail.com"

if git diff --exit-code history.json index.html uptime-badge.json assets/ blog.html blog/*.html; then
    echo "No changes detected. Skipping merge."
    exit 0
fi

BRANCH="sre-dashboard-$(date +%Y%m%d-%H%M%S)"
git checkout -b $BRANCH
git add .

git fetch origin main
git rebase origin/main

# --- 5. MENSAGENS DE COMMIT ---
MESSAGES=(
    "metrics: update dashboard"
    "stats: sync uptime data"
    "ci: refresh reliability metrics"
    "monitor: update service status"
    "sre: dashboard metrics refresh"
)

ALERT_MESSAGES=(
    "alert: performance degradation detected"
    "alert: significant page size change detected"
    "alert: service disruption detected"
)

if [ "${MONITOR_EXIT_CODE:-0}" -eq 1 ]; then
    RANDOM_INDEX=$((RANDOM % ${#ALERT_MESSAGES[@]}))
    COMMIT_MSG="${ALERT_MESSAGES[$RANDOM_INDEX]}"
else
    RANDOM_INDEX=$((RANDOM % ${#MESSAGES[@]}))
    COMMIT_MSG="${MESSAGES[$RANDOM_INDEX]}"
fi

git commit -m "$COMMIT_MSG" -m "Co-authored-by: pklavc-labs <modderkcaheua@gmail.com>"

git push origin $BRANCH --force

if [ "${MONITOR_EXIT_CODE:-0}" -eq 1 ]; then
    PR_TITLE="🔴 Inteligência GTA VI: Atualização Detectada - $(date +'%Y-%m-%d %H:%M')"
else
    PR_TITLE="🟢 Vigilância Rockstar: Sistema Monitorado - $(date +'%Y-%m-%d %H:%M')"
fi

PR_URL=$(gh pr create --title "$PR_TITLE" \
                      --body "Atualização automática de monitoramento de inteligência em tempo real sobre GTA VI.

**Mudanças:**
- Histórico de vigilância atualizado em history.json
- Visualizações do dashboard atualizadas em index.html
- Novos dados de detecção de atualização e análise de conteúdo

**Dashboard:** [index.html](./index.html)" \
                      --base main --head $BRANCH --fill)

sleep $(( ( RANDOM % 120 ) + 60 ))

echo "Merging PR: $PR_URL"
gh pr merge "$PR_URL" --squash --delete-branch --admin
