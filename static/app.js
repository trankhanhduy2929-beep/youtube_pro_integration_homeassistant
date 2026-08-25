const API_BASE = window.location.pathname.replace(/\/$/, '');
const SILENT_AUDIO = 'data:audio/wav;base64,UklGRnQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YVAAAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const elements = {
    appShell: $('.app-shell'),
    licenseGate: $('#licenseGate'),
    licenseGateStatus: $('#licenseGateStatus'),
    licenseGateDescription: $('#licenseGateDescription'),
    licenseGatePortalLink: $('#licenseGatePortalLink'),
    licenseGateForm: $('#licenseGateForm'),
    licenseGateKey: $('#licenseGateKey'),
    licenseGateRefresh: $('#licenseGateRefresh'),
    licenseGateInstallation: $('#licenseGateInstallation'),
    searchForm: $('#searchForm'),
    searchInput: $('#searchInput'),
    searchStatus: $('#searchStatus'),
    resultList: $('#resultList'),
    featuredSection: $('#featuredSection'),
    featuredResults: $('#featuredResults'),
    loadMore: $('#loadMore'),
    loadMoreSentinel: $('#loadMoreSentinel'),
    loadMoreLabel: $('#loadMoreLabel'),
    deviceSelect: $('#deviceSelect'),
    timerDevice: $('#timerDevice'),
    timerPlaylist: $('#timerPlaylist'),
    queueList: $('#queueList'),
    playlistTabs: $('#playlistTabs'),
    playlistToolbar: $('#playlistToolbar'),
    playlistTitle: $('#playlistTitle'),
    playlistItems: $('#playlistItems'),
    historyList: $('#historyList'),
    queueCount: $('#queueCount'),
    playlistCount: $('#playlistCount'),
    historyCount: $('#historyCount'),
    timerList: $('#timerList'),
    timerForm: $('#timerForm'),
    timerType: $('#timerType'),
    timerPlaylistWrap: $('#timerPlaylistWrap'),
    timerDurationWrap: $('#timerDurationWrap'),
    sleepStatus: $('#sleepStatus'),
    systemStatus: $('#systemStatus'),
    cookieForm: $('#cookieForm'),
    cookieFile: $('#cookieFile'),
    cookieFileName: $('#cookieFileName'),
    cookieStatus: $('#cookieStatus'),
    integrationToken: $('#integrationToken'),
    integrationTokenStatus: $('#integrationTokenStatus'),
    licensePanel: $('#licensePanel'),
    licenseStatus: $('#licenseStatus'),
    licenseDescription: $('#licenseDescription'),
    licensePortalLink: $('#licensePortalLink'),
    licenseForm: $('#licenseForm'),
    licenseKey: $('#licenseKey'),
    refreshLicense: $('#refreshLicense'),
    deactivateLicense: $('#deactivateLicense'),
    licenseInstallation: $('#licenseInstallation'),
    toggleIntegrationToken: $('#toggleIntegrationToken'),
    copyIntegrationToken: $('#copyIntegrationToken'),
    rotateIntegrationToken: $('#rotateIntegrationToken'),
    themeToggle: $('#themeToggle'),
    themeColor: $('meta[name="theme-color"]'),
    player: $('#player'),
    playerImage: $('#playerImage'),
    playerTitle: $('#playerTitle'),
    playerDevice: $('#playerDevice'),
    playerMessage: $('#playerMessage'),
    togglePlayer: $('#togglePlayer'),
    playerDetails: $('#playerDetails'),
    audio: $('#audioPlayer'),
    remoteControls: $('#remoteControls'),
    remoteSeek: $('#remoteSeek'),
    remoteVolume: $('#remoteVolume'),
    remoteProgress: $('#remoteProgress'),
    remoteElapsed: $('#remoteElapsed'),
    remoteDuration: $('#remoteDuration'),
    remoteProgressHint: $('#remoteProgressHint'),
    shuffleToggle: $('#shuffleToggle'),
    repeatToggle: $('#repeatToggle'),
    detailsDialog: $('#detailsDialog'),
    detailsTitle: $('#detailsTitle'),
    detailsImage: $('#detailsImage'),
    detailsChannel: $('#detailsChannel'),
    detailsStatus: $('#detailsStatus'),
    detailsDuration: $('#detailsDuration'),
    detailsViews: $('#detailsViews'),
    detailsLikes: $('#detailsLikes'),
    detailsDate: $('#detailsDate'),
    detailsDescription: $('#detailsDescription'),
    detailsOpenVideo: $('#detailsOpenVideo'),
    detailsPlay: $('#detailsPlay'),
    toast: $('#toast')
};

const state = {
    results: [],
    offset: 0,
    query: '',
    devices: [],
    device: localStorage.getItem('youtubeProDevice') || 'browser',
    queue: [],
    playlists: {},
    history: [],
    timers: [],
    current: null,
    token: null,
    selectedPlaylist: null,
    resolveId: 0,
    playingDevice: null,
    loadingUrl: null,
    playingUrl: null,
    hasMore: true,
    prefetched: new Map(),
    remoteChains: new Map(),
    playbackLists: new Map(),
    playbackContext: null,
    detailsCache: new Map(),
    detailsTrack: null,
    detailsContext: null,
    detailsRequestId: 0,
    audioUnlocked: false,
    audioPriming: false,
    remotePollHandle: null,
    remotePollEntity: null,
    remoteStateBusy: false,
    remoteStateRequest: 0,
    remoteSeeking: false,
    remoteSeekRequest: 0,
    remotePosition: 0,
    remoteDuration: 0,
    remoteCanSeek: false,
    remoteState: 'idle',
    remoteSyncedAt: 0,
    remoteStartedAt: 0,
    mediaSessionUpdatedAt: 0,
    playbackSession: null,
    repeatMode: localStorage.getItem('youtubeProRepeatMode') || 'off',
    shuffle: localStorage.getItem('youtubeProShuffle') === '1',
    eventSource: null,
    playerCollapsed: localStorage.getItem('youtubeProPlayerCollapsed') == null
        ? window.matchMedia('(max-width: 820px)').matches
        : localStorage.getItem('youtubeProPlayerCollapsed') === '1',
    sleepHandle: null,
    lastSleepTrigger: localStorage.getItem('youtubeProLastSleepTrigger') || '',
    licensedRuntime: false,
    sleepPollInterval: null,
    progressInterval: null,
    licensePollInterval: null
};

async function api(path, options = {}) {
    const response = await fetch(API_BASE + path, options);
    let data = null;
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok || data?.success === false) {
        if (response.status === 402 && data?.license) renderLicense(data.license);
        const error = new Error(data?.error || `HTTP ${response.status}`);
        error.status = response.status;
        error.payload = data;
        throw error;
    }
    return data;
}

function toast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => elements.toast.classList.remove('show'), 2200);
}

function setMessage(message) {
    elements.playerMessage.textContent = message;
}

function applyTheme(theme, persist = true) {
    const next = theme === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;
    elements.themeColor.content = next === 'light' ? '#f6f6f6' : '#080808';
    elements.themeToggle.textContent = next === 'light' ? '☾' : '☀';
    elements.themeToggle.title = next === 'light' ? 'Bật giao diện tối' : 'Bật giao diện sáng';
    elements.themeToggle.setAttribute('aria-label', elements.themeToggle.title);
    elements.themeToggle.setAttribute('aria-pressed', String(next === 'light'));
    if (persist) localStorage.setItem('youtubeProTheme', next);
}

function updateMediaSessionMetadata(track = state.current) {
    if (!('mediaSession' in navigator) || typeof MediaMetadata === 'undefined' || !track) return;
    const artwork = safeImage(track.thumbnail);
    navigator.mediaSession.metadata = new MediaMetadata({
        title: track.title || 'YouTube Pro',
        artist: track.channel || 'YouTube',
        album: state.playingDevice === 'browser' ? 'Điện thoại này' : 'YouTube Pro',
        artwork: artwork ? [{ src: artwork }] : []
    });
}

function setMediaSessionPlayback(playbackState) {
    if (!('mediaSession' in navigator)) return;
    try { navigator.mediaSession.playbackState = playbackState; } catch (_) {}
}

function updateMediaSessionPosition(position, duration, playbackRate = 1, force = false) {
    if (!('mediaSession' in navigator) || typeof navigator.mediaSession.setPositionState !== 'function') return;
    const safeDuration = Number(duration || 0);
    if (!(safeDuration > 0)) return;
    const now = Date.now();
    if (!force && now - state.mediaSessionUpdatedAt < 950) return;
    const safePosition = Math.max(0, Math.min(Number(position || 0), safeDuration));
    const safeRate = Number(playbackRate) > 0 ? Number(playbackRate) : 1;
    try {
        navigator.mediaSession.setPositionState({ duration: safeDuration, playbackRate: safeRate, position: safePosition });
        state.mediaSessionUpdatedAt = now;
    } catch (_) {}
}

function mediaSessionSeekTarget(offset) {
    if (state.playingDevice === 'browser') {
        const duration = Number(elements.audio.duration || state.current?.duration || 0);
        if (!duration) return;
        elements.audio.currentTime = Math.max(0, Math.min(elements.audio.currentTime + offset, duration));
        return;
    }
    const elapsed = state.remoteState === 'playing' && state.remoteSyncedAt
        ? Math.max(0, (Date.now() - state.remoteSyncedAt) / 1000)
        : 0;
    seekRemote(Math.max(0, state.remotePosition + elapsed + offset));
}

function setupMediaSession() {
    if (!('mediaSession' in navigator)) return;
    const handlers = {
        play: () => (state.playingDevice || state.device) === 'browser'
            ? elements.audio.play().catch(() => null)
            : remoteControl('play'),
        pause: () => (state.playingDevice || state.device) === 'browser'
            ? elements.audio.pause()
            : remoteControl('pause'),
        stop: () => (state.playingDevice || state.device) === 'browser'
            ? stopBrowserPlayback()
            : remoteControl('stop'),
        previoustrack: () => playRelative(-1),
        nexttrack: () => playRelative(1),
        seekbackward: details => mediaSessionSeekTarget(-Number(details.seekOffset || 10)),
        seekforward: details => mediaSessionSeekTarget(Number(details.seekOffset || 10)),
        seekto: details => {
            const target = Number(details.seekTime || 0);
            if ((state.playingDevice || state.device) === 'browser') elements.audio.currentTime = target;
            else seekRemote(target);
        }
    };
    for (const [action, handler] of Object.entries(handlers)) {
        try { navigator.mediaSession.setActionHandler(action, handler); } catch (_) {}
    }
}

function formatDuration(seconds) {
    const value = Number(seconds || 0);
    if (!value) return '';
    const minutes = Math.floor(value / 60);
    const remain = Math.floor(value % 60);
    return `${minutes}:${remain < 10 ? '0' : ''}${remain}`;
}

function formatClock(seconds) {
    const value = Math.max(0, Number(seconds) || 0);
    const total = Math.floor(value);
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remain = total % 60;
    if (hours) return `${hours}:${minutes < 10 ? '0' : ''}${minutes}:${remain < 10 ? '0' : ''}${remain}`;
    return `${minutes}:${remain < 10 ? '0' : ''}${remain}`;
}

function formatCount(value) {
    const count = Number(value || 0);
    return count > 0 ? new Intl.NumberFormat('vi-VN').format(count) : '—';
}

function formatUploadDate(value) {
    const raw = String(value || '').replace(/\D/g, '');
    if (raw.length < 8) return '—';
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`;
}

function trackMeta(track, fallback = '') {
    const parts = [];
    if (track?.channel) parts.push(track.channel);
    const duration = formatDuration(track?.duration);
    if (duration) parts.push(duration);
    return parts.join(' · ') || fallback || 'YouTube Music';
}

function safeImage(url) {
    try {
        const parsed = new URL(String(url || ''));
        return parsed.protocol === 'https:' ? parsed.href : '';
    } catch (_) {
        return '';
    }
}

function safeYouTubeUrl(url) {
    try {
        const parsed = new URL(String(url || ''));
        const host = parsed.hostname.toLowerCase();
        return parsed.protocol === 'https:' && ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'].includes(host)
            ? parsed.href
            : '';
    } catch (_) {
        return '';
    }
}

function emptyNode(message) {
    const node = document.createElement('div');
    node.className = 'empty';
    node.textContent = message;
    return node;
}

function actionButton(label, title, handler, danger = false) {
    const button = document.createElement('button');
    button.type = 'button';
    const icons = {
        'ⓘ': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 10h2v7h-2v-7Zm0-3h2v2h-2V7Zm1-5a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8Z"/></svg>',
        '+': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z"/></svg>',
        '☆': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.9L12 3.5Zm0 4.5-1.3 2.7-3 .4 2.2 2.1-.5 3 2.6-1.4 2.6 1.4-.5-3 2.2-2.1-3-.4L12 8Z"/></svg>',
        '×': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7.4 6 4.6 4.6L16.6 6 18 7.4 13.4 12l4.6 4.6-1.4 1.4-4.6-4.6L7.4 18 6 16.6l4.6-4.6L6 7.4 7.4 6Z"/></svg>'
    };
    button.innerHTML = icons[label] || label;
    button.title = title;
    button.setAttribute('aria-label', title);
    if (danger) button.classList.add('danger');
    button.addEventListener('click', event => {
        event.stopPropagation();
        handler();
    });
    return button;
}

function trackRow(track, options = {}) {
    const row = document.createElement('article');
    row.className = 'track-row';
    row.dataset.url = track.url || '';

    const artwork = document.createElement('div');
    artwork.className = 'track-artwork';
    const image = document.createElement('img');
    image.alt = '';
    image.loading = 'lazy';
    image.src = safeImage(track.thumbnail);
    artwork.append(image);

    const main = document.createElement('button');
    main.type = 'button';
    main.className = 'track-main';
    const title = document.createElement('strong');
    title.textContent = track.title || 'Không rõ tên';
    const meta = document.createElement('span');
    meta.textContent = options.meta || trackMeta(track);
    main.append(title, meta);
    const context = options.contextKey ? { key: options.contextKey, index: options.contextIndex } : null;
    const warmTrack = () => prefetchTrack(track);
    main.addEventListener('pointerdown', warmTrack, { passive: true });
    main.addEventListener('focus', warmTrack);
    main.addEventListener('click', () => playTrack(track, context));

    const actions = document.createElement('div');
    actions.className = 'track-actions';
    if (options.details !== false) actions.append(actionButton('ⓘ', 'Xem thông tin video', () => openDetails(track, context)));
    if (options.queue !== false) actions.append(actionButton('+', 'Thêm vào hàng chờ', () => addQueue(track)));
    if (options.favorite !== false) actions.append(actionButton('☆', 'Thêm vào Yêu thích', () => addFavorite(track)));
    if (options.remove) actions.append(actionButton('×', 'Xóa', options.remove, true));

    row.append(artwork, main, actions);
    syncTrackRow(row);
    return row;
}

function albumCard(track, index) {
    const card = document.createElement('article');
    card.className = 'album-card';
    card.dataset.url = track.url || '';

    const artwork = document.createElement('div');
    artwork.className = 'album-artwork';
    const image = document.createElement('img');
    image.alt = '';
    image.loading = 'lazy';
    image.src = safeImage(track.thumbnail);
    const play = document.createElement('button');
    play.type = 'button';
    play.className = 'album-play';
    play.setAttribute('aria-label', `Phát ${track.title || 'bài hát'}`);
    play.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7V5Z"/></svg>';
    artwork.append(image, play);

    const copy = document.createElement('div');
    copy.className = 'album-copy';
    const title = document.createElement('strong');
    title.textContent = track.title || 'Không rõ tên';
    const meta = document.createElement('span');
    meta.textContent = track.channel || formatDuration(track.duration) || 'YouTube Music';
    copy.append(title, meta);

    const context = { key: 'search', index };
    const warmTrack = () => prefetchTrack(track);
    play.addEventListener('pointerdown', warmTrack, { passive: true });
    play.addEventListener('click', () => playTrack(track, context));
    artwork.addEventListener('click', event => {
        if (!event.target.closest('button')) playTrack(track, context);
    });
    artwork.addEventListener('dblclick', () => playTrack(track, context));
    card.addEventListener('contextmenu', event => {
        event.preventDefault();
        openDetails(track, context);
    });
    card.append(artwork, copy);
    syncAlbumCard(card);
    return card;
}

function syncAlbumCard(card) {
    const url = card.dataset.url;
    card.classList.toggle('is-loading', Boolean(url && url === state.loadingUrl));
    card.classList.toggle('is-playing', Boolean(url && url === state.playingUrl));
}

function renderFeaturedResults(tracks) {
    if (!elements.featuredSection || !elements.featuredResults) return;
    const featured = tracks.slice(0, 8);
    elements.featuredSection.classList.toggle('hidden', !featured.length);
    elements.featuredResults.replaceChildren(...featured.map(albumCard));
}

function syncTrackRow(row) {
    const url = row.dataset.url;
    row.classList.toggle('is-loading', Boolean(url && url === state.loadingUrl));
    row.classList.toggle('is-playing', Boolean(url && url === state.playingUrl));
    row.setAttribute('aria-busy', String(Boolean(url && url === state.loadingUrl)));
}

function updateTrackStates() {
    $$('.track-row').forEach(syncTrackRow);
    $$('.album-card').forEach(syncAlbumCard);
}

function renderTrackList(container, tracks, optionsFactory, emptyMessage, contextKey = null) {
    container.replaceChildren();
    if (contextKey) state.playbackLists.set(contextKey, tracks);
    if (!tracks.length) {
        container.append(emptyNode(emptyMessage));
        return;
    }
    tracks.forEach((track, index) => {
        const options = optionsFactory?.(track, index) || {};
        container.append(trackRow(track, { ...options, contextKey, contextIndex: index }));
    });
}

function appendTrackList(container, tracks, optionsFactory, startIndex = 0, contextKey = null, fullList = tracks) {
    if (contextKey) state.playbackLists.set(contextKey, fullList);
    tracks.forEach((track, index) => {
        const contextIndex = startIndex + index;
        const options = optionsFactory?.(track, contextIndex) || {};
        container.append(trackRow(track, { ...options, contextKey, contextIndex }));
    });
}

function selectTab(name) {
    $$('.view').forEach(view => view.classList.toggle('active', view.dataset.view === name));
    $$('.bottom-nav button').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
    if (name === 'queue') loadQueue();
    if (name === 'library') loadLibrary();
    if (name === 'home') setTimeout(maybeLoadMore, 120);
    if (name === 'timer') {
        loadSleep();
        loadTimers();
        loadStatus();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadDevices() {
    try {
        state.devices = await api('/api/entities');
    } catch (error) {
        state.devices = [];
        toast(`Không đọc được loa: ${error.message}`);
    }
    elements.deviceSelect.replaceChildren(new Option('Điện thoại này', 'browser'));
    elements.timerDevice.replaceChildren();
    state.devices.forEach(device => {
        elements.deviceSelect.add(new Option(device.name, device.entity_id));
        elements.timerDevice.add(new Option(device.name, device.entity_id));
    });
    const validDevice = state.device === 'browser' || state.devices.some(device => device.entity_id === state.device);
    state.device = validDevice ? state.device : 'browser';
    elements.deviceSelect.value = state.device;
    updatePlayerMode();
}

function updatePlayerMode() {
    const activeDevice = state.playingDevice || state.device;
    const browser = activeDevice === 'browser';
    elements.audio.classList.toggle('hidden', !browser);
    elements.remoteControls.classList.toggle('hidden', browser);
    elements.remoteProgress?.classList.toggle('hidden', browser);
    const device = state.devices.find(item => item.entity_id === activeDevice);
    elements.playerDevice.textContent = browser ? 'Điện thoại này' : (device?.name || activeDevice);
    updateMediaSessionMetadata(state.current);
    if (browser || !state.current || state.playingDevice !== activeDevice || state.loadingUrl) stopRemoteProgressPolling();
    else startRemoteProgressPolling(activeDevice);
}

function activeRemoteEntity() {
    const entityId = state.playingDevice && state.playingDevice !== 'browser'
        ? state.playingDevice
        : state.device;
    return entityId && entityId !== 'browser' ? entityId : null;
}

function resetRemoteProgress(duration = 0) {
    state.remoteStateRequest += 1;
    state.remoteStateBusy = false;
    state.remotePosition = 0;
    state.remoteDuration = Math.max(0, Number(duration) || 0);
    state.remoteCanSeek = false;
    state.remoteState = 'idle';
    state.remoteSyncedAt = 0;
    state.remoteStartedAt = Date.now();
    if (!elements.remoteSeek) return;
    elements.remoteSeek.min = '0';
    elements.remoteSeek.max = String(Math.max(1, state.remoteDuration));
    elements.remoteSeek.value = '0';
    elements.remoteSeek.disabled = true;
    elements.remoteElapsed.textContent = '0:00';
    elements.remoteDuration.textContent = state.remoteDuration ? formatClock(state.remoteDuration) : '—';
    elements.remoteProgressHint.textContent = state.remoteDuration
        ? 'Đang chờ loa báo vị trí phát...'
        : 'Loa chưa báo thời lượng';
}

function updateRemoteProgress(position, duration, keepSlider = false) {
    const nextDuration = Math.max(0, Number(duration) || state.remoteDuration || 0);
    const nextPosition = Math.max(0, Math.min(Number(position) || 0, nextDuration || Number.MAX_SAFE_INTEGER));
    state.remoteDuration = nextDuration;
    state.remotePosition = nextPosition;
    if (!elements.remoteSeek) return;
    elements.remoteSeek.max = String(Math.max(1, nextDuration || 1));
    elements.remoteSeek.disabled = nextDuration <= 0 || !state.remoteCanSeek;
    if (!keepSlider && !state.remoteSeeking) elements.remoteSeek.value = String(nextPosition);
    elements.remoteElapsed.textContent = formatClock(nextPosition);
    elements.remoteDuration.textContent = nextDuration ? formatClock(nextDuration) : '—';
    elements.remoteProgressHint.textContent = !nextDuration
        ? 'Loa chưa báo thời lượng'
        : (state.remoteCanSeek ? 'Kéo thanh để tua trên loa' : 'Loa này không hỗ trợ tua');
    updateMediaSessionPosition(nextPosition, nextDuration, state.remoteState === 'playing' ? 1 : 0, true);
}

function tickRemoteProgress() {
    if (
        state.remoteSeeking
        || state.remoteState !== 'playing'
        || !state.remoteSyncedAt
        || !activeRemoteEntity()
    ) return;
    const elapsed = Math.max(0, (Date.now() - state.remoteSyncedAt) / 1000);
    const position = state.remotePosition + elapsed;
    const limited = state.remoteDuration ? Math.min(position, state.remoteDuration) : position;
    elements.remoteElapsed.textContent = formatClock(limited);
    if (state.remoteDuration && !elements.remoteSeek.disabled) {
        elements.remoteSeek.value = String(limited);
    }
    updateMediaSessionPosition(limited, state.remoteDuration, 1);
}

function stopRemoteProgressPolling() {
    if (state.remotePollHandle) {
        clearTimeout(state.remotePollHandle);
        state.remotePollHandle = null;
    }
    state.remoteStateRequest += 1;
    state.remoteStateBusy = false;
    state.remotePollEntity = null;
    state.remoteSeeking = false;
}

function scheduleRemoteStatePoll(delay = 0) {
    if (state.remotePollHandle) clearTimeout(state.remotePollHandle);
    const entityId = state.playingDevice && state.playingDevice !== 'browser' ? state.playingDevice : null;
    if (!entityId) {
        state.remotePollHandle = null;
        return;
    }
    state.remotePollHandle = setTimeout(async () => {
        state.remotePollHandle = null;
        await pollRemoteState(entityId);
        if (state.playingDevice === entityId) {
            const interval = state.remoteState === 'playing' || state.remoteState === 'buffering' ? 1400 : 2600;
            scheduleRemoteStatePoll(interval);
        }
    }, delay);
}

async function pollRemoteState(entityId = activeRemoteEntity()) {
    if (!entityId || state.remoteStateBusy || state.playingDevice !== entityId) return;
    const requestId = ++state.remoteStateRequest;
    state.remoteStateBusy = true;
    try {
        const data = await api(`/api/state?entity_id=${encodeURIComponent(entityId)}`);
        if (requestId !== state.remoteStateRequest || state.playingDevice !== entityId) return;
        if (data.playback_session) applyPlaybackSession(data.playback_session);
        const fallbackDuration = Number(state.current?.duration || 0);
        const duration = Number(data.duration || 0) || fallbackDuration;
        const position = Number(data.position || 0);
        state.remoteState = String(data.state || 'unknown').toLowerCase();
        state.remoteCanSeek = Boolean(data.supports_seek);
        if (data.volume != null && document.activeElement !== elements.remoteVolume) {
            elements.remoteVolume.value = String(data.volume);
        }
        state.remoteSyncedAt = Date.now();
        updateRemoteProgress(position, duration);
        if (state.remoteState === 'playing') {
            setMediaSessionPlayback('playing');
            setMessage('Đang phát trên loa');
        } else if (state.remoteState === 'buffering') {
            setMediaSessionPlayback('playing');
            setMessage('Loa đang tải audio...');
        } else if (state.remoteState === 'paused') {
            setMediaSessionPlayback('paused');
            setMessage('Đang tạm dừng trên loa');
        } else if (state.remoteState === 'idle' || state.remoteState === 'off') {
            setMediaSessionPlayback('none');
            setMessage(Date.now() - state.remoteStartedAt < 5000
                ? 'Loa đang kết nối audio...'
                : 'Loa đã dừng hoặc chưa nhận audio');
        }
    } catch (_) {
        if (requestId === state.remoteStateRequest && state.playingDevice === entityId) {
            elements.remoteProgressHint.textContent = 'Chưa đọc được trạng thái loa';
        }
    } finally {
        if (requestId === state.remoteStateRequest) state.remoteStateBusy = false;
    }
}

function startRemoteProgressPolling(entityId = activeRemoteEntity()) {
    if (!entityId || entityId === 'browser') return;
    if (state.remotePollEntity === entityId && (state.remotePollHandle || state.remoteStateBusy)) return;
    stopRemoteProgressPolling();
    state.remotePollEntity = entityId;
    resetRemoteProgress(state.current?.duration || 0);
    scheduleRemoteStatePoll(320);
}

async function seekRemote(value) {
    const entityId = activeRemoteEntity();
    const position = Math.max(0, Number(value) || 0);
    if (!entityId || !state.remoteDuration || !state.remoteCanSeek) return;
    const requestId = ++state.remoteSeekRequest;
    state.remoteStateRequest += 1;
    state.remoteStateBusy = false;
    state.remoteSeeking = true;
    updateRemoteProgress(position, state.remoteDuration, true);
    try {
        await enqueueRemoteCommand(entityId, () => remoteControlRequest(entityId, 'seek', {
            seek_position: position
        }));
        if (requestId === state.remoteSeekRequest) {
            state.remoteSeeking = false;
            state.remotePosition = position;
            state.remoteSyncedAt = Date.now();
            scheduleRemoteStatePoll(120);
        }
    } catch (error) {
        if (requestId === state.remoteSeekRequest) {
            state.remoteSeeking = false;
            toast(`Không tua được trên loa: ${error.message}`);
            scheduleRemoteStatePoll(120);
        }
    }
}

function stopBrowserPlayback() {
    state.audioPriming = true;
    try { elements.audio.pause(); } catch (_) {}
    elements.audio.removeAttribute('src');
    try { elements.audio.load(); } catch (_) {}
    setMediaSessionPlayback('none');
}

function unlockBrowserAudio(device = state.device) {
    if (device !== 'browser' || state.audioUnlocked) return;
    state.audioUnlocked = true;
    state.audioPriming = true;
    elements.audio.src = SILENT_AUDIO;
    elements.audio.load();
    try {
        const pending = elements.audio.play();
        if (pending?.catch) pending.catch(() => {
            if (state.audioPriming) state.audioUnlocked = false;
        });
    } catch (_) {
        state.audioUnlocked = false;
    }
}

function enqueueRemoteCommand(entityId, command) {
    const previous = state.remoteChains.get(entityId);
    const invoke = () => {
        try { return Promise.resolve(command()); }
        catch (error) { return Promise.reject(error); }
    };
    const queued = previous ? previous.catch(() => null).then(invoke) : invoke();
    let tail = null;
    tail = queued.catch(() => null).finally(() => {
        if (state.remoteChains.get(entityId) === tail) state.remoteChains.delete(entityId);
    });
    state.remoteChains.set(entityId, tail);
    return queued;
}

function remoteControlRequest(entityId, action, extra = {}) {
    return api('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId, action, ...extra })
    });
}

function stopRemotePlayback(entityId) {
    if (!entityId || entityId === 'browser') return Promise.resolve();
    const hadPendingCommand = state.remoteChains.has(entityId);
    const immediate = remoteControlRequest(entityId, 'stop').catch(() => null);
    if (!hadPendingCommand) {
        let tail = null;
        tail = immediate.finally(() => {
            if (state.remoteChains.get(entityId) === tail) state.remoteChains.delete(entityId);
        });
        state.remoteChains.set(entityId, tail);
        return immediate;
    }
    return enqueueRemoteCommand(entityId, () => immediate.then(() => remoteControlRequest(entityId, 'stop'))).catch(() => null);
}

function stopPlaybackImmediately(device = state.playingDevice) {
    stopBrowserPlayback();
    state.playingUrl = null;
    updateTrackStates();
    if (!device || device === 'browser') return Promise.resolve();
    return stopRemotePlayback(device);
}

function setPlayerCollapsed(collapsed, persist = true) {
    state.playerCollapsed = Boolean(collapsed);
    elements.player.classList.toggle('collapsed', state.playerCollapsed);
    document.body.classList.toggle('player-collapsed', state.playerCollapsed);
    elements.togglePlayer.textContent = state.playerCollapsed ? '⌃' : '⌄';
    elements.togglePlayer.setAttribute('aria-expanded', String(!state.playerCollapsed));
    elements.togglePlayer.setAttribute('aria-label', state.playerCollapsed ? 'Mở trình phát' : 'Thu gọn trình phát');
    if (persist) localStorage.setItem('youtubeProPlayerCollapsed', state.playerCollapsed ? '1' : '0');
}

function updateSearchLoader() {
    const active = state.hasMore && state.results.length > 0;
    elements.loadMoreSentinel.classList.toggle('hidden', !active);
    elements.loadMoreSentinel.classList.toggle('loading', Boolean(search.loading));
    elements.loadMoreLabel.textContent = search.loading ? 'Đang tải thêm bài hát...' : 'Cuộn xuống để tải thêm';
    elements.loadMore.classList.toggle('hidden', Boolean(search.observer) || !active || search.loading);
}

function maybeLoadMore() {
    if (search.loading || !state.hasMore || !state.results.length || !$('#viewHome').classList.contains('active')) return;
    const top = elements.loadMoreSentinel.getBoundingClientRect().top;
    if (top <= window.innerHeight + 650) setTimeout(() => search(false), 60);
}

function setupInfiniteScroll() {
    if (!('IntersectionObserver' in window)) {
        updateSearchLoader();
        return;
    }
    search.observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) maybeLoadMore();
    }, { rootMargin: '650px 0px' });
    search.observer.observe(elements.loadMoreSentinel);
}

function rememberDetails(url, data) {
    const details = data?.details;
    if (!url || !details || !Object.keys(details).length) return;
    state.detailsCache.delete(url);
    state.detailsCache.set(url, { ...details, strategy: data.strategy, format_id: data.format_id });
    while (state.detailsCache.size > 24) state.detailsCache.delete(state.detailsCache.keys().next().value);
}

function getResolveEntry(url) {
    const entry = state.prefetched.get(url);
    if (!entry) return null;
    if (Date.now() - entry.createdAt > 30 * 60 * 1000) {
        state.prefetched.delete(url);
        return null;
    }
    state.prefetched.delete(url);
    state.prefetched.set(url, entry);
    return entry;
}

function startResolve(track) {
    if (!track?.url) return Promise.reject(new Error('Bài hát không hợp lệ'));
    const existing = getResolveEntry(track.url);
    if (existing) return existing.promise;
    const entry = { createdAt: Date.now(), promise: null };
    entry.promise = api('/api/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: track.url })
    }).then(data => {
        rememberDetails(track.url, data);
        return data;
    }).catch(error => {
        if (state.prefetched.get(track.url) === entry) state.prefetched.delete(track.url);
        throw error;
    });
    state.prefetched.set(track.url, entry);
    while (state.prefetched.size > 10) state.prefetched.delete(state.prefetched.keys().next().value);
    return entry.promise;
}

function prefetchTrack(track) {
    if (!track?.url) return Promise.resolve(null);
    return startResolve(track).catch(() => null);
}

function schedulePrefetch(track, delay = 220) {
    if (!track) return;
    setTimeout(() => prefetchTrack(track), delay);
}

function prefetchTracks(tracks, initialDelay = 100, stepDelay = 220) {
    const seen = new Set();
    tracks.filter(track => {
        if (!track?.url || seen.has(track.url)) return false;
        seen.add(track.url);
        return true;
    }).forEach((track, index) => schedulePrefetch(track, initialDelay + index * stepDelay));
}

async function resolveTrackData(track) {
    return startResolve(track);
}

async function search(reset = true) {
    if (search.loading) return;
    search.loading = true;
    let failed = false;
    const query = elements.searchInput.value.trim();
    if (reset) {
        state.offset = 0;
        state.results = [];
        state.hasMore = true;
        state.query = query;
        elements.resultList.replaceChildren(emptyNode('Đang tìm nhạc...'));
    }
    elements.searchStatus.textContent = 'Đang tải kết quả...';
    updateSearchLoader();
    try {
        const data = await api('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: state.query, offset: state.offset })
        });
        const rows = data.results || [];
        const knownUrls = new Set(state.results.map(item => item.url));
        const uniqueRows = rows.filter(item => {
            if (!item?.url || knownUrls.has(item.url)) return false;
            knownUrls.add(item.url);
            return true;
        });
        const previousCount = state.results.length;
        state.results = reset ? uniqueRows : state.results.concat(uniqueRows);
        state.offset += rows.length;
        state.hasMore = Boolean(data.has_more ?? rows.length >= 20) && rows.length > 0;
        if (reset) {
            renderTrackList(elements.resultList, state.results, null, 'Không tìm thấy bài hát', 'search');
            renderFeaturedResults(state.results);
        }
        else appendTrackList(elements.resultList, uniqueRows, null, previousCount, 'search', state.results);
        elements.searchStatus.textContent = state.hasMore ? `${state.results.length} kết quả · kéo xuống để xem thêm` : `${state.results.length} kết quả`;
        if (reset) prefetchTracks(state.results.slice(0, 3), 80, 240);
    } catch (error) {
        failed = true;
        if (reset) state.hasMore = false;
        if (reset) elements.resultList.replaceChildren(emptyNode(`Không tìm được nhạc: ${error.message}`));
        else toast(`Không tải thêm được: ${error.message}`);
        elements.searchStatus.textContent = reset ? 'Tìm kiếm thất bại' : `${state.results.length} kết quả · thử kéo lại`;
    } finally {
        search.loading = false;
        updateSearchLoader();
        if (!failed) maybeLoadMore();
    }
}

function showCurrent(track) {
    state.current = track;
    elements.player.classList.remove('hidden');
    document.body.classList.add('player-visible');
    elements.playerTitle.textContent = track.title || 'Không rõ tên';
    elements.playerImage.src = safeImage(track.thumbnail);
    const artwork = safeImage(track.thumbnail);
    document.documentElement.style.setProperty('--current-artwork', artwork ? `url("${artwork.replaceAll('"', '%22')}")` : 'none');
    updateMediaSessionMetadata(track);
    setPlayerCollapsed(state.playerCollapsed, false);
    updatePlayerMode();
}

function resolvePlaybackContext(track, context = null) {
    if (context?.key) {
        const list = state.playbackLists.get(context.key) || [];
        const direct = Number(context.index);
        const index = list[direct]?.url === track.url ? direct : list.findIndex(item => item.url === track.url);
        if (index >= 0) return { key: context.key, index };
    }
    for (const [key, list] of state.playbackLists) {
        const index = list.findIndex(item => item.url === track.url);
        if (index >= 0) return { key, index };
    }
    return null;
}

function playbackPayload(track, context = state.playbackContext) {
    const key = context?.key || 'single';
    const sourceList = context?.key ? (state.playbackLists.get(context.key) || []) : [track];
    const tracks = sourceList.length ? sourceList : [track];
    const index = Math.max(0, tracks.findIndex(item => item.url === track.url));
    return {
        tracks,
        index,
        repeat: state.repeatMode,
        shuffle: state.shuffle,
        source: key,
        source_name: key.startsWith('playlist:') ? key.slice(9) : key
    };
}

function updatePlaybackModeButtons() {
    elements.shuffleToggle.classList.toggle('active', state.shuffle);
    elements.shuffleToggle.setAttribute('aria-pressed', String(state.shuffle));
    elements.shuffleToggle.title = state.shuffle ? 'Tắt phát ngẫu nhiên' : 'Bật phát ngẫu nhiên';
    const repeatLabels = { off: 'Lặp lại: tắt', all: 'Lặp lại toàn bộ', one: 'Lặp lại một bài' };
    elements.repeatToggle.classList.toggle('active', state.repeatMode !== 'off');
    elements.repeatToggle.setAttribute('aria-pressed', String(state.repeatMode !== 'off'));
    elements.repeatToggle.textContent = state.repeatMode === 'one' ? '↻¹' : '↻';
    elements.repeatToggle.title = repeatLabels[state.repeatMode] || repeatLabels.off;
}

function applyPlaybackSession(session) {
    if (!session?.entity_id) return;
    const relevant = state.playingDevice === session.entity_id || state.device === session.entity_id;
    if (!relevant) return;
    state.playbackSession = session;
    state.repeatMode = session.repeat || 'off';
    state.shuffle = Boolean(session.shuffle);
    localStorage.setItem('youtubeProRepeatMode', state.repeatMode);
    localStorage.setItem('youtubeProShuffle', state.shuffle ? '1' : '0');
    updatePlaybackModeButtons();
    const track = session.current_track;
    const activeStates = ['resolving', 'starting', 'playing', 'paused'];
    if (track) {
        state.current = track;
        state.playingDevice = activeStates.includes(session.state) ? session.entity_id : null;
        state.playingUrl = activeStates.includes(session.state) ? track.url : null;
        state.loadingUrl = ['resolving', 'starting'].includes(session.state) ? track.url : null;
        showCurrent(track);
    }
    state.remoteState = session.state === 'starting' ? 'buffering' : session.state;
    updateRemoteProgress(session.last_position || 0, session.last_duration || track?.duration || 0);
    const messages = {
        resolving: 'Backend đang chuẩn bị bài hát...',
        starting: 'Đã gửi tới loa · đang kết nối...',
        playing: 'Đang phát trên loa',
        paused: 'Đang tạm dừng trên loa',
        completed: 'Đã phát hết danh sách',
        stopped: 'Loa đã dừng',
        error: `Lỗi playback: ${session.last_error || 'không xác định'}`
    };
    if (messages[session.state]) setMessage(messages[session.state]);
    setMediaSessionPlayback(session.state === 'playing' ? 'playing' : session.state === 'paused' ? 'paused' : 'none');
    elements.player.classList.toggle('loading', ['resolving', 'starting'].includes(session.state));
    updateTrackStates();
    updatePlayerMode();
}

function handleServerEvent(payload) {
    if (!payload || typeof payload !== 'object') return;
    if (payload.type === 'playback') applyPlaybackSession(payload.data);
    if (payload.type === 'snapshot') {
        const sessions = payload.data?.playback_sessions || {};
        const entityId = activeRemoteEntity();
        if (entityId && sessions[entityId]) applyPlaybackSession(sessions[entityId]);
    }
    if (payload.type === 'player_state' && payload.data?.entity_id === activeRemoteEntity()) {
        state.remoteState = payload.data.state || state.remoteState;
        state.remoteSyncedAt = Date.now();
        updateRemoteProgress(payload.data.position || 0, payload.data.duration || 0);
    }
}

function setupEventStream() {
    if (typeof EventSource === 'undefined') return;
    try { state.eventSource?.close(); } catch (_) {}
    const source = new EventSource(`${API_BASE}/api/events`);
    state.eventSource = source;
    source.onmessage = event => {
        try { handleServerEvent(JSON.parse(event.data)); } catch (_) {}
    };
}

async function updatePlaybackModes(nextRepeat = state.repeatMode, nextShuffle = state.shuffle) {
    const entityId = activeRemoteEntity();
    state.repeatMode = nextRepeat;
    state.shuffle = Boolean(nextShuffle);
    localStorage.setItem('youtubeProRepeatMode', state.repeatMode);
    localStorage.setItem('youtubeProShuffle', state.shuffle ? '1' : '0');
    updatePlaybackModeButtons();
    if (!entityId || !state.playbackSession) return;
    try {
        const data = await api('/api/playback/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entity_id: entityId,
                action: 'mode',
                repeat: state.repeatMode,
                shuffle: state.shuffle
            })
        });
        if (data.session) applyPlaybackSession(data.session);
    } catch (error) {
        toast(error.message);
    }
}

function relativeCandidate(step, automatic = false) {
    if (!state.current) return null;
    const context = state.playbackContext;
    let remainingInContext = 0;
    if (context?.key) {
        const list = state.playbackLists.get(context.key) || [];
        const currentIndex = list.findIndex(item => item.url === state.current.url);
        const activeIndex = currentIndex >= 0 ? currentIndex : Number(context.index);
        if (automatic && state.repeatMode === 'one') {
            return { track: list[activeIndex] || state.current, context: { key: context.key, index: activeIndex }, fromQueue: false };
        }
        let index = activeIndex + step;
        if (state.shuffle && step > 0 && list.length > 1) {
            do { index = Math.floor(Math.random() * list.length); } while (index === activeIndex);
        } else if ((index < 0 || index >= list.length) && state.repeatMode === 'all' && list.length) {
            index = index < 0 ? list.length - 1 : 0;
        }
        if (list[index]) return { track: list[index], context: { key: context.key, index }, fromQueue: false };
        remainingInContext = Math.max(0, list.length - activeIndex - 1);
    }
    if (step > 0 && context?.key !== 'queue' && state.queue.length) {
        const queueIndex = Math.max(0, step - remainingInContext - 1);
        if (state.queue[queueIndex]) {
            return { track: state.queue[queueIndex], context: null, fromQueue: true, queueIndex };
        }
    }
    return null;
}

function prefetchRelative(step) {
    const candidate = relativeCandidate(step);
    if (candidate) prefetchTrack(candidate.track);
}

function prefetchFollowingTracks() {
    const tracks = [relativeCandidate(1)?.track, relativeCandidate(2)?.track];
    prefetchTracks(tracks, 100, 260);
}

async function playTrack(track, context = null) {
    if (!track?.url) return;
    const requestId = ++state.resolveId;
    const targetDevice = state.device;
    const previousDevice = state.playingDevice;
    stopPlaybackImmediately(previousDevice);
    state.playingDevice = targetDevice;
    state.loadingUrl = track.url;
    state.playingUrl = null;
    state.playbackContext = resolvePlaybackContext(track, context);
    showCurrent(track);
    if (targetDevice !== 'browser') resetRemoteProgress(track.duration || 0);
    updateTrackStates();
    setMessage('Đang tải nhanh bài hát...');
    elements.player.classList.add('loading');
    unlockBrowserAudio(targetDevice);
    const resolvePromise = resolveTrackData(track);
    let playbackStarted = false;
    try {
        const data = await resolvePromise;
        if (requestId !== state.resolveId) return;
        state.current = data.track || track;
        state.token = data.token;
        rememberDetails(state.current.url, data);
        showCurrent(state.current);
        if (targetDevice === 'browser') {
            elements.audio.src = API_BASE + data.media_path;
            elements.audio.load();
            state.audioPriming = false;
            try {
                await elements.audio.play();
                if (requestId !== state.resolveId) return;
                state.audioUnlocked = true;
                playbackStarted = true;
                setMessage('Đang phát trên điện thoại');
            } catch (_) {
                if (requestId !== state.resolveId) return;
                setMessage('Audio đã sẵn sàng — nhấn Play');
                toast('Nhấn nút Play trong thanh phát để bắt đầu');
            }
        } else {
            const playback = playbackPayload(state.current, state.playbackContext);
            const castData = await enqueueRemoteCommand(targetDevice, () => api('/api/cast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: data.token, entity_id: targetDevice, ...playback })
            }));
            if (requestId !== state.resolveId) return;
            if (castData.session) applyPlaybackSession(castData.session);
            playbackStarted = true;
            setMessage('Đã gửi tới loa · đang kết nối...');
        }
        state.loadingUrl = null;
        state.playingUrl = playbackStarted ? state.current.url : null;
        if (!playbackStarted && state.playingDevice === targetDevice) state.playingDevice = null;
        updateTrackStates();
        updatePlayerMode();
        if (targetDevice === 'browser') {
            prefetchFollowingTracks();
            addHistory(state.current);
        }
    } catch (error) {
        if (requestId !== state.resolveId) return;
        state.loadingUrl = null;
        state.playingUrl = null;
        if (state.playingDevice === targetDevice) state.playingDevice = null;
        updateTrackStates();
        updatePlayerMode();
        setMessage(`Không phát được: ${error.message}`);
        toast(`Lỗi phát nhạc: ${error.message}`);
    } finally {
        if (requestId === state.resolveId) {
            state.loadingUrl = null;
            state.audioPriming = false;
            elements.player.classList.remove('loading');
            updateTrackStates();
        }
    }
}

async function playRelative(step, automatic = false) {
    const entityId = state.playingDevice && state.playingDevice !== 'browser' ? state.playingDevice : null;
    if (entityId && state.playbackSession) {
        try {
            const data = await api('/api/playback/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entity_id: entityId, action: step > 0 ? 'next' : 'previous' })
            });
            if (data.session) applyPlaybackSession(data.session);
        } catch (error) {
            toast(error.message);
        }
        return;
    }
    const candidate = relativeCandidate(step, automatic);
    if (!candidate) return;
    if (candidate.fromQueue) {
        state.queue.splice(0, 1);
        state.playbackLists.set('queue', state.queue);
        state.playbackLists.set('queue-fallback', [candidate.track]);
        candidate.context = { key: 'queue-fallback', index: 0 };
        api('/api/queue/0', { method: 'DELETE' }).then(loadQueue).catch(loadQueue);
    }
    await playTrack(candidate.track, candidate.context);
}

function showDetailsDialog() {
    if (elements.detailsDialog.open) return;
    if (typeof elements.detailsDialog.showModal === 'function') elements.detailsDialog.showModal();
    else elements.detailsDialog.setAttribute('open', '');
}

function closeDetailsDialog() {
    state.detailsRequestId += 1;
    if (typeof elements.detailsDialog.close === 'function') elements.detailsDialog.close();
    else elements.detailsDialog.removeAttribute('open');
}

function renderDetails(track, details = {}, loading = false, error = '') {
    const merged = { ...track, ...details };
    elements.detailsTitle.textContent = merged.title || 'Không rõ tên';
    elements.detailsImage.src = safeImage(merged.thumbnail);
    elements.detailsChannel.textContent = merged.channel || 'Chưa rõ kênh';
    elements.detailsDuration.textContent = formatDuration(merged.duration) || '—';
    elements.detailsViews.textContent = formatCount(merged.view_count);
    elements.detailsLikes.textContent = formatCount(merged.like_count);
    elements.detailsDate.textContent = formatUploadDate(merged.upload_date);
    elements.detailsDescription.textContent = loading
        ? 'Đang tải mô tả...'
        : (merged.description || 'Video này không có mô tả.');
    const source = merged.strategy ? ` · ${merged.strategy}${merged.format_id ? ` / ${merged.format_id}` : ''}` : '';
    elements.detailsStatus.textContent = error || (loading ? 'Đang lấy thông tin từ YouTube...' : `Đã tải thông tin${source}`);
    const videoUrl = safeYouTubeUrl(merged.url || track.url);
    elements.detailsOpenVideo.classList.toggle('hidden', !videoUrl);
    if (videoUrl) elements.detailsOpenVideo.href = videoUrl;
    else elements.detailsOpenVideo.removeAttribute('href');
}

async function openDetails(track, context = null) {
    if (!track?.url) return;
    const requestId = ++state.detailsRequestId;
    state.detailsTrack = track;
    state.detailsContext = context || resolvePlaybackContext(track);
    const cached = state.detailsCache.get(track.url);
    renderDetails(track, cached || {}, !cached);
    showDetailsDialog();
    if (cached) return;
    try {
        const pending = getResolveEntry(track.url);
        const data = pending
            ? await pending.promise
            : await api('/api/details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: track.url })
            });
        if (requestId !== state.detailsRequestId || !elements.detailsDialog.open) return;
        rememberDetails(track.url, data);
        const details = state.detailsCache.get(track.url) || data.details || {};
        state.detailsTrack = { ...track, ...(data.track || {}) };
        renderDetails(state.detailsTrack, details);
        if (!pending) schedulePrefetch(state.detailsTrack, 0);
    } catch (error) {
        if (requestId !== state.detailsRequestId || !elements.detailsDialog.open) return;
        renderDetails(track, {}, false, `Không tải được chi tiết: ${error.message}`);
    }
}

async function addQueue(track) {
    try {
        await api('/api/queue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(track)
        });
        toast('Đã thêm vào hàng chờ');
        await loadQueue();
    } catch (error) { toast(error.message); }
}

async function loadQueue() {
    try { state.queue = await api('/api/queue'); } catch (_) { state.queue = []; }
    if (elements.queueCount) elements.queueCount.textContent = String(state.queue.length);
    renderTrackList(
        elements.queueList,
        state.queue,
        (_, index) => ({ favorite: false, queue: false, remove: () => removeQueue(index), meta: `Vị trí ${index + 1}` }),
        'Hàng chờ đang trống',
        'queue'
    );
}

async function removeQueue(index, refresh = true) {
    await api(`/api/queue/${index}`, { method: 'DELETE' });
    if (refresh) await loadQueue();
    else state.queue.splice(index, 1);
}

async function clearQueue() {
    await api('/api/queue', { method: 'DELETE' });
    await loadQueue();
}

async function loadLibrary() {
    await Promise.all([loadPlaylists(), loadHistory()]);
}

async function loadPlaylists() {
    try { state.playlists = await api('/api/playlists'); } catch (_) { state.playlists = {}; }
    const names = Object.keys(state.playlists);
    if (elements.playlistCount) elements.playlistCount.textContent = String(names.length);
    if (!state.selectedPlaylist || !state.playlists[state.selectedPlaylist]) {
        state.selectedPlaylist = names[0] || null;
    }
    elements.playlistTabs.replaceChildren();
    names.forEach(name => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `chip${name === state.selectedPlaylist ? ' active' : ''}`;
        button.textContent = name;
        button.addEventListener('click', () => {
            state.selectedPlaylist = name;
            renderPlaylists();
        });
        elements.playlistTabs.append(button);
    });
    renderPlaylists();
    refreshPlaylistSelect();
}

function renderPlaylists() {
    const name = state.selectedPlaylist;
    elements.playlistToolbar.classList.toggle('hidden', !name);
    elements.playlistTitle.textContent = name || '';
    const tracks = name ? state.playlists[name] || [] : [];
    renderTrackList(
        elements.playlistItems,
        tracks,
        (_, index) => ({ queue: true, favorite: false, remove: () => removePlaylistItem(name, index) }),
        name ? 'Playlist đang trống' : 'Chưa có playlist',
        name ? `playlist:${name}` : null
    );
    $$('.chip').forEach(button => button.classList.toggle('active', button.textContent === name));
}

function refreshPlaylistSelect() {
    elements.timerPlaylist.replaceChildren();
    Object.keys(state.playlists).forEach(name => elements.timerPlaylist.add(new Option(name, name)));
}

async function createPlaylist() {
    const name = prompt('Tên playlist mới');
    if (!name) return;
    try {
        await api('/api/playlists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        state.selectedPlaylist = name.trim();
        await loadPlaylists();
    } catch (error) { toast(error.message); }
}

async function deletePlaylist() {
    const name = state.selectedPlaylist;
    if (!name || !confirm(`Xóa playlist “${name}”?`)) return;
    await api(`/api/playlists/${encodeURIComponent(name)}`, { method: 'DELETE' });
    state.selectedPlaylist = null;
    await loadPlaylists();
}

async function removePlaylistItem(name, index) {
    await api(`/api/playlists/${encodeURIComponent(name)}/items/${index}`, { method: 'DELETE' });
    await loadPlaylists();
}

async function ensureFavorites() {
    if (!state.playlists['Yêu thích']) {
        await api('/api/playlists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Yêu thích' })
        });
    }
}

async function addFavorite(track) {
    try {
        await ensureFavorites();
        await api(`/api/playlists/${encodeURIComponent('Yêu thích')}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(track)
        });
        toast('Đã thêm vào Yêu thích');
        await loadPlaylists();
    } catch (error) { toast(error.message); }
}

async function addHistory(track) {
    try {
        await api('/api/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(track)
        });
        await loadHistory();
    } catch (_) {}
}

async function loadHistory() {
    try { state.history = await api('/api/history'); } catch (_) { state.history = []; }
    if (elements.historyCount) elements.historyCount.textContent = String(state.history.length);
    const rows = state.history.slice().reverse().slice(0, 20);
    renderTrackList(
        elements.historyList,
        rows,
        track => ({ meta: track.played_at || 'Đã nghe', queue: true, favorite: true }),
        'Chưa có lịch sử nghe',
        'history'
    );
}

async function clearHistory() {
    await api('/api/history', { method: 'DELETE' });
    await loadHistory();
}

function stopBrowserForSleep() {
    state.resolveId += 1;
    state.playingDevice = null;
    state.loadingUrl = null;
    state.playingUrl = null;
    stopBrowserPlayback();
    elements.player.classList.remove('loading');
    updateTrackStates();
    updatePlayerMode();
    setMessage('Đã dừng theo sleep timer');
    toast('Đã dừng nhạc theo hẹn giờ');
}

function syncSleepTimer(data) {
    clearTimeout(state.sleepHandle);
    state.sleepHandle = null;
    if (data.enabled && data.end_at) {
        const delay = new Date(data.end_at).getTime() - Date.now();
        if (data.entity_id === 'browser' && delay > 0) {
            state.sleepHandle = setTimeout(stopBrowserForSleep, delay);
        }
        const seconds = Number(data.remaining || Math.max(0, delay / 1000));
        elements.sleepStatus.textContent = `Còn ${Math.floor(seconds / 60)} phút`;
        return;
    }
    elements.sleepStatus.textContent = 'Chưa bật';
    if (data.entity_id === 'browser' && data.last_triggered_at && data.last_triggered_at !== state.lastSleepTrigger) {
        const age = Date.now() - new Date(data.last_triggered_at).getTime();
        if (age >= 0 && age < 120000) stopBrowserForSleep();
        state.lastSleepTrigger = data.last_triggered_at;
        localStorage.setItem('youtubeProLastSleepTrigger', state.lastSleepTrigger);
    }
}

async function loadSleep() {
    try { syncSleepTimer(await api('/api/sleep')); } catch (_) {}
}

async function setSleep(minutes) {
    try {
        const data = await api('/api/sleep', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ minutes, entity_id: state.device })
        });
        syncSleepTimer(data.sleep);
        toast(`Đã hẹn tắt sau ${minutes} phút`);
    } catch (error) { toast(error.message); }
}

async function cancelSleep() {
    await api('/api/sleep', { method: 'DELETE' });
    await loadSleep();
}

function toggleTimerFields() {
    const stop = elements.timerType.value === 'stop';
    elements.timerPlaylistWrap.classList.toggle('hidden', stop);
    elements.timerDurationWrap.classList.toggle('hidden', stop);
}

async function loadTimers() {
    try { state.timers = await api('/api/timers'); } catch (_) { state.timers = []; }
    elements.timerList.replaceChildren();
    if (!state.timers.length) {
        elements.timerList.append(emptyNode('Chưa có lịch phát'));
        return;
    }
    const dayNames = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
    state.timers.forEach(timer => {
        const card = document.createElement('article');
        card.className = 'timer-card';
        const title = document.createElement('strong');
        title.textContent = `${timer.time} · ${timer.type === 'play' ? 'Phát' : 'Dừng'}`;
        const meta = document.createElement('p');
        const days = timer.days?.length ? timer.days.map(day => dayNames[day]).join(', ') : 'Mỗi ngày';
        meta.textContent = timer.type === 'play' ? `${timer.playlist_name} · ${days}` : days;
        const remove = actionButton('Xóa', 'Xóa lịch', async () => {
            await api(`/api/timers/${encodeURIComponent(timer.id)}`, { method: 'DELETE' });
            await loadTimers();
        }, true);
        card.append(title, meta, remove);
        elements.timerList.append(card);
    });
}

async function saveTimer(event) {
    event.preventDefault();
    const days = $$('input[name="timerDay"]:checked').map(input => Number(input.value));
    const body = {
        time: $('#timerTime').value,
        entity_id: elements.timerDevice.value,
        type: elements.timerType.value,
        playlist_name: elements.timerPlaylist.value,
        duration: Number($('#timerDuration').value || 0),
        days,
        is_random: $('#timerRandom').checked,
        enabled: true
    };
    try {
        await api('/api/timers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        toast('Đã lưu lịch');
        elements.timerForm.reset();
        $('#timerRandom').checked = true;
        toggleTimerFields();
        await loadTimers();
    } catch (error) { toast(error.message); }
}

async function remoteControl(action) {
    const entityId = activeRemoteEntity();
    if (!entityId || entityId === 'browser') return;
    if (action === 'stop') {
        state.resolveId += 1;
        state.playingDevice = null;
        state.loadingUrl = null;
        state.playingUrl = null;
        elements.player.classList.remove('loading');
        updateTrackStates();
        updatePlayerMode();
    }
    try {
        if (action === 'stop') await stopRemotePlayback(entityId);
        else await enqueueRemoteCommand(entityId, () => remoteControlRequest(entityId, action));
        setMessage(action === 'stop' ? 'Đã dừng loa' : 'Đã gửi lệnh tới loa');
        if (action === 'stop') resetRemoteProgress(state.current?.duration || 0);
        else scheduleRemoteStatePoll(180);
    } catch (error) { toast(error.message); }
}

async function setRemoteVolume(value) {
    const entityId = activeRemoteEntity();
    if (entityId === 'browser') return;
    try {
        await enqueueRemoteCommand(entityId, () => remoteControlRequest(entityId, 'volume', { volume: Number(value) }));
    } catch (_) {}
}

async function loadStatus() {
    elements.systemStatus.textContent = 'Đang kiểm tra...';
    try {
        const data = await api('/api/status');
        const cookie = data.cookie || {};
        if (!cookie.installed) {
            elements.cookieStatus.textContent = 'Chưa cài';
        } else if (!cookie.valid) {
            elements.cookieStatus.textContent = 'Không hợp lệ';
        } else if (!cookie.authenticated) {
            elements.cookieStatus.textContent = 'Thiếu đăng nhập';
        } else {
            elements.cookieStatus.textContent = `Sẵn sàng · ${cookie.active} cookie`;
        }
        const extractor = data.last_extractor || {};
        const preference = data.extractor_preference || {};
        const pot = data.pot_token_provider || {};
        const castProfile = data.cast_preference || {};
        const websocketState = data.ha_websocket || {};
        const integration = data.integration_api || {};
        const license = data.license || {};
        renderLicense(license);
        elements.integrationTokenStatus.textContent = integration.ready
            ? `API v${integration.api_version || 1} · sẵn sàng`
            : 'Chưa sẵn sàng';
        elements.systemStatus.textContent = [
            `Home Assistant: ${data.ha_ok ? 'OK' : 'Lỗi kết nối'}`,
            `Deno: ${data.deno ? 'OK' : 'Chưa có'}`,
            `yt-dlp-ejs: ${data.ejs || 'Chưa có'}`,
            `yt-dlp: ${data.yt_dlp}`,
            `Extractor: ${extractor.strategy || 'Chưa phát'}${extractor.format_id ? ` · format ${extractor.format_id}` : ''}${extractor.cache_hit ? ' · cache' : ''}${extractor.elapsed_ms != null ? ` · ${extractor.elapsed_ms} ms` : ''}`,
            `Ưu tiên lần sau: ${preference.preferred || 'Tự động'}`,
            `PO Token: ${!pot.enabled ? 'Tắt' : (pot.available ? `OK · server ${pot.version || '?'} · plugin ${pot.plugin || '?'}` : `Chưa sẵn sàng${pot.error ? ` · ${pot.error}` : ''}`)}`,
            `Profile loa: ${castProfile.preferred_transport ? `${castProfile.preferred_transport} · ${castProfile.preferred_media_type || 'auto'}` : 'Chưa học'}`,
            `HA WebSocket: ${websocketState.connected ? 'Đã kết nối' : `REST fallback${websocketState.last_error ? ` · ${websocketState.last_error}` : ''}`}`,
            `License: ${license.valid ? `${license.plan_name || license.plan_code || 'Hợp lệ'} · ${formatLicenseExpiry(license.expires_at)}` : `${license.state || 'chưa có'}${license.enforcement ? ' · enforcement bật' : ' · enforcement tắt'}`}`,
            `Cookie: ${elements.cookieStatus.textContent}`,
            `Relay loa: ${data.media_base_url}`,
            data.last_error ? `Lỗi gần nhất: ${data.last_error}` : 'Không có lỗi gần đây'
        ].join('\n');
    } catch (error) {
        elements.systemStatus.textContent = error.message;
    }
}

function formatLicenseExpiry(value) {
    if (!value) return 'Vĩnh viễn';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString('vi-VN');
}

function renderLicense(license) {
    const state = license.state || 'unlicensed';
    const labels = {
        active: 'Đang hoạt động',
        offline_grace: 'Offline grace',
        unlicensed: 'Chưa có license',
        expired: 'Đã hết hạn',
        invalid: 'Không hợp lệ',
        server_unreachable: 'Không kết nối server',
        not_configured: 'Chưa cấu hình server'
    };
    const label = labels[state] || state;
    const installation = `Installation: …${license.installation_suffix || '—'}`;
    if (elements.licenseStatus) {
        elements.licenseStatus.textContent = label;
        elements.licenseStatus.dataset.state = state;
    }
    if (elements.licenseGateStatus) elements.licenseGateStatus.textContent = label;
    if (elements.licenseInstallation) elements.licenseInstallation.textContent = installation;
    if (elements.licenseGateInstallation) elements.licenseGateInstallation.textContent = installation;
    if ('portal_url' in license || 'claim_url' in license) {
        const portal = license.portal_url || '';
        for (const link of [elements.licensePortalLink, elements.licenseGatePortalLink]) {
            if (!link) continue;
            if (portal) {
                link.href = license.claim_url || portal;
                link.textContent = license.claim_url ? 'Nhận key · liên kết installation' : 'Mở website License';
                link.classList.remove('hidden');
            } else {
                link.classList.add('hidden');
                link.removeAttribute('href');
            }
        }
    }
    let description = '';
    if (license.valid) {
        description = `${license.plan_name || license.plan_code || 'License'} · hết hạn: ${formatLicenseExpiry(license.expires_at)}${license.key_prefix ? ` · ${license.key_prefix}` : ''}`;
        elements.deactivateLicense?.classList.remove('hidden');
    } else if (state === 'not_configured') {
        description = 'License Server chưa được cấu hình. YouTube Pro vẫn khóa cho tới khi kết nối server và nhập key hợp lệ.';
        elements.deactivateLicense?.classList.add('hidden');
    } else if (license.error) {
        description = `Chưa xác minh được license: ${license.error}`;
        elements.deactivateLicense?.classList.add('hidden');
    } else {
        description = license.claim_url
            ? 'Mở website để đăng nhập, nhận trial hoặc mua gói. Sau đó dán License Key vào ô bên dưới.'
            : 'Chưa có license hợp lệ. Hãy nhập key hoặc kiểm tra lại kết nối License Server.';
        elements.deactivateLicense?.classList.add('hidden');
    }
    if (elements.licenseDescription) elements.licenseDescription.textContent = description;
    if (elements.licenseGateDescription) elements.licenseGateDescription.textContent = description;

    const valid = license.valid === true;
    document.body.classList.remove('license-pending', 'license-locked', 'license-active');
    document.body.classList.add(valid ? 'license-active' : 'license-locked');
    if (elements.appShell) {
        elements.appShell.inert = !valid;
        elements.appShell.setAttribute('aria-hidden', valid ? 'false' : 'true');
    }
    if (!valid) stopLicensedRuntime();
    return valid;
}

async function loadLicense(force = false) {
    try {
        const data = await api(`/api/license${force ? '?refresh=1' : ''}`, { cache: 'no-store' });
        const license = data.license || {};
        if (renderLicense(license)) await startLicensedRuntime();
        return license;
    } catch (error) {
        document.body.classList.remove('license-pending', 'license-active');
        document.body.classList.add('license-locked');
        if (elements.licenseDescription) elements.licenseDescription.textContent = error.message;
        if (elements.licenseGateDescription) elements.licenseGateDescription.textContent = error.message;
        if (elements.licenseGateStatus) elements.licenseGateStatus.textContent = 'Không kết nối được License Server';
        return null;
    }
}

function formatLicenseKey(value) {
    const compact = String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 23);
    if (compact.length <= 3) return compact;
    const prefix = compact.slice(0, 3);
    const body = compact.slice(3).match(/.{1,5}/g)?.join('-') || '';
    return `${prefix}-${body}`;
}

function syncLicenseInputs(source) {
    const formatted = formatLicenseKey(source.value);
    source.value = formatted;
    $$('[data-license-key]').forEach(input => {
        if (input !== source) input.value = formatted;
    });
}

function setLicenseSubmitBusy(busy) {
    $$('[data-license-submit]').forEach(button => {
        button.disabled = busy;
        button.classList.toggle('loading', busy);
        const label = button.querySelector('span');
        if (label) label.textContent = busy ? 'Đang xác minh' : 'Kích hoạt key';
    });
}

async function activateLicense(event) {
    event.preventDefault();
    const input = event.currentTarget.querySelector('[data-license-key]');
    const key = formatLicenseKey(input?.value).trim();
    if (!key) return toast('Hãy nhập License Key');
    try {
        setLicenseSubmitBusy(true);
        if (elements.licenseGateStatus) elements.licenseGateStatus.textContent = 'Đang xác minh License Key';
        const data = await api('/api/license', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ license_key: key })
        });
        $$('[data-license-key]').forEach(field => { field.value = ''; });
        const valid = renderLicense(data.license || {});
        toast('Đã kích hoạt License Key');
        if (valid) await startLicensedRuntime();
    } catch (error) {
        toast(error.message);
        const license = error.payload?.license;
        if (license) renderLicense(license);
        if (elements.licenseGateStatus) elements.licenseGateStatus.textContent = 'Kích hoạt chưa thành công';
    } finally {
        setLicenseSubmitBusy(false);
    }
}

async function deactivateLicense() {
    if (!confirm('Gỡ liên kết license khỏi installation này?')) return;
    try {
        const data = await api('/api/license', { method: 'DELETE' });
        renderLicense(data.license || {});
        toast('Đã gỡ liên kết license');
    } catch (error) {
        toast(error.message);
    }
}

async function fetchIntegrationToken() {
    const data = await api('/api/integration-token', { cache: 'no-store' });
    elements.integrationToken.value = data.token || '';
    elements.integrationTokenStatus.textContent = data.updated_at
        ? `Sẵn sàng · ${data.updated_at}`
        : 'Sẵn sàng';
    return elements.integrationToken.value;
}

async function toggleIntegrationToken() {
    try {
        if (!elements.integrationToken.value) await fetchIntegrationToken();
        const reveal = elements.integrationToken.type === 'password';
        elements.integrationToken.type = reveal ? 'text' : 'password';
        elements.toggleIntegrationToken.textContent = reveal ? 'Ẩn token' : 'Hiện token';
    } catch (error) {
        toast(error.message);
    }
}

async function copyIntegrationToken() {
    try {
        const token = elements.integrationToken.value || await fetchIntegrationToken();
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(token);
        } else {
            const previousType = elements.integrationToken.type;
            elements.integrationToken.type = 'text';
            elements.integrationToken.select();
            document.execCommand('copy');
            elements.integrationToken.type = previousType;
        }
        toast('Đã sao chép integration token');
    } catch (error) {
        toast(error.message);
    }
}

async function rotateIntegrationToken() {
    if (!confirm('Tạo token mới? Custom integration đang dùng token cũ sẽ mất kết nối ngay.')) return;
    try {
        const data = await api('/api/integration-token', {
            method: 'POST',
            cache: 'no-store',
            headers: { 'X-YouTube-Pro-Action': 'rotate-token' }
        });
        elements.integrationToken.value = data.token || '';
        elements.integrationToken.type = 'password';
        elements.toggleIntegrationToken.textContent = 'Hiện token';
        elements.integrationTokenStatus.textContent = data.updated_at
            ? `Đã tạo mới · ${data.updated_at}`
            : 'Đã tạo mới';
        toast('Đã tạo integration token mới');
    } catch (error) {
        toast(error.message);
    }
}

async function resetCastProfile() {
    const entityId = activeRemoteEntity();
    try {
        await api('/api/cast-preferences', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entity_id: entityId || '' })
        });
        toast(entityId ? 'Đã quên profile của loa đang chọn' : 'Đã xóa mọi profile loa');
        await loadStatus();
    } catch (error) {
        toast(error.message);
    }
}

async function uploadCookies(event) {
    event.preventDefault();
    const file = elements.cookieFile.files[0];
    if (!file) return toast('Hãy chọn file cookies.txt');
    const body = new FormData();
    body.append('file', file, file.name);
    try {
        await api('/api/cookies', { method: 'POST', body });
        elements.cookieFile.value = '';
        elements.cookieFileName.textContent = 'Chọn cookies.txt';
        toast('Đã nhập cookie YouTube');
        await loadStatus();
    } catch (error) {
        toast(error.message);
    }
}

async function deleteCookies() {
    if (!confirm('Xóa cookie YouTube đã lưu?')) return;
    try {
        await api('/api/cookies', { method: 'DELETE' });
        toast('Đã xóa cookie YouTube');
        await loadStatus();
    } catch (error) {
        toast(error.message);
    }
}

function bindEvents() {
    elements.themeToggle.addEventListener('click', () => {
        applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
    });
    elements.searchForm.addEventListener('submit', event => { event.preventDefault(); search(true); });
    $$('.quick-search').forEach(button => button.addEventListener('click', () => {
        elements.searchInput.value = button.dataset.query || '';
        selectTab('home');
        search(true);
    }));
    $('#refreshSearch').addEventListener('click', () => search(true));
    elements.loadMore.addEventListener('click', () => search(false));
    elements.deviceSelect.addEventListener('change', () => {
        const previousDevice = state.playingDevice;
        state.resolveId += 1;
        stopPlaybackImmediately(previousDevice);
        state.device = elements.deviceSelect.value;
        state.playingDevice = null;
        state.loadingUrl = null;
        state.playingUrl = null;
        localStorage.setItem('youtubeProDevice', state.device);
        elements.player.classList.remove('loading');
        updateTrackStates();
        updatePlayerMode();
        if (state.current) setMessage('Đã đổi thiết bị — chọn bài để phát');
    });
    $$('.bottom-nav button').forEach(button => button.addEventListener('click', () => selectTab(button.dataset.tab)));
    $('#clearQueue').addEventListener('click', clearQueue);
    $('#createPlaylist').addEventListener('click', createPlaylist);
    $('#deletePlaylist').addEventListener('click', deletePlaylist);
    $('#clearHistory').addEventListener('click', clearHistory);
    $('#favoriteCurrent').addEventListener('click', () => state.current && addFavorite(state.current));
    elements.playerDetails.addEventListener('click', () => state.current && openDetails(state.current, state.playbackContext));
    elements.togglePlayer.addEventListener('click', event => {
        event.stopPropagation();
        setPlayerCollapsed(!state.playerCollapsed);
    });
    $('#playerInfo').addEventListener('click', event => {
        if (state.playerCollapsed && !event.target.closest('button')) setPlayerCollapsed(false);
    });
    $('#previousTrack').addEventListener('pointerdown', () => prefetchRelative(-1), { passive: true });
    $('#nextTrack').addEventListener('pointerdown', () => prefetchRelative(1), { passive: true });
    $('#previousTrack').addEventListener('click', () => playRelative(-1));
    $('#nextTrack').addEventListener('click', () => playRelative(1));
    elements.shuffleToggle.addEventListener('click', () => updatePlaybackModes(state.repeatMode, !state.shuffle));
    elements.repeatToggle.addEventListener('click', () => {
        const next = state.repeatMode === 'off' ? 'all' : state.repeatMode === 'all' ? 'one' : 'off';
        updatePlaybackModes(next, state.shuffle);
    });
    $('#closeDetails').addEventListener('click', closeDetailsDialog);
    elements.detailsDialog.addEventListener('cancel', () => { state.detailsRequestId += 1; });
    elements.detailsDialog.addEventListener('click', event => {
        if (event.target === elements.detailsDialog) closeDetailsDialog();
    });
    elements.detailsPlay.addEventListener('click', () => {
        const track = state.detailsTrack;
        const context = state.detailsContext;
        closeDetailsDialog();
        if (track) playTrack(track, context);
    });
    elements.audio.addEventListener('ended', () => {
        if (!state.audioPriming) {
            setMediaSessionPlayback('none');
            playRelative(1, true);
        }
    });
    elements.audio.addEventListener('playing', () => {
        if (!state.audioPriming) {
            state.audioUnlocked = true;
            state.playingDevice = 'browser';
            state.loadingUrl = null;
            state.playingUrl = state.current?.url || null;
            updateTrackStates();
            updatePlayerMode();
            setMediaSessionPlayback('playing');
            setMessage('Đang phát trên điện thoại');
        }
    });
    elements.audio.addEventListener('pause', () => {
        if (!state.audioPriming && !elements.audio.ended) setMediaSessionPlayback('paused');
    });
    elements.audio.addEventListener('timeupdate', () => {
        if (!state.audioPriming) {
            updateMediaSessionPosition(
                elements.audio.currentTime,
                elements.audio.duration || state.current?.duration || 0,
                elements.audio.playbackRate || 1
            );
        }
    });
    elements.audio.addEventListener('waiting', () => { if (!state.audioPriming) setMessage('Đang tải thêm dữ liệu...'); });
    elements.audio.addEventListener('error', () => {
        if (!state.audioPriming) {
            setMediaSessionPlayback('none');
            setMessage('Audio lỗi — thử phát lại bài hát');
        }
    });
    $('#sleepButtons').addEventListener('click', event => {
        const minutes = Number(event.target.closest('button')?.dataset.minutes);
        if (minutes) setSleep(minutes);
    });
    $('#cancelSleep').addEventListener('click', cancelSleep);
    elements.timerType.addEventListener('change', toggleTimerFields);
    elements.timerForm.addEventListener('submit', saveTimer);
    elements.remoteControls.addEventListener('click', event => {
        const action = event.target.closest('button')?.dataset.control;
        if (action) remoteControl(action);
    });
    elements.remoteVolume.addEventListener('change', () => setRemoteVolume(elements.remoteVolume.value));
    elements.remoteSeek.addEventListener('pointerdown', () => { state.remoteSeeking = true; });
    elements.remoteSeek.addEventListener('input', () => {
        state.remoteSeeking = true;
        updateRemoteProgress(elements.remoteSeek.value, state.remoteDuration, true);
    });
    elements.remoteSeek.addEventListener('change', () => seekRemote(elements.remoteSeek.value));
    $('#refreshStatus').addEventListener('click', loadStatus);
    elements.refreshLicense.addEventListener('click', () => loadLicense(true));
    elements.licenseGateRefresh.addEventListener('click', () => loadLicense(true));
    $$('[data-license-form]').forEach(form => form.addEventListener('submit', activateLicense));
    $$('[data-license-key]').forEach(input => input.addEventListener('input', () => syncLicenseInputs(input)));
    elements.deactivateLicense.addEventListener('click', deactivateLicense);
    $('#resetCastProfile').addEventListener('click', resetCastProfile);
    elements.toggleIntegrationToken.addEventListener('click', toggleIntegrationToken);
    elements.copyIntegrationToken.addEventListener('click', copyIntegrationToken);
    elements.rotateIntegrationToken.addEventListener('click', rotateIntegrationToken);
    elements.cookieForm.addEventListener('submit', uploadCookies);
    elements.cookieFile.addEventListener('change', () => {
        elements.cookieFileName.textContent = elements.cookieFile.files[0]?.name || 'Chọn cookies.txt';
    });
    $('#deleteCookies').addEventListener('click', deleteCookies);
    window.addEventListener('keydown', event => {
        const target = event.target;
        const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
        if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
            event.preventDefault();
            elements.searchInput.focus();
        }
        if (event.key === 'Escape' && document.activeElement === elements.searchInput) {
            elements.searchInput.blur();
        }
    });
    window.addEventListener('scroll', maybeLoadMore, { passive: true });
}

function stopLicensedRuntime() {
    if (!state.licensedRuntime) return;
    state.licensedRuntime = false;
    try { state.eventSource?.close(); } catch (_) {}
    state.eventSource = null;
    stopRemoteProgressPolling();
    clearInterval(state.sleepPollInterval);
    clearInterval(state.progressInterval);
    state.sleepPollInterval = null;
    state.progressInterval = null;
    if (!elements.audio.paused) elements.audio.pause();
}

async function startLicensedRuntime() {
    if (state.licensedRuntime) return;
    state.licensedRuntime = true;
    setupEventStream();
    await Promise.all([loadDevices(), loadPlaylists(), loadQueue(), loadHistory()]);
    toggleTimerFields();
    await search(true);
    await loadSleep();
    await loadStatus();
    if (!state.licensedRuntime) return;
    state.sleepPollInterval = setInterval(loadSleep, 5000);
    state.progressInterval = setInterval(tickRemoteProgress, 500);
}

async function init() {
    applyTheme(document.documentElement.dataset.theme || 'dark', false);
    setupMediaSession();
    updatePlaybackModeButtons();
    bindEvents();
    setPlayerCollapsed(state.playerCollapsed, false);
    setupInfiniteScroll();
    await loadLicense(false);
    state.licensePollInterval = setInterval(() => loadLicense(false), 60000);
}

init();
