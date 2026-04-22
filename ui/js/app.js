/* VRP Dashboard - Main Application */

const App = {
    data: [],
    stats: null,
    md: null,
    deployMode: 'local',
    loadError: null,
    _debounceTimer: null,
    currentSort: { field: 'created_date', dir: 'desc' },
    currentPage: 1,
    pageSize: 50,
    filters: { search: '', year: '', severity: '', status: '' },
    chartInstances: {},

    async init() {
        this.md = window.markdownit({ html: false, linkify: true, breaks: true });
        this.deployMode = document.querySelector('meta[name="vrp-deploy-mode"]')?.content || 'local';

        // Show skeleton while loading
        document.getElementById('app').innerHTML = Components.listSkeleton();

        await this.loadData();
        window.addEventListener('hashchange', () => this.route());
        this.route();
    },

    async loadData() {
        try {
            const [indexRes, statsRes] = await Promise.all([
                fetch('/data/index.json'),
                fetch('/data/stats.json'),
            ]);
            if (!indexRes.ok) throw new Error(`Failed to load index (HTTP ${indexRes.status})`);
            this.data = await indexRes.json();
            if (statsRes.ok) this.stats = await statsRes.json();
        } catch (e) {
            console.error('Failed to load data:', e);
            this.loadError = e.message || 'Failed to load data';
        }
    },

    renderError() {
        document.getElementById('app').innerHTML = `
            <div class="error-banner">
                <strong>Failed to load dashboard data</strong>
                <p>${Components.escapeHtml(this.loadError)}</p>
                <button onclick="App.retryLoad()">Retry</button>
            </div>
        `;
    },

    async retryLoad() {
        this.loadError = null;
        document.getElementById('app').innerHTML = Components.listSkeleton();
        await this.loadData();
        this.route();
    },

    route() {
        if (this.loadError) {
            this.renderError();
            return;
        }

        const hash = location.hash || '#/';
        const isListView = hash === '#/' || hash.startsWith('#/?');

        // Update nav active state
        document.querySelectorAll('.nav-link').forEach(el => {
            el.classList.toggle('active',
                (hash.startsWith('#/stats') && el.dataset.nav === 'stats') ||
                (isListView && el.dataset.nav === 'list') ||
                (hash.startsWith('#/report/') && el.dataset.nav === 'list')
            );
        });

        if (hash.startsWith('#/report/')) {
            const id = hash.split('/')[2];
            this.showReport(id);
        } else if (hash.startsWith('#/stats')) {
            this.showStats();
        } else {
            // URL is source of truth — parse state before rendering
            this.parseState(hash);
            this.showList();
        }
    },

    // Parse filter/sort/page from URL hash: #/?q=v8&year=2024&sort=bounty_amount:desc&page=2
    parseState(hash) {
        // Reset to defaults first so navigating back to #/ clears filters
        this.filters = { search: '', year: '', severity: '', status: '' };
        this.currentSort = { field: 'created_date', dir: 'desc' };
        this.currentPage = 1;

        const qIndex = hash.indexOf('?');
        if (qIndex === -1) return;

        const params = new URLSearchParams(hash.slice(qIndex + 1));
        if (params.has('q'))        this.filters.search   = params.get('q');
        if (params.has('year'))     this.filters.year     = params.get('year');
        if (params.has('severity')) this.filters.severity = params.get('severity');
        if (params.has('status'))   this.filters.status   = params.get('status');
        if (params.has('sort')) {
            const [field, dir] = params.get('sort').split(':');
            if (field && (dir === 'asc' || dir === 'desc')) {
                this.currentSort = { field, dir };
            }
        }
        if (params.has('page')) {
            const p = parseInt(params.get('page'), 10);
            if (!isNaN(p) && p > 0) this.currentPage = p;
        }
    },

    // Serialize current state to URL hash string
    serializeState() {
        const params = new URLSearchParams();
        if (this.filters.search)   params.set('q',        this.filters.search);
        if (this.filters.year)     params.set('year',     this.filters.year);
        if (this.filters.severity) params.set('severity', this.filters.severity);
        if (this.filters.status)   params.set('status',   this.filters.status);
        const isDefaultSort = this.currentSort.field === 'created_date' && this.currentSort.dir === 'desc';
        if (!isDefaultSort) params.set('sort', `${this.currentSort.field}:${this.currentSort.dir}`);
        if (this.currentPage > 1) params.set('page', this.currentPage);
        const qs = params.toString();
        return qs ? `#/?${qs}` : '#/';
    },

    updateHash() {
        history.replaceState(null, '', this.serializeState());
    },

    // === LIST VIEW ===
    showList() {
        const app = document.getElementById('app');
        const filtered = this.getFilteredData();
        const sorted = this.getSortedData(filtered);
        const totalPages = Math.max(1, Math.ceil(sorted.length / this.pageSize));
        if (this.currentPage > totalPages) this.currentPage = totalPages;
        const pageData = sorted.slice(
            (this.currentPage - 1) * this.pageSize,
            this.currentPage * this.pageSize
        );

        const totalBounty = filtered.reduce((s, r) => s + (r.bounty_amount || 0), 0);
        const years = [...new Set(this.data.map(r => r.year).filter(Boolean))].sort();
        const severities = [...new Set(this.data.map(r => r.severity).filter(Boolean))].sort();
        const statuses = [...new Set(this.data.map(r => r.status).filter(Boolean))].sort();

        const hasActiveFilters = this.filters.search || this.filters.year ||
            this.filters.severity || this.filters.status;

        const startIdx = (this.currentPage - 1) * this.pageSize + 1;
        const endIdx = Math.min(this.currentPage * this.pageSize, sorted.length);
        const resultCount = sorted.length > 0
            ? `Showing ${startIdx}–${endIdx} of ${sorted.length} report${sorted.length !== 1 ? 's' : ''}`
            : 'No reports match your filters.';

        app.innerHTML = `
            <div class="stats-bar">
                ${Components.statCard('Total Reports', filtered.length)}
                ${Components.statCard('Total Bounty', '$' + totalBounty.toLocaleString())}
                ${Components.statCard('Avg Bounty',
                    '$' + (filtered.length
                        ? Math.round(totalBounty / (filtered.filter(r => r.bounty_amount).length || 1)).toLocaleString()
                        : '0')
                )}
                ${Components.statCard('With Attachments',
                    filtered.filter(r => r.attachment_count > 0).length
                )}
            </div>

            <div class="filters">
                <input type="search" class="search-box"
                    placeholder="Search by ID, title, or component..."
                    aria-label="Search reports"
                    value="${Components.escapeHtml(this.filters.search)}"
                    oninput="App.onFilterDebounced('search', this.value)">
                <select aria-label="Filter by year" onchange="App.onFilter('year', this.value)">
                    <option value="">All Years</option>
                    ${years.map(y => `<option value="${y}" ${this.filters.year == y ? 'selected' : ''}>${y}</option>`).join('')}
                </select>
                <select aria-label="Filter by severity" onchange="App.onFilter('severity', this.value)">
                    <option value="">All Severities</option>
                    ${severities.map(s => `<option value="${s}" ${this.filters.severity === s ? 'selected' : ''}>${Components.escapeHtml(s)}</option>`).join('')}
                </select>
                <select aria-label="Filter by status" onchange="App.onFilter('status', this.value)">
                    <option value="">All Statuses</option>
                    ${statuses.map(s => `<option value="${s}" ${this.filters.status === s ? 'selected' : ''}>${Components.escapeHtml(s)}</option>`).join('')}
                </select>
                ${hasActiveFilters ? `<button class="outline small clear-btn" onclick="App.clearFilters()">Clear filters</button>` : ''}
                <button class="outline small" onclick="App.exportCSV()" title="Export filtered results as CSV">Export CSV</button>
            </div>

            <div class="result-count">${resultCount}</div>

            <div class="table-wrapper">
                <table class="report-table" role="grid">
                    <thead>
                        <tr>
                            ${this.thSortable('id', 'ID', 'col-id')}
                            ${this.thSortable('title', 'Title', 'col-title')}
                            ${this.thSortable('severity', 'Severity', 'col-severity')}
                            ${this.thSortable('bounty_amount', 'Bounty', 'col-bounty')}
                            ${this.thSortable('status', 'Status', 'col-status')}
                            ${this.thSortable('created_date', 'Date', 'col-date')}
                        </tr>
                    </thead>
                    <tbody>
                        ${pageData.length === 0
                            ? '<tr><td colspan="6" style="text-align:center;padding:3rem 0;color:var(--fg-muted);font-family:var(--mono);letter-spacing:.08em;">No reports match your filters.</td></tr>'
                            : ''}
                        ${pageData.map(r => `
                            <tr onclick="location.hash='#/report/${r.id}'"
                                tabindex="0"
                                onkeydown="if(event.key==='Enter')location.hash='#/report/${r.id}'"
                                aria-label="Report ${r.id}: ${Components.escapeHtml(r.title || 'Untitled')}">
                                <td class="col-id"><code>${Components.escapeHtml(r.id || '')}</code></td>
                                <td class="col-title">${Components.escapeHtml(r.title || 'Untitled')}</td>
                                <td class="col-severity">${Components.severityBadge(r.severity)}</td>
                                <td class="col-bounty">${Components.bountyBadge(r.bounty_amount)}</td>
                                <td class="col-status">${Components.statusBadge(r.status)}</td>
                                <td class="col-date">${Components.formatDate(r.created_date)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div id="pagination"></div>
        `;

        if (totalPages > 1) {
            document.getElementById('pagination').appendChild(
                Components.pagination(this.currentPage, totalPages, (p) => {
                    this.currentPage = p;
                    this.updateHash();
                    this.showList();
                })
            );
        }
    },

    thSortable(field, label, cls) {
        const sorted = this.currentSort.field === field;
        const arrow = sorted ? (this.currentSort.dir === 'asc' ? '&#9650;' : '&#9660;') : '&#8597;';
        const ariaSort = sorted ? (this.currentSort.dir === 'asc' ? 'ascending' : 'descending') : 'none';
        return `<th class="${cls} ${sorted ? 'sorted' : ''}"
            onclick="App.onSort('${field}')"
            aria-sort="${ariaSort}">
            ${label}<span class="sort-arrow">${arrow}</span>
        </th>`;
    },

    onSort(field) {
        if (this.currentSort.field === field) {
            this.currentSort.dir = this.currentSort.dir === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort = { field, dir: field === 'bounty_amount' ? 'desc' : 'asc' };
        }
        this.currentPage = 1;
        this.updateHash();
        this.showList();
    },

    onFilter(key, value) {
        this.filters[key] = value;
        this.currentPage = 1;
        this.updateHash();
        this.showList();
    },

    onFilterDebounced(key, value) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this.onFilter(key, value), 150);
    },

    clearFilters() {
        this.filters = { search: '', year: '', severity: '', status: '' };
        this.currentPage = 1;
        this.updateHash();
        this.showList();
    },

    exportCSV() {
        const filtered = this.getSortedData(this.getFilteredData());
        const header = ['ID', 'Title', 'Severity', 'Bounty', 'Status', 'Date', 'URL'];
        const rows = filtered.map(r => [
            r.id || '',
            (r.title || '').replace(/"/g, '""'),
            r.severity || '',
            r.bounty_amount || '',
            r.status || '',
            (r.created_date || '').substring(0, 10),
            r.url || '',
        ].map(v => `"${v}"`).join(','));

        const csv = [header.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'vrp-reports.csv';
        a.click();
        URL.revokeObjectURL(url);
    },

    getFilteredData() {
        return this.data.filter(r => {
            if (this.filters.search) {
                const q = this.filters.search.toLowerCase();
                const match = (r.id || '').toLowerCase().includes(q) ||
                    (r.title || '').toLowerCase().includes(q) ||
                    (r.component || '').toLowerCase().includes(q);
                if (!match) return false;
            }
            if (this.filters.year && r.year != this.filters.year) return false;
            if (this.filters.severity && r.severity !== this.filters.severity) return false;
            if (this.filters.status && r.status !== this.filters.status) return false;
            return true;
        });
    },

    getSortedData(data) {
        const { field, dir } = this.currentSort;
        const mult = dir === 'asc' ? 1 : -1;
        return [...data].sort((a, b) => {
            let va = a[field], vb = b[field];
            if (va == null) va = '';
            if (vb == null) vb = '';
            if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * mult;
            return String(va).localeCompare(String(vb)) * mult;
        });
    },

    // === REPORT DETAIL VIEW ===
    async showReport(id) {
        const app = document.getElementById('app');
        app.innerHTML = '<p aria-busy="true">Loading report...</p>';

        try {
            const fetches = [
                fetch(`/data/issues/${id}/report.json`),
                fetch(`/data/issues/${id}/report.md`),
            ];
            // raw_updates.json is not deployed in static mode (Cloudflare Pages)
            if (this.deployMode !== 'static') {
                fetches.push(fetch(`/data/issues/${id}/raw_updates.json`));
            }

            const results = await Promise.all(fetches);
            const [reportRes, mdRes] = results;
            const updatesRes = results[2] || null;

            if (!reportRes.ok) {
                app.innerHTML = `<p>Report ${Components.escapeHtml(id)} not found.</p><a href="#/">Back to list</a>`;
                return;
            }

            const report = await reportRes.json();
            const mdContent = mdRes.ok ? await mdRes.text() : null;
            let updates = [];

            if (updatesRes?.ok) {
                try {
                    const raw = await updatesRes.json();
                    updates = this.parseRawUpdates(raw, id);
                } catch (e) { /* ignore parse errors */ }
            }

            this.renderReport(report, mdContent, updates);

        } catch (e) {
            console.error('Error loading report:', e);
            app.innerHTML = `
                <div class="error-banner">
                    <strong>Error loading report</strong>
                    <p>${Components.escapeHtml(e.message)}</p>
                    <a href="#/">Back to list</a>
                </div>`;
        }
    },

    parseRawUpdates(raw, issueId) {
        try {
            const list = raw[0][1][0];
            if (!Array.isArray(list)) return [];
            return list.map((entry, idx) => {
                const author = entry?.[0]?.[1] || 'Unknown';
                const epoch = entry?.[1]?.[0];
                const timestamp = epoch ? new Date(epoch * 1000).toISOString() : null;
                const text_plain = entry?.[2]?.[0] || '';
                const is_bounty = text_plain.toLowerCase().includes('decided to award you');
                return { index: idx, author, timestamp, text_plain, is_bounty_award: is_bounty };
            }).filter(u => u.text_plain.trim());
        } catch (e) {
            return [];
        }
    },

    renderReport(report, mdContent, updates) {
        const app = document.getElementById('app');
        const attachments = report.attachments || [];
        const isStatic = this.deployMode === 'static';

        const metaItems = [
            Components.metadataItem('Status', Components.statusBadge(report.status)),
            Components.metadataItem('Severity', Components.severityBadge(report.severity)),
            Components.metadataItem('Priority', report.priority || 'Unknown'),
            Components.metadataItem('Bounty', Components.bountyBadge(report.bounty_amount)),
            Components.metadataItem('Component', report.component || 'Unknown'),
            Components.metadataItem('Reporter', report.reporter || 'Unknown'),
        ];
        if (report.assignee)          metaItems.push(Components.metadataItem('Assignee', report.assignee));
        if (report.chrome_version)    metaItems.push(Components.metadataItem('Chrome Version', report.chrome_version));
        if (report.os_platforms?.length) metaItems.push(Components.metadataItem('Platforms', report.os_platforms.join(', ')));
        if (report.cve_ids?.length)   metaItems.push(Components.metadataItem('CVE IDs', report.cve_ids.join(', ')));
        if (report.created_date)      metaItems.push(Components.metadataItem('Created', Components.formatDate(report.created_date)));
        if (report.update_count)      metaItems.push(Components.metadataItem('Updates', report.update_count));

        let descriptionHtml = '';
        if (mdContent) {
            descriptionHtml = this.md.render(mdContent);
        } else {
            descriptionHtml = `<pre>${Components.escapeHtml(report.description_snippet || 'No description available.')}</pre>`;
        }

        // Inline previews only available in local mode (static mode lacks downloaded files)
        const previews = isStatic ? '' : attachments
            .filter(a => a.mime_type?.startsWith('image/') || a.mime_type?.startsWith('video/'))
            .map(a => Components.inlinePreview(a, report.id))
            .join('');

        const attCards = attachments.map(a => Components.attachmentCard(a, report.id)).join('');

        // Timeline only available when raw_updates.json was fetched (local mode)
        const showTimeline = !isStatic && updates.length > 1;
        const timelineHtml = showTimeline
            ? updates.slice(1).map(u => Components.timelineEntry(u)).join('')
            : '';

        app.innerHTML = `
            <div class="report-detail">
                <a href="#/" class="back-link">&larr; Back to reports</a>

                <div class="report-header">
                    <h1>${Components.escapeHtml(report.title || 'Untitled')}</h1>
                    <a href="${Components.safeUrl(report.url)}" target="_blank" rel="noopener">
                        View on Chromium Issue Tracker &rarr;
                    </a>
                </div>

                <div class="metadata-grid">${metaItems.join('')}</div>

                <h2>${mdContent ? 'Report' : 'Description'}</h2>
                <div class="markdown-content">${descriptionHtml}</div>

                ${previews ? `<h2>Previews</h2>${previews}` : ''}

                ${attachments.length ? `
                    <div class="attachments-section">
                        <h2>Attachments (${attachments.length})</h2>
                        <div class="attachment-grid">${attCards}</div>
                    </div>
                ` : ''}

                ${showTimeline ? `
                    <h2>Timeline (${updates.length - 1} comments)</h2>
                    <div class="timeline">${timelineHtml}</div>
                ` : ''}

                <hr>
                <div style="display:flex;gap:1rem;margin:1rem 0;flex-wrap:wrap;">
                    <a href="/data/issues/${report.id}/report.json" target="_blank" class="outline small">report.json</a>
                    ${report.has_markdown !== false ? `<a href="/data/issues/${report.id}/report.md" target="_blank" class="outline small">report.md</a>` : ''}
                    ${!isStatic ? `<a href="/data/issues/${report.id}/raw_updates.json" target="_blank" class="outline small">raw_updates.json</a>` : ''}
                </div>
            </div>
        `;
    },

    // === STATS VIEW ===
    showStats() {
        const app = document.getElementById('app');

        if (!this.stats) {
            app.innerHTML = '<p>No statistics available. Run <code>vrp index</code> to generate.</p>';
            return;
        }

        const s = this.stats;

        app.innerHTML = `
            <h1>Statistics</h1>
            <div class="stats-bar">
                ${Components.statCard('Total Reports', s.total_reports)}
                ${Components.statCard('Total Bounty', '$' + (s.total_bounty || 0).toLocaleString())}
                ${Components.statCard('Avg Bounty', '$' + (s.avg_bounty || 0).toLocaleString())}
            </div>

            <div class="stats-grid">
                <div class="chart-card">
                    <h3>Reports by Year</h3>
                    <canvas id="chartYear"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Bounty by Year ($)</h3>
                    <canvas id="chartBountyYear"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Severity Distribution</h3>
                    <canvas id="chartSeverity"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Bounty Distribution</h3>
                    <canvas id="chartBountyHist"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Top Components</h3>
                    <canvas id="chartComponents"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Status Distribution</h3>
                    <canvas id="chartStatus"></canvas>
                </div>
            </div>

            ${s.top_bounties?.length ? `
                <h2 style="margin-top:2rem;">Top Bounties</h2>
                <table class="top-bounties-table">
                    <thead>
                        <tr>
                            <th class="rank">#</th>
                            <th>Title</th>
                            <th>Severity</th>
                            <th>Bounty</th>
                            <th>Year</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${s.top_bounties.map((b, i) => `
                            <tr onclick="location.hash='#/report/${b.id}'"
                                tabindex="0"
                                onkeydown="if(event.key==='Enter')location.hash='#/report/${b.id}'"
                                style="cursor:pointer">
                                <td class="rank">${i + 1}</td>
                                <td>${Components.escapeHtml(b.title || '')}</td>
                                <td>${Components.severityBadge(b.severity)}</td>
                                <td>${Components.bountyBadge(b.bounty_amount)}</td>
                                <td>${b.year || 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : ''}
        `;

        requestAnimationFrame(() => this.renderCharts(s));
    },

    renderCharts(s) {
        Object.values(this.chartInstances).forEach(c => c.destroy());
        this.chartInstances = {};

        const isDark = document.documentElement.dataset.theme === 'dark';
        const textColor = isDark ? '#a1a1a1' : '#525252';
        const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = gridColor;
        Chart.defaults.font.family = "'Geist', -apple-system, sans-serif";
        Chart.defaults.font.size = 11;

        // v0-style: primary bars near-monochrome, categorical uses distinct hues.
        const barColor = isDark ? '#ededed' : '#0a0a0a';
        const palette = {
            primary: barColor,
            red:     '#e5484d',
            orange:  '#ff8a3d',
            amber:   '#f1a10d',
            blue:    '#3b82f6',
            green:   '#30a46c',
            violet:  '#8b5cf6',
            gray:    isDark ? '#525252' : '#a3a3a3',
        };

        if (s.by_year) {
            const years = Object.keys(s.by_year).sort();
            this.chartInstances.year = new Chart(document.getElementById('chartYear'), {
                type: 'bar',
                data: {
                    labels: years,
                    datasets: [{
                        label: 'Reports',
                        data: years.map(y => s.by_year[y].count),
                        backgroundColor: palette.primary,
                        borderRadius: 4,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    onClick: (evt, elements) => {
                        if (elements.length > 0) {
                            const year = years[elements[0].index];
                            location.hash = `#/?year=${year}`;
                        }
                    },
                },
            });

            this.chartInstances.bountyYear = new Chart(document.getElementById('chartBountyYear'), {
                type: 'bar',
                data: {
                    labels: years,
                    datasets: [{
                        label: 'Bounty ($)',
                        data: years.map(y => s.by_year[y].total_bounty),
                        backgroundColor: palette.primary,
                        borderRadius: 4,
                        borderSkipped: false,
                    }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } },
            });
        }

        if (s.by_severity) {
            const sevLabels = Object.keys(s.by_severity);
            const sevColors = sevLabels.map(l => {
                if (l.includes('Critical')) return palette.red;
                if (l.includes('High'))     return palette.orange;
                if (l.includes('Medium'))   return palette.amber;
                if (l.includes('Low'))      return palette.blue;
                if (l.includes('Minimal'))  return palette.green;
                return palette.gray;
            });
            this.chartInstances.severity = new Chart(document.getElementById('chartSeverity'), {
                type: 'doughnut',
                data: {
                    labels: sevLabels,
                    datasets: [{ data: Object.values(s.by_severity), backgroundColor: sevColors }]
                },
                options: { responsive: true },
            });
        }

        if (s.bounty_histogram) {
            this.chartInstances.bountyHist = new Chart(document.getElementById('chartBountyHist'), {
                type: 'bar',
                data: {
                    labels: s.bounty_histogram.map(b => b.range),
                    datasets: [{
                        label: 'Count',
                        data: s.bounty_histogram.map(b => b.count),
                        backgroundColor: palette.primary,
                        borderRadius: 4,
                        borderSkipped: false,
                    }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } },
            });
        }

        if (s.by_component) {
            const compLabels = Object.keys(s.by_component).slice(0, 10);
            this.chartInstances.components = new Chart(document.getElementById('chartComponents'), {
                type: 'bar',
                data: {
                    labels: compLabels,
                    datasets: [{
                        label: 'Reports',
                        data: compLabels.map(c => s.by_component[c]),
                        backgroundColor: palette.primary,
                        borderRadius: 4,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } },
                },
            });
        }

        if (s.by_status) {
            const statusLabels = Object.keys(s.by_status);
            this.chartInstances.status = new Chart(document.getElementById('chartStatus'), {
                type: 'doughnut',
                data: {
                    labels: statusLabels,
                    datasets: [{
                        data: Object.values(s.by_status),
                        backgroundColor: [
                            palette.primary, palette.blue, palette.green, palette.red,
                            palette.orange, palette.amber, palette.violet, palette.gray,
                        ],
                    }]
                },
                options: { responsive: true },
            });
        }
    },
};

// Theme toggle
function toggleTheme() {
    const html = document.documentElement;
    const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
    html.dataset.theme = next;
    localStorage.setItem('vrp-theme', next);
    document.getElementById('themeIcon').innerHTML = next === 'dark' ? '&#9790;' : '&#9728;';
    if (location.hash.startsWith('#/stats') && App.stats) {
        App.renderCharts(App.stats);
    }
}

// Load saved theme
(function() {
    const saved = localStorage.getItem('vrp-theme');
    if (saved) {
        document.documentElement.dataset.theme = saved;
        document.getElementById('themeIcon').innerHTML = saved === 'dark' ? '&#9790;' : '&#9728;';
    }
})();

document.addEventListener('DOMContentLoaded', () => App.init());
