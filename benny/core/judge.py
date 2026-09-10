"""LAYER 2 — the judgment engine (benny's moral spine).

Runs the W-questions INTERNALLY (never asked of the user):
    who    -> who or what does the action touch?
    what   -> what is the exact action and its effect?
    where  -> which domain does it land in (offline / internet / other-person)?
    why    -> what is the intent behind it?
    weight -> how much could it hurt? (impact scale)

Verdicts (config-driven, model-agnostic — never welded into the model):
    green  -> full freedom, just do it.
    warn   -> gray lane: give a warning + let the user decide (warn-help-trust).
    refuse -> hard wall: real-person harm. Cannot be overridden by any level.

Core judgment axis: HARM + CONSENT, not action categories.
The same action is judged differently by whom it touches and where it lands.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

# Domain: where does the action land?
DOMAIN_OFFLINE = "offline"            # own machine/files/apps/scripts — absolute freedom
DOMAIN_NET_IN = "internet-inbound"    # read-only: data comes TO benny
DOMAIN_NET_OUT = "internet-outbound"  # write: benny's data leaves the box
DOMAIN_PERSON = "other-person"        # harm to a real person — the only hard wall

# Direction W: the traffic way. Fetching is inbound (safe); sending is outbound (the risk).
DIR_IN = "inbound"      # network -> user. one-way read. low risk.
DIR_OUT = "outbound"    # user/benny -> network. data leaves. the thing to guard.

# Verdicts
V_GREEN = "green"
V_WARN = "warn"
V_REFUSE = "refuse"


class Judge:
    def __init__(self, cfg: dict, audit_dir: str | Path | None = None):
        j = cfg.get("judgment", {})
        self.regulations = j.get("regulations", {})
        self.audit_dir = Path(audit_dir) if audit_dir else None
        if self.audit_dir:
            self.audit_dir.mkdir(parents=True, exist_ok=True)

    # ---- W sub-analyses (rule-based; the model may refine later, never replace) ----
    @staticmethod
    def _who(request: str) -> str:
        """Who/what does it touch? This drives the hard wall — real persons vs own box."""
        low = request.lower()
        # Explicit real-human targets (faster + more specific) first — these are HARD.
        person_targets = re.compile(
            r"classmate|friend|his |her |their |someone[’'']?s|that guy|that person|"
            r"my [^\s]+'s [^\s]+|\b(him|her|them)\b"
        )
        # verb that implies reaching INTO a person's private space / attacking a person
        if re.search(
            r"hack (into )?(his|her|their|someone|classmate|friend|him)\b"
            r"|(\b|into )(his|her|their|classmate|friend)\b (phone|account|profile|bank|camera|device|computer|pc|laptop)"
            r"|\b(dox|stalk|blackmail|harass|doxx)|leak (his|her|their|someone[’'']?s) (address|info|data|messages)"
            r"|read (his|her|their|someone[’'']?s) (messages|dms|chats|phone)\b", low
        ):
            return "other-person"
        if person_targets.search(low):
            return "other-person"
        if re.search(r"\b(my|our|my own|this|the pc|this laptop|local)\b", low):
            return "own-machine"
        return "general"

    @staticmethod
    def _what(request: str) -> str:
        return request.strip()

    @staticmethod
    def _direction(request: str) -> str:
        """Which way does the network traffic flow? Inbound read = safe; outbound = guarded."""
        low = request.lower()
        # explicit OUTBOUND signals: sending data, uploading, posting, submitting,
        # logging in, sending messages, exfil, webhooks, API writes, email...
        if re.search(r"\b(upload|post|submit|send (data|info|file|the|my|project|to)|exfil|"
                     r"exfiltrat|log in|sign in|login|signup|publish|email to|webhook|"
                     r"api (call|post|put)|share (my|my |the )?data|push to|commit to|"
                     r"deploy|send my|send\b.*\b(to )?(a |the )?(webhook|server|api|cloud|email))\b", low):
            return DIR_OUT
        # explicit INBOUND signals: fetching, reading, downloading, browsing (one-way to user)
        if re.search(r"\b(fetch|download|browse|open url|read url|get .* (from|url)|search web|"
                     r"pull (from|the )|load page)\b", low):
            return DIR_IN
        # ambiguous network — default to inbound (safe) so we under-warn reads, not over-warn
        if re.search(r"http://|https://|url|website|web", low):
            return DIR_IN
        return DIR_IN

    @staticmethod
    def _where(request: str) -> str:
        """Where does the action land? Offline freedom; network split by direction."""
        low = request.lower()
        # attacks/breaches live on the network and are covered by _illicit/_weight anyway
        if re.search(r"\b(my|my own|my pc|my laptop|this pc|local|offline|game|save|file|folder"
                     r"|install|uninstall|tweak|mod|script|program)\b", low) and not re.search(
            r"http://|https://|server|website|network|cloud|upload|api", low):
            return DOMAIN_OFFLINE
        if re.search(r"http://|https://|url|website|search web|browse|fetch|download|upload|"
                     r"server|network|cloud|api|post to|email|webhook|send (data|info|file)|"
                     r"upload|publish|deploy|login|sign in|submit", low):
            return DOMAIN_NET_IN if Judge._direction(request) == DIR_IN else DOMAIN_NET_OUT
        return DOMAIN_OFFLINE

    @staticmethod
    def _why(request: str) -> str:
        low = request.lower()
        if re.search(r"\b(hurt|harm|destroy|ruin|embarrass|punish|revenge|get back at)\b", low):
            return "malicious"
        if re.search(r"\b(learn|test|practice|school|study|fun|mine|my|help|fix|clean|optimize)\b", low):
            return "constructive"
        return "neutral"

    @staticmethod
    def _weight(request: str) -> int:
        """Impact scale 1-5. 5 == catastrophic/irreversible harm -> hard wall."""
        low = request.lower()
        if re.search(
            r"\b(ddose|dox|ruin|destroy|blackmail|stalk|hack (his|her|their))"
            r"\b|zero.?day|personal data of (him|her|them)|someone'?s (camera|phone|bank)"
            r"|pentagon|government|military|nuclear|power grid|hospital|school district"
            r"|\b(bank|hospital|airport|power station|dam|railway|defense) (system|site|server|network)", low
        ):
            return 5
        if re.search(r"\b(steal|breach|target (him|her|them)|malware that spreads)\b", low):
            return 4
        if "malware" in low or "keylogger" in low or "ransomware" in low:
            return 3
        if re.search(r"\b(hack|breach|attack)\b", low) or "game cheat" in low or "mod" in low:
            return 2
        return 1

    def _verdict(self, where: str, why: str, weight: int) -> tuple[str, str]:
        """Domain + consent axis -> verdict.
        Prototype phase HARD RULE: anything harmful/illicit is refused flat —
        no gray lane, no malware building, no 'educational' exception. We find
        a legitimate path before shipping the prototype."""
        # HARD WALL 1: potentially-harmful generation (malware/spyware/keylogger/dox/
        # breaches/cracks/ransomware) — refused flat, this phase. No exceptions.
        if weight >= 3:
            return V_REFUSE, "harmful/illicit — benny doesn't build this, even offline, for now"
        # HARD WALL 2: real-person targeting (who W already caught in analyze()).
        if where == DOMAIN_PERSON:
            return V_REFUSE, "targets a real person — benny never opens that door"
        if where == DOMAIN_OFFLINE:
            return V_GREEN, "offline / own machine — full freedom, benny is your hands"
        # INBOUND network = read-only, data comes to benny. Safe. Quiet green (still gatekept).
        if where == DOMAIN_NET_IN:
            return V_GREEN, "inbound read — data comes to you, the gatekeeper checks the route"
        # OUTBOUND network = benny's data LEAVES the box. This is the direction to guard.
        if where == DOMAIN_NET_OUT:
            return V_WARN, "outbound — your data would leave this machine. watch this one"
        return V_GREEN, "benign"

    @staticmethod
    def _illicit(request: str) -> bool:
        """Prototype-phase hard filter: any harmful/illicit generation is refused.
        This is a flat no — no malware, spyware, cracks, exploits, breaches,
        stolen credentials, phishing, or weaponized payloads. We find a
        legitimate path before the prototype ships."""
        low = request.lower()
        return bool(re.search(
            r"\b(malware|keylogger|ransomware|spyware|trojan|rootkit|virus|worm|"
            r"rat\b|botnet|zero.?day exploit|exploit dev|write a (virus|worm)|"
            r"steal (passwords|credentials|accounts)|phishing kit|credit card stealer|"
            r"password cracker|crack software|keygen|cryptominer|spywre|backdoor|"
            r"reverse shell|payload|ddos tool|ddose|bot herder|credential stealer|"
            r"ransom)\b", low))

    def analyze(self, request: str) -> dict:
        """Run the W-questions over a request. Returns the judgment record."""
        who = self._who(request)
        what = self._what(request)
        where = self._where(request)
        why = self._why(request)
        weight = self._weight(request)
        direction = self._direction(request)
        # THE HARD WALL — fires BEFORE anything else. This is the spine.
        verdict, reason = V_GREEN, ""
        if self._illicit(request):
            verdict, reason = V_REFUSE, "harmful/illicit — benny doesn't build this, even offline, for now"
        elif who == "other-person":
            verdict, reason = V_REFUSE, "targets a real person — benny never opens that door"
        else:
            verdict, reason = self._verdict(where, why, weight)
        rec = {
            "request": request,
            "w": {"who": who, "what": what, "where": where, "why": why, "weight": weight,
                  "direction": direction},
            "verdict": verdict,
            "reason": reason,
            "time": time.time(),
        }
        self._audit(rec)
        return rec

    # ---- policy hooks (config-driven verdicts) ----
    def policy_verdict(self, topic: str) -> str | None:
        """External config rules override at the topic level (e.g. 'political propaganda')."""
        regs = self.regulations.get("blocked_internet_topics", [])
        low = topic.lower()
        for r in regs:
            if r.lower() in low:
                return V_REFUSE
        return None

    def advise(self, request: str) -> str:
        """Human-facing one-liner for the warn-help-trust gray lane."""
        rec = self.analyze(request)
        w = rec["w"]
        if rec["verdict"] == V_REFUSE:
            return f"I can't do that — {rec['reason']}."
        if rec["verdict"] == V_WARN:
            return (f"heads-up: this lands in the {w['where']} with impact {w['weight']}/5 "
                    f"({rec['reason']}). I'll do it if you confirm, and I'll flag it.")
        return rec["reason"]

    def _audit(self, rec: dict) -> None:
        if not self.audit_dir:
            return
        day = time.strftime("%Y-%m-%d")
        f = self.audit_dir / f"judge_{day}.jsonl"
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
