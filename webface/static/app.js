/* benny webface — thin client. talks to the local server only. */
(function () {
  "use strict";

  const chat = document.getElementById("chat");
  const entry = document.getElementById("entry");
  const send = document.getElementById("send");
  const attach = document.getElementById("attach");
  const file = document.getElementById("file");
  const orb = document.getElementById("orb");
  const levelBadge = document.getElementById("level-badge");
  const memChip = document.getElementById("mem-chip");
  const latChip = document.getElementById("lat-chip");
  const clearBtn = document.getElementById("clear");
  const approval = document.getElementById("approval");
  const approvalUrl = document.getElementById("approval-url");
  const approvalQuery = document.getElementById("approval-query");
  const approvalYes = document.getElementById("approval-yes");
  const approvalNo = document.getElementById("approval-no");
  let approvalPoll = null;

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // markdown-lite renderer: headers, bold/italic, code blocks + spans,
  // bullet/numbered lists, links, horizontal rules, <br> paragraphs.
  // everything is escaped first; code and html-only links only (no scripts).
  function render(text) {
    const stash = [];
    const hold = (html) => { stash.push(html); return "\u0000" + (stash.length - 1) + "\u0000"; };

    function inline(s) {
      // links — https only, never raw javascript:
      s = s.replace(/\[([^\]]*)\]\(([^)\s]*)\)/g, (m, t, u) =>
        /^https?:\/\//i.test(u)
          ? '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + t + "</a>"
          : t);
      // bold **x** before italic *x* so the * inside ** isn't eaten
      s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      return s;
    }

    let html = esc(text).replace(/\r\n?/g, "\n");
    // code blocks first (their content is already escaped + stashed)
    html = html.replace(/```([\s\S]*?)```/g, (_, code) =>
      hold("<pre><code>" + code.replace(/^\n|\n$/g, "") + "</code></pre>"));
    // inline code spans
    html = html.replace(/`([^`\n]+)`/g, (_, code) => hold("<code>" + code + "</code>"));

    const out = [];
    let brace = null; // open <ul>/<ol> while collecting items
    let para = [];    // current plain-text group

    const flushPara = () => { if (para.length) { out.push(para.join("<br>")); para = []; } };
    const flushList = () => { if (brace) { out.push("</" + brace + ">"); brace = null; } };
    const flushAll = () => { flushPara(); flushList(); };

    for (const ln of html.split("\n")) {
      if (!ln.trim()) { flushAll(); continue; }               // blank = block break
      if (/^\s*(?:---|\*\*\*|___)\s*$/.test(ln)) {            // hr
        flushAll(); out.push("<hr>");
      } else if (/^(#{1,4})\s+(.*)$/.test(ln)) {              // headers
        flushAll();
        const lvl = RegExp.$1.length;
        out.push("<h" + lvl + ">" + inline(RegExp.$2) + "</h" + lvl + ">");
      } else if (/^\s*[-*+]\s+(.*)$/.test(ln)) {              // ul
        flushPara();
        if (brace !== "ul") { flushList(); brace = "ul"; out.push("<ul>"); }
        out.push("<li>" + inline(RegExp.$1) + "</li>");
      } else if (/^\s*\d+[.)]\s+(.*)$/.test(ln)) {            // ol
        flushPara();
        if (brace !== "ol") { flushList(); brace = "ol"; out.push("<ol>"); }
        out.push("<li>" + inline(RegExp.$1) + "</li>");
      } else {                                                // plain group
        flushList();
        para.push(inline(ln));
      }
    }
    flushAll();
    return out.join("").replace(/\u0000(\d+)\u0000/g, (_, n) => stash[+n]);
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

  // sample N evenly-spaced frames from an animated gif via canvas
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
        // draw using gif animation: browsers render the CURRENT frame, so
        // capture at staggered times won't work without a decoder — instead
        // sample the composed current frame a few times via load.
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
    const f = file.files && file.files[0];
    if (!f) return;
    file.value = "";

    if (!/^image\//.test(f.type) && !/\.gif$/i.test(f.name)) {
      addMsg("you", "(not an image — benny can only look at pictures right now)");
      return;
    }

    const wrap = addImageMsg("you", (function () {
      const img = document.createElement("img");
      img.alt = "attached";
      img.className = "attach";
      img.src = URL.createObjectURL(f);
      return img;
    })());

    const pending = addMsg("benny", "looking…", true);
    setBusy(true);

    const reader = new FileReader();
    reader.onload = async function () {
      const b64 = String(reader.result).split(",")[1];
      const isGif = /\.gif$/i.test(f.name) || f.type === "image/gif";
      const question = entry.value.trim() || "Describe what's in this image in one or two sentences.";
      entry.value = "";
      let payload = { question: isGif ? "Describe what is happening across these frames of an animated image." : question };
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
      const res = await fetch("/see", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.status);
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "";
      pending.querySelector(".bubble").innerHTML = render("(" + data.reply + ")");
      if (typeof data.latency_ms === "number")
        latChip.textContent = data.latency_ms + "ms";
    } catch (e) {
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "error: " + e.message;
    } finally {
      setBusy(false);
      chat.scrollTop = chat.scrollHeight;
    }
  }

  function setBusy(busy) {
    send.disabled = busy;
    if (busy) {
      orb.classList.add("thinking");
      startApprovalPoll();
    } else {
      orb.classList.remove("thinking");
      stopApprovalPoll();
      hideApproval();
    }
  }

  // ---- conversation history ----
  async function loadHistory() {
    try {
      const res = await fetch("/history", { cache: "no-store" });
      const data = await res.json();
      for (const m of data.messages || []) {
        if (m.who === "you") {
          addMsg("you", m.text);
        } else {
          const el = addMsg("benny", m.text);
          const gif = pickGif(m.text);
          if (gif) appendGif(el.querySelector(".bubble"), gif);
        }
      }
      chat.scrollTop = chat.scrollHeight;
    } catch (_) { /* history is a bonus, not a requirement */ }
  }

  async function clearChat() {
    if (!window.confirm("wipe this conversation history?")) return;
    try {
      await fetch("/clear", { method: "POST" });
    } catch (_) {}
    chat.innerHTML = "";
  }

  // ---- gatekeeper approval modal ----
  function startApprovalPoll() {
    stopApprovalPoll();
    approvalPoll = setInterval(async () => {
      try {
        const res = await fetch("/approval-status", { cache: "no-store" });
        const d = await res.json();
        if (d && d.pending) showApproval(d);
        else hideApproval();
      } catch (_) {}
    }, 700);
  }

  function stopApprovalPoll() {
    if (approvalPoll) { clearInterval(approvalPoll); approvalPoll = null; }
  }

  function showApproval(d) {
    approvalUrl.textContent = d.url || "?";
    approvalQuery.textContent = d.query
      ? "query: " + d.query
      : "benny wants to fetch a URL you haven't allowed yet.";
    approval.hidden = false;
  }

  function hideApproval() {
    approval.hidden = true;
  }

  async function answerApproval(approved) {
    try {
      await fetch("/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
    } catch (_) {}
    hideApproval();
  }

  async function ping() {
    try {
      const res = await fetch("/health", { cache: "no-store" });
      const data = await res.json();
      if (data.status === "ready") {
        orb.classList.remove("dead");
      }
    } catch (_) {
      /* face stays calm if server's asleep */
    }
  }
  ping();
  setInterval(ping, 30000);

  // mood -> pack file + trigger words (see gifs/README.md)
  const MOODS = [
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
    for (const m of MOODS) if (m.re.test(reply)) return m.file;
    return null;
  }

  function appendGif(bubble, name) {
    const img = document.createElement("img");
    img.className = "gifreact";
    img.src = "/gifs/" + name;
    img.alt = name;
    img.loading = "lazy";
    img.onerror = () => img.remove();
    bubble.appendChild(img);
    return img;
  }

  async function ask() {
    const text = entry.value.trim();
    if (!text) return;
    entry.value = "";
    addMsg("you", text);
    const pending = addMsg("benny", "whispering…", true);
    setBusy(true);
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.status);
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "";
      pending.querySelector(".bubble").innerHTML = render(data.reply);
      const gif = pickGif(data.reply);
      if (gif) appendGif(pending.querySelector(".bubble"), gif);
      if (data.level) levelBadge.textContent = data.level;
      if (typeof data.memory === "number")
        memChip.textContent = "mem " + data.memory;
      if (typeof data.latency_ms === "number")
        latChip.textContent = data.latency_ms + "ms";
    } catch (e) {
      pending.classList.remove("typing");
      pending.querySelector(".bubble").textContent = "error: " + e.message;
    } finally {
      setBusy(false);
      chat.scrollTop = chat.scrollHeight;
    }
  }

  send.addEventListener("click", ask);
  attach.addEventListener("click", () => file.click());
  file.addEventListener("change", attachFile);
  clearBtn.addEventListener("click", clearChat);
  approvalYes.addEventListener("click", () => answerApproval(true));
  approvalNo.addEventListener("click", () => answerApproval(false));
  entry.addEventListener("keydown", (e) => {
    if (e.key === "Enter") ask();
  });
  loadHistory();
  entry.focus();
})();