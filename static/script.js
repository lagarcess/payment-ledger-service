const API_BASE = 'http://127.0.0.1:8000/api';

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
        errBackend: "Failed to connect to backend engine.", errPayment: "Network error executing payment.", errReset: "Failed to reset database.",
        txtCredit: "CREDIT", txtDebit: "DEBIT", txtLeg: "Leg", fxClearing: "FX Clearing",
        appTitle: "Appearance", appSystem: "System", appLight: "Light", appDark: "Dark",
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
        errBackend: "Sin conexión al motor contable.", errPayment: "Error de red procesando la transferencia.", errReset: "Error al reiniciar el entorno.",
        txtCredit: "ABONO", txtDebit: "CARGO", txtLeg: "Apunte", fxClearing: "Compensación",
        appTitle: "Apariencia", appSystem: "Sistema", appLight: "Claro", appDark: "Oscuro",
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
    
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content')
};

// State
let state = null;
let currentSenderId = null;
let currentReceiverId = null;

// Initialization
async function init() {
    setupEventListeners();
    setLanguage(currentLang, false);
    setTheme(currentTheme);
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
        if (!els.settingsPopover.contains(e.target) && e.target !== els.btnSettings) {
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
    if (reRender && state) {
        render();
    }
}

function setTheme(theme) {
    currentTheme = theme;
    localStorage.setItem('revTheme', theme);
    
    document.documentElement.setAttribute('data-theme', theme);
    
    els.themeOptions.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.themeVal === theme);
    });
}

// Data Fetching
async function fetchState() {
    try {
        const res = await fetch(`${API_BASE}/state`);
        state = await res.json();
        render();
    } catch (err) {
        showToast(t('toastError'), t('errBackend'), 'error');
    }
}

// Rendering
function render() {
    removeSkeletons();
    
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
    if (!state) return;
    
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
        const res = await fetch(`${API_BASE}/payment`, {
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
        const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
        if(res.ok) {
            showToast(t('toastReset'), t('msgDbReset'), 'success');
            await fetchState();
            if(els.autoKey.checked) generateIdemKey();
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
            fetch(`${API_BASE}/payment`, { method: 'POST', headers, body: JSON.stringify(payloadA) }),
            fetch(`${API_BASE}/payment`, { method: 'POST', headers, body: JSON.stringify(payloadB) })
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
        const res = await fetch(`${API_BASE}/reverse/${txnId}`, { method: 'POST' });
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
