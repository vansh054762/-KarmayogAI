/* KarmayogAI — shared JS utilities */
const API_BASE = '/api';
function getToken() { return localStorage.getItem('token'); }
function getUser()  { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } }
function requireAuth()  { if (!getToken()) { location.href='/login'; return false; } return true; }
function requireAdmin() { if (!getToken()) { location.href='/login'; return false; } const u=getUser(); if (!u||u.role!=='admin') { location.href='/dashboard'; return false; } return true; }
function logout() { localStorage.removeItem('token'); localStorage.removeItem('user'); location.href='/login'; }

async function apiFetch(path, opts={}) {
  const headers = {'Content-Type':'application/json',...opts.headers};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(API_BASE+path, {...opts, headers});
  if (res.status===401) { logout(); return; }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error||'Request failed');
  return data;
}
async function refreshAndGetUser() {
  try { const u=await apiFetch('/auth/profile'); localStorage.setItem('user',JSON.stringify(u)); return u; }
  catch { return getUser()||{}; }
}

/* ── Toast ── */
function showToast(msg, type='ok') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span>${type==='ok'?'✓':'✕'}</span> ${msg}`;
  document.body.appendChild(el);
  setTimeout(()=>{ el.style.opacity='0'; el.style.transition='opacity .3s'; setTimeout(()=>el.remove(),320); }, 3000);
}

/* ── Gap helpers ── */
function gapBadge(score) {
  if (score<50) return `<span class="badge badge-crit">Critical Gap</span>`;
  if (score<70) return `<span class="badge badge-mod">Moderate Gap</span>`;
  if (score<85) return `<span class="badge badge-minor">Minor Gap</span>`;
  return `<span style="display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;font-size:10.5px;font-weight:700;background:#E0EAFF;color:#1A3A8F;border:1.5px solid #7090D8;">Proficient</span>`;
}
function gapColor(score) {
  if (score<50) return '#8C2010';
  if (score<70) return '#8A6010';
  if (score<85) return '#6A4E08';
  return '#2E5234';
}
function diffBadge(diff) {
  const m = {beginner:'badge-beg',intermediate:'badge-int',advanced:'badge-adv'};
  return `<span class="badge ${m[diff]||'badge-base'}">${diff}</span>`;
}

/* ── Active nav ── */
function setActivePage(id) {
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.remove('active'));
  const a = document.getElementById('nav-'+id);
  if (a) a.classList.add('active');
}

/* ── Render shell ── */
async function renderShell(title, pageId) {
  const user = await refreshAndGetUser();
  document.title = 'KarmayogAI — '+title;
  const ne = document.getElementById('user-name'); if (ne) ne.textContent = user.name||'User';
  const re = document.getElementById('user-role'); if (re) re.textContent = user.designation||(user.role==='admin'?'Administrator':'Employee');
  const ae = document.getElementById('user-avatar'); if (ae && user.name) ae.textContent = user.name[0].toUpperCase();
  const adminNav = document.getElementById('admin-nav');
  if (adminNav) adminNav.classList.toggle('hidden', user.role!=='admin');
  setActivePage(pageId);
  return user;
}

/* ── SVG Icons ── */
function iconBook(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M2 6c0-1.1.9-2 2-2h7v16H4a2 2 0 01-2-2V6z"/>
    <path d="M22 6c0-1.1-.9-2-2-2h-7v16h7a2 2 0 002-2V6z"/>
    <path d="M12 4v16"/>
    <path d="M6 9h3M6 12h3M15 9h3M15 12h3"/>
  </svg>`;
}

function iconCheck(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20 6L9 17l-5-5"/>
  </svg>`;
}

function iconPlay(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="5 3 19 12 5 21 5 3"/>
  </svg>`;
}

function iconTime(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>`;
}

function iconInfo(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="16" x2="12" y2="12"/>
    <line x1="12" y1="8" x2="12.01" y2="8"/>
  </svg>`;
}

function iconFolder(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
  </svg>`;
}

function iconCertificate(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="8" r="7"/>
    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
  </svg>`;
}

function iconTrash(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
  </svg>`;
}

function iconUsers(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 00-3-3.87"/>
    <path d="M16 3.13a4 4 0 010 7.75"/>
  </svg>`;
}

function iconChart(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
  </svg>`;
}

function iconTarget(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="6"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>`;
}

function iconMap(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
    <line x1="8" y1="2" x2="8" y2="18"/>
    <line x1="16" y1="6" x2="16" y2="22"/>
  </svg>`;
}

function iconMedal(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="8" r="7"/>
    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
  </svg>`;
}

function iconZap(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>`;
}

function iconTrendUp(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
    <polyline points="17 6 23 6 23 12"/>
  </svg>`;
}

function iconLightbulb(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 18h6"/>
    <path d="M10 22h4"/>
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8a6 6 0 00-12 0c0 1 .23 2.23 1.5 3.5.76.76 1.23 1.5 1.41 2.5"/>
  </svg>`;
}

function iconExternal(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
    <polyline points="15 3 21 3 21 9"/>
    <line x1="10" y1="14" x2="21" y2="3"/>
  </svg>`;
}

/* ── Icon wrapper for stat cards ── */
function iconWrapper(iconFn, bgColor, size=24) {
  return `<div class="stat-icon" style="background:${bgColor};">${iconFn('#7A5540', size)}</div>`;
}

function iconWorld(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
  </svg>`;
}

function iconShield(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>`;
}

function iconX(color='currentColor', size=20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>`;
}