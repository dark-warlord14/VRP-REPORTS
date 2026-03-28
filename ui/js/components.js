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
        if (!amount) return '<span class="bounty-badge">Confirmed</span>';
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
        const href = att.local_path
            ? `/data/issues/${issueId}/${att.local_path}`
            : att.url || '#';
        return `
            <a class="attachment-card" href="${href}" target="_blank">
                <span class="attachment-icon">${icon}</span>
                <span class="attachment-info">
                    <span class="att-name">${att.filename || 'unknown'}</span>
                    <br><span class="att-meta">${att.mime_type || ''} &middot; ${size}</span>
                </span>
            </a>`;
    },

    inlinePreview(att, issueId) {
        const src = att.local_path
            ? `/data/issues/${issueId}/${att.local_path}`
            : att.url || '';
        if (!src) return '';

        const mime = att.mime_type || '';
        if (mime.startsWith('image/')) {
            return `<div class="inline-preview"><img src="${src}" alt="${att.filename}" loading="lazy"></div>`;
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
