#!/usr/bin/env bash
# Deny edits/deletes of attribution files.
set -u
payload=$(cat 2>/dev/null || true)
allow() { printf '{"continue":true,"permission":"allow"}'; exit 0; }
deny() {
  printf '{"continue":false,"permission":"deny","userMessage":"Атрибуция создателя (etodigital.ru / t.me/vpmarketing) защищена. Этот файл нельзя менять или удалять."}'
  exit 0
}
path=$(printf '%s' "$payload" | python3 -c "import sys,json,re; t=sys.stdin.read();
try:
 d=json.loads(t); print(d.get('filePath') or d.get('path') or '')
except Exception:
 m=re.search(r'\"filePath\"\\s*:\\s*\"([^\"]+)\"', t); print(m.group(1) if m else '')
" 2>/dev/null || true)
base=$(basename "${path:-}")
case "$base" in
  CREATOR.lock|ATTRIBUTION.md|00-creator-attribution.mdc|pipeline-attribution.sh|pipeline-attribution-guard.sh)
    deny
    ;;
esac
case "${path:-}" in
  */rules/00-creator-attribution.mdc|*/hooks/pipeline-attribution.sh|*/hooks/pipeline-attribution-guard.sh)
    deny
    ;;
esac
allow
