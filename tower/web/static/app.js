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
  await Promise.all([loadReleases(), loadNetwork()]);
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

// --- start -------------------------------------------------------------------

if (wall) document.body.classList.add("wall");
window.addEventListener("hashchange", route);
loadInfo().catch(() => {});
route();
