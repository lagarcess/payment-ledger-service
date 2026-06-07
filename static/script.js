const API_ORIGIN_STORAGE_KEY = 'revApiOrigin';
const DEFAULT_REMOTE_API_ORIGIN = 'https://ledger-api.onrender.com';
const STATE_FETCH_TIMEOUT_LOCAL_MS = 60000;
const STATE_FETCH_TIMEOUT_REMOTE_MS = 90000;
const LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost', '::1']);

function getDefaultApiOrigin() {
    const { hostname, origin, port, protocol } = window.location;
    if (protocol === 'file:') return 'http://127.0.0.1:8000';
    if (LOCAL_HOSTS.has(hostname)) {
        return port === '8000' ? origin : 'http://127.0.0.1:8000';
    }
    return DEFAULT_REMOTE_API_ORIGIN;
}

function normalizeApiOrigin(value) {
    const fallback = getDefaultApiOrigin();
    const raw = String(value || '').trim();
    if (!raw) return fallback;

    try {
        const url = new URL(raw);
        const normalizedPath = url.pathname
            .replace(/\/api\/?$/, '')
            .replace(/\/+$/, '');
        return `${url.origin}${normalizedPath && normalizedPath !== '/' ? normalizedPath : ''}`;
    } catch (err) {
        return fallback;
    }
}

const params = new URLSearchParams(window.location.search);
const queryApiOrigin = params.get('api') || params.get('api_origin');
let currentApiOrigin = normalizeApiOrigin(
    queryApiOrigin || localStorage.getItem(API_ORIGIN_STORAGE_KEY) || getDefaultApiOrigin()
);
if (queryApiOrigin) {
    localStorage.setItem(API_ORIGIN_STORAGE_KEY, currentApiOrigin);
}

function apiUrl(path) {
    return `${currentApiOrigin}/api/${String(path).replace(/^\/+/, '')}`;
}

function healthUrl() {
    return `${currentApiOrigin}/health`;
}

function shouldUseRemoteWakeStatus() {
    return (
        window.location.hostname.endsWith('github.io')
        && currentApiOrigin === DEFAULT_REMOTE_API_ORIGIN
    );
}

function getStateFetchTimeoutMs() {
    return shouldUseRemoteWakeStatus()
        ? STATE_FETCH_TIMEOUT_REMOTE_MS
        : STATE_FETCH_TIMEOUT_LOCAL_MS;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = STATE_FETCH_TIMEOUT_LOCAL_MS) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

    try {
        return await fetch(url, {
            cache: options.cache || 'no-store',
            ...options,
            signal: controller.signal
        });
    } finally {
        window.clearTimeout(timeoutId);
    }
}

const i18n = {
    en: {
        sbTitle: "Payment Terminal", sbDesc: "Execute cross-currency transfers through the FX clearing engine.",
        langTitle: "Language", lblSenderReceiver: "Sender & Receiver", lblSender: "Sender", lblReceiver: "Receiver",
        lblPaymentParams: "Payment Parameters", lblAmount: "Amount", lblFxRate: "FX Rate", lblIdempotency: "Idempotency",
        lblAutoGenerate: "Auto-generate key", btnExecute: "Execute Payment", btnReset: "Reset Database",
        mainTitle: "Ledger Engine", mainSubtitle: "Double-entry payment ledger · Cross-currency FX clearing · Real-time invariant monitoring",
        metDebits: "TOTAL DEBITS", metCredits: "TOTAL CREDITS", metTxns: "TRANSACTIONS", metEntries: "ENTRIES",
        flowTitle: "Payment Flow", flowDesc: "Cross-currency settlement path through the Corporate FX Clearing Account.",
        accTitle: "Accounts", accDesc: "FX Clearing rows highlighted with subtle tint.",
        thId: "ID", thAccount: "ACCOUNT", thType: "TYPE", thCurrency: "CURRENCY", thBalance: "BALANCE",
        tabJournal: "Journal Entries", tabLegs: "Ledger Legs", txnsTitle: "Transactions",
        thTimestamp: "TIMESTAMP", thIdemKey: "IDEMPOTENCY KEY", thDesc: "DESCRIPTION", thLegs: "LEGS",
        entriesTitle: "Entry Legs", entriesDesc: "DEBIT in teal · CREDIT in red.", thTxn: "TXN", thDirection: "DIRECTION", thAmount: "AMOUNT",
        balPrefix: "Balance: ", rcvPrefix: "Receiver gets ", invBalanced: "PERFECTLY BALANCED (0.00) ─ Σ Debits == Σ Credits",
        invImbalance: "IMBALANCE DETECTED ─ Net: ", invLabel: "System Invariant", userCount: " user", usersCount: " users",
        accountCount: " account", accountsCount: " accounts", footerPayments: "Payments this session: ",
        toastSuccess: "Success", toastError: "Error", toastReset: "Reset", msgDbReset: "Database reset to seed state.",
        errBackend: "Backend unavailable. Warm it from settings or check the API URL.", errPayment: "Network error executing payment.", errReset: "Failed to reset database.",
        txtCredit: "CREDIT", txtDebit: "DEBIT", txtLeg: "Leg", fxClearing: "FX Clearing",
        appTitle: "Appearance", appSystem: "System", appLight: "Light", appDark: "Dark",
        apiTitle: "Backend", lblApiOrigin: "API URL", btnSaveApi: "Save", btnResetApi: "Default",
        apiDefaultHelper: "Default backend", apiDefaultRender: "Render", apiDefaultLocal: "local",
        btnWarmBackend: "Warm", apiStatusIdle: "Not checked", apiStatusChecking: "Checking...",
        apiStatusWaking: "Waking Render backend...",
        apiStatusOnline: "Online", apiStatusOffline: "Offline", apiStatusTimeout: "Cold start timeout",
        apiSaved: "Backend URL saved.", apiReset: "Backend URL reset.", apiWarmSuccess: "Backend is awake.",
        apiWarmFail: "Backend did not respond.", offlineInvariant: "BACKEND OFFLINE — Warm or set API URL",
        offlineFlow: "Ledger state unavailable until the backend responds.",
        apiRemoteWakeHintTitle: "Waking Render",
        apiRemoteWakeHintBody: "First load can take up to 90 seconds. Use the gear to switch API URL or retry Warm.",
        lblConcurrency: "Concurrency Strategy", lblLockingStrategy: "Locking Mode",
        lockingHelper: "Controls how concurrent transactions are serialized.",
        btnRace: "Simulate Concurrency Race", thActions: "ACTIONS",
        btnReverse: "Reverse", badgeReversed: "REVERSED", badgeReversal: "REVERSAL",
        raceTitle: "Race Condition Simulation", raceThreadA: "Thread A", raceThreadB: "Thread B",
        raceSuccess: "Committed", raceFailed: "Rejected", raceBlocked: "Blocked by lock",
        optPessimistic: "Pessimistic (FOR UPDATE)", optOptimistic: "Optimistic (OCC)",
        errSameSenderReceiver: "Select different sender and receiver.", errZeroBalance: "Sender has zero balance. Reset the database first.",
        errRaceNet: "Race simulation network error.", errRevNet: "Network error during reversal."
    },
    es: {
        sbTitle: "Terminal de Pagos", sbDesc: "Ejecución de transferencias multidivisa mediante el motor de compensación.",
        langTitle: "Idioma", lblSenderReceiver: "Origen y Destino", lblSender: "Cuenta de Origen", lblReceiver: "Cuenta de Destino",
        lblPaymentParams: "Detalles de la Operación", lblAmount: "Monto", lblFxRate: "Tipo de Cambio", lblIdempotency: "Idempotencia",
        lblAutoGenerate: "Generar clave automáticamente", btnExecute: "Procesar Transferencia", btnReset: "Reiniciar Entorno",
        mainTitle: "Motor Contable", mainSubtitle: "Libro mayor de partida doble · Compensación cambiaria · Monitoreo de invariantes",
        metDebits: "CARGOS TOTALES", metCredits: "ABONOS TOTALES", metTxns: "OPERACIONES", metEntries: "APUNTES CONTABLES",
        flowTitle: "Flujo de Fondos", flowDesc: "Ruta de liquidación multidivisa a través de las cuentas de compensación.",
        accTitle: "Cuentas", accDesc: "Cuentas de compensación resaltadas.",
        thId: "ID", thAccount: "CUENTA", thType: "TIPO", thCurrency: "DIVISA", thBalance: "SALDO",
        tabJournal: "Registro de Operaciones", tabLegs: "Libro Mayor", txnsTitle: "Operaciones",
        thTimestamp: "FECHA", thIdemKey: "CLAVE DE IDEMPOTENCIA", thDesc: "CONCEPTO", thLegs: "APUNTES",
        entriesTitle: "Apuntes Contables", entriesDesc: "CARGO en turquesa · ABONO en rojo.", thTxn: "OP", thDirection: "NATURALEZA", thAmount: "IMPORTE",
        balPrefix: "Saldo: ", rcvPrefix: "Destino recibe ", invBalanced: "BALANCE PERFECTO (0.00) ─ Σ Cargos == Σ Abonos",
        invImbalance: "DESCUADRE DETECTADO ─ Neto: ", invLabel: "Invariante del Sistema", userCount: " usuario", usersCount: " usuarios",
        accountCount: " cuenta", accountsCount: " cuentas", footerPayments: "Pagos procesados en esta sesión: ",
        toastSuccess: "Éxito", toastError: "Error", toastReset: "Reiniciado", msgDbReset: "Entorno restaurado a su estado inicial.",
        errBackend: "Motor no disponible. Actívelo desde ajustes o revise la URL de API.", errPayment: "Error de red procesando la transferencia.", errReset: "Error al reiniciar el entorno.",
        txtCredit: "ABONO", txtDebit: "CARGO", txtLeg: "Apunte", fxClearing: "Compensación",
        appTitle: "Apariencia", appSystem: "Sistema", appLight: "Claro", appDark: "Oscuro",
        apiTitle: "Backend", lblApiOrigin: "URL de API", btnSaveApi: "Guardar", btnResetApi: "Predeterminado",
        apiDefaultHelper: "Backend predeterminado", apiDefaultRender: "Render", apiDefaultLocal: "local",
        btnWarmBackend: "Activar", apiStatusIdle: "Sin comprobar", apiStatusChecking: "Comprobando...",
        apiStatusWaking: "Activando backend de Render...",
        apiStatusOnline: "En línea", apiStatusOffline: "Sin conexión", apiStatusTimeout: "Arranque agotado",
        apiSaved: "URL del backend guardada.", apiReset: "URL del backend restaurada.", apiWarmSuccess: "Backend activo.",
        apiWarmFail: "El backend no respondió.", offlineInvariant: "BACKEND SIN CONEXIÓN — Active o configure la URL",
        offlineFlow: "El estado contable no está disponible hasta que responda el backend.",
        apiRemoteWakeHintTitle: "Activando Render",
        apiRemoteWakeHintBody: "La primera carga puede tardar hasta 90 segundos. Use el engrane para cambiar la URL de API o reintentar Activar.",
        lblConcurrency: "Estrategia de Concurrencia", lblLockingStrategy: "Modo de Bloqueo",
        lockingHelper: "Controla c\u00f3mo se serializan las transacciones concurrentes.",
        btnRace: "Simular Carrera de Concurrencia", thActions: "ACCIONES",
        btnReverse: "Revertir", badgeReversed: "REVERTIDA", badgeReversal: "REVERSI\u00d3N",
        raceTitle: "Simulaci\u00f3n de Condici\u00f3n de Carrera", raceThreadA: "Hilo A", raceThreadB: "Hilo B",
        raceSuccess: "Confirmada", raceFailed: "Rechazada", raceBlocked: "Bloqueada por candado",
        optPessimistic: "Pesimista (FOR UPDATE)", optOptimistic: "Optimista (OCC)",
        errSameSenderReceiver: "Seleccione cuentas de origen y destino distintas.", errZeroBalance: "La cuenta origen tiene saldo cero. Reinicie la base de datos.",
        errRaceNet: "Error de red durante la simulación de carrera.", errRevNet: "Error de red al revertir operación."
    }
};

let currentLang = localStorage.getItem('revLang') || 'en';
let currentTheme = localStorage.getItem('revTheme') || 'system';

function t(key) {
    return i18n[currentLang][key] || key;
}

// Translators for dynamic backend data
const tDyn = (val) => {
    if (currentLang !== 'es' || !val) return val;
    let translated = String(val);
    const dict = {
        'CORPORATE_FX_CLEARING': 'COMPENSACIÓN',
        'USER': 'USUARIO',
        'CREDIT': 'ABONO',
        'DEBIT': 'CARGO',
        'Cross-currency transfer': 'Transferencia multidivisa',
        'Same-currency transfer': 'Transferencia local',
        'Initial funding: Alice receives': 'Fondeo inicial: Alicia recibe',
        'Treasury funding: FX Clearing': 'Fondeo de Tesorería: Compensación',
        'Treasury capitalisation: FX Clearing': 'Capitalización de Tesorería: Compensación',
        'Alice (User 1)': 'Alicia (Usuario 1)',
        'Bob (User 2)': 'Roberto (Usuario 2)',
        'from Alice to Bob': 'de Alicia a Roberto',
        'from Bob to Alice': 'de Roberto a Alicia',
        'Alice': 'Alicia',
        'Bob': 'Roberto',
        'pool': ' ',
        'Idempotency Rejection: Transaction with idempotency_key': 'Operación Duplicada: Ya existe una transacción con la clave',
        'already exists': 'registrada',
        '(txn_id=': '(id_transacción=',
        'Overdraft Prevention: Account': 'Fondos Insuficientes: La cuenta',
        'has balance': 'dispone de',
        'cents but tried to send': 'centavos, lo cual es insuficiente para procesar el envío de',
        'cents but needs': 'centavos, pero se requieren',
        'cents to fund the receiver': 'centavos para completar la operación de destino',
        'cents.': 'centavos.',
        'Sender and Receiver must differ': 'Las cuentas de origen y destino no pueden ser la misma',
        'Transaction #': 'Transacción #',
        ' committed successfully.': ' confirmada con éxito.',
        'Reversal transaction #': 'Transacción de reversión #',
        ' committed. Original transaction #': ' confirmada. La operación original #',
        ' has been offset.': ' ha sido compensada.',
        'Already Reversed: ': 'Ya revertida: '
    };
    for (let key in dict) {
        if (translated.includes(key)) {
            translated = translated.split(key).join(dict[key]);
        }
    }
    return translated.trim();
};

function updateStaticText() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[currentLang][key]) {
            el.textContent = i18n[currentLang][key];
        }
    });
}
// DOM Elements
const els = {
    invariantCard: document.getElementById('invariant-card'),
    metricDebits: document.getElementById('metric-debits'),
    metricCredits: document.getElementById('metric-credits'),
    metricTxns: document.getElementById('metric-txns'),
    metricTxnsSub: document.getElementById('metric-txns-sub'),
    metricEntries: document.getElementById('metric-entries'),
    metricEntriesSub: document.getElementById('metric-entries-sub'),
    flowCard: document.getElementById('flow-card'),
    
    badgeAccounts: document.getElementById('badge-accounts'),
    tableAccounts: document.querySelector('#table-accounts tbody'),
    badgeTxns: document.getElementById('badge-txns'),
    tableTxns: document.querySelector('#table-txns tbody'),
    badgeEntries: document.getElementById('badge-entries'),
    tableEntries: document.querySelector('#table-entries tbody'),
    
    sender: document.getElementById('sender'),
    receiver: document.getElementById('receiver'),
    senderBalance: document.getElementById('sender-balance'),
    amount: document.getElementById('amount'),
    fxRate: document.getElementById('fx-rate'),
    fxRateVal: document.getElementById('fx-rate-val'),
    fxCalc: document.getElementById('fx-calculation'),
    autoKey: document.getElementById('auto-key'),
    idemKeyDisplay: document.getElementById('idem-key-display'),
    idemKeyInput: document.getElementById('idem-key-input'),
    
    btnExecute: document.getElementById('btn-execute'),
    btnRace: document.getElementById('btn-race'),
    btnReset: document.getElementById('btn-reset'),
    lockingStrategy: document.getElementById('locking-strategy'),
    toastContainer: document.getElementById('toast-container'),
    footerPayments: document.getElementById('footer-payments'),
    
    btnSettings: document.getElementById('btn-settings'),
    settingsPopover: document.getElementById('settings-popover'),
    langOptions: document.querySelectorAll('.menu-list-item'),
    themeOptions: document.querySelectorAll('.segmented-btn'),
    apiOriginInput: document.getElementById('api-origin'),
    apiDefaultHelper: document.getElementById('api-default-helper'),
    apiStatus: document.getElementById('api-status'),
    btnApiSave: document.getElementById('btn-api-save'),
    btnApiReset: document.getElementById('btn-api-reset'),
    btnWarmBackend: document.getElementById('btn-warm-backend'),
    
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content')
};

// State
let state = null;
let currentSenderId = null;
let currentReceiverId = null;
let backendStatus = 'idle';
let backendStatusDetail = '';
let lastBackendError = null;
let remoteWakeHintShown = false;

// Initialization
async function init() {
    setupEventListeners();
    setLanguage(currentLang, false);
    setTheme(currentTheme);
    formatAmountInput();
    if (els.apiOriginInput) {
        els.apiOriginInput.value = currentApiOrigin;
    }
    updateApiDefaultHelper();
    setBackendStatus('idle');
    await fetchState();
    generateIdemKey();
}

function setupEventListeners() {
    // Tabs
    els.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            els.tabBtns.forEach(b => b.classList.remove('active'));
            els.tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });

    // Form inputs
    els.sender.addEventListener('change', updateFormState);
    els.receiver.addEventListener('change', updateFormState);
    els.amount.addEventListener('input', updateFormState);
    els.amount.addEventListener('change', () => {
        formatAmountInput();
        updateFormState();
    });
    els.amount.addEventListener('blur', () => {
        formatAmountInput();
        updateFormState();
    });
    els.fxRate.addEventListener('input', (e) => {
        els.fxRateVal.textContent = parseFloat(e.target.value).toFixed(2);
        updateFormState();
    });

    els.autoKey.addEventListener('change', () => {
        if(els.autoKey.checked) {
            els.idemKeyDisplay.style.display = 'block';
            els.idemKeyInput.style.display = 'none';
            generateIdemKey();
        } else {
            els.idemKeyDisplay.style.display = 'none';
            els.idemKeyInput.style.display = 'block';
        }
    });

    // Settings & Language
    els.btnSettings.addEventListener('click', (e) => {
        e.stopPropagation();
        els.settingsPopover.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
        if (!els.settingsPopover.contains(e.target) && !els.btnSettings.contains(e.target)) {
            els.settingsPopover.classList.remove('active');
        }
    });

    els.langOptions.forEach(btn => {
        btn.addEventListener('click', () => {
            setLanguage(btn.dataset.lang);
        });
    });

    els.themeOptions.forEach(btn => {
        btn.addEventListener('click', () => {
            setTheme(btn.dataset.themeVal);
        });
    });

    if (els.btnApiSave) {
        els.btnApiSave.addEventListener('click', saveApiOrigin);
    }
    if (els.btnApiReset) {
        els.btnApiReset.addEventListener('click', resetApiOrigin);
    }
    if (els.btnWarmBackend) {
        els.btnWarmBackend.addEventListener('click', () => warmBackend());
    }
    if (els.apiOriginInput) {
        els.apiOriginInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') saveApiOrigin();
        });
    }

    // Buttons
    els.btnExecute.addEventListener('click', executePayment);
    els.btnRace.addEventListener('click', simulateDoubleSpend);
    els.btnReset.addEventListener('click', resetDatabase);
}

function setLanguage(lang, reRender = true) {
    currentLang = lang;
    localStorage.setItem('revLang', lang);
    
    els.langOptions.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });
    
    updateStaticText();
    updateApiDefaultHelper();
    if (reRender && state) {
        render();
    } else if (reRender && lastBackendError) {
        renderDisconnectedState(lastBackendError, false);
    }
    setBackendStatus(backendStatus, backendStatusDetail);
}

function setTheme(theme) {
    currentTheme = theme;
    localStorage.setItem('revTheme', theme);
    
    document.documentElement.setAttribute('data-theme', theme);
    
    els.themeOptions.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.themeVal === theme);
    });
}

function formatAmountInput() {
    const value = parseFloat(els.amount.value);
    if (!Number.isFinite(value)) return;
    els.amount.value = value.toFixed(2);
}

function updateApiDefaultHelper() {
    if (!els.apiDefaultHelper) return;

    const defaultOrigin = getDefaultApiOrigin();
    const defaultLabel = defaultOrigin === DEFAULT_REMOTE_API_ORIGIN
        ? t('apiDefaultRender')
        : t('apiDefaultLocal');

    els.apiDefaultHelper.textContent = `${t('apiDefaultHelper')}: ${defaultLabel} · ${defaultOrigin}`;
    if (els.apiOriginInput) {
        els.apiOriginInput.placeholder = defaultOrigin;
    }
}

function setBackendStatus(status, detail = '') {
    backendStatus = status;
    backendStatusDetail = detail;
    if (!els.apiStatus) return;

    const labels = {
        idle: t('apiStatusIdle'),
        checking: t('apiStatusChecking'),
        waking: t('apiStatusWaking'),
        online: detail ? `${t('apiStatusOnline')} · ${detail}` : t('apiStatusOnline'),
        offline: detail || t('apiStatusOffline'),
        timeout: t('apiStatusTimeout')
    };

    els.apiStatus.className = `backend-status ${status}`;
    els.apiStatus.textContent = labels[status] || labels.idle;
}

function saveApiOrigin() {
    currentApiOrigin = normalizeApiOrigin(els.apiOriginInput.value);
    localStorage.setItem(API_ORIGIN_STORAGE_KEY, currentApiOrigin);
    els.apiOriginInput.value = currentApiOrigin;
    updateApiDefaultHelper();
    showToast(t('toastSuccess'), t('apiSaved'), 'success');
    fetchState();
}

function resetApiOrigin() {
    localStorage.removeItem(API_ORIGIN_STORAGE_KEY);
    currentApiOrigin = normalizeApiOrigin(getDefaultApiOrigin());
    els.apiOriginInput.value = currentApiOrigin;
    updateApiDefaultHelper();
    showToast(t('toastReset'), t('apiReset'), 'success');
    fetchState();
}

async function warmBackend({ silent = false } = {}) {
    if (els.btnWarmBackend) els.btnWarmBackend.disabled = true;
    setBackendStatus('checking');
    const startedAt = Date.now();

    try {
        const res = await fetchWithTimeout(healthUrl(), {}, 65000);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const latency = `${Date.now() - startedAt} ms`;
        setBackendStatus('online', latency);
        if (!silent) {
            showToast(t('toastSuccess'), `${t('apiWarmSuccess')} (${latency})`, 'success');
        }
        await fetchState({ showError: false });
        return true;
    } catch (err) {
        const isTimeout = err.name === 'AbortError';
        setBackendStatus(isTimeout ? 'timeout' : 'offline');
        if (!silent) {
            showToast(t('toastError'), t('apiWarmFail'), 'error');
        }
        return false;
    } finally {
        if (els.btnWarmBackend) els.btnWarmBackend.disabled = false;
    }
}

// Data Fetching
async function fetchState({ showError = true } = {}) {
    const useRemoteWake = shouldUseRemoteWakeStatus();
    let remoteWakeHintTimer = null;

    setBackendStatus(useRemoteWake ? 'waking' : 'checking');
    if (useRemoteWake && showError && !remoteWakeHintShown) {
        remoteWakeHintTimer = window.setTimeout(() => {
            remoteWakeHintShown = true;
            showToast(t('apiRemoteWakeHintTitle'), t('apiRemoteWakeHintBody'), 'warning');
        }, 900);
    }

    try {
        const res = await fetchWithTimeout(apiUrl('state'), {}, getStateFetchTimeoutMs());
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        state = await res.json();
        lastBackendError = null;
        render();
        setBackendStatus('online', currentApiOrigin);
    } catch (err) {
        lastBackendError = err;
        renderDisconnectedState(err, showError);
        setBackendStatus(err.name === 'AbortError' ? 'timeout' : 'offline');
        if (showError) {
            showToast(t('toastError'), t('errBackend'), 'error');
        }
    } finally {
        if (remoteWakeHintTimer) {
            window.clearTimeout(remoteWakeHintTimer);
        }
    }
}

function renderDisconnectedState(_err, showError = true) {
    state = null;
    removeSkeletons();

    els.invariantCard.className = 'invariant-card err';
    els.invariantCard.innerHTML = `
        <svg class="inv-icon err"><use href="#icon-alert"></use></svg>
        <div class="inv-details">
            <div class="inv-label">${t('apiStatusOffline')}</div>
            <div class="inv-value err">${t('offlineInvariant')}</div>
        </div>
    `;

    els.metricDebits.textContent = '--';
    els.metricCredits.textContent = '--';
    els.metricTxns.textContent = '--';
    els.metricTxnsSub.textContent = '';
    els.metricEntries.textContent = '--';
    els.metricEntriesSub.textContent = '';
    els.footerPayments.textContent = `${t('footerPayments')}0`;

    els.sender.innerHTML = '';
    els.receiver.innerHTML = '';
    els.senderBalance.textContent = `${t('balPrefix')}--`;
    els.fxCalc.textContent = t('offlineFlow');
    els.flowCard.textContent = t('offlineFlow');

    els.badgeAccounts.textContent = '0';
    els.badgeTxns.textContent = '0';
    els.badgeEntries.textContent = '0';
    els.tableAccounts.innerHTML = `<tr><td colspan="5" class="empty-cell">${t('apiStatusOffline')}</td></tr>`;
    els.tableTxns.innerHTML = `<tr><td colspan="6" class="empty-cell">${t('apiStatusOffline')}</td></tr>`;
    els.tableEntries.innerHTML = `<tr><td colspan="6" class="empty-cell">${t('apiStatusOffline')}</td></tr>`;

    els.btnExecute.disabled = true;
    els.btnRace.disabled = true;
    els.btnReset.disabled = true;

    if (showError && els.apiOriginInput) {
        els.apiOriginInput.value = currentApiOrigin;
    }
}

// Rendering
function render() {
    removeSkeletons();
    els.btnReset.disabled = false;
    els.btnRace.disabled = false;
    if (els.apiOriginInput) {
        els.apiOriginInput.value = currentApiOrigin;
    }
    
    // Invariant
    const inv = state.invariant;
    const svgIcon = inv.balanced ? '<svg class="inv-icon ok"><use href="#icon-check"></use></svg>' : '<svg class="inv-icon err"><use href="#icon-alert"></use></svg>';
    els.invariantCard.className = `invariant-card ${inv.balanced ? 'ok' : 'err'}`;
    els.invariantCard.innerHTML = `
        ${svgIcon}
        <div class="inv-details">
            <div class="inv-label">${t('invLabel')}</div>
            <div class="inv-value ${inv.balanced ? 'ok' : 'err'}">
                ${inv.balanced ? t('invBalanced') : t('invImbalance') + (inv.net/100).toFixed(2)}
            </div>
        </div>
    `;

    // Metrics
    const formatCurrency = (cents) => {
        return (cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    els.metricDebits.textContent = formatCurrency(state.metrics.total_debits_cents);
    els.metricCredits.textContent = formatCurrency(state.metrics.total_credits_cents);
    els.metricTxns.textContent = state.metrics.transaction_count;
    els.metricTxnsSub.textContent = `(${state.metrics.user_transaction_count}${state.metrics.user_transaction_count === 1 ? t('userCount') : t('usersCount')})`;
    els.metricEntries.textContent = state.metrics.entry_count;
    els.metricEntriesSub.textContent = `(${state.metrics.account_count}${state.metrics.account_count === 1 ? t('accountCount') : t('accountsCount')})`;
    els.footerPayments.textContent = `${t('footerPayments')}${state.session.pay_n}`;

    // Selects
    const prevSender = els.sender.value;
    const prevReceiver = els.receiver.value;
    
    els.sender.innerHTML = '';
    els.receiver.innerHTML = '';
    
    state.user_accounts.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = `${tDyn(a.name)} (${a.currency})`;
        
        els.sender.appendChild(opt.cloneNode(true));
        els.receiver.appendChild(opt);
    });

    if (prevSender) els.sender.value = prevSender;
    if (prevReceiver) els.receiver.value = prevReceiver;
    else if (els.receiver.options.length > 1) els.receiver.selectedIndex = 1;

    // Tables
    els.badgeAccounts.textContent = state.tables.accounts.length;
    els.tableAccounts.innerHTML = state.tables.accounts.map(r => `
        <tr class="${r.type === 'CORPORATE_FX_CLEARING' ? 'hl-fx' : ''}">
            <td>${r.id}</td>
            <td>${tDyn(r.name)}</td>
            <td>${tDyn(r.type)}</td>
            <td>${r.currency}</td>
            <td>${r.currency} ${r.balance_display}</td>
        </tr>
    `).join('');

    els.badgeTxns.textContent = state.tables.transactions.length;

    // Build a Set of transaction IDs that have already been reversed.
    // A reversal's idempotency_key is "REV-{original_key}".
    const reversedKeys = new Set();
    const reversalTxnIds = new Set();
    state.tables.transactions.forEach(r => {
        if (r.idempotency_key.startsWith('REV-')) {
            // This is a reversal transaction — find the original key
            const originalKey = r.idempotency_key.slice(4);
            // Find the original transaction by its key
            const orig = state.tables.transactions.find(t => t.idempotency_key === originalKey);
            if (orig) reversedKeys.add(orig.id);
            reversalTxnIds.add(r.id);
        }
    });

    els.tableTxns.innerHTML = state.tables.transactions.map(r => {
        const isSeed = r.idempotency_key.startsWith('SEED');
        const isReversal = reversalTxnIds.has(r.id);
        const isReversed = reversedKeys.has(r.id);
        const canReverse = !isSeed && !isReversal && !isReversed;

        let descHtml = tDyn(r.description);
        if (isReversed) descHtml = `<span class="td-reversed">${descHtml}</span><span class="badge-reversed">${t('badgeReversed')}</span>`;
        if (isReversal) descHtml = `${descHtml}<span class="badge-reversal">${t('badgeReversal')}</span>`;

        const actionHtml = canReverse
            ? `<button class="btn-icon-reverse" onclick="reverseTransaction(${r.id})" title="${t('btnReverse')}">
                   <svg><use href="#icon-undo"></use></svg>${t('btnReverse')}
               </button>`
            : isSeed ? '<span style="opacity:0.3">—</span>'
            : isReversed ? `<span style="opacity:0.45; font-size:11px;">${t('badgeReversed')}</span>`
            : '<span style="opacity:0.3">—</span>';

        return `
            <tr>
                <td>${r.id}</td>
                <td>${r.timestamp.split('.')[0]}</td>
                <td class="mono">${r.idempotency_key}</td>
                <td>${descHtml}</td>
                <td>${r.legs}</td>
                <td>${actionHtml}</td>
            </tr>
        `;
    }).join('');

    els.badgeEntries.textContent = state.tables.entries.length;
    els.tableEntries.innerHTML = state.tables.entries.map(r => {
        const isFx = r.account_type === 'CORPORATE_FX_CLEARING';
        const isDebit = r.direction === 'DEBIT';
        return `
            <tr class="${isFx ? 'hl-fx' : ''}">
                <td>${r.id}</td>
                <td>${r.txn_id}</td>
                <td>${tDyn(r.account_name)}</td>
                <td>${r.currency}</td>
                <td class="${isDebit ? 'td-debit' : 'td-credit'}">${tDyn(r.direction)}</td>
                <td class="${isDebit ? 'td-debit' : 'td-credit'}">${r.currency} ${r.amount_display}</td>
            </tr>
        `;
    }).join('');

    updateFormState();
}

function updateFormState() {
    if (!state) {
        els.btnExecute.disabled = true;
        els.btnRace.disabled = true;
        els.btnReset.disabled = true;
        return;
    }
    
    const senderId = parseInt(els.sender.value);
    const receiverId = parseInt(els.receiver.value);
    
    const sender = state.user_accounts.find(a => a.id === senderId);
    const receiver = state.user_accounts.find(a => a.id === receiverId);
    
    if (!sender || !receiver) return;

    els.senderBalance.innerHTML = `${t('balPrefix')}<strong>${sender.currency} ${sender.balance_display}</strong>`;
    
    const amt = parseFloat(els.amount.value) || 0;
    const rate = parseFloat(els.fxRate.value) || 1;
    const recvAmt = amt * rate;
    
    const formatNum = (num) => num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
    els.fxCalc.innerHTML = `${t('rcvPrefix')}<strong>${receiver.currency} ${formatNum(recvAmt)}</strong> · 1 ${sender.currency} = ${rate.toFixed(2)} ${receiver.currency}`;

    els.btnExecute.disabled = senderId === receiverId || amt <= 0;
    els.btnRace.disabled = senderId === receiverId;
    els.btnReset.disabled = false;

    // Update Flow Diagram
    const formatName = (name) => currentLang === 'es' ? name.replace('User', 'Usuario') : name;
    const senderName = formatName(sender.name);
    const receiverName = formatName(receiver.name);

    els.flowCard.innerHTML = `
<span class="fc-brand">${senderName}</span>  <span>──</span>  <span class="fc-credit">${t('txtCredit')}</span>  <span>──▶</span>  <span class="fc-node">${t('fxClearing')} (${sender.currency})</span>  <span>──</span>  <span class="fc-debit">${t('txtDebit')}</span>  <span>──▶</span>  <span class="fc-node">${t('fxClearing')} (${receiver.currency})</span>  <span>──</span>  <span class="fc-credit">${t('txtCredit')}</span>  <span>──▶</span>  <span class="fc-debit">${receiverName}</span>

<span>${t('txtLeg')} 1</span>  <span class="fc-credit">${t('txtCredit')}</span> ${senderName} <span>${sender.currency} ${formatNum(amt)}</span>   →   <span class="fc-debit">${t('txtDebit')}</span> ${t('fxClearing')} (${sender.currency}) <span>${sender.currency} ${formatNum(amt)}</span>
<span>${t('txtLeg')} 2</span>  <span class="fc-credit">${t('txtCredit')}</span> ${t('fxClearing')} (${receiver.currency}) <span>${receiver.currency} ${formatNum(recvAmt)}</span>   →   <span class="fc-debit">${t('txtDebit')}</span> ${receiverName} <span>${receiver.currency} ${formatNum(recvAmt)}</span>
    `.trim();
}

function removeSkeletons() {
    document.querySelectorAll('.skeleton').forEach(el => el.classList.remove('skeleton'));
    document.querySelectorAll('.skeleton-text').forEach(el => el.classList.remove('skeleton-text'));
}

function generateIdemKey() {
    const d = new Date();
    const ts = d.toISOString().replace(/[-:T]/g, '').slice(0,14);
    const rnd = Math.random().toString(36).substring(2, 8).toUpperCase();
    const key = `PAY-${ts}-${rnd}`;
    els.idemKeyDisplay.textContent = key;
    return key;
}

function showToast(title, msg, type = 'success') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<strong>${title}</strong><br>${msg}`;
    els.toastContainer.appendChild(t);
    setTimeout(() => t.remove(), 5000);
}

// API Actions
async function executePayment() {
    els.btnExecute.disabled = true;
    
    const payload = {
        sender_id: parseInt(els.sender.value),
        receiver_id: parseInt(els.receiver.value),
        send_dollars: parseFloat(els.amount.value),
        fx_rate: parseFloat(els.fxRate.value),
        idempotency_key: els.autoKey.checked ? els.idemKeyDisplay.textContent : els.idemKeyInput.value,
        locking_strategy: els.lockingStrategy.value
    };

    try {
        const res = await fetchWithTimeout(apiUrl('payment'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showToast(t('toastSuccess'), tDyn(data.message), 'success');
            if(els.autoKey.checked) generateIdemKey();
            await fetchState();
        } else {
            showToast(t('toastError'), tDyn(data.detail), 'error');
        }
    } catch (err) {
        showToast(t('toastError'), t('errPayment'), 'error');
    } finally {
        updateFormState(); // re-evaluates button disable logic
    }
}

async function resetDatabase() {
    els.btnReset.disabled = true;
    try {
        const res = await fetchWithTimeout(apiUrl('reset'), { method: 'POST' });
        if(res.ok) {
            showToast(t('toastReset'), t('msgDbReset'), 'success');
            await fetchState();
            if(els.autoKey.checked) generateIdemKey();
        } else {
            const data = await res.json();
            showToast(t('toastError'), tDyn(data.detail || t('errReset')), 'error');
        }
    } catch (err) {
        showToast(t('toastError'), t('errReset'), 'error');
    } finally {
        els.btnReset.disabled = false;
    }
}

// ── Race Condition Simulator ────────────────────────────────────────
async function simulateDoubleSpend() {
    els.btnRace.disabled = true;
    els.btnExecute.disabled = true;

    const senderId = parseInt(els.sender.value);
    const receiverId = parseInt(els.receiver.value);
    const sender = state.user_accounts.find(a => a.id === senderId);

    if (!sender || senderId === receiverId) {
        showToast(t('toastError'), t('errSameSenderReceiver'), 'error');
        els.btnRace.disabled = false;
        updateFormState();
        return;
    }

    // Auto-drain entire balance: use the sender's full balance
    const drainDollars = sender.balance_cents / 100;
    if (drainDollars <= 0) {
        showToast(t('toastError'), t('errZeroBalance'), 'error');
        els.btnRace.disabled = false;
        updateFormState();
        return;
    }

    const strategy = els.lockingStrategy.value;
    const fxRate = parseFloat(els.fxRate.value);

    const basePayload = {
        sender_id: senderId,
        receiver_id: receiverId,
        send_dollars: drainDollars,
        fx_rate: fxRate,
        locking_strategy: strategy,
    };

    const keyA = generateIdemKey();
    const keyB = generateIdemKey();
    const payloadA = { ...basePayload, idempotency_key: keyA };
    const payloadB = { ...basePayload, idempotency_key: keyB };

    const headers = { 'Content-Type': 'application/json' };

    try {
        // Fire both requests at the exact same instant
        const [resA, resB] = await Promise.all([
            fetchWithTimeout(apiUrl('payment'), { method: 'POST', headers, body: JSON.stringify(payloadA) }),
            fetchWithTimeout(apiUrl('payment'), { method: 'POST', headers, body: JSON.stringify(payloadB) })
        ]);

        const dataA = await resA.json();
        const dataB = await resB.json();

        // Build race results display
        const resultA = resA.ok
            ? `<div class="race-result win"><strong>${t('raceThreadA')}: ${t('raceSuccess')}</strong>${tDyn(dataA.message)}</div>`
            : `<div class="race-result lose"><strong>${t('raceThreadA')}: ${t('raceFailed')} (${resA.status})</strong>${tDyn(dataA.detail)}</div>`;
        const resultB = resB.ok
            ? `<div class="race-result win"><strong>${t('raceThreadB')}: ${t('raceSuccess')}</strong>${tDyn(dataB.message)}</div>`
            : `<div class="race-result lose"><strong>${t('raceThreadB')}: ${t('raceFailed')} (${resB.status})</strong>${tDyn(dataB.detail)}</div>`;

        const strategyLabel = strategy === 'OCC' ? t('optOptimistic') : t('optPessimistic');
        const raceHtml = `
            <strong>${t('raceTitle')} — ${strategyLabel}</strong>
            <div style="font-size:11px;margin:4px 0 6px;opacity:0.7">Drain amount: ${sender.currency} ${drainDollars.toFixed(2)} × 2 threads</div>
            <div class="race-results">${resultA}${resultB}</div>
        `;
        showToast('', raceHtml, resA.ok !== resB.ok ? 'warning' : (resA.ok && resB.ok ? 'error' : 'success'));

        if (els.autoKey.checked) generateIdemKey();
        await fetchState();
    } catch (err) {
        showToast(t('toastError'), t('errRaceNet'), 'error');
    } finally {
        els.btnRace.disabled = false;
        updateFormState();
    }
}

// ── Transaction Reversal ────────────────────────────────────────────
async function reverseTransaction(txnId) {
    try {
        const res = await fetchWithTimeout(apiUrl(`reverse/${txnId}`), { method: 'POST' });
        const data = await res.json();

        if (res.ok) {
            showToast(t('toastSuccess'), tDyn(data.message), 'success');
            await fetchState();
        } else {
            showToast(t('toastError'), tDyn(data.detail), 'error');
        }
    } catch (err) {
        showToast(t('toastError'), t('errRevNet'), 'error');
    }
}
// Make reverseTransaction available globally for onclick handlers
window.reverseTransaction = reverseTransaction;

// Boot
init();
