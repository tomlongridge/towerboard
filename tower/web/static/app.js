// Towerboard web app: one app for phones and the wall display (?display=wall).
"use strict";

const $ = (id) => document.getElementById(id);
const wall = new URLSearchParams(location.search).get("display") === "wall";

async function api(path, { method = "GET", body } = {}) {
  const opts = { method, headers: {} };
  if (method !== "GET") {
    opts.headers["X-Tower-Request"] = "1";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body || {});
  }
  const resp = await fetch(path, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  return data;
}

// --- views -----------------------------------------------------------------

function route() {
  const name = wall ? "home" : (location.hash.replace(/^#\/?/, "") || "home");
  for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== `view-${name}`;
  if (name === "diagnostics") loadDiagnostics();
  if (name === "admin") loadAdmin();
}

async function loadInfo() {
  const info = await api("/api/info");
  document.title = info.tower;
  $("tower-name").textContent = info.tower;
  $("home-title").textContent = info.tower;
  $("ssid").textContent = $("foot-ssid").textContent = info.ap_ssid;
  $("psk").textContent = info.ap_psk;
  $("app-url").textContent = $("foot-url").textContent = info.app_url;
  $("foot-version").textContent = info.version;
}

// --- diagnostics -------------------------------------------------------------

function flatten(obj, prefix = "", out = []) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) flatten(v, key, out);
    else out.push([key, Array.isArray(v) ? v.join(", ") || "none" : v === null ? "—" : String(v)]);
  }
  return out;
}

async function loadDiagnostics() {
  const root = $("diag");
  try {
    const d = await api("/api/diagnostics");
    const table = document.createElement("table");
    for (const [section, value] of Object.entries(d)) {
      const head = table.insertRow();
      const th = document.createElement("th");
      th.colSpan = 2;
      th.textContent = section;
      head.appendChild(th);
      const rows = value && typeof value === "object" ? flatten(value) : [["", String(value)]];
      for (const [k, v] of rows) {
        const tr = table.insertRow();
        tr.insertCell().textContent = k;
        tr.insertCell().textContent = v;
      }
    }
    root.replaceChildren(table);
  } catch (e) {
    root.textContent = `Could not load diagnostics: ${e.message}`;
  }
}

// --- admin -------------------------------------------------------------------

async function loadAdmin() {
  const s = await api("/api/admin/session");
  $("pin-form").hidden = s.logged_in;
  $("admin-panel").hidden = !s.logged_in;
  if (!s.logged_in) {
    const first = !s.has_pin;
    $("pin-title").textContent = first ? "Set an admin PIN" : "Log in";
    $("pin-help").textContent = first
      ? "No PIN is set yet. The PIN you choose now protects updates and network settings. Use 4 to 12 digits."
      : "Enter the admin PIN.";
    $("pin-submit").textContent = first ? "Set PIN" : "Log in";
    $("pin-form").dataset.first = first ? "1" : "";
    $("pin").autocomplete = first ? "new-password" : "current-password";
    return;
  }
  await Promise.all([loadReleases(), loadNetwork(), loadAudio(), offerTime()]);
}

// Without NTP or an RTC the Pi's date may be wrong; an admin's phone is the best clock
// in the tower (design C16). Offered automatically on admin connection.
async function offerTime() {
  try {
    const d = await api("/api/diagnostics");
    if (d.wall_clock && d.wall_clock.source === "none") {
      await api("/api/admin/time", { method: "POST", body: { epoch_ms: Date.now() } });
    }
  } catch (_) { /* best effort */ }
}

function describeResult(r) {
  if (!r) return "none";
  const what = r.action === "rollback" ? "Rollback" : "Update";
  if (r.result === "in_progress") return `${what} to ${r.version} in progress (${r.at})`;
  const verdict = r.result === "ok" ? "succeeded" : "FAILED";
  return `${what} to ${r.version} ${verdict} at ${r.at}${r.detail ? ` — ${r.detail}` : ""}`;
}

async function loadReleases() {
  const r = await api("/api/admin/releases");
  $("rel-running").textContent = r.running;
  $("rel-current").textContent = r.current || "none (running from a source checkout)";
  $("rel-previous").textContent = r.previous || "none";
  $("rel-last").textContent = describeResult(r.last_result);
  $("rel-systemd").hidden = r.systemd;
  $("rollback").disabled = !r.previous;
}

async function loadNetwork() {
  const n = await api("/api/admin/network");
  $("net-mode").value = n.mode;
  $("net-ap-ssid").value = n.ap_ssid || "";
  $("net-up-ssid").value = n.uplink_ssid || "";
  $("net-up-psk").placeholder = n.uplink_psk_set ? "unchanged" : "none";
  const info = await api("/api/info");
  $("net-ap-psk").value = info.ap_psk;
  if (!n.available) {
    $("net-status").textContent = n.detail;
  } else {
    const parts = [`AP ${n.ap_active ? "up" : "down"}`, `uplink ${n.uplink_active ? "up" : "down"}`,
      n.dongle ? `dongle ${n.dongle}` : "no USB dongle"];
    if (n.last_apply) parts.push(`last change: ${n.last_apply.detail}`);
    $("net-status").textContent = parts.join(" · ");
  }
}

$("pin-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("pin-error").textContent = "";
  const first = $("pin-form").dataset.first === "1";
  try {
    await api(first ? "/api/admin/pin" : "/api/admin/login", { method: "POST", body: { pin: $("pin").value } });
    $("pin").value = "";
    loadAdmin();
  } catch (e) {
    $("pin-error").textContent = e.message;
  }
});

$("logout").addEventListener("click", async () => {
  await api("/api/admin/logout", { method: "POST" });
  loadAdmin();
});

$("change-pin-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  try {
    await api("/api/admin/pin", { method: "POST", body: { pin: $("new-pin").value } });
    $("new-pin").value = "";
    $("change-pin-result").textContent = "PIN changed.";
  } catch (e) {
    $("change-pin-result").textContent = e.message;
  }
});

// Upload sends the raw file (no multipart) so progress can be shown on a slow AP link.
$("upload-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const file = $("bundle").files[0];
  if (!file) return;
  const bar = $("upload-progress");
  const out = $("upload-result");
  bar.hidden = false;
  bar.value = 0;
  out.textContent = `Uploading ${file.name}…`;
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/admin/update");
  xhr.setRequestHeader("X-Tower-Request", "1");
  xhr.setRequestHeader("Content-Type", "application/octet-stream");
  xhr.upload.onprogress = (e) => { if (e.lengthComputable) bar.value = (100 * e.loaded) / e.total; };
  xhr.onerror = () => { out.textContent = "Upload failed: connection lost."; };
  xhr.onload = () => {
    bar.hidden = true;
    let data = {};
    try { data = JSON.parse(xhr.responseText); } catch (_) { /* leave empty */ }
    if (xhr.status !== 202) {
      out.textContent = `Upload ${data.error ? data.error : `failed (HTTP ${xhr.status})`}`;
      return;
    }
    out.textContent = `Verified and staged ${data.staged}. Activation: ${data.activation}`;
    if (data.activation.startsWith("handed")) waitForRestart(data.staged, out);
    else loadReleases();
  };
  xhr.send(file);
});

$("rollback").addEventListener("click", async () => {
  if (!confirm("Roll back to the previous release?")) return;
  const out = $("upload-result");
  try {
    const r = await api("/api/admin/rollback", { method: "POST" });
    out.textContent = `Rollback: ${r.rollback}`;
    if (r.rollback.startsWith("handed")) waitForRestart(null, out);
  } catch (e) {
    out.textContent = `Rollback failed: ${e.message}`;
  }
});

// After a handoff the app restarts. Poll until the updater has recorded an outcome.
async function waitForRestart(expected, out) {
  const deadline = Date.now() + 180000;
  await new Promise((r) => setTimeout(r, 3000));
  while (Date.now() < deadline) {
    try {
      const r = await api("/api/admin/releases");
      const last = r.last_result;
      if (last && last.result !== "in_progress" && (!expected || last.version === expected)) {
        out.textContent = describeResult(last);
        loadReleases();
        return;
      }
    } catch (_) {
      // Restarting, or the session ended with the restart.
      try {
        if (!(await api("/api/admin/session")).logged_in) {
          out.textContent = "The app restarted. Log in again to see the result.";
          loadAdmin();
          return;
        }
      } catch (_) { /* still down */ }
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  out.textContent = "No result yet. Check Diagnostics.";
}

$("net-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const mode = $("net-mode").value;
  const body = {
    mode,
    ap_ssid: $("net-ap-ssid").value,
    ap_psk: $("net-ap-psk").value,
    uplink_ssid: $("net-up-ssid").value,
  };
  if ($("net-up-psk").value) body.uplink_psk = $("net-up-psk").value;
  if (mode === "joined" && !confirm(
    "In 'join' mode the tower access point turns off. If joining fails it comes back on its own. Continue?")) return;
  try {
    const r = await api("/api/admin/network", { method: "POST", body });
    $("net-result").textContent = r.applied === "in progress"
      ? "Saved. Applying now; you may need to reconnect to the WiFi."
      : r.detail;
    $("net-up-psk").value = "";
    setTimeout(loadNetwork, 4000);
  } catch (e) {
    $("net-result").textContent = e.message;
  }
});

$("diag-refresh").addEventListener("click", loadDiagnostics);

// --- live ringing --------------------------------------------------------------

const IDLE_AFTER_MS = 30000; // README: ringing view until a 30 s pause
const bellEls = new Map();
let lastStrikeAt = 0;
// Server monotonic t → this page's clock. Only events stamped at send time
// (heartbeat, state) qualify; strikes carry their future strike time.
const offsets = [];

function noteServerTime(t) {
  offsets.push(performance.now() / 1000 - t);
  if (offsets.length > 30) offsets.shift();
}

function serverToLocalMs(t) {
  if (!offsets.length) return performance.now();
  return (t + Math.min(...offsets)) * 1000;
}

function bellEl(n) {
  if (!bellEls.has(n)) {
    const el = document.createElement("div");
    el.className = "bell";
    el.textContent = n;
    el.dataset.bell = n;
    bellEls.set(n, el);
    const sorted = [...bellEls.keys()].sort((a, b) => a - b);
    $("bells").replaceChildren(...sorted.map((k) => bellEls.get(k)));
  }
  return bellEls.get(n);
}

function onStrike(p, t) {
  const delay = Math.max(0, serverToLocalMs(t) - performance.now());
  setTimeout(() => {
    const el = bellEl(p.bell);
    el.classList.remove("hand", "back");
    el.classList.add(p.stroke, "flash");
    setTimeout(() => el.classList.remove("flash"), 120);
    lastStrikeAt = Date.now();
    showRinging(true);
  }, delay);
}

function showRinging(on) {
  $("ringing").hidden = !on;
  $("idle").hidden = on;
}

setInterval(() => {
  if (lastStrikeAt && Date.now() - lastStrikeAt > IDLE_AFTER_MS) showRinging(false);
}, 1000);

function connectEvents() {
  const es = new EventSource("/api/events");
  es.onmessage = (msg) => {
    let env;
    try { env = JSON.parse(msg.data); } catch (_) { return; }
    if (env.type === "system" || env.type === "state") noteServerTime(env.t);
    if (env.type === "strike") onStrike(env.payload, env.t);
    if (env.type === "state" && env.payload.strokes_reset) {
      for (const el of bellEls.values()) el.classList.remove("hand", "back");
    }
  };
  // EventSource reconnects by itself; the server sends a fresh state snapshot each time.
}

$("reset-strokes").addEventListener("click", () => api("/api/strokes/reset", { method: "POST" }).catch(() => {}));

// --- admin: sound and calibration ---------------------------------------------------

let calibration = {};

async function loadAudio() {
  const a = await api("/api/admin/audio");
  const sel = $("pack-select");
  sel.replaceChildren(...a.packs.map((p) => {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.name;
    o.selected = p.id === a.active;
    return o;
  }));
  $("volume").value = a.volume_db;
  $("volume-value").textContent = a.volume_db;
  calibration = a.calibration_ms;
  const rt = a.rt;
  $("audio-status").textContent = !rt ? "The sound engine is not reporting."
    : rt.audio.status === "ok" ? `Playing on ${rt.audio.device}. ${rt.audio.late} late strikes, ${rt.audio.steals} voice steals.`
    : `Sound unavailable: ${rt.audio.detail}`;
  try { $("cal-bells").value = localStorage.getItem("calBells") || 8; } catch (_) { /* private mode */ }
  renderCalibration();
}

function renderCalibration() {
  const n = Math.max(2, Math.min(16, Number($("cal-bells").value) || 8));
  const table = $("cal-table");
  table.replaceChildren();
  const hr = table.insertRow();
  for (const h of ["Bell", "Handstroke", "Backstroke", ""]) {
    const th = document.createElement("th");
    th.textContent = h;
    hr.appendChild(th);
  }
  for (let bell = 1; bell <= n; bell++) {
    const tr = table.insertRow();
    tr.insertCell().textContent = bell;
    for (const stroke of ["hand", "back"]) {
      const td = tr.insertCell();
      const ms = document.createElement("span");
      ms.className = "ms";
      ms.textContent = `${((calibration[bell] || {})[stroke] || 0).toFixed(0)} ms`;
      const nudge = (steps, label) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "secondary";
        b.textContent = label;
        b.setAttribute("aria-label", `${label === "−" ? "Earlier" : "Later"} ${stroke}stroke, bell ${bell}`);
        b.onclick = async () => {
          try {
            const r = await api("/api/admin/calibration", { method: "POST", body: { bell, stroke, steps } });
            calibration[bell] = { ...(calibration[bell] || {}), [stroke]: r.ms };
            ms.textContent = `${r.ms.toFixed(0)} ms`;
            $("cal-result").textContent = r.applied ? "" : "Saved; the sound engine is not running, it will pick this up when it starts.";
          } catch (e) { $("cal-result").textContent = e.message; }
        };
        return b;
      };
      td.append(nudge(-1, "−"), ms, nudge(1, "+"));
    }
    const ring = document.createElement("button");
    ring.type = "button";
    ring.className = "secondary";
    ring.textContent = "Ring";
    ring.onclick = () => api("/api/admin/test-strike", { method: "POST", body: { bell } }).catch((e) => {
      $("cal-result").textContent = e.message;
    });
    tr.insertCell().appendChild(ring);
  }
}

$("cal-bells").addEventListener("change", () => {
  try { localStorage.setItem("calBells", $("cal-bells").value); } catch (_) { /* private mode */ }
  renderCalibration();
});

$("pack-select").addEventListener("change", async () => {
  try {
    await api("/api/admin/soundpack/select", { method: "POST", body: { id: $("pack-select").value } });
    $("pack-result").textContent = "Sound pack changed.";
  } catch (e) { $("pack-result").textContent = e.message; }
});

let volumeTimer;
$("volume").addEventListener("input", () => {
  $("volume-value").textContent = $("volume").value;
  clearTimeout(volumeTimer);
  volumeTimer = setTimeout(() => api("/api/admin/volume", { method: "POST", body: { db: Number($("volume").value) } })
    .catch((e) => { $("pack-result").textContent = e.message; }), 150);
});

$("pack-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const file = $("pack-file").files[0];
  if (!file) return;
  $("pack-result").textContent = `Uploading ${file.name}…`;
  try {
    const resp = await fetch("/api/admin/soundpack", {
      method: "POST",
      headers: { "X-Tower-Request": "1", "Content-Type": "application/zip" },
      body: file,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    $("pack-result").textContent = `Installed ${data.installed.name} (${data.installed.bells.length} bells). Select it above to use it.`;
    loadAudio();
  } catch (e) { $("pack-result").textContent = `Upload failed: ${e.message}`; }
});

// --- start -------------------------------------------------------------------

if (wall) document.body.classList.add("wall");
window.addEventListener("hashchange", route);
loadInfo().catch(() => {});
connectEvents();
route();
