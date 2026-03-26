const CATEGORIES = [
  { key:"linkedin",   label:"LinkedIn",               icon:"💼", group:"social"     },
  { key:"instagram",  label:"Instagram",              icon:"📸", group:"social"     },
  { key:"facebook",   label:"Facebook",               icon:"📘", group:"social"     },
  { key:"twitter",    label:"X / Twitter",            icon:"🐦", group:"social"     },
  { key:"vk",         label:"VKontakte",              icon:"🅥", group:"social"     },
  { key:"whitepages", label:"Whitepages / Annuaires", icon:"📞", group:"whitepages" },
  { key:"images",     label:"Galerie d'Images",       icon:"🖼️", group:"images"     },
];

let currentTab = "all";
let panelState = {};
let lastData   = null;
let currentSid = null;
let activeSSE  = null;

CATEGORIES.forEach(c => panelState[c.key] = { visible:true, expanded:false });

// DOM refs
const heroEl    = document.getElementById("hero");
const loaderEl  = document.getElementById("loader");
const errorEl   = document.getElementById("errorBox");
const resultsEl = document.getElementById("results");
const gridEl    = document.getElementById("resultsGrid");
const searchWrap= document.getElementById("searchWrap");
const headerInp = document.getElementById("queryInput");
const heroInp   = document.getElementById("heroInput");

// ── STEP INDICATOR ────────────────────────────────────────────────────────────
function setStep(key, state, count) {
  const el = document.getElementById("s-" + key);
  if (!el) return;
  el.classList.remove("done","active","captcha-step");
  if (state === "active")   el.classList.add("active");
  if (state === "done")     { el.classList.add("done");   if (count !== undefined) el.textContent = el.textContent.split("(")[0].trim() + ` (${count})`; }
  if (state === "captcha")  { el.classList.add("captcha-step"); el.textContent = el.textContent.split("(")[0].trim() + " 🤖"; }
}

// ── SEARCH ────────────────────────────────────────────────────────────────────
function doSearch(e) {
  e.preventDefault();
  const q = (heroInp.value || headerInp.value).trim();
  if (!q) return;
  heroInp.value = headerInp.value = q;
  startSearch(q);
}

async function startSearch(query) {
  if (activeSSE) { activeSSE.close(); activeSSE = null; }
  lastData = {};
  heroEl.classList.add("hidden");
  searchWrap.classList.add("visible");
  loaderEl.classList.remove("hidden");
  errorEl.classList.add("hidden");
  resultsEl.classList.remove("hidden");
  gridEl.innerHTML = "";
  CATEGORIES.forEach(c => setStep(c.key, ""));

  // Créer les panels vides immédiatement
  CATEGORIES.forEach(cat => {
    if (!matchesTab(cat)) return;
    lastData[cat.key] = [];
    gridEl.appendChild(buildPanel(cat, []));
  });

  try {
    const r   = await fetch(`/search/start?q=${encodeURIComponent(query)}`);
    const res = await r.json();
    if (res.error) { showError(res.error); loaderEl.classList.add("hidden"); return; }
    currentSid = res.sid;
    connectSSE(res.sid);
  } catch(err) {
    showError("Erreur réseau : " + err.message);
    loaderEl.classList.add("hidden");
  }
}

function connectSSE(sid) {
  const sse = new EventSource(`/events/${sid}`);
  activeSSE  = sse;
  sse.onmessage = (e) => handleEvt(JSON.parse(e.data), sid);
  sse.onerror   = () => { sse.close(); loaderEl.classList.add("hidden"); };
}

function handleEvt(evt, sid) {
  if (evt.type === "ping") return;

  if (evt.type === "scanning") {
    setStep(evt.category, "active");
    document.getElementById("loaderMsg").textContent = `🔎 Scan ${evt.category}…`;
  }

  if (evt.type === "cat_done") {
    setStep(evt.category, "done", evt.count);
    lastData[evt.category] = evt.results || [];
    // Mise à jour progressive du panel
    const cat = CATEGORIES.find(c => c.key === evt.category);
    if (cat && matchesTab(cat)) refreshPanel(cat, lastData[evt.category]);
  }

  if (evt.type === "captcha") {
    setStep(evt.category, "captcha");
    showCaptchaModal(evt.category, sid);
  }

  if (evt.type === "captcha_solved") {
    setStep(evt.category, "active");
    closeCaptchaModal();
  }

  if (evt.type === "complete") {
    activeSSE?.close();
    activeSSE = null;
    loaderEl.classList.add("hidden");
    if (evt.data) {
      lastData = evt.data;
      renderResults(lastData);
    }
  }
}

// ── CAPTCHA MODAL ─────────────────────────────────────────────────────────────
function showCaptchaModal(category, sid) {
  document.getElementById("captchaCategory").textContent =
    CATEGORIES.find(c => c.key === category)?.label || category;
  const modal = document.getElementById("captchaModal");
  modal.classList.remove("hidden");
  document.getElementById("captchaAckBtn").onclick = async () => {
    await fetch(`/captcha/ack/${sid}`, { method: "POST" });
    closeCaptchaModal();
  };
}
function skipCaptcha() {
  // L'user ignore : on close juste le modal, le scraper timeout tout seul après 120s
  closeCaptchaModal();
}
function closeCaptchaModal() {
  document.getElementById("captchaModal").classList.add("hidden");
}

// ── TAB FILTER ────────────────────────────────────────────────────────────────
function filterTab(tab, el) {
  currentTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  el.classList.add("active");
  if (lastData) renderResults(lastData);
}

function matchesTab(cat) {
  if (currentTab === "all")        return true;
  if (currentTab === "images")     return cat.key === "images";
  if (currentTab === "whitepages") return cat.key === "whitepages";
  if (currentTab === "social")     return cat.group === "social";
  if (currentTab === "people")     return ["linkedin","whitepages"].includes(cat.key);
  return true;
}

// ── RENDER ────────────────────────────────────────────────────────────────────
function renderResults(data) {
  gridEl.innerHTML = "";
  resultsEl.classList.remove("hidden");
  CATEGORIES.filter(matchesTab).forEach(cat =>
    gridEl.appendChild(buildPanel(cat, data[cat.key] || []))
  );
}

function refreshPanel(cat, items) {
  const existing = document.getElementById("panel-" + cat.key);
  const newPanel = buildPanel(cat, items);
  if (existing) {
    existing.replaceWith(newPanel);
  } else {
    if (matchesTab(cat)) gridEl.appendChild(newPanel);
  }
}

function buildPanel(cat, items) {
  const st  = panelState[cat.key];
  const div = document.createElement("div");
  div.className = "panel panel-" + cat.key + (st.expanded ? " expanded" : "");
  div.id = "panel-" + cat.key;

  div.innerHTML = `
    <div class="panel-header">
      <span class="panel-icon">${cat.icon}</span>
      <span class="panel-title">${cat.label}</span>
      <span class="panel-count">${items.length} résultats</span>
      <button class="btn-expand" onclick="toggleExpand('${cat.key}')">
        ${st.expanded ? "▲ Réduire" : "▼ Tout voir"}
      </button>
      <button class="btn-eye ${st.visible ? "" : "masked"}"
        onclick="toggleVisibility('${cat.key}')">
        ${st.visible ? "👁" : "🚫"}
      </button>
    </div>
    <div class="panel-body${st.visible ? "" : " hidden-body"}" id="body-${cat.key}"></div>`;

  fillBody(div.querySelector("#body-" + cat.key), cat, items, st.expanded);
  return div;
}

function fillBody(body, cat, items, expanded) {
  body.innerHTML = "";
  if (cat.key === "images") { body.appendChild(buildGallery(items)); return; }
  if (!items.length) { body.innerHTML = `<div class="empty-state">Aucun résultat trouvé.</div>`; return; }
  const limit = expanded ? items.length : Math.min(3, items.length);
  items.slice(0, limit).forEach(it => body.appendChild(buildItem(it)));
}

function buildItem(it) {
  const a = document.createElement("a");
  a.className = "result-item";
  a.href = it.url || "#";
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  const disp = (it.url || "").replace(/^https?:\/\//,"").split("?")[0].substring(0,70);
  a.innerHTML = `
    <div class="result-title">${esc(it.title||"(sans titre)")}</div>
    <div class="result-url">${esc(disp)}</div>
    <div class="result-snippet">${esc(it.snippet||"")}</div>`;
  return a;
}

function buildGallery(images) {
  const g = document.createElement("div");
  g.className = "img-gallery";
  if (!images.length) {
    g.innerHTML = `<div class="empty-state" style="grid-column:1/-1">Aucune image trouvée.</div>`;
    return g;
  }
  images.forEach(img => {
    const a = document.createElement("div");
    a.className = "img-thumb";
    a.innerHTML = `
      <img src="${esc(img.src)}" alt="${esc(img.alt||"")}" loading="lazy"
           onerror="this.closest('.img-thumb').style.display='none'"/>
      <div class="img-label">${esc(img.alt||img.filename||"")}</div>`;
    a.addEventListener("click", () => openImgModal(img));
    g.appendChild(a);
  });
  return g;
}

// ── IMAGE MODAL ───────────────────────────────────────────────────────────────
function openImgModal(img) {
  document.getElementById("imgModalSrc").src = img.src;
  document.getElementById("imgModalCaption").textContent = img.alt || img.filename || "";
  document.getElementById("imgModalLink").href = img.source_url || img.src;
  document.getElementById("imgModal").classList.remove("hidden");
}
function closeImgModal() {
  document.getElementById("imgModal").classList.add("hidden");
  document.getElementById("imgModalSrc").src = "";
}

// ── PANEL CONTROLS ────────────────────────────────────────────────────────────
function toggleVisibility(key) {
  const st = panelState[key];
  st.visible = !st.visible;
  document.getElementById("body-" + key)?.classList.toggle("hidden-body", !st.visible);
  const btn = document.querySelector(`#panel-${key} .btn-eye`);
  if (btn) { btn.textContent = st.visible ? "👁" : "🚫"; btn.classList.toggle("masked", !st.visible); }
}

function toggleExpand(key) {
  const st    = panelState[key];
  st.expanded = !st.expanded;
  const panel = document.getElementById("panel-" + key);
  const body  = document.getElementById("body-" + key);
  const btn   = panel?.querySelector(".btn-expand");
  const cat   = CATEGORIES.find(c => c.key === key);
  panel?.classList.toggle("expanded", st.expanded);
  if (btn) btn.textContent = st.expanded ? "▲ Réduire" : "▼ Tout voir";
  if (cat?.key !== "images") fillBody(body, cat, (lastData && lastData[key]) || [], st.expanded);
}

// ── MISC ──────────────────────────────────────────────────────────────────────
function clearSearch() {
  if (activeSSE) { activeSSE.close(); activeSSE = null; }
  headerInp.value = heroInp.value = "";
  heroEl.classList.remove("hidden");
  searchWrap.classList.remove("visible");
  resultsEl.classList.add("hidden");
  errorEl.classList.add("hidden");
  loaderEl.classList.add("hidden");
  gridEl.innerHTML = "";
  lastData = null;
}
function showError(msg) {
  errorEl.textContent = "⚠️ " + msg;
  errorEl.classList.remove("hidden");
}
function closeFAQ(e) {
  if (e.target.id === "faqOverlay") document.getElementById("faqOverlay").classList.add("hidden");
}
function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
heroInp.addEventListener("input",   () => { headerInp.value = heroInp.value; });
headerInp.addEventListener("input", () => { heroInp.value = headerInp.value; });
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    document.getElementById("faqOverlay").classList.add("hidden");
    closeImgModal();
    closeCaptchaModal();
  }
});