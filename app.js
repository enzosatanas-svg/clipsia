/**
 * ClipAI Generator — Frontend Application Logic (ES6)
 * Handles form submission, real-time polling, and dynamic DOM rendering.
 */

// Global Configuration
const CONFIG = {
    DEFAULT_API_URL: 'http://localhost:8000',
    POLL_INTERVAL_MS: 2000,
    MAX_RETRIES: 3,
};

// State Store
let state = {
    apiUrl: localStorage.getItem('clipai_api_url') || CONFIG.DEFAULT_API_URL,
    activeJobId: null,
    pollTimer: null,
    backendOnline: false,
    libraryClips: [],
};

// DOM Elements
const DOM = {
    // Nav
    backendStatusPill: document.getElementById('backendStatusPill'),
    backendStatusText: document.getElementById('backendStatusText'),
    btnOpenConfig: document.getElementById('btnOpenConfig'),
    btnNavLibrary: document.getElementById('btnNavLibrary'),
    refreshLibraryBtn: document.getElementById('refresh-library-btn'),
    libraryCountBadge: document.getElementById('libraryCountBadge'),
    // Form
    clipForm: document.getElementById('clipForm'),
    ytUrl: document.getElementById('ytUrl'),
    btnClearUrl: document.getElementById('btnClearUrl'),
    maxClips: document.getElementById('maxClips'),
    subtitleStyle: document.getElementById('subtitleStyle'),
    layoutMode: document.getElementById('layoutMode'),
    btnSubmit: document.getElementById('btnSubmit'),
    btnSubmitText: document.getElementById('btnSubmitText'),
    // Progress
    progressSection: document.getElementById('progressSection'),
    progressTitle: document.getElementById('progressTitle'),
    progressBar: document.getElementById('progressBar'),
    progressPercent: document.getElementById('progressPercent'),
    progressMessage: document.getElementById('progressMessage'),
    step1: document.getElementById('step1'),
    step2: document.getElementById('step2'),
    step3: document.getElementById('step3'),
    step4: document.getElementById('step4'),
    // Error
    errorSection: document.getElementById('errorSection'),
    errorMessageText: document.getElementById('errorMessageText'),
    btnRetry: document.getElementById('btnRetry'),
    // Results & Library
    resultsSection: document.getElementById('resultsSection'),
    resultsTitle: document.getElementById('resultsTitle'),
    resultsSubtitle: document.getElementById('resultsSubtitle'),
    clipsGallery: document.getElementById('clipsGallery'),
    clipsGrid: document.getElementById('clips-grid'),
    btnNewVideo: document.getElementById('btnNewVideo'),
    btnBannerRefresh: document.getElementById('btnBannerRefresh'),
    librarySearchInput: document.getElementById('librarySearchInput'),
    libraryFilteredCount: document.getElementById('libraryFilteredCount'),
    // Modal
    configModal: document.getElementById('configModal'),
    apiUrlInput: document.getElementById('apiUrlInput'),
    btnCloseModal: document.getElementById('btnCloseModal'),
    btnSaveConfig: document.getElementById('btnSaveConfig'),
    // Toast
    toast: document.getElementById('toast'),
    toastMsg: document.getElementById('toastMsg'),
};

// =============================================================================
// Initialization
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    initEventListeners();
    checkBackendHealth();
    // Poll backend health every 15s
    setInterval(checkBackendHealth, 15000);
    // Cargar biblioteca de clips previamente generados
    setTimeout(loadLibrary, 800);
});

function initSettings() {
    DOM.apiUrlInput.value = state.apiUrl;
}

function initEventListeners() {
    // Form submission
    DOM.clipForm.addEventListener('submit', handleFormSubmit);

    // Clear URL input
    DOM.btnClearUrl.addEventListener('click', () => {
        DOM.ytUrl.value = '';
        DOM.ytUrl.focus();
    });

    // Reset for new video
    DOM.btnNewVideo.addEventListener('click', () => {
        resetAppUI();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        DOM.ytUrl.focus();
    });

    // Retry on error
    DOM.btnRetry.addEventListener('click', () => {
        DOM.errorSection.classList.add('hidden');
        DOM.clipForm.dispatchEvent(new Event('submit'));
    });

    // Settings Modal
    DOM.btnOpenConfig.addEventListener('click', () => {
        DOM.apiUrlInput.value = state.apiUrl;
        DOM.configModal.classList.remove('hidden');
    });

    DOM.btnCloseModal.addEventListener('click', () => {
        DOM.configModal.classList.add('hidden');
    });

    DOM.btnSaveConfig.addEventListener('click', () => {
        const inputUrl = DOM.apiUrlInput.value.trim().replace(/\/+$/, '');
        if (inputUrl) {
            state.apiUrl = inputUrl;
            localStorage.setItem('clipai_api_url', inputUrl);
            showToast('✅ URL del Backend guardada');
            DOM.configModal.classList.add('hidden');
            checkBackendHealth();
        }
    });

    // Close modal on click outside
    DOM.configModal.addEventListener('click', (e) => {
        if (e.target === DOM.configModal) {
            DOM.configModal.classList.add('hidden');
        }
    });

    // Real-time Search filter for library clips
    if (DOM.librarySearchInput) {
        DOM.librarySearchInput.addEventListener('input', renderFilteredClips);
    }

    // Refresh library handlers
    const triggerRefresh = (e) => {
        if (e) e.preventDefault();
        showToast('🔄 Actualizando biblioteca...');
        loadLibrary(true);
    };
    if (DOM.refreshLibraryBtn) {
        DOM.refreshLibraryBtn.addEventListener('click', triggerRefresh);
    }
    if (DOM.btnBannerRefresh) {
        DOM.btnBannerRefresh.addEventListener('click', triggerRefresh);
    }

    // Nav Library button: scroll to library
    if (DOM.btnNavLibrary) {
        DOM.btnNavLibrary.addEventListener('click', (e) => {
            e.preventDefault();
            DOM.resultsSection.classList.remove('hidden');
            loadLibrary(true);
            DOM.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
}

// =============================================================================
// Backend Health Checker
// =============================================================================
async function checkBackendHealth() {
    try {
        const response = await fetch(`${state.apiUrl}/health`, { method: 'GET', mode: 'cors' });
        if (response.ok) {
            setBackendStatus(true, 'Backend Activo');
            // Cargar biblioteca automáticamente al conectar
            if (!state.libraryClips || state.libraryClips.length === 0) {
                loadLibrary();
            }
        } else {
            setBackendStatus(false, 'Backend Error (' + response.status + ')');
        }
    } catch (err) {
        setBackendStatus(false, 'Backend Desconectado');
    }
}

function setBackendStatus(isOnline, text) {
    state.backendOnline = isOnline;
    DOM.backendStatusText.textContent = text;
    DOM.backendStatusPill.className = 'status-pill ' + (isOnline ? 'status-online' : 'status-offline');
}

// =============================================================================
// Generation Pipeline Trigger
// =============================================================================
async function handleFormSubmit(e) {
    e.preventDefault();

    const url = DOM.ytUrl.value.trim();
    if (!url) {
        showToast('⚠️ Ingresa una URL válida de YouTube');
        DOM.ytUrl.focus();
        return;
    }

    // Prepare Payload
    const payload = {
        youtube_url: url,
        max_clips: parseInt(DOM.maxClips.value, 10) || 3,
        subtitle_style: DOM.subtitleStyle.value || 'alex_hormozi',
        layout: DOM.layoutMode.value || 'autoframing',
        aspect_ratio: '9:16',
        burn_subtitles: true,
    };

    // UI Updates
    setLoadingState(true);
    DOM.errorSection.classList.add('hidden');
    DOM.resultsSection.classList.add('hidden');
    DOM.progressSection.classList.remove('hidden');
    updateProgressUI(5, 'Conectando con el servidor e iniciando tarea...', 'queued');

    try {
        // Enviar POST a /api/process-video (con fallback a /api/pipeline/generate)
        let response;
        try {
            response = await fetch(`${state.apiUrl}/api/process-video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        } catch (fetchErr) {
            // Fallback directo a /api/pipeline/generate
            response = await fetch(`${state.apiUrl}/api/pipeline/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        }

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`Error ${response.status}: ${errBody}`);
        }

        const data = await response.json();
        const jobId = data.job_id || data.pipeline_id;

        if (!jobId) {
            throw new Error('El backend no devolvió un identificador de tarea válido.');
        }

        state.activeJobId = jobId;
        console.log(`[ClipAI] Job iniciado exitosamente con ID: ${jobId}`);

        // Iniciar Sondeo (Polling) cada 2 segundos
        startPolling(jobId);

    } catch (error) {
        console.error('[ClipAI] Fallo al iniciar proceso:', error);
        handlePipelineError(error.message || 'No se pudo conectar con el backend de procesamiento.');
    }
}

// =============================================================================
// Polling Mechanism (Sondeo cada 2 segundos)
// =============================================================================
function startPolling(jobId) {
    stopPolling();

    state.pollTimer = setInterval(async () => {
        try {
            // Intentar primero /api/status/{jobId}, luego fallback a /api/pipeline/status/{jobId}
            let res;
            try {
                res = await fetch(`${state.apiUrl}/api/status/${jobId}`, { method: 'GET' });
            } catch (err) {
                res = await fetch(`${state.apiUrl}/api/pipeline/status/${jobId}`, { method: 'GET' });
            }

            if (!res.ok) {
                // Silencioso reintento hasta siguiente ciclo
                return;
            }

            const data = await res.json();
            const status = (data.status || '').toLowerCase();
            const progress = data.progress || 0;
            const message = data.message || 'Procesando...';
            const step = data.current_step || status;

            // Actualizar interfaz visual
            updateProgressUI(progress, message, step);

            // Verificar si finalizó
            if (status === 'completed' || status === 'done') {
                stopPolling();
                setLoadingState(false);
                handlePipelineSuccess(data);
            } else if (status === 'error') {
                stopPolling();
                setLoadingState(false);
                handlePipelineError(data.error || 'Ocurrió un error en el servidor durante el procesamiento.');
            }

        } catch (pollErr) {
            console.warn('[ClipAI] Error en sondeo temporal:', pollErr);
        }
    }, CONFIG.POLL_INTERVAL_MS);
}

function stopPolling() {
    if (state.pollTimer) {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
    }
}

// =============================================================================
// Progress Visual Updates (4-Step Tracker)
// =============================================================================
function updateProgressUI(percent, message, step) {
    const clampedPercent = Math.min(100, Math.max(0, percent));
    DOM.progressBar.style.width = `${clampedPercent}%`;
    DOM.progressPercent.textContent = `${clampedPercent}%`;
    DOM.progressMessage.textContent = message;

    // Reset all steps
    [DOM.step1, DOM.step2, DOM.step3, DOM.step4].forEach(s => {
        s.classList.remove('active', 'completed');
    });

    // Step 1: Descarga HD (0 - 35%)
    if (clampedPercent >= 10) {
        DOM.step1.classList.add('active');
    }
    if (clampedPercent >= 35) {
        DOM.step1.classList.remove('active');
        DOM.step1.classList.add('completed');
        DOM.step2.classList.add('active');
    }

    // Step 2: Whisper IA (35 - 65%)
    if (clampedPercent >= 65) {
        DOM.step2.classList.remove('active');
        DOM.step2.classList.add('completed');
        DOM.step3.classList.add('active');
    }

    // Step 3: Detección Momentos Virales (65 - 75%)
    if (clampedPercent >= 75) {
        DOM.step3.classList.remove('active');
        DOM.step3.classList.add('completed');
        DOM.step4.classList.add('active');
    }

    // Step 4: Render 9:16 (75 - 100%)
    if (clampedPercent >= 100) {
        DOM.step4.classList.remove('active');
        DOM.step4.classList.add('completed');
    }
}

// =============================================================================
// Biblioteca: Carga de clips previos desde /api/library
// =============================================================================
async function loadLibrary(forceShow = false) {
    const refreshBtns = [DOM.refreshLibraryBtn, DOM.btnBannerRefresh].filter(Boolean);
    refreshBtns.forEach(b => b.classList.add('loading-spin'));

    try {
        const res = await fetch(`${state.apiUrl}/api/library`, { method: 'GET', mode: 'cors' });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        setBackendStatus(true, 'Backend Activo');
        const data = await res.json();
        const rawClips = data.clips || [];

        const clips = rawClips.map((c, idx) => {
            const rawTags = c.hashtags;
            let tagsArray = [];
            if (Array.isArray(rawTags)) {
                tagsArray = rawTags;
            } else if (typeof rawTags === 'string') {
                tagsArray = rawTags.trim().split(/\s+/).filter(Boolean);
            }
            if (tagsArray.length === 0) {
                tagsArray = ['#shorts', '#viral', '#reels', '#tiktok'];
            }

            const title = c.title || `Momento Viral #${idx + 1}`;
            const hook = c.hook_text || c.hook || title;
            const fileSizeMb = c.size_mb || (typeof c.size === 'number' ? c.size : 0);
            const sizeFormatted = c.size || (fileSizeMb ? `${fileSizeMb} MB` : '');

            return {
                clip_id: c.filename ? c.filename.replace('.mp4', '') : `clip_${idx + 1}`,
                title: title,
                hook: hook,
                viral_score: c.viral_score || 9.0,
                duration: parseFloat(c.duration || 0),
                file_size_mb: fileSizeMb,
                size: sizeFormatted,
                hashtags: tagsArray,
                video_url: c.url || `/clips/${c.filename}`,
                thumbnail_url: c.thumbnail_url || null,
                ai_copy: c.ai_copy || null,
                platforms: c.platforms || {},
                best_posting_times: c.best_posting_times || null,
                _library_filename: c.filename,
                niche: c.niche || 'Interés General',
                created_at: c.created_at || '',
            };
        });

        state.libraryClips = clips;

        if (DOM.libraryCountBadge) {
            DOM.libraryCountBadge.textContent = clips.length;
        }

        if (clips.length > 0 || forceShow) {
            DOM.resultsSection.classList.remove('hidden');
            if (DOM.resultsTitle) {
                DOM.resultsTitle.textContent = '📚 Biblioteca de Clips Virales 9:16';
            }
            if (DOM.resultsSubtitle) {
                DOM.resultsSubtitle.innerHTML = `
                    📚 Biblioteca guardada — <strong>${clips.length} clips en formato vertical 9:16</strong> listos para descargar y compartir.
                `;
            }
            renderFilteredClips();
        }
    } catch (err) {
        console.warn('No se pudo sincronizar la biblioteca con el backend:', err);
    } finally {
        refreshBtns.forEach(b => b.classList.remove('loading-spin'));
    }
}

function renderFilteredClips() {
    const query = (DOM.librarySearchInput?.value || '').toLowerCase().trim();
    let filtered = state.libraryClips || [];
    if (query) {
        filtered = filtered.filter(c => 
            (c.title && c.title.toLowerCase().includes(query)) ||
            (c.hook && c.hook.toLowerCase().includes(query)) ||
            (c.niche && c.niche.toLowerCase().includes(query))
        );
    }
    if (DOM.libraryFilteredCount) {
        DOM.libraryFilteredCount.textContent = `Mostrando ${filtered.length} de ${state.libraryClips.length} clips`;
    }
    renderClipsGallery(filtered, true);
}

// =============================================================================
// Pipeline Handlers: Success & Error
// =============================================================================
function handlePipelineSuccess(data) {
    DOM.progressSection.classList.add('hidden');
    DOM.resultsSection.classList.remove('hidden');

    const clips = data.clips || [];
    const videoTitle = data.video_title || 'Video';

    DOM.resultsSubtitle.innerHTML = `
        Video original: <strong>${escapeHtml(videoTitle)}</strong> — 
        Se generaron <strong>${clips.length} clips en formato vertical 9:16</strong> con subtítulos quemados.
    `;

    renderClipsGallery(clips);

    // Scroll suave hacia los resultados
    DOM.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    showToast(`🎉 ¡${clips.length} clips generados exitosamente!`);
    // Recargar la biblioteca completa para que aparezcan los nuevos clips también
    setTimeout(loadLibrary, 1500);
}

function handlePipelineError(errorMsg) {
    setLoadingState(false);
    DOM.progressSection.classList.add('hidden');
    DOM.errorSection.classList.remove('hidden');
    DOM.errorMessageText.textContent = errorMsg;
}

// =============================================================================
// Dynamic DOM Gallery Renderer
// =============================================================================
function renderClipsGallery(clips, fromLibrary = false) {
    DOM.clipsGallery.innerHTML = '';

    if (!clips || clips.length === 0) {
        DOM.clipsGallery.innerHTML = `
            <div class="card glass-card text-center" style="text-align: center; padding: 40px;">
                <p style="color: var(--text-secondary);">No se generaron clips en este lote.</p>
            </div>
        `;
        return;
    }

    clips.forEach((clip, index) => {
        const clipCard = document.createElement('div');
        clipCard.className = 'clip-card';

        const clipId = clip.clip_id || `clip_${index + 1}`;
        const title = clip.title || `Momento Viral #${index + 1}`;
        const hook = clip.hook || '¡No vas a creer lo que pasó aquí!';
        const score = clip.viral_score || 9.0;
        const duration = parseFloat(clip.duration || 30).toFixed(1);
        const fileSize = clip.file_size_mb || 0;
        const sizeText = clip.size || (fileSize > 0 ? `${fileSize} MB` : '');
        const hashtagsList = Array.isArray(clip.hashtags)
            ? clip.hashtags
            : (typeof clip.hashtags === 'string' ? clip.hashtags.trim().split(/\s+/) : ['#shorts', '#viral', '#reels', '#tiktok']);
        const hashtagsStr = hashtagsList.map(t => t.startsWith('#') ? t : `#${t}`).join(' ');

        // Video URL normalizada
        let rawVideoUrl = clip.video_url || `/output/${clipId}.mp4`;
        const fullVideoUrl = rawVideoUrl.startsWith('http') ? rawVideoUrl : `${state.apiUrl}${rawVideoUrl}`;

        // AI Copywriting optimizado para redes
        const fullCopy = clip.ai_copy || (
            `🔥 ${title}\n\n` +
            `👀 ${hook}...\n\n` +
            `👇 ¿Qué opinas al respecto? ¡Comenta abajo y sígueme para más contenido diario!\n\n` +
            `${hashtagsStr}`
        );

        const tiktokCopy = clip.platforms?.tiktok?.caption || (
            `🔥 ${hook}\n\n` +
            `¿Tú qué opinas? 👇 Déjamelo en los comentarios.\n\n` +
            `${hashtagsStr}`
        );

        const reelsCopy = clip.platforms?.instagram_reels?.caption || (
            `🔥 ${title}\n\n` +
            `👀 ${hook}\n\n` +
            `💡 Guarda este reel para repasarlo más tarde y compártelo con alguien a quien le sirva.\n\n` +
            `${hashtagsStr}`
        );

        const shortsCopy = clip.platforms?.youtube_shorts ? (
            `${clip.platforms.youtube_shorts.title}\n\n` +
            `${clip.platforms.youtube_shorts.description}`
        ) : (
            `🔥 ${title} | #Shorts\n\n` +
            `${hook}\n\n` +
            `${hashtagsStr}`
        );

        const postingTimes = clip.best_posting_times ? (
            Array.isArray(clip.best_posting_times) ? clip.best_posting_times.join(' o ') : clip.best_posting_times
        ) : '12:00 - 14:00 | 18:30 - 21:00';

        clipCard.innerHTML = `
            <!-- Left: 9:16 Video Player -->
            <div class="video-frame-9-16">
                <video controls playsinline preload="metadata" poster="${clip.thumbnail_url ? `${state.apiUrl}${clip.thumbnail_url}` : ''}">
                    <source src="${fullVideoUrl}" type="video/mp4">
                    Tu navegador no soporta reproducción de video HTML5.
                </video>
            </div>

            <!-- Right: Details & Actions -->
            <div class="clip-info">
                <div class="clip-header-meta">
                    <div class="meta-badges">
                        <span class="badge badge-gray">Clip #${index + 1}</span>
                        <span class="badge badge-gray">📱 9:16 Vertical</span>
                        ${clip.niche ? `<span class="badge badge-gray">🎯 ${escapeHtml(clip.niche)}</span>` : ''}
                        ${duration > 0 ? `<span class="badge badge-gray">⏱️ ${duration}s</span>` : ''}
                        ${sizeText ? `<span class="badge badge-gray">💾 ${escapeHtml(sizeText)}</span>` : ''}
                        ${clip.created_at ? `<span class="badge badge-gray">📅 ${escapeHtml(clip.created_at)}</span>` : ''}
                    </div>
                    <span class="badge-score">⭐ Viral Score: ${score}/10</span>
                </div>

                <h3 class="clip-title">${escapeHtml(title)}</h3>
                <p class="clip-hook"><strong>Hook:</strong> <em>"${escapeHtml(hook)}"</em></p>

                <!-- Copy Box -->
                <div class="copy-box">
                    <div class="copy-box-header">
                        <span class="copy-box-title">📝 Estrategia Viral & Copywriting Multi-Plataforma</span>
                        <div class="copy-platform-btns">
                            <button type="button" class="btn-copy-action" data-copy="${escapeAttribute(fullCopy)}" title="Copiar estrategia completa">
                                📋 Todo
                            </button>
                            <button type="button" class="btn-copy-action btn-copy-tiktok" data-copy="${escapeAttribute(tiktokCopy)}" title="Copiar copy optimizado para TikTok">
                                📱 TikTok
                            </button>
                            <button type="button" class="btn-copy-action btn-copy-reels" data-copy="${escapeAttribute(reelsCopy)}" title="Copiar caption para Instagram Reels">
                                📸 Reels
                            </button>
                            <button type="button" class="btn-copy-action btn-copy-shorts" data-copy="${escapeAttribute(shortsCopy)}" title="Copiar título y descripción para YouTube Shorts">
                                ▶️ Shorts
                            </button>
                        </div>
                    </div>
                    <div class="copy-text">${escapeHtml(fullCopy)}</div>
                    <div style="margin-top: 9px; font-size: 0.78rem; color: #94A3B8; display: flex; align-items: center; gap: 6px;">
                        <span>⏰ <strong>Horarios recomendados:</strong> ${escapeHtml(postingTimes)}</span>
                    </div>
                </div>

                <!-- Actions -->
                <div class="clip-actions">
                    <a href="${fullVideoUrl}" download="${clipId}.mp4" class="btn-primary" target="_blank" rel="noopener">
                        <span>📥</span> Descargar Clip MP4
                    </a>
                    ${clip._library_filename ? `
                    <button type="button" class="btn-delete-clip" data-filename="${escapeAttribute(clip._library_filename)}"
                        style="margin-top:10px;background:rgba(255,46,84,0.15);border:1px solid rgba(255,46,84,0.4);color:#ff2e54;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;width:100%;">
                        🗑️ Eliminar Clip
                    </button>` : ''}
                </div>
            </div>
        `;

    DOM.clipsGallery.appendChild(clipCard);
    });

    // Delegación de eventos: Copiar copy
    DOM.clipsGallery.querySelectorAll('.btn-copy-action').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const button = e.currentTarget;
            const originalLabel = button.textContent;
            const textToCopy = button.getAttribute('data-copy');
            try {
                await navigator.clipboard.writeText(textToCopy);
                showToast('📋 ¡Copiado al portapapeles!');
                button.textContent = '✅ Copiado';
                setTimeout(() => {
                    button.textContent = originalLabel;
                }, 2000);
            } catch (err) {
                fallbackCopy(textToCopy);
                showToast('📋 ¡Texto copiado!');
            }
        });
    });

    // Delegación de eventos: Eliminar clip de la biblioteca
    DOM.clipsGallery.querySelectorAll('.btn-delete-clip').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const filename = e.currentTarget.getAttribute('data-filename');
            if (!confirm(`¿Eliminar el clip "${filename}" del servidor? Esta acción no se puede deshacer.`)) return;
            try {
                const res = await fetch(`${state.apiUrl}/api/library/${encodeURIComponent(filename)}`, { method: 'DELETE' });
                if (res.ok) {
                    showToast('🗑️ Clip eliminado de la biblioteca.');
                    // Eliminar la tarjeta visualmente
                    e.currentTarget.closest('.clip-card')?.remove();
                    // Recargar biblioteca
                    setTimeout(loadLibrary, 500);
                } else {
                    showToast('⚠️ Error al eliminar el clip.');
                }
            } catch (err) {
                showToast('⚠️ Error de conexión al eliminar.');
            }
        });
    });
}


// =============================================================
// Helper Utilities
// =============================================================
function setLoadingState(isLoading) {
    DOM.btnSubmit.disabled = isLoading;
    if (isLoading) {
        DOM.btnSubmitText.textContent = 'PROCESANDO EN SEGUNDO PLANO...';
    } else {
        DOM.btnSubmitText.textContent = 'GENERAR CLIPS VIRALES 9:16';
    }
}

function resetAppUI() {
    stopPolling();
    setLoadingState(false);
    DOM.progressSection.classList.add('hidden');
    DOM.errorSection.classList.add('hidden');
    DOM.resultsSection.classList.add('hidden');
    DOM.ytUrl.value = '';
    DOM.progressBar.style.width = '0%';
    DOM.progressPercent.textContent = '0%';
}

function showToast(message) {
    DOM.toastMsg.textContent = message;
    DOM.toast.classList.remove('hidden');
    setTimeout(() => {
        DOM.toast.classList.add('hidden');
    }, 2800);
}

function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
}

function escapeHtml(string) {
    if (!string) return '';
    return String(string)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeAttribute(string) {
    if (!string) return '';
    return String(string)
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Global compatibility exports
window.loadLibrary = loadLibrary;
window.loadClipLibrary = loadLibrary;

