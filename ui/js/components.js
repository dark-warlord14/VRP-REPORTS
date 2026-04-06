/* VRP Dashboard UI Components */

const Components = {
    severityClass(severity) {
        if (!severity) return 'unknown';
        return severity.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    },

    severityBadge(severity) {
        const cls = this.severityClass(severity);
        return `<span class="severity-badge ${cls}">${severity || 'Unknown'}</span>`;
    },

    statusBadge(status) {
        return `<span class="status-badge">${status || 'Unknown'}</span>`;
    },

    bountyBadge(amount) {
        if (amount == null) return '<span class="bounty-badge">Confirmed</span>';
        return `<span class="bounty-badge">$${amount.toLocaleString()}</span>`;
    },

    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        return dateStr.substring(0, 10);
    },

    formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    },

    fileIcon(mime) {
        if (!mime) return '&#128196;';
        if (mime.startsWith('image/')) return '&#128247;';
        if (mime.startsWith('video/')) return '&#127909;';
        if (mime.startsWith('text/html')) return '&#127760;';
        if (mime.includes('diff') || mime.includes('patch')) return '&#128203;';
        if (mime.includes('python') || mime.includes('javascript')) return '&#128187;';
        return '&#128196;';
    },

    statCard(label, value) {
        return `
            <div class="stat-card">
                <div class="stat-value">${value}</div>
                <div class="stat-label">${label}</div>
            </div>`;
    },

    metadataItem(label, value) {
        return `
            <div class="metadata-item">
                <div class="meta-label">${label}</div>
                <div class="meta-value">${value}</div>
            </div>`;
    },

    attachmentCard(att, issueId) {
        const icon = this.fileIcon(att.mime_type);
        const size = this.formatSize(att.size_bytes || 0);
        const isStatic = window.App?.deployMode === 'static';
        // In static deploy, local files aren't available — link to issue tracker instead
        const href = isStatic
            ? this.safeUrl(att.url)
            : (att.local_path ? `/data/issues/${issueId}/${att.local_path}` : this.safeUrl(att.url));
        const name = this.escapeHtml(att.filename || 'unknown');
        const mime = this.escapeHtml(att.mime_type || '');
        const externalHint = isStatic ? ' &#8599;' : '';
        return `
            <a class="attachment-card" href="${href}" target="_blank" rel="noopener">
                <span class="attachment-icon">${icon}</span>
                <span class="attachment-info">
                    <span class="att-name">${name}${externalHint}</span>
                    <br><span class="att-meta">${mime} &middot; ${size}</span>
                </span>
            </a>`;
    },

    inlinePreview(att, issueId) {
        // Inline previews are only available in local mode (files not deployed in static mode)
        if (window.App?.deployMode === 'static') return '';

        const src = att.local_path
            ? `/data/issues/${issueId}/${att.local_path}`
            : this.safeUrl(att.url);
        if (!src || src === '#') return '';

        const mime = att.mime_type || '';
        const alt = this.escapeHtml(att.filename || '');
        if (mime.startsWith('image/')) {
            return `<div class="inline-preview"><img src="${src}" alt="${alt}" loading="lazy"></div>`;
        }
        if (mime.startsWith('video/')) {
            return `<div class="inline-preview"><video src="${src}" controls preload="metadata"></video></div>`;
        }
        return '';
    },

    timelineEntry(update) {
        const isBounty = update.is_bounty_award;
        const cls = isBounty ? 'timeline-entry bounty-entry' : 'timeline-entry';
        const date = this.formatDate(update.timestamp);
        const author = update.author || 'Unknown';
        const text = this.escapeHtml(update.text_plain || '');

        return `
            <div class="${cls}">
                <div class="timeline-header">
                    <span class="timeline-author">${author}</span>
                    <span>${date}</span>
                </div>
                <div class="timeline-text">${text}</div>
            </div>`;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Allow only https:// and http:// URLs to prevent javascript: injection
    safeUrl(url) {
        if (!url) return '#';
        const lower = url.trim().toLowerCase();
        if (lower.startsWith('https://') || lower.startsWith('http://')) return url;
        return '#';
    },

    listSkeleton() {
        const skCard = () => `<div class="stat-card"><div class="skeleton-line" style="width:60%;height:1.8rem;margin:0 auto 0.5rem"></div><div class="skeleton-line" style="width:40%;height:0.8rem;margin:0 auto"></div></div>`;
        const skRow = () => `<tr>${['100px','1fr','100px','90px','90px','100px'].map(w => `<td><div class="skeleton-line" style="width:80%;height:0.85rem"></div></td>`).join('')}</tr>`;
        return `
            <div class="stats-bar">${[1,2,3,4].map(skCard).join('')}</div>
            <div class="skeleton-line" style="width:100%;height:2.5rem;margin-bottom:1rem"></div>
            <div class="skeleton-line" style="width:120px;height:0.85rem;margin-bottom:0.5rem"></div>
            <table class="report-table" style="opacity:0.5">
                <tbody>${[1,2,3,4,5,6,7,8].map(skRow).join('')}</tbody>
            </table>`;
    },

    pagination(currentPage, totalPages, onPageChange) {
        const container = document.createElement('div');
        container.className = 'pagination';

        const prevBtn = document.createElement('button');
        prevBtn.className = 'outline small';
        prevBtn.textContent = 'Prev';
        prevBtn.disabled = currentPage <= 1;
        prevBtn.onclick = () => onPageChange(currentPage - 1);

        const info = document.createElement('span');
        info.className = 'page-info';
        info.textContent = `Page ${currentPage} of ${totalPages}`;

        const nextBtn = document.createElement('button');
        nextBtn.className = 'outline small';
        nextBtn.textContent = 'Next';
        nextBtn.disabled = currentPage >= totalPages;
        nextBtn.onclick = () => onPageChange(currentPage + 1);

        container.append(prevBtn, info, nextBtn);
        return container;
    },
};
