
const API = {
  async call(method, endpoint, body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
    if (body) opts.body = JSON.stringify(body);
    const res  = await fetch('/api' + endpoint, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Sunucu hatası');
    return data;
  },
  register:     (d)       => API.call('POST',   '/auth/register', d),
  login:        (d)       => API.call('POST',   '/auth/login', d),
  logout:       ()        => API.call('POST',   '/auth/logout'),
  me:           ()        => API.call('GET',    '/auth/me'),
  getTrips:     (p = '')  => API.call('GET',    `/trips${p}`),
  createTrip:   (d)       => API.call('POST',   '/trips', d),
  updateTrip:   (id, d)   => API.call('PUT',    `/trips/${id}`, d),
  deleteTrip:   (id)      => API.call('DELETE', `/trips/${id}`),
  getNodes:     ()        => API.call('GET',    '/graph/nodes'),
  getEdges:     ()        => API.call('GET',    '/graph/edges'),
  dijkstra:     (d)       => API.call('POST',   '/graph/dijkstra', d),
  getSummary:   ()        => API.call('GET',    '/stats/summary'),
  getWeekly:    ()        => API.call('GET',    '/stats/weekly'),
  getIntensity: ()        => API.call('GET',    '/stats/intensity'),
  getNodeFreq:  ()        => API.call('GET',    '/stats/nodes'),
  getCO2:       ()        => API.call('GET',    '/stats/co2'),
  getUsers:     ()        => API.call('GET',    '/users'),
  deleteUser:   (id)      => API.call('DELETE', `/users/${id}`),
  getActivity:  (n = 10)  => API.call('GET',    `/activity?limit=${n}`),
  dbInfo:       ()        => API.call('GET',    '/db/info'),
  dbReset:      ()        => API.call('POST',   '/db/reset'),
};



let currentUser = null;

const ROLE_LABELS = {
  admin: '👑 Yönetici', driver: '🚗 Sürücü',
  passenger: '👤 Yolcu',   urban:  '🏙️ Kent Yöneticisi',
};
const ROLE_COLORS = { admin:'bad', driver:'high', passenger:'med', urban:'warn' };

function showRegister() {
  document.getElementById('form-login').classList.remove('active');
  document.getElementById('form-register').classList.add('active');
}
function showLogin() {
  document.getElementById('form-register').classList.remove('active');
  document.getElementById('form-login').classList.add('active');
}

async function doLogin() {
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');
  errEl.style.display = 'none';
  if (!email || !password) { errEl.textContent = 'Tüm alanları doldurunuz.'; errEl.style.display = 'block'; return; }
  try {
    const data = await API.login({ email, password });
    currentUser = data.user;
    launchApp();
  } catch (e) { errEl.textContent = e.message; errEl.style.display = 'block'; }
}

async function doRegister() {
  const name     = document.getElementById('reg-name').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const role     = document.getElementById('reg-role').value;
  const errEl    = document.getElementById('reg-error');
  errEl.style.display = 'none';
  if (!name || !email || !password) { errEl.textContent = 'Tüm alanları doldurunuz.'; errEl.style.display = 'block'; return; }
  if (password.length < 6) { errEl.textContent = 'Şifre çok kısa (en az 6 karakter).'; errEl.style.display = 'block'; return; }
  try {
    const data = await API.register({ name, email, password, role });
    currentUser = data.user;
    launchApp();
  } catch (e) { errEl.textContent = e.message; errEl.style.display = 'block'; }
}

async function doLogout() {
  try { await API.logout(); } catch(e) {}
  currentUser = null;
  ['main','full','route'].forEach(k => {
    const m = window[k + 'MapInstance'];
    if (m) { m.remove(); window[k + 'MapInstance'] = null; }
  });
  document.getElementById('app-screen').style.display  = 'none';
  document.getElementById('auth-screen').style.display = 'flex';
  showToast('Başarıyla çıkış yapıldı', 'info');
}

function launchApp() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('app-screen').style.display  = 'flex';

  document.getElementById('topbar-user').textContent = `${currentUser.name} · ${ROLE_LABELS[currentUser.role].split(' ')[0]}`;

  const initials = currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  document.getElementById('sidebar-user').innerHTML = `
    <div class="user-avatar">${initials}</div>
    <div class="user-info">
      <div class="user-name">${currentUser.name}</div>
      <span class="user-role-badge">${ROLE_LABELS[currentUser.role]}</span>
    </div>`;

  const btn = document.getElementById('btn-add-trip');
  if (btn) btn.style.display = currentUser.role === 'urban' ? 'none' : 'inline-flex';

  buildNav();
  navigateTo('dashboard');
}

function canEdit(trip)   { return currentUser?.role === 'admin' || trip.user_id === currentUser?.id; }
function canDelete(trip) { return canEdit(trip); }
function isAdmin()       { return currentUser?.role === 'admin'; }
function isUrban()       { return currentUser?.role === 'urban'; }



let mainMapInstance = null, fullMapInstance = null, routeMapInstance = null, routeLayer = null;
const TILES  = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const CENTER = [40.460, 39.480], ZOOM = 14;
const MC = { o:'#ff7c20', b:'#3b82f6', a:'#f59e0b', m:'#6b7a99', g:'#22c55e' };

function mkTile() { return L.tileLayer(TILES, { attribution: '© OSM © CARTO', maxZoom: 19 }); }

function mkIcon(color, label) {
  return L.divIcon({ className: '', html: `<div style="width:${label?18:13}px;height:${label?18:13}px;background:${color};border:2px solid #fff;border-radius:50%;box-shadow:0 0 12px ${color}99;display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:900;color:#000">${label||''}</div>`, iconSize: [label?18:13, label?18:13], iconAnchor: [label?9:6, label?9:6] });
}

function addNodes(map, nodes, edges, interactive) {
  if (edges) edges.forEach(e => {
    const f = nodes[e.from], t = nodes[e.to];
    if (f && t) L.polyline([[f.lat,f.lng],[t.lat,t.lng]], { color:MC.m, weight:2, opacity:0.35, dashArray:'4 6' }).addTo(map);
  });
  Object.values(nodes).forEach(n => {
    const c = n.type==='hub' ? MC.o : n.type==='place' ? MC.b : MC.a;
    const m = L.marker([n.lat, n.lng], { icon: mkIcon(c, n.type==='hub' ? 'H' : '') }).addTo(map);
    if (interactive) m.bindPopup(`<strong style="color:${c}">${n.name}</strong><br><small>Düğüm ${n.id} · ${n.type}</small>`);
  });
}

async function initMainMap() {
  const el = document.getElementById('main-map'); if (!el) return;
  if (mainMapInstance) { mainMapInstance.remove(); mainMapInstance = null; }
  mainMapInstance = L.map('main-map', { zoomControl:true, scrollWheelZoom:false }).setView(CENTER, ZOOM);
  mkTile().addTo(mainMapInstance);
  if (Object.keys(graphNodes).length) {
    addNodes(mainMapInstance, graphNodes, graphEdges, false);
    try {
      const d = await API.getTrips();
      d.trips.filter(t => t.status === 'active').forEach(t => {
        const f = graphNodes[t.from_node], to = graphNodes[t.to_node];
        if (f && to) L.polyline([[f.lat,f.lng],[to.lat,to.lng]], { color:MC.o, weight:3.5, opacity:0.85 }).addTo(mainMapInstance).bindTooltip(`${t.from_name} → ${t.to_name}`);
      });
    } catch(e) {}
  }
}

function renderMapPage(container) {
  container.innerHTML = `<div class="grid-3-1" style="align-items:start"><div class="panel fade-up"><div class="panel-header"><div class="panel-title">🗺️ Tam Harita — OpenStreetMap</div><div style="display:flex;gap:8px"><button class="btn btn-ghost btn-sm" onclick="toggleHeatmap()">🌡️ Isı Haritası</button><button class="btn btn-ghost btn-sm" onclick="initFullMap()">↺ Reset</button></div></div><div class="panel-body"><div id="fullmap"></div><div style="margin-top:10px;display:flex;gap:12px;font-size:11px;color:var(--muted);flex-wrap:wrap"><span style="color:var(--accent)">● Hub</span><span style="color:var(--accent2)">● Lieu</span><span style="color:var(--accent3)">● Bölge</span><span style="margin-left:auto">Leaflet · OpenStreetMap · CARTO Dark</span></div></div></div><div style="display:flex;flex-direction:column;gap:16px"><div class="panel fade-up"><div class="panel-header"><div class="panel-title">📍 Graf Düğümleri</div></div><div class="panel-body" style="max-height:300px;overflow-y:auto">${Object.values(graphNodes).map(n=>`<div class="stat-row"><div class="stat-icon ${n.type==='hub'?'o':n.type==='place'?'b':'a'}">${n.type==='hub'?'🔴':n.type==='place'?'📍':'📌'}</div><div class="stat-info"><div class="stat-name">${n.name}</div><div class="stat-desc">Düğüm ${n.id} · ${n.type}</div></div></div>`).join('')}</div></div><div class="panel fade-up"><div class="panel-header"><div class="panel-title">📊 Ağ</div></div><div class="panel-body"><div class="stat-row"><div class="stat-icon o">🔗</div><div class="stat-info"><div class="stat-name">Bağlantılar (kenarlar)</div></div><div class="stat-val" style="color:var(--accent)">${graphEdges.length}</div></div><div class="stat-row"><div class="stat-icon b">📍</div><div class="stat-info"><div class="stat-name">Düğüms</div></div><div class="stat-val" style="color:var(--accent2)">${Object.keys(graphNodes).length}</div></div></div></div></div></div>`;
}

async function initFullMap() {
  const el = document.getElementById('fullmap'); if (!el) return;
  if (fullMapInstance) { fullMapInstance.remove(); fullMapInstance = null; }
  fullMapInstance = L.map('fullmap', { zoomControl:true }).setView(CENTER, ZOOM - 1);
  mkTile().addTo(fullMapInstance);
  if (Object.keys(graphNodes).length) {
    addNodes(fullMapInstance, graphNodes, graphEdges, true);
    try {
      const d = await API.getTrips();
      d.trips.filter(t => t.status === 'active').forEach(t => {
        const f = graphNodes[t.from_node], to = graphNodes[t.to_node];
        if (f && to) L.polyline([[f.lat,f.lng],[to.lat,to.lng]], { color:MC.o, weight:4, opacity:0.85 }).addTo(fullMapInstance).bindTooltip(`<strong>${t.from_name} → ${t.to_name}</strong><br>${t.distance} km`);
      });
    } catch(e) {}
  }
}

async function toggleHeatmap() {
  if (!fullMapInstance) return;
  try {
    const d = await API.getNodeFreq();
    d.nodes.forEach(n => {
      const node = graphNodes[n.node]; if (!node) return;
      const col  = n.count > 3 ? MC.o : n.count > 1 ? MC.a : MC.m;
      L.circle([node.lat, node.lng], { radius:60+n.count*60, color:col, fillColor:col, fillOpacity:0.2, weight:0 }).addTo(fullMapInstance);
    });
    showToast('Isı haritası etkinleştirildi', 'success');
  } catch(e) {}
}

function initRouteMap() {
  const el = document.getElementById('route-map'); if (!el) return;
  if (routeMapInstance) { routeMapInstance.remove(); routeMapInstance = null; }
  routeMapInstance = L.map('route-map', { zoomControl:true }).setView(CENTER, ZOOM);
  mkTile().addTo(routeMapInstance);
  if (Object.keys(graphNodes).length) addNodes(routeMapInstance, graphNodes, graphEdges, true);
}

function highlightRouteOnMap(path) {
  if (!routeMapInstance) return;
  if (routeLayer) routeMapInstance.removeLayer(routeLayer);
  const ll  = path.map(id => { const n = graphNodes[id]; return [n.lat, n.lng]; });
  routeLayer = L.polyline(ll, { color:MC.o, weight:5, opacity:0.9 }).addTo(routeMapInstance);
  if (ll.length > 1) routeMapInstance.fitBounds(ll, { padding: [40, 40] });
}


let selFrom = null, selTo = null;

function renderDijkstraPage(container) {
  const ids = Object.keys(graphNodes);
  container.innerHTML = `<div class="grid-2" style="align-items:start"><div style="display:flex;flex-direction:column;gap:20px"><div class="panel fade-up"><div class="panel-header"><div class="panel-title">⚡ Dijkstra Hesaplama — NetworkX (Python)</div></div><div class="panel-body"><div style="margin-bottom:14px"><div style="font-size:11px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">1 — Düğüm de départ</div><div class="node-graph" id="from-nodes">${ids.map(id=>`<div class="node-chip" id="from-${id}" onclick="selectFrom('${id}')">${id}: ${graphNodes[id].name.split(' ')[0]}</div>`).join('')}</div></div><div style="margin-bottom:16px"><div style="font-size:11px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">2 — Düğüm d'arrivée</div><div class="node-graph" id="to-nodes">${ids.map(id=>`<div class="node-chip" id="to-${id}" onclick="selectTo('${id}')">${id}: ${graphNodes[id].name.split(' ')[0]}</div>`).join('')}</div></div><button class="btn btn-primary btn-full" onclick="runDijkstra()">⚡ Flask/NetworkX ile Hesapla</button></div></div><div class="panel fade-up" id="dijkstra-result" style="display:none"><div class="panel-header"><div class="panel-title">📍 NetworkX Sonucu</div></div><div class="panel-body" id="dijkstra-result-body"></div></div><div class="panel fade-up"><div class="panel-header"><div class="panel-title">💡 Dijkstra Algoritması (NetworkX)</div></div><div class="panel-body"><div class="algo-box"><div class="algo-title">Python — NetworkX</div><div class="algo-code"><span class="algo-highlight">import</span> networkx <span class="algo-highlight">as</span> nx<br><br>G = nx.Graph()<br>G.add_edge('A','B', weight=2.1)<br># ... (${graphEdges.length} kenar toplam)<br><br>path = nx.dijkstra_path(G, source, target)<br>dist = nx.dijkstra_path_length(G, source, target)</div></div></div></div></div><div class="panel fade-up"><div class="panel-header"><div class="panel-title">🗺️ Görselleştirme</div></div><div class="panel-body"><div id="route-map"></div><div style="margin-top:10px;font-size:11px;color:var(--muted)"><span style="color:var(--accent)">━━</span> Optimal güzergah (NetworkX)</div></div></div></div>`;
}

function selectFrom(id) {
  selFrom = id;
  document.querySelectorAll('[id^="from-"]').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById(`from-${id}`); if (el) el.classList.add('selected');
}
function selectTo(id) {
  selTo = id;
  document.querySelectorAll('[id^="to-"]').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById(`to-${id}`); if (el) el.classList.add('selected');
}

async function runDijkstra() {
  if (!selFrom || !selTo) { showToast('Başlangıç VE varış seçiniz', 'error'); return; }
  if (selFrom === selTo)  { showToast('Başlangıç ve varış farklı olmalı', 'error'); return; }
  const panel = document.getElementById('dijkstra-result');
  const body  = document.getElementById('dijkstra-result-body');
  panel.style.display = 'block';
  body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted)">⏳ NetworkX hesaplanıyor...</div>';
  try {
    const res = await API.dijkstra({ from_node: selFrom, to_node: selTo });
    body.innerHTML = `<div class="result-path">${res.path.map((id,i)=>`${i>0?'<span class="path-arrow">→</span>':''}<span class="path-node">${id}</span>`).join('')}</div>
    <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;text-align:center">
      <div style="background:var(--surface2);border-radius:8px;padding:12px"><div style="font-size:10px;color:var(--muted)">MESAFE</div><div style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--accent)">${res.distance} km</div></div>
      <div style="background:var(--surface2);border-radius:8px;padding:12px"><div style="font-size:10px;color:var(--muted)">TAHMİNİ SÜRE</div><div style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--accent2)">${res.duration} min</div></div>
      <div style="background:var(--surface2);border-radius:8px;padding:12px"><div style="font-size:10px;color:var(--muted)">ADIMLAR</div><div style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--accent3)">${res.nodes_count}</div></div>
    </div>
    <div style="margin-top:12px"><div class="algo-box"><div class="algo-title">Güzergah — ${res.algorithm}</div>
    <div class="algo-code">Başlangıç : <span class="algo-highlight">${res.from_name}</span><br>Varış    : <span class="algo-highlight">${res.to_name}</span><br>${res.steps.map(s=>`${s.from_name} → ${s.to_name} : ${s.segment_km} km (cumul: ${s.cumul_km} km)`).join('<br>')}</div></div></div>
    <div style="margin-top:10px"><button class="btn btn-primary btn-full" onclick="saveRoute()">💾 Kaydet en SQLite</button></div>`;
    highlightRouteOnMap(res.path);
    document.querySelectorAll('[id^="from-"],[id^="to-"]').forEach(el => el.classList.remove('path'));
    res.path.forEach(id => { ['from-','to-'].forEach(p => { const el = document.getElementById(p+id); if(el) el.classList.add('path'); }); });
    showToast(`NetworkX: ${res.distance} km bulundu ✓`, 'success');
    window._lastDijkstraResult = res;
  } catch(e) {
    body.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>${e.message}</p></div>`;
    showToast(e.message, 'error');
  }
}

async function saveRoute() {
  const res = window._lastDijkstraResult; if (!res || !selFrom || !selTo) return;
  try {
    await API.createTrip({ from_node:selFrom, to_node:selTo, distance:res.distance, passengers:1, intensity: res.distance<3?'high':res.distance<6?'med':'low', from_name:res.from_name, to_name:res.to_name });
    showToast('Yolculuk enregistré en SQLite ✓', 'success');
  } catch(e) { showToast(e.message, 'error'); }
}


let currentPage = 'dashboard', sidebarOpen = true;
let graphNodes  = {}, graphEdges = [];

const NAV_ITEMS = [
  { section: 'Navigasyon' },
  { id:'dashboard', icon:'🏠', label:'Gösterge Paneli' },
  { id:'map',       icon:'🗺️', label:'İnteraktif Harita' },
  { id:'trips',     icon:'🚗', label:'Yolculuklarım' },
  { section: 'Analiz' },
  { id:'dijkstra',  icon:'⚡', label:'Dijkstra Optimizasyonu' },
  { id:'stats',     icon:'📊', label:'İstatistikler (Pandas)' },
  { id:'actors',    icon:'👥', label:'Sistem Aktörleri' },
  { section: 'Yönetim' },
  { id:'users',     icon:'🔐', label:'Kullanıcılar',   roles:['admin','urban'] },
  { id:'database',  icon:'🗄️', label:'Veritabanı', roles:['admin','urban'] },
  { section: 'Sistem' },
  { id:'settings',  icon:'⚙️', label:'Ayarlar' },
];

function buildNav() {
  const nav = document.getElementById('nav-menu'); if (!nav) return;
  nav.innerHTML = '';
  NAV_ITEMS.forEach(item => {
    if (item.roles && !item.roles.includes(currentUser?.role)) return;
    if (item.section) {
      const s = document.createElement('span');
      s.className   = 'nav-section-label';
      s.textContent = item.section;
      nav.appendChild(s);
    } else {
      const a = document.createElement('a');
      a.className = 'nav-item' + (item.id === currentPage ? ' active' : '');
      a.innerHTML = `<span class="nav-icon">${item.icon}</span><span>${item.label}</span>`;
      a.onclick   = () => navigateTo(item.id);
      nav.appendChild(a);
    }
  });
}

function toggleSidebar(forceClose) {
  const sidebar = document.getElementById('sidebar');
  const main    = document.getElementById('main-area');
  if (forceClose === true) {
    sidebar.classList.add('collapsed'); main.classList.add('expanded'); sidebarOpen = false;
  } else {
    sidebarOpen = !sidebarOpen;
    sidebar.classList.toggle('collapsed', !sidebarOpen);
    main.classList.toggle('expanded', !sidebarOpen);
  }
}

async function navigateTo(page) {
  currentPage = page;
  const titles = { dashboard:'Gösterge Paneli', map:'İnteraktif Harita', trips:'Yolculuklarım',
    dijkstra:'Dijkstra Optimizasyonu — NetworkX', stats:'İstatistikler — Pandas',
    actors:'Sistem Aktörleri', users:'Kullanıcı Yönetimi', database:'SQLite Veritabanı', settings:'Ayarlar' };
  document.getElementById('page-title').textContent = titles[page] || page;
  buildNav();

  const container = document.getElementById('app-content');
  container.innerHTML = `<div class="empty-state"><div class="empty-icon">⏳</div><p>Flask'tan yükleniyor...</p></div>`;

  if (!Object.keys(graphNodes).length) {
    try {
      const nd = await API.getNodes(); graphNodes = nd.nodes;
      const ed = await API.getEdges(); graphEdges = ed.edges;
    } catch(e) {}
  }

  switch(page) {
    case 'dashboard': await renderDashboard(container);  break;
    case 'map':       renderMapPage(container);           break;
    case 'trips':     await renderTripsPage(container);   break;
    case 'dijkstra':  renderDijkstraPage(container);      break;
    case 'stats':     await renderStatsPage(container);   break;
    case 'actors':    renderActorsPage(container);        break;
    case 'users':     await renderUsersPage(container);   break;
    case 'database':  await renderDBPage(container);      break;
    case 'settings':  renderSettingsPage(container);      break;
  }

  setTimeout(() => {
    if (page === 'dashboard') { initMainMap(); animateProgs(); }
    if (page === 'map')       initFullMap();
    if (page === 'dijkstra')  initRouteMap();
    if (page === 'stats')     animateProgs();
  }, 100);

  if (window.innerWidth < 800) toggleSidebar(true);
}


async function renderDashboard(container) {
  const [sumData, actData, tripsData, weekData] = await Promise.all([
    API.getSummary().catch(() => ({ total_trips:0, active_trips:0, total_users:0, co2_saved_kg:0 })),
    API.getActivity(5).catch(() => ({ activity:[] })),
    API.getTrips().catch(() => ({ trips:[] })),
    API.getWeekly().catch(() => ({ weekly:[] })),
  ]);
  const s = sumData, acts = actData.activity, trips = tripsData.trips, weekly = weekData.weekly;
  const maxDay = weekly.length ? Math.max(...weekly.map(d => d.trips)) : 1;

  container.innerHTML = `
  <div class="kpi-grid">
    <div class="kpi-card orange fade-up" style="animation-delay:.05s"><div class="kpi-icon">🚗</div><div class="kpi-label">Aktif Yolculuklar</div><div class="kpi-value">${s.active_trips}</div><div class="kpi-change up">SQLite Veritabanı</div></div>
    <div class="kpi-card blue fade-up" style="animation-delay:.1s"><div class="kpi-icon">👥</div><div class="kpi-label">Kullanıcılar</div><div class="kpi-value">${s.total_users}</div><div class="kpi-change up">Kayıtlı</div></div>
    <div class="kpi-card amber fade-up" style="animation-delay:.15s"><div class="kpi-icon">🌱</div><div class="kpi-label">Tasarruf Edilen CO₂</div><div class="kpi-value">${s.co2_saved_kg} kg</div><div class="kpi-change up">Pandas ile hesaplandı</div></div>
    <div class="kpi-card red fade-up" style="animation-delay:.2s"><div class="kpi-icon">📍</div><div class="kpi-label">Toplam Yolculuk</div><div class="kpi-value">${s.total_trips}</div><div class="kpi-change">SQLite Veritabanı</div></div>
  </div>
  <div class="grid-3-1">
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">🗺️ Harita — OpenStreetMap (Leaflet)</div><span class="panel-action" onclick="navigateTo('map')">Tam ekran →</span></div>
      <div class="panel-body">
        <div id="main-map"></div>
        <div style="margin-top:10px;display:flex;gap:14px;font-size:11px;color:var(--muted);flex-wrap:wrap">
          <span style="color:var(--accent)">● Aktif yolculuk</span><span style="color:var(--accent2)">● Düğüm</span><span style="color:var(--accent3)">● Bölge</span>
        </div>
      </div>
    </div>
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">⏱ Son Aktivite</div><span class="panel-action" onclick="navigateTo('trips')">Tümünü gör</span></div>
      <div class="panel-body">
        ${acts.length ? acts.map(a=>`<div class="feed-item"><div class="feed-dot ${a.type||'o'}"></div><div><div class="feed-text">${a.message}</div><div class="feed-time">${a.created_at}</div></div></div>`).join('') : '<div class="empty-state"><div class="empty-icon">📭</div><p>Aktivite yok</p></div>'}
      </div>
    </div>
  </div>
  <div class="grid-2">
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">📈 Haftalık Trafik (Pandas)</div></div>
      <div class="panel-body">
        <div class="bar-chart">
          ${weekly.map(d=>`<div class="bar-group"><div class="bar" style="height:${Math.round(d.trips/maxDay*100)}%;background:${d.trips===maxDay?'#ff7c20':'#3b82f6'}" title="${d.trips} trajets"></div><div class="bar-lbl">${d.day}</div></div>`).join('')}
        </div>
        <div style="margin-top:18px">
          <div class="prog-row"><div class="prog-header"><span class="prog-label">Sabah yoğun saati (07:00–09:00)</span><span class="prog-val" style="color:var(--accent)">78%</span></div><div class="prog-track"><div class="prog-fill" data-width="78" style="background:var(--accent)"></div></div></div>
          <div class="prog-row"><div class="prog-header"><span class="prog-label">Akşam yoğun saati (17:00–19:00)</span><span class="prog-val" style="color:var(--accent2)">65%</span></div><div class="prog-track"><div class="prog-fill" data-width="65" style="background:var(--accent2)"></div></div></div>
          <div class="prog-row"><div class="prog-header"><span class="prog-label">Sakin saatler</span><span class="prog-val" style="color:var(--muted)">22%</span></div><div class="prog-track"><div class="prog-fill" data-width="22" style="background:var(--muted)"></div></div></div>
        </div>
      </div>
    </div>
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">🏆 Son Yolculuklar (SQLite)</div><span class="panel-action" onclick="navigateTo('trips')">Tümünü gör</span></div>
      <div class="panel-body">
        <table class="data-table">
          <thead><tr><th>Yolculuk</th><th>Yolcular</th><th>Yoğunluk</th></tr></thead>
          <tbody>
          ${trips.slice(0,5).map(t=>`<tr><td><div class="td-main">${t.from_name} → ${t.to_name}</div><div class="td-sub">${t.distance} km · ${t.duration} min</div></td><td>${t.passengers} 👤</td><td><span class="pill ${t.intensity}">${{high:'Yüksek',med:'Orta',low:'Düşük'}[t.intensity]}</span></td></tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>
  </div>`;
}

async function renderTripsPage(container) {
  const data  = await API.getTrips().catch(() => ({ trips:[] }));
  const trips = data.trips;
  container.innerHTML = `
  <div class="panel fade-up">
    <div class="panel-header">
      <div class="panel-title">🚗 ${isAdmin()?'Tous les Yolculuks':'Mes Yolculuks'} — SQLite (${trips.length})</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <select id="filter-int" class="form-input" style="padding:6px 10px;font-size:12px" onchange="filterTrips()">
          <option value="">Tüm yoğunluklar</option>
          <option value="high">🟠 Yüksek</option><option value="med">🔵 Orta</option><option value="low">⚫ Düşük</option>
        </select>
        <select id="filter-status" class="form-input" style="padding:6px 10px;font-size:12px" onchange="filterTrips()">
          <option value="">Tüm durumlar</option><option value="active">Aktif</option><option value="done">Tamamlandı</option>
        </select>
        ${!isUrban()?`<button class="btn btn-primary btn-sm" onclick="showAddTrip()">+ Yeni</button>`:''}
      </div>
    </div>
    <div class="panel-body" style="padding:0">
      <div style="overflow-x:auto">
        <table class="data-table" style="min-width:750px">
          <thead><tr>
            <th style="padding-left:18px">Başlangıç → Varış</th>
            <th>Mesafe</th><th>Yolcular</th><th>Yoğunluk</th><th>Durum</th><th>Tarih</th><th>Sürücü</th>
            ${!isUrban()?'<th>İşlemler</th>':''}
          </tr></thead>
          <tbody id="trips-body">${renderTripRows(trips)}</tbody>
        </table>
      </div>
    </div>
  </div>`;
  window._allTrips = trips;
}

function renderTripRows(trips) {
  if (!trips.length) return `<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--muted)">Yolculuk bulunamadı</td></tr>`;
  return trips.map(t => {
    const canE = canEdit(t), canD = canDelete(t);
    const actions = !isUrban() ? `<td><div class="action-btns">
      ${canE?`<button class="btn-edit" onclick="showEditTrip(${t.id})">✏️</button>`:''}
      ${canD?`<button class="btn-del" onclick="confirmDeleteTrip(${t.id})">🗑</button>`:''}
    </div></td>` : '';
    return `<tr>
      <td style="padding-left:18px"><div class="td-main">${t.from_name} → ${t.to_name}</div></td>
      <td>${t.distance} km · ${t.duration} min</td>
      <td>${t.passengers} 👤</td>
      <td><span class="pill ${t.intensity}">${{high:'Yüksek',med:'Orta',low:'Düşük'}[t.intensity]}</span></td>
      <td><span class="pill ${t.status==='active'?'ok':'low'}">${t.status==='active'?'Aktif':'Tamamlandı'}</span></td>
      <td>${t.date||'—'}</td>
      <td>${t.driver_name||'—'}</td>
      ${actions}
    </tr>`;
  }).join('');
}

async function filterTrips() {
  const int = document.getElementById('filter-int')?.value || '';
  const st  = document.getElementById('filter-status')?.value || '';
  let params = '?';
  if (int) params += `intensity=${int}&`;
  if (st)  params += `status=${st}`;
  const data = await API.getTrips(params).catch(() => ({ trips:[] }));
  document.getElementById('trips-body').innerHTML = renderTripRows(data.trips);
}


async function renderStatsPage(container) {
  const [sum, weekly, intens, nodes, co2] = await Promise.all([
    API.getSummary().catch(() => ({})),
    API.getWeekly().catch(() => ({ weekly:[] })),
    API.getIntensity().catch(() => ({ intensity:{} })),
    API.getNodeFreq().catch(() => ({ nodes:[] })),
    API.getCO2().catch(() => ({})),
  ]);
  const w = weekly.weekly, maxDay = w.length ? Math.max(...w.map(d => d.trips)) : 1;
  const i = intens.intensity;
  container.innerHTML = `
  <div class="kpi-grid fade-up">
    <div class="kpi-card orange"><div class="kpi-icon">📏</div><div class="kpi-label">Mesafe Toplame</div><div class="kpi-value">${sum.total_distance||0} km</div></div>
    <div class="kpi-card blue"><div class="kpi-icon">👤</div><div class="kpi-label">Yolcular Toplam</div><div class="kpi-value">${sum.total_passengers||0}</div></div>
    <div class="kpi-card amber"><div class="kpi-icon">📊</div><div class="kpi-label">Ort. yolcu/yolculuk</div><div class="kpi-value">${sum.avg_passengers||0}</div></div>
    <div class="kpi-card green"><div class="kpi-icon">🌱</div><div class="kpi-label">Tasarruf Edilen CO₂</div><div class="kpi-value">${co2.total_co2_kg||0} kg</div></div>
  </div>
  <div class="grid-2">
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">📅 Haftalık Trafik (Pandas)</div></div>
      <div class="panel-body">
        <div class="bar-chart">${w.map(d=>`<div class="bar-group"><div class="bar" style="height:${Math.round(d.trips/maxDay*100)}%;background:${d.trips===maxDay?'#ff7c20':'#3b82f6'}"></div><div class="bar-lbl">${d.day}<br><span style="color:#ff7c20;font-size:9px">${d.trips}</span></div></div>`).join('')}</div>
      </div>
    </div>
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">🎯 Répartition par Yoğunluk (Pandas)</div></div>
      <div class="panel-body">
        <div class="prog-row"><div class="prog-header"><span class="prog-label">🟠 Yüksek</span><span class="prog-val" style="color:var(--accent)">${i.high||0} yolculuk (${i.high_pct||0}%)</span></div><div class="prog-track"><div class="prog-fill" data-width="${i.high_pct||0}" style="background:var(--accent)"></div></div></div>
        <div class="prog-row"><div class="prog-header"><span class="prog-label">🔵 Orta</span><span class="prog-val" style="color:var(--accent2)">${i.med||0} yolculuk (${i.med_pct||0}%)</span></div><div class="prog-track"><div class="prog-fill" data-width="${i.med_pct||0}" style="background:var(--accent2)"></div></div></div>
        <div class="prog-row"><div class="prog-header"><span class="prog-label">⚫ Düşük</span><span class="prog-val" style="color:var(--muted)">${i.low||0} yolculuk (${i.low_pct||0}%)</span></div><div class="prog-track"><div class="prog-fill" data-width="${i.low_pct||0}" style="background:var(--muted)"></div></div></div>
        <div style="margin-top:16px"><div class="algo-box"><div class="algo-title">🌱 CO₂ Etkisi (Pandas)</div>
        <div class="algo-code">Formül : mesafe × 120g/km<br>Toplam : ${co2.total_co2_kg||0} kg<br>Ort/yolculuk : ${co2.avg_co2_per_trip||0} kg<br>≈ ${co2.trees_equivalent||0} ağaç/ay</div></div></div>
      </div>
    </div>
  </div>
  <div class="panel fade-up">
    <div class="panel-header"><div class="panel-title">🔢 Düğüm Frekansı (Pandas value_counts)</div></div>
    <div class="panel-body">
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px">
        ${nodes.nodes.map(n=>`<div style="background:var(--surface2);border-radius:10px;padding:14px;border:1px solid var(--border)">
          <div style="font-family:'Syne',sans-serif;font-weight:800;color:var(--accent);font-size:18px">${n.node}</div>
          <div style="font-size:12px;font-weight:500;margin:4px 0">${graphNodes[n.node]?.name||n.node}</div>
          <div style="height:4px;background:var(--surface3);border-radius:99px;overflow:hidden;margin:8px 0"><div style="height:100%;width:${n.pct}%;background:var(--accent);border-radius:99px"></div></div>
          <div style="font-size:11px;color:var(--muted)">${n.count} yolculuk · ${n.pct}%</div>
        </div>`).join('')}
      </div>
    </div>
  </div>`;
}


function renderActorsPage(container) {
  const actors = [
    { icon:'🚗', name:'Sürücü',        role:'Yolculuk teklif eder',   need:'Yolcu bulmak ve güzergahını optimize etmek', access:'Yolculuk oluşturma, düzenleme ve silme' },
    { icon:'👤', name:'Yolcu',           role:'Yolculuk arar',   need:'En iyi güzergahı hızlıca bulmak',         access:'Yolculukları görüntüleme ve önerme' },
    { icon:'🏙️', name:'Kent Yöneticisi',role:'Verileri analiz eder', need:'Akışları ve az kullanılan bölgeleri belirlemek',            access:'Salt okunur, istatistikler, veritabanı' },
    { icon:'👑', name:'Yönetici',     role:'Sistemi yönetir',     need:'Veri güvenilirliğini sağlamak',                  access:'Tam erişim, kullanıcı yönetimi' },
  ];
  container.innerHTML = `
  <div class="panel fade-up" style="margin-bottom:20px">
    <div class="panel-header"><div class="panel-title">👥 Sistem Aktörleri</div></div>
    <div class="panel-body">
      <p style="color:var(--text2);margin-bottom:20px;font-size:13px">YolPayı sisteminde dört farklı aktör türü yer almakta olup her biri Flask backend tarafından yönetilen belirli erişim haklarına sahiptir.</p>
      <div class="actors-grid">
        ${actors.map((a,i)=>`<div class="actor-card fade-up" style="animation-delay:${i*.08}s"><div class="actor-icon">${a.icon}</div><div><div class="actor-name">${a.name}</div><div class="actor-role">Rol : ${a.role}</div><div class="actor-need">İhtiyaç : ${a.need}</div><div style="margin-top:8px;font-size:11px;color:var(--accent)">Erişim : ${a.access}</div></div></div>`).join('')}
      </div>
    </div>
  </div>
  <div class="panel fade-up">
    <div class="panel-header"><div class="panel-title">📋 Özet Tablo</div></div>
    <div class="panel-body" style="padding:0">
      <table class="data-table" style="min-width:500px">
        <thead><tr><th style="padding-left:18px">Aktör</th><th>Rol</th><th>Temel İhtiyaç</th><th>Erişim</th></tr></thead>
        <tbody>
          <tr><td style="padding-left:18px"><strong>🚗 Sürücü</strong></td><td>Yolculuk teklif eder</td><td>Yolcu bulmak</td><td><span class="pill high">Yolculuks CRUD</span></td></tr>
          <tr><td style="padding-left:18px"><strong>👤 Yolcu</strong></td><td>Yolculuk arar</td><td>En iyi güzergah</td><td><span class="pill med">Consultation</span></td></tr>
          <tr><td style="padding-left:18px"><strong>🏙️ Kent Yöneticisi</strong></td><td>Verileri analiz eder</td><td>Akış ve bölgeleri belirlemek</td><td><span class="pill warn">İstat. + Veritabanı</span></td></tr>
          <tr><td style="padding-left:18px"><strong>👑 Yönetici</strong></td><td>Sistemi yönetir</td><td>Veri güvenilirliği</td><td><span class="pill bad">Erişim total</span></td></tr>
        </tbody>
      </table>
    </div>
  </div>`;
}


async function renderUsersPage(container) {
  if (!isAdmin() && !isUrban()) { container.innerHTML = `<div class="empty-state"><div class="empty-icon">🔐</div><p>Erişim réservé</p></div>`; return; }
  const data  = await API.getUsers().catch(() => ({ users:[] }));
  const users = data.users;
  container.innerHTML = `
  <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr)">
    <div class="kpi-card blue fade-up"><div class="kpi-icon">👥</div><div class="kpi-label">Toplam</div><div class="kpi-value">${users.length}</div></div>
    <div class="kpi-card orange fade-up"><div class="kpi-icon">🚗</div><div class="kpi-label">Sürücüs</div><div class="kpi-value">${users.filter(u=>u.role==='driver').length}</div></div>
    <div class="kpi-card amber fade-up"><div class="kpi-icon">👤</div><div class="kpi-label">Yolcular</div><div class="kpi-value">${users.filter(u=>u.role==='passenger').length}</div></div>
    <div class="kpi-card green fade-up"><div class="kpi-icon">🏙️</div><div class="kpi-label">Yöneticiler</div><div class="kpi-value">${users.filter(u=>u.role==='urban').length}</div></div>
  </div>
  <div class="panel fade-up">
    <div class="panel-header"><div class="panel-title">🔐 Kullanıcılar enregistrés (SQLite)</div></div>
    <div class="panel-body" style="padding:0">
      <table class="data-table" style="min-width:620px">
        <thead><tr><th style="padding-left:18px">Kullanıcı</th><th>E-posta</th><th>Rol</th><th>Kayıt tarihi</th><th>Yolculuks</th>${isAdmin()?'<th>İşlemler</th>':''}</tr></thead>
        <tbody>
        ${users.map(u=>`<tr>
          <td style="padding-left:18px"><div style="display:flex;align-items:center;gap:10px">
            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--accent2),var(--accent));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;color:#000">${u.name.split(' ').map(n=>n[0]).join('').slice(0,2)}</div>${u.name}</div></td>
          <td>${u.email}</td>
          <td><span class="pill ${ROLE_COLORS[u.role]}">${ROLE_LABELS[u.role]}</span></td>
          <td>${u.created_at}</td>
          <td>${u.trip_count}</td>
          ${isAdmin()&&u.id!==currentUser?.id?`<td><button class="btn-del" onclick="deleteUser(${u.id},'${u.name}')">🗑</button></td>`:(isAdmin()?'<td>—</td>':'')}
        </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

async function deleteUser(id, name) {
  if (!confirm(`Kullanıcıyı sil "${name}" ve tüm yolculuklarını sil?`)) return;
  try { await API.deleteUser(id); showToast(`Kullanıcı ${name} silindi`, 'success'); navigateTo('users'); }
  catch(e) { showToast(e.message, 'error'); }
}


async function renderDBPage(container) {
  const info = await API.dbInfo().catch(() => ({ users_count:0, trips_count:0, activity_count:0, schema:{} }));
  container.innerHTML = `
  <div class="grid-2">
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">🗄️ SQLite Şeması — yolpayi.db</div></div>
      <div class="panel-body">
        <div class="db-box">
<span class="db-table-name">TABLE users</span><br>
&nbsp;&nbsp;<span class="db-field">id</span>         <span class="db-type">INTEGER PRIMARY KEY AUTOINCREMENT</span><br>
&nbsp;&nbsp;<span class="db-field">name</span>       <span class="db-type">TEXT NOT NULL</span><br>
&nbsp;&nbsp;<span class="db-field">email</span>      <span class="db-type">TEXT UNIQUE NOT NULL</span><br>
&nbsp;&nbsp;<span class="db-field">password</span>   <span class="db-type">TEXT NOT NULL (SHA-256)</span><br>
&nbsp;&nbsp;<span class="db-field">role</span>       <span class="db-type">TEXT CHECK(role IN ('admin','driver','passenger','urban'))</span><br>
&nbsp;&nbsp;<span class="db-field">created_at</span> <span class="db-type">TEXT DEFAULT CURRENT_TIMESTAMP</span><br><br>
<span class="db-table-name">TABLE trips</span><br>
&nbsp;&nbsp;<span class="db-field">id</span>         <span class="db-type">INTEGER PRIMARY KEY AUTOINCREMENT</span><br>
&nbsp;&nbsp;<span class="db-field">user_id</span>    <span class="db-type">INTEGER REFERENCES users(id) ON DELETE CASCADE</span><br>
&nbsp;&nbsp;<span class="db-field">from_node</span>  <span class="db-type">TEXT NOT NULL</span><br>
&nbsp;&nbsp;<span class="db-field">to_node</span>    <span class="db-type">TEXT NOT NULL</span><br>
&nbsp;&nbsp;<span class="db-field">distance</span>   <span class="db-type">REAL</span><br>
&nbsp;&nbsp;<span class="db-field">passengers</span> <span class="db-type">INTEGER DEFAULT 1</span><br>
&nbsp;&nbsp;<span class="db-field">intensity</span>  <span class="db-type">TEXT CHECK(intensity IN ('high','med','low'))</span><br>
&nbsp;&nbsp;<span class="db-field">status</span>     <span class="db-type">TEXT CHECK(status IN ('active','done'))</span><br><br>
<span class="db-table-name">TABLE activity_log</span><br>
&nbsp;&nbsp;<span class="db-field">id</span>         <span class="db-type">INTEGER PRIMARY KEY AUTOINCREMENT</span><br>
&nbsp;&nbsp;<span class="db-field">type</span>       <span class="db-type">TEXT</span><br>
&nbsp;&nbsp;<span class="db-field">message</span>    <span class="db-type">TEXT</span><br>
&nbsp;&nbsp;<span class="db-field">user_id</span>    <span class="db-type">INTEGER</span><br>
&nbsp;&nbsp;<span class="db-field">created_at</span> <span class="db-type">TEXT</span>
        </div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="panel fade-up">
        <div class="panel-header"><div class="panel-title">📊 Veritabanı Durumu</div></div>
        <div class="panel-body">
          <div class="stat-row"><div class="stat-icon o">👥</div><div class="stat-info"><div class="stat-name">Kullanıcılar</div></div><div class="stat-val" style="color:var(--accent)">${info.users_count}</div></div>
          <div class="stat-row"><div class="stat-icon b">🚗</div><div class="stat-info"><div class="stat-name">Yolculuks</div></div><div class="stat-val" style="color:var(--accent2)">${info.trips_count}</div></div>
          <div class="stat-row"><div class="stat-icon a">📝</div><div class="stat-info"><div class="stat-name">Aktivite Kayıtları</div></div><div class="stat-val" style="color:var(--accent3)">${info.activity_count}</div></div>
        </div>
      </div>
      <div class="panel fade-up">
        <div class="panel-header"><div class="panel-title">🛠️ Teknik Yığın</div></div>
        <div class="panel-body">
          ${[['Python 3.x','Flask Backend','o'],['Flask','API REST','b'],['SQLite','Veritabanı','a'],['Pandas','Analiz + CSV','o'],['NetworkX','Dijkstra','b'],['Leaflet','İnteraktif Harita','a']].map(([t,r,c])=>`<div class="stat-row"><div class="stat-icon ${c}" style="font-size:10px;font-family:'Syne',sans-serif;font-weight:800">${t[0]}</div><div class="stat-info"><div class="stat-name">${t}</div><div class="stat-desc">${r}</div></div></div>`).join('')}
        </div>
      </div>
      ${isAdmin()?`<div class="panel fade-up">
        <div class="panel-header"><div class="panel-title">⚠️ Yönetici — Sıfırlama</div></div>
        <div class="panel-body"><button class="btn btn-danger btn-full" onclick="resetDB()">🔄 Veritabanını Sıfırla</button></div>
      </div>`:''}
    </div>
  </div>`;
}

async function resetDB() {
  if (!confirm('SQLite veritabanını tamamen sıfırlamak istediğinizden emin misiniz?')) return;
  try { await API.dbReset(); showToast('Veritabanı sıfırlandı, lütfen tekrar giriş yapın', 'info'); doLogout(); }
  catch(e) { showToast(e.message, 'error'); }
}


function renderSettingsPage(container) {
  container.innerHTML = `
  <div class="grid-2">
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">⚙️ Sistem Tercihleri</div></div>
      <div class="panel-body" style="display:flex;flex-direction:column;gap:14px">
        <div class="form-group"><label>Sistem adı</label><input class="form-input" value="YolPayı v3"></div>
        <div class="form-group"><label>Şehir</label><input class="form-input" value="Gümüşhane, Türkiye"></div>
        <div class="form-group"><label>Dil</label><select class="form-input"><option>Türkçe</option><option>Türkçe</option><option>English</option></select></div>
        <button class="btn btn-primary" onclick="showToast('Ayarlar kaydedildi ✓','success')">Kaydet</button>
      </div>
    </div>
    <div class="panel fade-up">
      <div class="panel-header"><div class="panel-title">👤 Hesabım</div></div>
      <div class="panel-body" style="display:flex;flex-direction:column;gap:14px">
        <div class="form-group"><label>Ad</label><input class="form-input" value="${currentUser?.name||''}"></div>
        <div class="form-group"><label>E-posta</label><input class="form-input" value="${currentUser?.email||''}" disabled></div>
        <div class="form-group"><label>Rol</label><input class="form-input" value="${ROLE_LABELS[currentUser?.role]||''}" disabled></div>
        <div class="form-group"><label>Yeni şifre</label><input class="form-input" type="password" placeholder="Değiştirmek istemiyorsanız boş bırakın"></div>
        <button class="btn btn-primary" onclick="showToast('Profil güncellendi ✓','success')">Güncelle</button>
        <button class="btn btn-danger" onclick="doLogout()">🚪 Çıkış Yap</button>
      </div>
    </div>
  </div>`;
}


function getNodeOptions() {
  return Object.values(graphNodes).map(n => `<option value="${n.id}">${n.id} — ${n.name}</option>`).join('');
}

async function showAddTrip() {
  document.getElementById('modal-trip-title').textContent = 'Nouveau Yolculuk';
  document.getElementById('edit-trip-id').value = '';
  const opts = getNodeOptions();
  document.getElementById('trip-from').innerHTML = opts;
  document.getElementById('trip-to').innerHTML   = opts;
  document.getElementById('trip-dist').value     = '';
  document.getElementById('trip-pass').value     = '';
  document.getElementById('trip-intensity').value = 'med';
  document.getElementById('modal-trip').style.display = 'flex';
}

async function showEditTrip(id) {
  const d    = await API.getTrips().catch(() => ({ trips:[] }));
  const trip = d.trips.find(t => t.id === id); if (!trip) return;
  document.getElementById('modal-trip-title').textContent = 'Modifier le Yolculuk';
  document.getElementById('edit-trip-id').value = id;
  const opts = getNodeOptions();
  document.getElementById('trip-from').innerHTML = opts;
  document.getElementById('trip-to').innerHTML   = opts;
  document.getElementById('trip-from').value     = trip.from_node;
  document.getElementById('trip-to').value       = trip.to_node;
  document.getElementById('trip-dist').value     = trip.distance;
  document.getElementById('trip-pass').value     = trip.passengers;
  document.getElementById('trip-intensity').value = trip.intensity;
  document.getElementById('modal-trip').style.display = 'flex';
}

async function submitTrip() {
  const editId    = document.getElementById('edit-trip-id').value;
  const from      = document.getElementById('trip-from').value;
  const to        = document.getElementById('trip-to').value;
  const dist      = parseFloat(document.getElementById('trip-dist').value);
  const pass      = parseInt(document.getElementById('trip-pass').value);
  const intensity = document.getElementById('trip-intensity').value;
  if (!from || !to || !dist || !pass) { showToast('Tüm alanları doldurunuz', 'error'); return; }
  if (from === to) { showToast('Başlangıç ve varış farklı olmalı', 'error'); return; }
  try {
    const btn = document.getElementById('submit-trip-btn');
    btn.textContent = 'Kaydediliyor...'; btn.disabled = true;
    const from_name = graphNodes[from]?.name || from;
    const to_name   = graphNodes[to]?.name   || to;
    if (editId) {
      await API.updateTrip(parseInt(editId), { from_node:from, to_node:to, from_name, to_name, distance:dist, passengers:pass, intensity });
      showToast('Yolculuk modifié ✓', 'success');
    } else {
      await API.createTrip({ from_node:from, to_node:to, from_name, to_name, distance:dist, passengers:pass, intensity });
      showToast('Yolculuk créé en SQLite ✓', 'success');
    }
    btn.textContent = 'Kaydet'; btn.disabled = false;
    closeModal('modal-trip');
    if (currentPage === 'trips' || currentPage === 'dashboard') navigateTo(currentPage);
  } catch(e) {
    showToast(e.message, 'error');
    document.getElementById('submit-trip-btn').textContent = 'Kaydet';
    document.getElementById('submit-trip-btn').disabled   = false;
  }
}

function confirmDeleteTrip(id) {
  document.getElementById('modal-confirm').style.display = 'flex';
  document.getElementById('confirm-delete-btn').onclick = async () => {
    try { await API.deleteTrip(id); closeModal('modal-confirm'); showToast('Yolculuk silindi', 'success'); navigateTo('trips'); }
    catch(e) { showToast(e.message, 'error'); }
  };
}

function closeModal(id)   { document.getElementById(id).style.display = 'none'; }
function closeAllModals() { document.querySelectorAll('.modal-overlay').forEach(m => m.style.display = 'none'); }
async function exportCSV() { window.location.href = '/api/export/csv'; showToast('CSV Dışa Aktarma (Pandas) ✓', 'success'); }

function animateProgs() {
  document.querySelectorAll('.prog-fill').forEach(el => {
    const w = el.dataset.width;
    if (w) setTimeout(() => el.style.width = w + '%', 150);
  });
}

function showToast(msg, type = 'success') {
  const c = document.getElementById('toast-container'); if (!c) return;
  const t = document.createElement('div');
  t.className   = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3300);
}

document.addEventListener('DOMContentLoaded', async () => {
  try { const d = await API.me(); currentUser = d.user; launchApp(); } catch(e) {}

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeAllModals();
  });
  document.querySelectorAll('.modal-overlay').forEach(m => m.addEventListener('click', e => { if (e.target === m) closeAllModals(); }));
  document.getElementById('login-password')?.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  document.getElementById('reg-password')?.addEventListener('keydown',   e => { if (e.key === 'Enter') doRegister(); });
});

window.addEventListener('resize', () => {
  mainMapInstance?.invalidateSize?.();
  fullMapInstance?.invalidateSize?.();
  routeMapInstance?.invalidateSize?.();
});
