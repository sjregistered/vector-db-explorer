/* ═══════════════════════════════════════════════
   Vector DB Explorer – Frontend Logic
   RTB Cycle 16 – Generative AI Advance (Milestone 5)
   ═══════════════════════════════════════════════ */

(function () {
    'use strict';

    // ─── State ───
    const state = {
        collections: [],
        activeDocCollection: '',
        editingDocId: null,
    };

    const $ = (id) => document.getElementById(id);

    // ─── Helpers ───
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function api(url, options = {}) {
        const opts = { headers: { 'Content-Type': 'application/json' }, ...options };
        if (opts.body && typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
        let res;
        try {
            res = await fetch(url, opts);
        } catch (err) {
            throw new Error('Network error – is the server running?');
        }
        let data = {};
        try { data = await res.json(); } catch (_) { /* non-JSON */ }
        if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
        return data;
    }

    function toast(message, type = 'info') {
        const container = $('toastContainer');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => {
            el.style.transition = 'opacity 0.3s, transform 0.3s';
            el.style.opacity = '0';
            el.style.transform = 'translateX(20px)';
            setTimeout(() => el.remove(), 300);
        }, 3200);
    }

    function setLoading(btn, loading, label) {
        if (!btn) return;
        if (loading) {
            btn.dataset.originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span class="loading-spinner"></span> ${label || 'Working...'}`;
        } else {
            btn.disabled = false;
            if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
        }
    }

    function emptyState(title, subtitle = '') {
        return `<div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <p>${escapeHtml(title)}</p>${subtitle ? `<span>${escapeHtml(subtitle)}</span>` : ''}
        </div>`;
    }

    function formatTime(ts) {
        if (!ts) return '';
        const d = new Date(ts * 1000);
        return isNaN(d.getTime()) ? '' : d.toLocaleString();
    }

    // ─── Navigation ───
    function switchTab(tab) {
        document.querySelectorAll('.nav-item').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
        document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
        const panel = $('tab' + tab.charAt(0).toUpperCase() + tab.slice(1));
        if (panel) panel.classList.add('active');
        $('sidebar').classList.remove('mobile-open');
        if (tab === 'collections') loadCollections();
    }

    // ─── Collections ───
    async function loadCollections() {
        try {
            const data = await api('/api/collections');
            state.collections = data.collections || [];
            renderCollections();
            populateSelects();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function renderCollections() {
        const grid = $('collectionsGrid');
        if (!state.collections.length) {
            grid.innerHTML = emptyState('No collections yet', 'Create a collection to get started');
            return;
        }
        grid.innerHTML = state.collections.map((c) => {
            const space = (c.metadata && c.metadata['hnsw:space']) || 'l2';
            return `<div class="collection-card" data-name="${escapeHtml(c.name)}">
                <div class="collection-card-header">
                    <span class="collection-name">${escapeHtml(c.name)}</span>
                    <span class="collection-count">${c.count} docs</span>
                </div>
                <div class="collection-meta">Distance: ${escapeHtml(space)}</div>
                <div class="collection-actions">
                    <button class="btn btn-ghost btn-sm" data-action="view" data-name="${escapeHtml(c.name)}">View Docs</button>
                    <button class="btn btn-ghost btn-sm" data-action="search" data-name="${escapeHtml(c.name)}">Search</button>
                    <button class="btn btn-danger btn-sm" data-action="delete" data-name="${escapeHtml(c.name)}">Delete</button>
                </div>
            </div>`;
        }).join('');
    }

    function populateSelects() {
        ['docCollectionSelect', 'searchCollectionSelect'].forEach((id) => {
            const sel = $(id);
            const current = sel.value;
            sel.innerHTML = '<option value="">-- Select --</option>' +
                state.collections.map((c) => `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)} (${c.count})</option>`).join('');
            if (state.collections.some((c) => c.name === current)) sel.value = current;
        });
        $('addDocumentBtn').disabled = !$('docCollectionSelect').value;
    }

    async function createCollection() {
        const input = $('collectionNameInput');
        const name = input.value.trim();
        if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]{1,61}[a-zA-Z0-9]$/.test(name)) {
            toast('Name must be 3–63 chars, alphanumeric/underscore/hyphen, starting & ending alphanumeric.', 'error');
            return;
        }
        const btn = $('submitCreateCollection');
        setLoading(btn, true, 'Creating...');
        try {
            await api('/api/collections', { method: 'POST', body: { name } });
            toast(`Collection "${name}" created`, 'success');
            input.value = '';
            $('createCollectionForm').classList.add('hidden');
            await loadCollections();
        } catch (err) {
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    async function deleteCollection(name) {
        if (!confirm(`Delete collection "${name}" and all its documents?`)) return;
        try {
            await api(`/api/collections/${encodeURIComponent(name)}`, { method: 'DELETE' });
            toast(`Collection "${name}" deleted`, 'success');
            if (state.activeDocCollection === name) {
                state.activeDocCollection = '';
                $('documentsList').innerHTML = emptyState('Select a collection to view documents');
            }
            await loadCollections();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    // ─── Documents ───
    async function loadDocuments() {
        const name = state.activeDocCollection;
        const list = $('documentsList');
        if (!name) {
            list.innerHTML = emptyState('Select a collection to view documents');
            return;
        }
        list.innerHTML = '<div class="empty-state"><span class="loading-spinner"></span><p>Loading documents...</p></div>';
        try {
            const data = await api(`/api/documents?collection=${encodeURIComponent(name)}&limit=200`);
            const docs = data.documents || [];
            if (!docs.length) {
                list.innerHTML = emptyState('No documents in this collection', 'Click "Add Document" to insert one');
                return;
            }
            list.innerHTML = docs.map((d) => {
                const meta = d.metadata || {};
                const time = formatTime(meta.updated_at || meta.inserted_at);
                return `<div class="document-card">
                    <div class="doc-header">
                        <span class="doc-id">${escapeHtml(d.id)}</span>
                        <div class="doc-actions">
                            <button class="btn btn-ghost btn-sm" data-action="edit" data-id="${escapeHtml(d.id)}">Edit</button>
                            <button class="btn btn-danger btn-sm" data-action="delete-doc" data-id="${escapeHtml(d.id)}">Delete</button>
                        </div>
                    </div>
                    <div class="doc-text">${escapeHtml(d.document)}</div>
                    <div class="doc-meta">
                        ${d.embedding_dim ? `<span class="doc-meta-item">${d.embedding_dim}d vector</span>` : ''}
                        <span class="doc-meta-item">${(d.document || '').length} chars</span>
                        ${time ? `<span class="doc-meta-item">${escapeHtml(time)}</span>` : ''}
                    </div>
                </div>`;
            }).join('');
            // keep raw text for the edit modal
            list._docs = docs;
        } catch (err) {
            list.innerHTML = emptyState('Failed to load documents', err.message);
            toast(err.message, 'error');
        }
    }

    async function insertDocument() {
        const text = $('docTextInput').value.trim();
        const id = $('docIdInput').value.trim();
        if (!text) { toast('Document text is required.', 'error'); return; }
        const btn = $('submitAddDoc');
        setLoading(btn, true, 'Embedding...');
        try {
            const body = { collection: state.activeDocCollection, documents: [text] };
            if (id) body.ids = [id];
            await api('/api/documents', { method: 'POST', body });
            toast('Document inserted', 'success');
            $('docTextInput').value = '';
            $('docIdInput').value = '';
            $('addDocumentForm').classList.add('hidden');
            await Promise.all([loadDocuments(), loadCollections()]);
        } catch (err) {
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    function openEditModal(docId) {
        const docs = $('documentsList')._docs || [];
        const doc = docs.find((d) => d.id === docId);
        if (!doc) return;
        state.editingDocId = docId;
        $('editDocId').value = docId;
        $('editDocText').value = doc.document || '';
        $('editModal').classList.remove('hidden');
        $('editDocText').focus();
    }

    function closeEditModal() {
        $('editModal').classList.add('hidden');
        state.editingDocId = null;
    }

    async function saveEdit() {
        const text = $('editDocText').value.trim();
        if (!text) { toast('Document text cannot be empty.', 'error'); return; }
        const btn = $('submitEdit');
        setLoading(btn, true, 'Saving...');
        try {
            await api(`/api/documents/${encodeURIComponent(state.editingDocId)}`, {
                method: 'PUT',
                body: { collection: state.activeDocCollection, document: text, metadata: {} },
            });
            toast('Document updated (re-embedded)', 'success');
            closeEditModal();
            await loadDocuments();
        } catch (err) {
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    async function deleteDocument(docId) {
        if (!confirm(`Delete document "${docId}"?`)) return;
        try {
            await api(`/api/documents/${encodeURIComponent(docId)}?collection=${encodeURIComponent(state.activeDocCollection)}`, { method: 'DELETE' });
            toast('Document deleted', 'success');
            await Promise.all([loadDocuments(), loadCollections()]);
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    // ─── Search ───
    async function runSearch() {
        const collection = $('searchCollectionSelect').value;
        const query = $('searchQueryInput').value.trim();
        const topK = parseInt($('topKInput').value, 10) || 5;
        const out = $('searchResults');
        if (!collection) { toast('Select a collection first.', 'error'); return; }
        if (!query) { toast('Enter a search query.', 'error'); return; }

        const btn = $('searchBtn');
        setLoading(btn, true, 'Searching...');
        try {
            const data = await api('/api/search', { method: 'POST', body: { collection, query, top_k: topK } });
            const results = data.results || [];
            let html = `<div class="search-meta">
                Found <span class="search-meta-highlight">${results.length}</span> results in
                <span class="search-meta-highlight">${(data.search_time_seconds * 1000).toFixed(1)} ms</span>
                for "<em>${escapeHtml(query)}</em>"
            </div>`;
            if (!results.length) {
                html += emptyState('No results', 'The collection may be empty');
            } else {
                html += results.map((r, i) => `<div class="result-card" style="animation-delay:${i * 60}ms">
                    <div class="result-header">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span class="result-rank">#${i + 1}</span>
                            <span class="result-id">${escapeHtml(r.id)}</span>
                        </div>
                        <div class="result-scores">
                            <span class="score-badge similarity">sim ${r.similarity !== null ? r.similarity.toFixed(4) : '–'}</span>
                            <span class="score-badge distance">dist ${r.distance !== null ? Number(r.distance).toFixed(4) : '–'}</span>
                        </div>
                    </div>
                    <div class="result-text">${escapeHtml(r.document)}</div>
                </div>`).join('');
            }
            out.innerHTML = html;
        } catch (err) {
            out.innerHTML = '';
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    // ─── Chunking ───
    const chunkConfig = {
        sentence: { param: 'sentences_per_chunk', value: 3, hint: 'sentences per chunk', show: true },
        character: { param: 'chunk_size', value: 500, hint: 'characters per chunk (overlap 10%)', show: true },
        word: { param: 'words_per_chunk', value: 100, hint: 'words per chunk (overlap 10%)', show: true },
        paragraph: { param: null, value: null, hint: '', show: false },
    };

    function onChunkMethodChange() {
        const cfg = chunkConfig[$('chunkMethodSelect').value];
        $('chunkSizeGroup').classList.toggle('hidden', !cfg.show);
        if (cfg.show) {
            $('chunkSizeInput').value = cfg.value;
            $('chunkSizeHint').textContent = cfg.hint;
        }
    }

    async function runChunking() {
        const text = $('chunkTextInput').value;
        if (!text.trim()) { toast('Paste some text to chunk.', 'error'); return; }
        const method = $('chunkMethodSelect').value;
        const cfg = chunkConfig[method];
        const body = { text, method };
        if (cfg.param) {
            const size = parseInt($('chunkSizeInput').value, 10) || cfg.value;
            body[cfg.param] = size;
            if (method === 'character') body.overlap = Math.floor(size * 0.1);
            if (method === 'word') body.overlap_words = Math.floor(size * 0.1);
        }

        const btn = $('chunkBtn');
        setLoading(btn, true, 'Chunking...');
        try {
            const data = await api('/api/chunk', { method: 'POST', body });
            const s = data.stats || {};
            $('chunkStatsCard').classList.remove('hidden');
            const stats = [
                ['Chunks', s.total_chunks || 0],
                ['Total chars', s.total_characters || 0],
                ['Avg size', s.avg_chunk_size || 0],
                ['Min size', s.min_chunk_size || 0],
                ['Max size', s.max_chunk_size || 0],
            ];
            $('chunkStats').innerHTML = stats.map(([label, val]) =>
                `<div class="stat-item"><div class="stat-value">${val}</div><div class="stat-label">${label}</div></div>`).join('');

            const chunks = data.chunks || [];
            $('chunksDisplay').innerHTML = chunks.length
                ? chunks.map((c, i) => `<div class="chunk-card">
                    <div class="chunk-header">
                        <span class="chunk-index">${i + 1}</span>
                        <span class="chunk-label">${escapeHtml(c.id)}</span>
                        <span class="chunk-size">${c.char_count} chars</span>
                    </div>
                    <div class="chunk-text">${escapeHtml(c.text)}</div>
                </div>`).join('')
                : emptyState('No chunks produced', 'Paragraph mode skips fragments under 20 characters');
        } catch (err) {
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    // ─── Visualization ───
    const PALETTE = ['#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa', '#a78bfa', '#f87171', '#2dd4bf', '#fb923c', '#c084fc'];

    function drawScatter(points) {
        const canvas = $('vizCanvas');
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const cssW = canvas.parentElement.clientWidth || 700;
        const cssH = 450;
        canvas.style.width = cssW + 'px';
        canvas.style.height = cssH + 'px';
        canvas.width = cssW * dpr;
        canvas.height = cssH * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, cssW, cssH);

        const pad = 50;
        const xs = points.map((p) => p.x);
        const ys = points.map((p) => p.y);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const rangeX = maxX - minX || 1;
        const rangeY = maxY - minY || 1;
        const sx = (x) => pad + ((x - minX) / rangeX) * (cssW - 2 * pad);
        const sy = (y) => cssH - pad - ((y - minY) / rangeY) * (cssH - 2 * pad);

        // grid
        ctx.strokeStyle = 'rgba(255,255,255,0.06)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 8; i++) {
            const gx = pad + (i / 8) * (cssW - 2 * pad);
            const gy = pad + (i / 8) * (cssH - 2 * pad);
            ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, cssH - pad); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(cssW - pad, gy); ctx.stroke();
        }
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText('PC1 →', cssW - pad - 30, cssH - pad + 20);
        ctx.save();
        ctx.translate(pad - 22, pad + 30);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('PC2 →', 0, 0);
        ctx.restore();

        // points + labels
        points.forEach((p, i) => {
            const x = sx(p.x), y = sy(p.y);
            const color = PALETTE[i % PALETTE.length];
            const grad = ctx.createRadialGradient(x, y, 0, x, y, 18);
            grad.addColorStop(0, color + '66');
            grad.addColorStop(1, color + '00');
            ctx.fillStyle = grad;
            ctx.beginPath(); ctx.arc(x, y, 18, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = color;
            ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();

            const label = p.text.length > 32 ? p.text.slice(0, 32) + '…' : p.text;
            ctx.font = '12px Inter, sans-serif';
            const w = ctx.measureText(label).width;
            let lx = x + 10;
            if (lx + w > cssW - 6) lx = x - 10 - w;
            ctx.fillStyle = 'rgba(15,17,26,0.8)';
            ctx.fillRect(lx - 4, y - 20, w + 8, 18);
            ctx.fillStyle = '#e2e8f0';
            ctx.fillText(label, lx, y - 7);
        });
    }

    function renderMatrix(texts, matrix) {
        const short = (t) => (t.length > 18 ? t.slice(0, 18) + '…' : t);
        const color = (v) => {
            const t = Math.max(0, Math.min(1, v));
            return `rgba(129, 140, 248, ${0.08 + t * 0.72})`;
        };
        let html = '<table class="sim-table"><thead><tr><th></th>';
        html += texts.map((t, i) => `<th title="${escapeHtml(t)}">${i + 1}. ${escapeHtml(short(t))}</th>`).join('');
        html += '</tr></thead><tbody>';
        matrix.forEach((row, i) => {
            html += `<tr><th title="${escapeHtml(texts[i])}">${i + 1}. ${escapeHtml(short(texts[i]))}</th>`;
            html += row.map((v) => `<td style="background:${color(v)}">${v.toFixed(3)}</td>`).join('');
            html += '</tr>';
        });
        html += '</tbody></table>';
        $('simMatrix').innerHTML = html;
    }

    let lastPoints = null;

    async function runVisualize() {
        const texts = $('vizTextsInput').value.split('\n').map((t) => t.trim()).filter(Boolean);
        if (texts.length < 2) { toast('Enter at least 2 texts (one per line).', 'error'); return; }
        const btn = $('visualizeBtn');
        setLoading(btn, true, 'Embedding...');
        try {
            const data = await api('/api/embeddings/visualize', { method: 'POST', body: { texts } });
            $('vizCard').classList.remove('hidden');
            $('simMatrixCard').classList.remove('hidden');
            lastPoints = data.points;
            drawScatter(data.points);
            renderMatrix(data.points.map((p) => p.text), data.similarity_matrix);
        } catch (err) {
            toast(err.message, 'error');
        } finally {
            setLoading(btn, false);
        }
    }

    // ─── Model Info ───
    async function loadModelInfo() {
        try {
            const info = await api('/api/embeddings/info');
            $('dimBadge').textContent = `${info.dimension}d`;
        } catch (_) { /* non-critical */ }
    }

    // ─── Event Wiring ───
    function bindEvents() {
        document.querySelectorAll('.nav-item').forEach((btn) =>
            btn.addEventListener('click', () => switchTab(btn.dataset.tab)));

        $('mobileMenuBtn').addEventListener('click', () => $('sidebar').classList.toggle('mobile-open'));

        // Collections
        $('createCollectionBtn').addEventListener('click', () => {
            $('createCollectionForm').classList.toggle('hidden');
            $('collectionNameInput').focus();
        });
        $('cancelCreateCollection').addEventListener('click', () => $('createCollectionForm').classList.add('hidden'));
        $('submitCreateCollection').addEventListener('click', createCollection);
        $('collectionNameInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') createCollection(); });

        $('collectionsGrid').addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            const card = e.target.closest('.collection-card');
            
            if (btn) {
                const name = btn.dataset.name;
                if (btn.dataset.action === 'delete') deleteCollection(name);
                if (btn.dataset.action === 'view') {
                    $('docCollectionSelect').value = name;
                    state.activeDocCollection = name;
                    $('addDocumentBtn').disabled = false;
                    switchTab('documents');
                    loadDocuments();
                }
                if (btn.dataset.action === 'search') {
                    $('searchCollectionSelect').value = name;
                    switchTab('search');
                    $('searchQueryInput').focus();
                }
                return;
            }
            
            // Allow clicking the card itself to view documents
            if (card) {
                const name = card.dataset.name;
                if (name) {
                    $('docCollectionSelect').value = name;
                    state.activeDocCollection = name;
                    $('addDocumentBtn').disabled = false;
                    switchTab('documents');
                    loadDocuments();
                }
            }
        });

        // Documents
        $('docCollectionSelect').addEventListener('change', (e) => {
            state.activeDocCollection = e.target.value;
            $('addDocumentBtn').disabled = !e.target.value;
            $('addDocumentForm').classList.add('hidden');
            loadDocuments();
        });
        $('addDocumentBtn').addEventListener('click', () => {
            $('addDocumentForm').classList.toggle('hidden');
            $('docTextInput').focus();
        });
        $('cancelAddDoc').addEventListener('click', () => $('addDocumentForm').classList.add('hidden'));
        $('submitAddDoc').addEventListener('click', insertDocument);
        $('documentsList').addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;
            if (btn.dataset.action === 'edit') openEditModal(btn.dataset.id);
            if (btn.dataset.action === 'delete-doc') deleteDocument(btn.dataset.id);
        });

        // Modal
        $('closeEditModal').addEventListener('click', closeEditModal);
        $('cancelEdit').addEventListener('click', closeEditModal);
        $('submitEdit').addEventListener('click', saveEdit);
        $('editModal').addEventListener('click', (e) => { if (e.target.id === 'editModal') closeEditModal(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeEditModal(); });

        // Search
        $('searchBtn').addEventListener('click', runSearch);
        $('searchQueryInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runSearch();
        });

        // Chunking
        $('chunkMethodSelect').addEventListener('change', onChunkMethodChange);
        $('chunkBtn').addEventListener('click', runChunking);

        // Visualize
        $('visualizeBtn').addEventListener('click', runVisualize);
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => { if (lastPoints) drawScatter(lastPoints); }, 150);
        });
    }

    function init() {
        bindEvents();
        onChunkMethodChange();
        loadCollections();
        loadModelInfo();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
