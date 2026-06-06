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
        errBackend: "Failed to connect to backend engine.", errPayment: "Network error executing payment.", errReset: "Failed to reset database."
    },
    es: {
        sbTitle: "Terminal de Pagos", sbDesc: "Ejecuta transferencias entre divisas a través del motor de compensación FX.",
        langTitle: "Idioma", lblSenderReceiver: "Emisor y Receptor", lblSender: "Emisor", lblReceiver: "Receptor",
        lblPaymentParams: "Parámetros de Pago", lblAmount: "Monto", lblFxRate: "Tasa de Cambio FX", lblIdempotency: "Idempotencia",
        lblAutoGenerate: "Generar clave automática", btnExecute: "Ejecutar Pago", btnReset: "Restablecer Base de Datos",
        mainTitle: "Motor de Libro Mayor", mainSubtitle: "Libro de pagos de doble entrada · Compensación cruzada de divisas FX · Monitoreo de invariantes",
        metDebits: "TOTAL DÉBITOS", metCredits: "TOTAL CRÉDITOS", metTxns: "TRANSACCIONES", metEntries: "ASIENTOS",
        flowTitle: "Flujo de Pago", flowDesc: "Ruta de liquidación cruzada de divisas a través de la Cuenta Corporativa FX.",
        accTitle: "Cuentas", accDesc: "Cuentas de Compensación FX resaltadas sutilmente.",
        thId: "ID", thAccount: "CUENTA", thType: "TIPO", thCurrency: "DIVISA", thBalance: "SALDO",
        tabJournal: "Asientos de Diario", tabLegs: "Líneas de Libro Mayor", txnsTitle: "Transacciones",
        thTimestamp: "FECHA Y HORA", thIdemKey: "CLAVE DE IDEMPOTENCIA", thDesc: "DESCRIPCIÓN", thLegs: "LÍNEAS",
        entriesTitle: "Líneas de Asiento", entriesDesc: "DÉBITO en turquesa · CRÉDITO en rojo.", thTxn: "TXN", thDirection: "DIRECCIÓN", thAmount: "MONTO",
        balPrefix: "Saldo: ", rcvPrefix: "Receptor recibe ", invBalanced: "PERFECTAMENTE BALANCEADO (0.00) ─ Σ Débitos == Σ Créditos",
        invImbalance: "DESBALANCE DETECTADO ─ Neto: ", invLabel: "Invariante del Sistema", userCount: " usuario", usersCount: " usuarios",
        accountCount: " cuenta", accountsCount: " cuentas", footerPayments: "Pagos en esta sesión: ",
        toastSuccess: "Éxito", toastError: "Error", toastReset: "Restablecido", msgDbReset: "Base de datos restablecida al estado inicial.",
        errBackend: "No se pudo conectar al motor backend.", errPayment: "Error de red al ejecutar el pago.", errReset: "No se pudo restablecer la base de datos."
    }
};

let currentLang = localStorage.getItem('revLang') || 'en';

function t(key) {
    return i18n[currentLang][key] || key;
}

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
    btnReset: document.getElementById('btn-reset'),
    toastContainer: document.getElementById('toast-container'),
    footerPayments: document.getElementById('footer-payments'),
    
    btnSettings: document.getElementById('btn-settings'),
    settingsPopover: document.getElementById('settings-popover'),
    langOptions: document.querySelectorAll('.lang-option'),
    
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
            els.settingsPopover.classList.remove('active');
        });
    });

    // Buttons
    els.btnExecute.addEventListener('click', executePayment);
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
        opt.textContent = `${a.name} (${a.currency})`;
        
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
            <td>${r.name}</td>
            <td>${r.type}</td>
            <td>${r.currency}</td>
            <td>${r.currency} ${r.balance_display}</td>
        </tr>
    `).join('');

    els.badgeTxns.textContent = state.tables.transactions.length;
    els.tableTxns.innerHTML = state.tables.transactions.map(r => `
        <tr>
            <td>${r.id}</td>
            <td>${r.timestamp.split('.')[0]}</td>
            <td style="font-family: monospace;">${r.idempotency_key}</td>
            <td>${r.description}</td>
            <td>${r.legs}</td>
        </tr>
    `).join('');

    els.badgeEntries.textContent = state.tables.entries.length;
    els.tableEntries.innerHTML = state.tables.entries.map(r => {
        const isFx = r.account_type === 'CORPORATE_FX_CLEARING';
        const isDebit = r.direction === 'DEBIT';
        return `
            <tr class="${isFx ? 'hl-fx' : ''}">
                <td>${r.id}</td>
                <td>${r.txn_id}</td>
                <td>${r.account_name}</td>
                <td>${r.currency}</td>
                <td class="${isDebit ? 'td-debit' : 'td-credit'}">${r.direction}</td>
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
    els.flowCard.innerHTML = `
<span class="fc-brand">${sender.name}</span>  <span>──</span>  <span class="fc-credit">CREDIT</span>  <span>──▶</span>  <span class="fc-node">FX Clearing (${sender.currency})</span>  <span>──</span>  <span class="fc-debit">DEBIT</span>  <span>──▶</span>  <span class="fc-node">FX Clearing (${receiver.currency})</span>  <span>──</span>  <span class="fc-credit">CREDIT</span>  <span>──▶</span>  <span class="fc-debit">${receiver.name}</span>

<span>Leg 1</span>  <span class="fc-credit">CREDIT</span> ${sender.name} <span>${sender.currency} ${formatNum(amt)}</span>   →   <span class="fc-debit">DEBIT</span> FX Clearing (${sender.currency}) <span>${sender.currency} ${formatNum(amt)}</span>
<span>Leg 2</span>  <span class="fc-credit">CREDIT</span> FX Clearing (${receiver.currency}) <span>${receiver.currency} ${formatNum(recvAmt)}</span>   →   <span class="fc-debit">DEBIT</span> ${receiver.name} <span>${receiver.currency} ${formatNum(recvAmt)}</span>
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
        idempotency_key: els.autoKey.checked ? els.idemKeyDisplay.textContent : els.idemKeyInput.value
    };

    try {
        const res = await fetch(`${API_BASE}/payment`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showToast(t('toastSuccess'), data.message, 'success');
            if(els.autoKey.checked) generateIdemKey();
            await fetchState();
        } else {
            showToast(t('toastError'), data.detail, 'error');
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

// Boot
init();
