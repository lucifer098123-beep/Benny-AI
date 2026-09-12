/* benny webface — thin client. talks to the local server only. */
(function () {
  "use strict";

  const chat = document.getElementById("chat");
  const entry = document.getElementById("entry");
  const send = document.getElementById("send");
  const orb = document.getElementById("orb");
  const levelBadge = document.getElementById("level-badge");
  const memChip = document.getElementById("mem-chip");
  const latChip = document.getElementById("lat-chip");

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // minimal formatting: backticks -> code, nothing else. keeps replies honest.
  function render(text) {
    const parts = text.split(/`([^`]+)`/g);
    return parts
      .map((p, i) =>
        i % 2 === 1 ? "<code>" + esc(p) + "</code>" : esc(p).replace(/\n/g, "<br>")
      )
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

  function setBusy(busy) {
    send.disabled = busy;
    if (busy) orb.classList.add("thinking");
    else orb.classList.remove("thinking");
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
  entry.addEventListener("keydown", (e) => {
    if (e.key === "Enter") ask();
  });
  entry.focus();
})();