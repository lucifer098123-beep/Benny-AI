(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  const chat = $("chat");
  const entry = $("entry");
  const send = $("send");
  const attach = $("attach");
  const file = $("file");
  const drawer = $("drawer");
  const scrim = $("scrim");
  const menuBtn = $("menu");
  const emptyEl = $("empty");
  const sessionList = $("session-list");
  const sessionEmpty = $("session-empty");
  const topTitle = $("top-title");

  const ICO_EYE =
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const ICO_EYE_OFF =
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/><path d="M14.12 14.12a3 3 0 11-4.24-4.24"/></svg>';
  const ICO_TRASH =
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>';

  const state = {
    active: null,
    busy: false,
  };

  const orbs = document.querySelectorAll(".orb");

  function setLevel(v) {
    const t = v || "novice";
    $("level-badge").textContent = t;
    $("d-level").textContent = t;
  }
  function setMem(v) {
    const t = typeof v === "number" ? v : 0;
    $("mem-chip").textContent = "mem " + t;
    $("d-mem").textContent = t;
  }
  function setLat(v) {
    if (typeof v !== "number") return;
    const t = v + " ms";
    $("lat-chip").textContent = t;
    $("d-lat").textContent = t;
  }
  function setEyes(ok) {
    const chip = $("eyes-chip");
    chip.textContent = "eyes " + (ok ? "online" : "offline");
    chip.className = "chip " + (ok ? "on" : "off");
    const dEyes = $("d-eyes");
    dEyes.textContent = ok ? "online" : "offline";
    dEyes.className = ok ? "on" : "";
  }

  function setOrbsThinking(on) {
    orbs.forEach(function (o) {
      o.classList.toggle("thinking", on);
    });
  }
  function setOrbsDead(on) {
    orbs.forEach(function (o) {
      o.classList.toggle("dead", on);
    });
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function render(text) {
    const parts = String(text).split(/`([^`]+)`/g);
    return parts
      .map(function (p, i) {
        return i % 2 === 1
          ? "<code>" + esc(p) + "</code>"
          : esc(p).replace(/\n/g, "<br>");
      })
      .join("");
  }

  function addMsg(who, text, typing) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + who + (typing ? " typing" : "");
    const label = document.createElement("span");
    label.className = "who";
    label.textContent = who === "benny" ? "benny" : "you";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = render(text);
    wrap.appendChild(label);
    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
    return wrap;
  }

  function addImageMsg(who, imgEl) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + who + " image";
    const label = document.createElement("span");
    label.className = "who";
    label.textContent = who === "benny" ? "benny" : "you";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.appendChild(imgEl);
    wrap.appendChild(label);
    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
    return wrap;
  }

  function clearChat() {
    chat.querySelectorAll(".msg").forEach(function (m) { m.remove(); });
  }

  function showEmpty() { emptyEl.hidden = false; }
  function hideEmpty() { emptyEl.hidden = true; }

  function setBusy(busy) {
    state.busy = busy;
    send.disabled = busy;
    attach.disabled = busy;
    setOrbsThinking(busy);
  }

  function relTime(tsSec) {
    const s = Math.floor(Date.now() / 1000 - tsSec);
    if (s < 45) return "just now";
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    if (s < 86400) return Math.floor(s / 3600) + "h ago";
    if (s < 172800) return "yesterday";
    const d = new Date(tsSec * 1000);
    const now = new Date();
    if (d.getFullYear() === now.getFullYear())
      return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  // ===== API =====
  async function api(path, opts) {
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch (_) { /* non-json */ }
    if (!res.ok) {
      const err = new Error(data.error || data.message || ("http " + res.status));
      err.data = data;
      throw err;
    }
    return data;
  }

  // ===== sessions =====
  function renderSessionList(sessions) {
    state.sessions = sessions || state.sessions || [];
    const visible = state.sessions.filter(function (s) { return s.count > 0; });
    sessionEmpty.hidden = visible.length > 0;
    sessionList.textContent = "";
    visible.forEach(function (s) {
      const row = document.createElement("div");
      row.className = "session-row" + (state.active && state.active.id === s.id ? " active" : "");
      row.dataset.id = s.id;

      const open = document.createElement("button");
      open.className = "session-open";
      open.type = "button";
      open.dataset.id = s.id;
      open.setAttribute("aria-label", "open chat: " + esc(s.title));

      const title = document.createElement("span");
      title.className = "s-title";
      title.textContent = s.title;
      const time = document.createElement("span");
      time.className = "s-time";
      time.textContent = relTime(s.updated);
      open.appendChild(title);
      open.appendChild(time);

      const del = document.createElement("button");
      del.className = "session-del";
      del.type = "button";
      del.dataset.id = s.id;
      del.setAttribute("aria-label", "delete chat: " + esc(s.title));
      del.innerHTML = ICO_TRASH;

      row.appendChild(open);
      row.appendChild(del);
      sessionList.appendChild(row);
    });
  }

  async function refreshSessions() {
    try {
      const d = await api("/sessions");
      renderSessionList(d.sessions || []);
    } catch (_) { /* keep what we have */ }
  }

  async function loadSession(id) {
    setBusy(true);
    try {
      const d = await api("/session?id=" + encodeURIComponent(id));
      state.active = { id: d.id, title: d.title };
      clearChat();
      const msgs = d.messages || [];
      msgs.forEach(function (m) {
        if (m && m.content) addMsg(m.role === "benny" ? "benny" : "you", m.content);
      });
      if (msgs.length === 0) showEmpty(); else hideEmpty();
      topTitle.textContent = d.title || "";
      renderSessionList();
    } catch (e) {
      addMsg("benny", "couldn't load that chat: " + e.message);
      hideEmpty();
    } finally {
      setBusy(false);
    }
  }

  async function newChat() {
    setBusy(true);
    try {
      const d = await api("/session", { method: "POST" });
      state.active = { id: d.id, title: d.title };
      clearChat();
      showEmpty();
      topTitle.textContent = "";
      renderSessionList();
      closeDrawer();
      entry.focus();
    } catch (e) {
      addMsg("benny", "couldn't start a new chat: " + e.message);
      hideEmpty();
    } finally {
      setBusy(false);
    }
  }

  async function deleteSession(id) {
    try {
      await api("/session?del=" + encodeURIComponent(id), { method: "POST" });
      state.sessions = (state.sessions || []).filter(function (s) { return s.id !== id; });
      renderSessionList();
      if (state.active && state.active.id === id) {
        state.active = null;
        clearChat();
        showEmpty();
        topTitle.textContent = "";
      }
    } catch (e) {
      addMsg("benny", "couldn't delete that chat: " + e.message);
      hideEmpty();
    }
  }

  sessionList.addEventListener("click", function (e) {
    const del = e.target.closest(".session-del");
    if (del) { deleteSession(del.dataset.id); return; }
    const open = e.target.closest(".session-open");
    if (open) { loadSession(open.dataset.id); closeDrawer(); entry.focus(); }
  });

  // ===== drawer =====
  function openDrawer() {
    drawer.classList.add("open");
    scrim.classList.add("on");
    drawer.setAttribute("aria-hidden", "false");
    menuBtn.setAttribute("aria-expanded", "true");
    refreshSessions();
    loadBrain();
    $("drawer-close").focus();
  }
  function closeDrawer() {
    drawer.classList.remove("open");
    scrim.classList.remove("on");
    drawer.setAttribute("aria-hidden", "true");
    menuBtn.setAttribute("aria-expanded", "false");
    menuBtn.focus();
  }
  function toggleDrawer() {
    if (drawer.classList.contains("open")) closeDrawer(); else openDrawer();
  }

  menuBtn.addEventListener("click", toggleDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);

  $("new-chat").addEventListener("click", newChat);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && drawer.classList.contains("open")) closeDrawer();
  });

  // ===== model port =====
  async function loadBrain() {
    try {
      const d = await api("/brain");
      const b = d.brain || {};
      $("brain-summary").textContent = (b.mode || "?") + " \u00b7 " + (b.model || "?");
      $("b-mode").textContent = b.mode || "\u2014";
      $("b-model").textContent = b.model || "\u2014";
      $("b-heavy").textContent = b.model_heavy || "\u2014";
      $("b-endpoint").textContent = b.endpoint || "\u2014";
      const ready = !!b.ready;
      $("b-ready").textContent = ready ? "online" : "offline";
      $("b-ready").className = "badge" + (ready ? " on" : "");
      const vision = !!d.vision;
      $("b-vision").textContent = vision ? "online" : "offline";
      $("b-vision").className = "badge" + (vision ? " on" : "");
      setEyes(d.vision || false);
    } catch (_) {
      $("brain-summary").textContent = "unreachable";
    }
  }

  function setBrainMsg(text, kind) {
    const el = $("brain-msg");
    el.textContent = text || "";
    el.className = "brain-msg" + (kind ? " " + kind : "");
  }

  const keyToggle = $("key-toggle");
  keyToggle.innerHTML = ICO_EYE;
  let keyShown = false;
  keyToggle.addEventListener("click", function () {
    keyShown = !keyShown;
    $("f-key").type = keyShown ? "text" : "password";
    keyToggle.innerHTML = keyShown ? ICO_EYE_OFF : ICO_EYE;
    keyToggle.setAttribute("aria-label", keyShown ? "hide api key" : "show api key");
  });

  $("brain-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {};
    const model = $("f-model").value.trim();
    const endpoint = $("f-endpoint").value.trim();
    const key = $("f-key").value.trim();
    if (model) body.model = model;
    if (endpoint) body.endpoint = endpoint;
    if (key) body.api_key = key;
    if (!Object.keys(body).length) {
      setBrainMsg("fill at least one field to switch", "warn");
      return;
    }
    const btn = $("brain-switch");
    btn.disabled = true;
    try {
      const d = await api("/brain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setBrainMsg(d.message || "brain switched", "good");
      loadBrain();
    } catch (err) {
      setBrainMsg("error: " + err.message, "bad");
    } finally {
      btn.disabled = false;
    }
  });

  // ===== health =====
  async function ping() {
    try {
      const d = await api("/health", { cache: "no-store" });
      const ok = d.status === "ready";
      setOrbsDead(!ok);
      setEyes(ok && !!d.vision);
      if (d.model) $("brain-summary").textContent = d.model;
    } catch (_) {
      setOrbsDead(true);
      setEyes(false);
    }
  }

  // ===== gif reactions =====
  var MOODS = [
    { file: "laugh.gif",  re: /😂+|🤣+|ha+h+|funny|lol|lmao/i },
    { file: "kudos.gif",  re: /kudos|locked|shipped|master key|\bwin\b|nice\b/i },
    { file: "fire.gif",   re: /cooking|🔥|on fire|live\b|running now|hot/i },
    { file: "think.gif",  re: /\bhmm\b|pattern|actually|interesting|wait\.\.\./i },
    { file: "t_t.gif",    re: /T_T|sorry|oops|rip|that failed|nooo/i },
    { file: "blink.gif",  re: /no way|ohh|whoa|really\?|\?!/i },
    { file: "win.gif",    re: /battle|victory|flex|bracket|podium|champion/i },
    { file: "gg.gif",     re: /\bgg\b|that's a wrap|done and dusted|fin\b/i },
    { file: "salute.gif", re: /respect|on it|boss|o7/i },
    { file: "grin.gif",   re: /\\o|great work|smooth|clean\b/i },
  ];

  function pickGif(reply) {
    for (var i = 0; i < MOODS.length; i++) {
      if (MOODS[i].re.test(reply)) return MOODS[i].file;
    }
    return null;
  }

  function appendGif(bubble, name) {
    var img = document.createElement("img");
    img.className = "gifreact";
    img.src = "/gifs/" + name;
    img.alt = name;
    img.loading = "lazy";
    img.onerror = function () { img.remove(); };
    bubble.appendChild(img);
    return img;
  }

  // ===== chat =====
  async function ask() {
    var text = entry.value.trim();
    if (!text || state.busy) return;
    entry.value = "";
    hideEmpty();
    addMsg("you", text);
    var pending = addMsg("benny", "whispering\u2026", true);
    setBusy(true);
    try {
      var payload = { text: text };
      if (state.active) payload.session_id = state.active.id;
      var data = await api("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      pending.classList.remove("typing");
      pending.querySelector(".bubble").innerHTML = render(data.reply);
      var gif = pickGif(data.reply);
      if (gif) appendGif(pending.querySelector(".bubble"), gif);
      if (data.level) setLevel(data.level);
      if (typeof data.memory === "number") setMem(data.memory);
      if (typeof data.latency_ms === "number") setLat(data.latency_ms);
      if (!state.active || state.active.id !== data.session_id) {
        state.active = { id: data.session_id, title: "new chat" };
      }
      refreshSessions();
    } catch (e) {
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "error: " + e.message;
      hideEmpty();
    } finally {
      setBusy(false);
      chat.scrollTop = chat.scrollHeight;
      entry.focus();
    }
  }

  // ===== vision lane =====
  function sampleGifFrames(file, n, cb) {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = function () {
      const frames = [];
      let done = 0;
      const canvas = document.createElement("canvas");
      const w = Math.max(1, Math.round(img.width / 2));
      const h = Math.max(1, Math.round(img.height / 2));
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (img.width > 0 && img.height > 0) {
        for (let i = 0; i < n; i++) {
          (function (idx) {
            setTimeout(function () {
              try {
                ctx.fillStyle = "#000";
                ctx.fillRect(0, 0, w, h);
                ctx.drawImage(img, 0, 0, w, h);
                frames.push(canvas.toDataURL("image/webp", 0.6).split(",")[1] || "");
              } catch (_) {
                frames.push("");
              }
              done++;
              if (done === n) {
                URL.revokeObjectURL(url);
                cb(frames.join(",") ? frames : null);
              }
            }, idx * 80);
          })(i);
        }
      } else {
        cb(null);
      }
    };
    img.onerror = function () { URL.revokeObjectURL(url); cb(null); };
    img.src = url;
  }

  function attachFile() {
    if (state.busy) return;
    const f = file.files && file.files[0];
    if (!f) return;
    file.value = "";

    if (!/^image\//.test(f.type) && !/\.gif$/i.test(f.name)) {
      addMsg("you", "(not an image \u2014 benny can only look at pictures right now)");
      hideEmpty();
      return;
    }

    hideEmpty();
    addImageMsg("you", (function () {
      const img = document.createElement("img");
      img.alt = "attached";
      img.className = "attach";
      img.src = URL.createObjectURL(f);
      return img;
    })());

    const pending = addMsg("benny", "looking\u2026", true);
    setBusy(true);

    const reader = new FileReader();
    reader.onload = async function () {
      const b64 = String(reader.result).split(",")[1];
      const isGif = /\.gif$/i.test(f.name) || f.type === "image/gif";
      const question = entry.value.trim() || "Describe what's in this image in one or two sentences.";
      entry.value = "";
      var payload = { question: isGif ? "Describe what is happening across these frames of an animated image." : question };
      if (isGif) {
        sampleGifFrames(f, 6, async function (frames) {
          payload.frames = frames || [b64];
          await sendSee(pending, payload);
        });
      } else {
        payload.base64 = b64;
        await sendSee(pending, payload);
      }
    };
    reader.readAsDataURL(f);
  }

  async function sendSee(pending, payload) {
    try {
      const data = await api("/see", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      pending.classList.remove("typing");
      pending.querySelector(".bubble").innerHTML = render("(" + data.reply + ")");
      if (typeof data.latency_ms === "number") setLat(data.latency_ms);
    } catch (e) {
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "error: " + e.message;
    } finally {
      setBusy(false);
      chat.scrollTop = chat.scrollHeight;
    }
  }

  send.addEventListener("click", ask);
  attach.addEventListener("click", function () { if (!state.busy) file.click(); });
  file.addEventListener("change", attachFile);
  entry.addEventListener("keydown", function (e) {
    if (e.key === "Enter") ask();
  });

  // ===== boot =====
  ping();
  setInterval(ping, 30000);
  loadBrain();
  refreshSessions().then(function () {
    if (state.sessions && state.sessions.length) {
      const newest = state.sessions.slice().sort(function (a, b) { return b.updated - a.updated; })[0];
      if (newest && newest.count > 0) {
        loadSession(newest.id);
        return;
      }
    }
    showEmpty();
  });
  entry.focus();
})();