#!/usr/bin/env bash
# Assembles the static dist/ directory for Cloudflare Pages deployment.
# Output: ~22.5MB (ui assets + index/stats + per-issue report.json/report.md only)
# Excludes: attachments, raw JSON, discovery queue files.
set -euo pipefail

DIST=dist
DATA=data

echo "Building ${DIST}/..."
rm -rf "${DIST}"
mkdir -p "${DIST}"

# Copy UI assets
cp -r ui/* "${DIST}/"

# Copy Cloudflare _headers file (root-level config)
cp _headers "${DIST}/"

# Inject deploy-mode meta tag into index.html (after <meta charset=...>)
sed -i.bak 's|<meta charset="UTF-8">|<meta charset="UTF-8">\n    <meta name="vrp-deploy-mode" content="static">|' "${DIST}/index.html"
rm -f "${DIST}/index.html.bak"

# Fingerprint the mutable app bundle so Cloudflare cannot serve stale UI logic
# from the custom-domain cache after a deployment.
APP_JS="${DIST}/js/app.js"
if command -v sha256sum >/dev/null 2>&1; then
    APP_JS_HASH=$(sha256sum "${APP_JS}" | awk '{print substr($1, 1, 12)}')
else
    APP_JS_HASH=$(shasum -a 256 "${APP_JS}" | awk '{print substr($1, 1, 12)}')
fi
cp "${APP_JS}" "${DIST}/js/app.${APP_JS_HASH}.js"
sed -i.bak "s|src=\"js/app.js\"|src=\"js/app.${APP_JS_HASH}.js\"|" "${DIST}/index.html"
rm -f "${DIST}/index.html.bak"

# Copy top-level data files
if [ ! -f "${DATA}/index.json" ] || [ ! -f "${DATA}/stats.json" ]; then
    echo "ERROR: ${DATA}/index.json or ${DATA}/stats.json missing. Run 'vrp index' first." >&2
    exit 1
fi
mkdir -p "${DIST}/data/issues"
cp "${DATA}/index.json" "${DIST}/data/"
cp "${DATA}/stats.json" "${DIST}/data/"

# Copy per-issue report.json + report.md only (no attachments, no raw JSON)
for issue_dir in "${DATA}/issues"/*/; do
    id=$(basename "${issue_dir}")
    dest="${DIST}/data/issues/${id}"
    mkdir -p "${dest}"
    [ -f "${issue_dir}/report.json" ] && cp "${issue_dir}/report.json" "${dest}/"
    [ -f "${issue_dir}/report.md"   ] && cp "${issue_dir}/report.md"   "${dest}/"
done

SIZE=$(du -sh "${DIST}" | cut -f1)
COUNT=$(find "${DIST}/data/issues" -name "report.json" | wc -l | tr -d ' ')
echo "Done: ${DIST}/ is ${SIZE}, ${COUNT} reports deployed."
