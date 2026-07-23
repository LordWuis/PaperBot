from __future__ import annotations

import datetime as dt
import os
import textwrap
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "daily-intelligence"
PDF_PATH = OUT_DIR / "2026-07-01-daily-internet-intelligence-dossier.pdf"
MD_PATH = OUT_DIR / "2026-07-01-daily-internet-intelligence-dossier.md"

PAGE_W, PAGE_H = fitz.paper_size("a4")
MARGIN = 42
TEXT_W = PAGE_W - 2 * MARGIN

COLORS = {
    "ink": (0.08, 0.1, 0.13),
    "muted": (0.37, 0.42, 0.48),
    "line": (0.82, 0.85, 0.88),
    "navy": (0.05, 0.16, 0.28),
    "teal": (0.0, 0.47, 0.52),
    "green": (0.08, 0.49, 0.32),
    "amber": (0.84, 0.48, 0.08),
    "red": (0.72, 0.18, 0.16),
    "blue": (0.1, 0.32, 0.72),
    "soft": (0.96, 0.98, 0.99),
    "cream": (1.0, 0.98, 0.92),
}


sources = [
    ("OpenAI Codex usage-limit fix and reset", "Business Insider", "2026-07-01", "https://www.businessinsider.com/openai-codex-usage-limit-warroom-fix-issue-2026-6"),
    ("The Shift to Agentic AI: Evidence from Codex", "arXiv", "2026-06-25", "https://arxiv.org/abs/2606.26959"),
    ("Anthropic debuts Sonnet 5 for everyday work", "Axios", "2026-06-30", "https://www.axios.com/2026/06/30/anthropic-sonnet-5-agents-mythos-fable"),
    ("Google DeepMind AI Control Roadmap coverage", "Axios", "2026-06-18", "https://www.axios.com/2026/06/18/google-deepmind-prepares-for-rogue-ai-agents"),
    ("RBI draft model-risk framework and AI kill switches", "Economic Times", "2026-06-24", "https://economictimes.indiatimes.com/industry/banking/finance/banking/rbi-mandates-kill-switch-for-ai-models-introduces-comprehensive-model-risk-framework/articleshow/131969198.cms"),
    ("AI coding agents tricked into malware via clean repos", "Tom's Hardware", "2026-06-28", "https://www.tomshardware.com/tech-industry/cyber-security/ai-coding-agents-can-be-tricked-into-installing-malware-via-clean-github-repositories-mozillas-0din-team-shows-how-claude-code-can-be-exploited-by-its-own-helpfulness"),
    ("Detecting AI Coding Agents in Open Source", "arXiv", "2026-06-23", "https://arxiv.org/abs/2606.24429"),
    ("Etched raises $800M for AI chips", "Economic Times", "2026-07-01", "https://economictimes.indiatimes.com/markets/us-stocks/news/jane-street-tsmc-linked-ai-startup-etched-raises-800-m/articleshow/132103929.cms"),
    ("OpenAI Jalapeno homegrown AI chip", "Axios", "2026-06-24", "https://www.axios.com/2026/06/24/openai-jalapeno-ai-chip-broadcom-nvidia"),
    ("Toward Next-Generation AI Data Centers", "arXiv", "2026-06-23", "https://arxiv.org/abs/2606.25095"),
    ("AI Agents Under EU Law", "arXiv", "2026-04-06", "https://arxiv.org/abs/2604.04604"),
    ("High-Risk AI Systems and the Problem of Identity in the European AI Act", "arXiv", "2026-04-17", "https://arxiv.org/abs/2605.23922"),
    ("Meta pressed to submit models for US review", "TechRadar", "2026-06-24", "https://www.techradar.com/pro/we-hope-to-sign-the-agreement-soon-white-house-calls-on-meta-to-submit-ai-models-for-review-citing-abilities-and-vulnerabilities-evaluation"),
    ("AI coding costs may overtake developer salaries by 2028", "TechRadar", "2026-06-26", "https://www.techradar.com/pro/token-discipline-will-not-emerge-through-developer-choice-alone-experts-predict-that-ai-coding-costs-will-overtake-developer-salaries-by-2028"),
    ("GitHub best month ever from AI coding", "Business Insider", "2026-06-25", "https://www.businessinsider.com/github-best-month-ever-internal-meeting-2026-6"),
    ("California-Anthropic public-sector Claude deal", "Business Insider", "2026-06-30", "https://www.businessinsider.com/newsom-anthropic-ink-deal-expand-government-use-2026-6"),
    ("Anthropic alleges Alibaba distillation attack", "Business Insider", "2026-06-26", "https://www.businessinsider.com/anthropic-china-alibaba-exploiting-ai-models-distillation-attack-2026-6"),
    ("Brekfuz raises seed funding in India", "Economic Times", "2026-07-01", "https://economictimes.indiatimes.com/tech/funding/gurugram-ai-startup-brekfuz-raises-525000-in-funding-valued-at-7-5-million/articleshow/132095543.cms"),
    ("Agyn zero-trust agent platform", "arXiv", "2026-05-26", "https://arxiv.org/abs/2605.27575"),
]


sections = [
    {
        "title": "1. Executive Dashboard",
        "visual": "dashboard",
        "body": [
            ("Thesis of the day", "The overnight signal is not another generic model race. The sharper change is that useful agents are colliding with three hard constraints at once: compute accounting, privileged permissions, and regulator-visible operational risk. This creates a near-term opening for products that make agent work measurable, permissioned, replayable, and affordable."),
            ("Top 10 things Aman must know", "1. OpenAI reset Codex usage caps after auto-review and subagent behavior consumed more background compute than expected. 2. Anthropic launched Sonnet 5 as the cheaper default workhorse for browsing, coding, planning, and knowledge work. 3. Codex research data shows agent adoption is moving beyond developers and toward delegated knowledge work. 4. DeepMind is treating autonomous agents like potential insider threats. 5. RBI's draft model-risk framework would require kill switches, human override, explainability thresholds, and board accountability for AI models in regulated Indian finance. 6. Mozilla's 0din demo shows coding agents can be tricked by clean-looking repos into running malware. 7. Open-source agent traces on GitHub are materially undercounted by bot-only methods. 8. Etched raised $800M and OpenAI is testing Jalapeno, confirming inference silicon is now a strategic control point. 9. Data-center power architecture is becoming a bottleneck, not a footnote. 10. The best founder wedge is not 'build an agent'; it is 'make agent work governable in one painful workflow.'"),
            ("Scores", "Opportunity score: 9/10. Risk score: 8/10. Action score: 9/10. Rationale: the pain is observable in usage caps, security incidents, policy drafts, and enterprise buying behavior; the window is practical because buyers need controls before they scale agent deployments."),
        ],
    },
    {
        "title": "2. Calendar and Personal Operating Context",
        "visual": "calendar",
        "body": [
            ("Calendar access", "Unavailable. I do not have a connected calendar tool in this automation run, so I cannot verify Aman’s meetings, travel, deadlines, or conflicts for 2026-07-01."),
            ("Operating assumption", "Use today as a validation-and-synthesis day: one 60-minute customer discovery block, one 90-minute prototype block, and one short publishing block. If a real calendar conflict exists, compress the prototype into a paper mock and preserve customer outreach."),
            ("One priority", "Validate whether Indian founders, agencies, or regulated SMBs will pay for agent spend/permission/audit controls before they add Codex, Claude Code, browser agents, or custom workflow agents to daily operations."),
        ],
    },
    {
        "title": "3. The World Changed Overnight",
        "visual": "world",
        "body": [
            ("Fact", "Codex users reported unexpectedly fast quota depletion; OpenAI attributed the problem to auto-review and subagent behavior running more often than intended, plus dashboard reporting confusion, then reset caps and added monitoring."),
            ("Analysis", "Agent products are no longer single-turn software. They are background systems that consume compute while making invisible decisions. That turns pricing, logs, retries, tool calls, and background tasks into product-safety surfaces."),
            ("Builder implication", "The buyer question shifts from 'does the model work?' to 'what exactly did the agent do, why did it cost this much, and can I stop it before damage?' A lightweight agent-metering and approval layer is sellable even before deep enterprise compliance."),
            ("Second-order effect", "Vendors will reduce unlimited plans; teams will seek local policies, cheaper model routing, and task budgeting. This favors middleware and workflow-specific copilots over raw model wrappers."),
        ],
    },
    {
        "title": "4. AI Frontier Watch",
        "visual": "frontier",
        "body": [
            ("Models and agents", "Anthropic's Sonnet 5 launch is positioned as an affordable, safer default for everyday autonomous work while higher-risk Mythos/Fable-class systems remain more restricted. The frontier is tiering into cheap workhorses, expensive specialists, and gated high-capability models."),
            ("Research signal", "The Codex usage paper reports fivefold active-user growth in the first half of 2026, growing non-developer usage, over 10% of users managing three or more concurrent agents weekly, and increasing use of shared workflow skills."),
            ("Technical gap", "Agent skills, memory, and concurrent work management are becoming primitives. The missing layer is not another chat UI; it is a control plane that tracks skills, permissions, cost, evidence, and rollback across tasks."),
            ("What to test", "Build a tiny local ledger that records every agent command, network call, file mutation, estimated token burn, and human approval. Wrap it around one real workflow: invoice reconciliation, lead enrichment, policy monitoring, or GitHub issue triage."),
        ],
    },
    {
        "title": "5. AI Giants Pulse",
        "visual": "giants",
        "body": [
            ("OpenAI", "OpenAI's Codex incident highlights the fragility of compute accounting and background-task transparency. Separately, Jalapeno shows OpenAI wants inference-stack control for cost, latency, and power efficiency."),
            ("Anthropic", "Sonnet 5 is a distribution play: put agentic capability in the default tier while reserving frontier-risk models for stricter access. Anthropic also faces a geopolitical model-extraction narrative through its allegation that Alibaba-affiliated actors attempted large-scale distillation."),
            ("Google DeepMind", "DeepMind's control roadmap reframes agents as systems that may need live monitoring, alerts, access limits, and shutdown mechanisms. This overlaps strongly with RBI-style kill switches and enterprise security buying criteria."),
            ("Meta and frontier evaluations", "Reporting indicates US officials are pushing Meta toward voluntary pre-release model review. Even voluntary evaluations create a de facto compliance lane for frontier launches."),
        ],
    },
    {
        "title": "6. Regulation and Policy Radar",
        "visual": "policy",
        "body": [
            ("India", "RBI's draft model-risk framework is the most actionable India-specific signal: regulated entities remain accountable for third-party AI models, must maintain human oversight, disclose customer-facing AI, classify model risk, and support override/suspension/deactivation."),
            ("EU", "Agent providers face overlapping obligations under the AI Act, GDPR, Cyber Resilience Act, Digital Services Act, Data Act, NIS2, and product-liability rules. The practical first task is an inventory of agent actions, data flows, connected systems, and affected persons."),
            ("US", "Frontier model review is hardening into national-security infrastructure. Public-sector adoption is also moving: California's Anthropic deal discounts Claude for agencies and local governments."),
            ("Founder implication", "Regulation is creating demand for compliance scaffolding before customers trust autonomy. Sell the workflow map, audit log, data-flow inventory, and kill switch before selling full automation."),
        ],
    },
    {
        "title": "7. Community Pain Map",
        "visual": "pain",
        "body": [
            ("Recurring pain", "Developers complain about usage limits, opaque token burn, unpredictable background work, outages, and tool-specific quotas. Security researchers show that agents still follow plausible setup instructions too trustingly."),
            ("Hidden demand", "Teams want agents, but they also want spending predictability, safe defaults, repo trust scoring, network egress controls, and proof that an agent did not exfiltrate secrets."),
            ("Community-derived product gaps", "A 'preflight for agent tasks' that scores a repo before an agent touches it; a 'token budget guard' that enforces per-task caps; a 'skill provenance scanner' for local agent skills; a 'human handoff and rollback' workflow for non-technical operators."),
            ("India angle", "SMBs adopting AI through agencies will not understand model limits, OAuth scopes, or repo security. A vernacular dashboard that says 'this automation can read Gmail, update Sheets, and spend credits' is more useful than a developer-only log."),
        ],
    },
    {
        "title": "8. Market and Money Signals",
        "visual": "money",
        "body": [
            ("Compute", "Etched raising $800M and OpenAI testing Jalapeno both point to a market where inference cost and specialized silicon decide margins. Nvidia remains central, but hyperscalers and labs are buying optionality."),
            ("Enterprise software", "GitHub's best-month signal and consumption pricing show that coding agents are already a budget line. The next fight is not adoption; it is cost governance, capacity reliability, and integration into internal controls."),
            ("India startup signal", "Small India AI rounds such as Brekfuz's $525K seed show capital is still available for narrow AI-native workflows, but investors will expect sharper distribution and evidence than broad 'AI assistant' claims."),
            ("Macro inference", "As agent pricing becomes metered and chip capacity gets strategic, founders who reduce waste, route tasks to the right model, or make AI spend auditable can sell into a rising cost curve."),
        ],
    },
    {
        "title": "9. Technical Opportunity Map",
        "visual": "tech",
        "body": [
            ("Security", "The Mozilla 0din-style exploit uses indirection: clean repo, plausible setup command, DNS TXT payload, reverse shell. The opportunity is an agent-aware sandbox that blocks suspicious command chains, DNS TXT reads during setup, and unapproved network egress."),
            ("Measurement", "Agent adoption studies show bot-account methods miss most activity. The opportunity is repository governance that detects agent-authored code, flags missing review metadata, and creates AI contribution ledgers."),
            ("Infrastructure", "AI data-center power research points to shifts from 48V rack designs toward higher-voltage DC conversion and solid-state transformers. Downstream, software teams will see more quota pressure, regional capacity differences, and pressure for inference efficiency."),
            ("Agent runtime", "Agyn-like zero-trust platforms validate that agent operations need stateful runtime, infrastructure-as-code definitions, least privilege, and model-agnostic execution. A smaller founder wedge can target one vertical workflow before becoming a platform."),
        ],
    },
    {
        "title": "10. Personal Impact Analysis for Aman",
        "visual": "impact",
        "body": [
            ("Positive effects", "Aman can move faster because agent tooling is finally useful for multi-hour work. The market is also revealing concrete pain around costs, permissioning, compliance, and trust that a small team can attack."),
            ("Negative effects", "Raw app-building with agents will get commoditized. If Aman builds only another wrapper, pricing pressure and model-owner distribution will crush margins."),
            ("Skill gaps to close", "Agent sandboxing, OAuth permission design, audit logs, RBI-style model-risk language, evaluation design, and customer discovery with regulated or semi-regulated businesses."),
            ("What to ignore today", "Ignore generic model leaderboard discourse unless it changes cost, access, liability, latency, or a customer workflow. Also ignore broad AGI commentary that does not translate into a buying trigger."),
        ],
    },
    {
        "title": "11. Billion-Dollar Problem Radar",
        "visual": "radar",
        "body": [
            ("1. Agent spend and permission control for SMBs", "Problem: teams cannot see or cap agent compute, OAuth scope, or file/network actions. Customer: AI-heavy agencies, SaaS teams, Indian SMB operators. Evidence: Codex limit incident and Gartner-style cost warnings. Urgency: budgets are moving from flat to consumption. Wedge MVP: browser/CLI proxy that logs tasks, blocks risky commands, and sets per-workflow caps. Distribution: dev agencies and LinkedIn founder demos. Pricing: $29/user/month or usage-based team tier. Moat: workflow logs and policy templates. Risk: platform APIs may limit visibility. 48-hour validation: interview 10 Codex/Claude Code users and demo a fake dashboard. Action today: build the landing-page mock and ask for screenshots of quota pain."),
            ("2. RBI-ready AI model inventory for fintechs", "Problem: regulated entities need model risk tiering, kill switches, explainability thresholds, and vendor accountability. Customer: NBFCs, fintechs, lending SaaS vendors. Evidence: RBI draft framework. Wedge MVP: spreadsheet-to-dashboard inventory with controls checklist and evidence upload. Distribution: compliance consultants and fintech CTO webinars. Pricing: Rs 50k setup plus monthly retainer. Moat: India-specific templates and audit history. Risk: banks may buy from incumbents. 48-hour validation: call 5 fintech compliance leads. Action today: create a one-page RBI controls checklist."),
            ("3. Agent-safe repo preflight scanner", "Problem: agents trust clean-looking repos and setup scripts. Customer: developers, security teams, coding-agent vendors. Evidence: Mozilla 0din exploit. Wedge MVP: scan README, package scripts, install hooks, DNS/network commands, and secrets access before agent execution. Distribution: GitHub Action and CLI. Pricing: free CLI, paid team policies. Moat: exploit corpus and integrations. Risk: noisy false positives. Action today: implement 10 risky-pattern checks."),
            ("4. AI contribution ledger for open-source maintainers", "Problem: agent-authored code is underdetected and review responsibility is unclear. Customer: maintainers, enterprises using OSS, security vendors. Evidence: arXiv census finds single-signal detection badly undercounts agent traces. Wedge MVP: PR bot labels probable AI contributions and requires human attestation. Pricing: $10/repo/month. Risk: attribution disputes. Action today: scrape commit-message patterns from public examples and build a prototype classifier."),
            ("5. Vernacular workflow agents for Indian back offices", "Problem: India SMBs need invoice, GST, WhatsApp, Tally, bank-statement, and customer-support automation but fear mistakes. Customer: accountants, clinics, coaching centers, exporters. Evidence: India sovereign-language model momentum and agent-control pain. Wedge MVP: Hindi/English approval-first assistant for one workflow. Pricing: Rs 999-4999/month. Moat: local integrations and trusted operators. Risk: messy data. Action today: pick one workflow and record a manual process walkthrough."),
            ("6. Public-sector AI procurement guardrails", "Problem: governments are buying AI tools but need training, audit, and data-flow controls. Customer: local governments, smart-city vendors, civic-tech NGOs. Evidence: California-Anthropic deal. Wedge MVP: procurement checklist plus pilot dashboard. Pricing: consulting plus SaaS. Risk: slow sales. Action today: write a sample procurement policy for a municipal chatbot."),
            ("7. Agent skill marketplace security", "Problem: agent skills can become supply-chain attack vectors. Customer: users of Codex/Claude/OpenClaw-like environments and enterprise IT. Evidence: agent skill ecosystem papers and clean-repo malware demo. Wedge MVP: signed skill registry with provenance and permission manifests. Pricing: enterprise seats. Risk: platform owners may build it. Action today: design a SKILL.md manifest extension with permissions."),
            ("8. Inference-cost router for Indian SaaS", "Problem: teams overspend by sending cheap tasks to expensive frontier models. Customer: SaaS startups and agencies. Evidence: Codex quota incident, custom-chip rush, coding-cost warnings. Wedge MVP: classify tasks into cheap, medium, premium model lanes and report savings. Pricing: percentage of savings or API gateway fee. Risk: reliability. Action today: benchmark 20 common tasks across 2-3 model tiers."),
        ],
    },
    {
        "title": "12. Micro-Opportunities",
        "visual": "micro",
        "body": [
            ("Ten small bets", "1. Chrome extension showing AI-tool quota burn per task. 2. CLI wrapper that blocks curl/wget/DNS during agent repo setup unless approved. 3. RBI AI model-risk Notion template. 4. LinkedIn carousel explaining 'AI kill switches' for Indian fintech founders. 5. Public GitHub Action that labels likely agent-authored PRs. 6. Google Sheets agent-cost calculator for agencies. 7. WhatsApp lead magnet: 'Can your AI tool read your Drive?' permission audit. 8. YouTube teardown of Codex quota economics. 9. Dataset of risky package scripts for agent sandboxes. 10. One-page buyer guide: Claude Sonnet 5 vs Codex vs Copilot for Indian agencies."),
        ],
    },
    {
        "title": "13. Contrarian Corner",
        "visual": "contrarian",
        "body": [
            ("Contrarian take 1", "Most people think better models will solve agent reliability. More likely: better permissions, logs, and rollback will unlock adoption before another capability jump does. Uncertainty: medium."),
            ("Contrarian take 2", "Open-source agent usage may be larger and messier than public PR metrics imply. The invisible adoption surface is local commits, config files, and silent maintenance work. Uncertainty: low to medium."),
            ("Contrarian take 3", "India's AI opportunity may be less about building a frontier model and more about becoming the test market for low-cost, multilingual, human-in-the-loop agent operations in messy regulated workflows. Uncertainty: medium."),
        ],
    },
    {
        "title": "14. Watchlist",
        "visual": "watch",
        "body": [
            ("People and companies", "Thibault Sottiaux/OpenAI Codex, Rohin Shah/DeepMind control, Anthropic Sonnet and policy team, Meta model-review posture, Etched shipments, Broadcom custom silicon, RBI model-risk consultation, California public-sector AI rollout, Sarvam and Indian-language AI providers."),
            ("Repos and papers", "Codex usage paper, AI coding-agent census, Agyn zero-trust agent platform, AI Agents Under EU Law, AI data-center power architecture paper, agent skill security research."),
            ("Signals to monitor", "Usage-limit resets, pricing page changes, OAuth permission incidents, enterprise AI spend caps, RBI final circular timeline, EU AI Act GPAI enforcement milestones, chip shipment delays, public-sector AI procurement templates."),
        ],
    },
    {
        "title": "15. Today's Ranked Action Plan",
        "visual": "actions",
        "body": [
            ("15-minute actions", "1. Post a concise take: 'Agent costs are now a product surface.' 2. DM five Indian AI agencies asking whether clients complain about token or tool limits. 3. Save RBI model-risk requirements into a checklist."),
            ("1-hour actions", "1. Build a Figma or HTML mock for an Agent Cost and Permission Ledger. 2. Draft a repo preflight scanner spec with 10 checks. 3. Write a customer discovery script for fintechs and agencies."),
            ("Deep-work actions", "1. Prototype a CLI wrapper that logs commands, network calls, and file writes before an agent runs setup. 2. Build a model-risk inventory spreadsheet for one hypothetical NBFC. 3. Benchmark one workflow across cheap and premium models and calculate cost spread."),
        ],
    },
    {
        "title": "16. Methodology and Limitations",
        "visual": "method",
        "body": [
            ("Method", "Scanned current accessible web/news results, official or primary-like technical sources where available, arXiv papers, policy/regulatory reporting, market/funding reports, and community-pain proxies from public developer/social reporting. Prioritized items with a clear builder consequence."),
            ("Limitations", "No calendar connector was available. X/Twitter, Reddit, Hacker News, Product Hunt, app reviews, and some newsletters were only partially accessible through web search/reporting; private Discords, login-gated feeds, paywalled full text, and proprietary datasets were not accessed. Some company claims are reported through secondary sources and are labeled as such in the source appendix."),
        ],
    },
]


def clean(text: str) -> str:
    return (
        text.replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
        .replace("₹", "Rs ")
        .replace("‑", "-")
    )


class Writer:
    def __init__(self) -> None:
        self.doc = fitz.open()
        self.page = None
        self.y = MARGIN
        self.page_no = 0

    def new_page(self, title: str | None = None) -> None:
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page_no += 1
        self.y = MARGIN
        self.page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=(1, 1, 1))
        self.page.draw_line(fitz.Point(MARGIN, PAGE_H - 32), fitz.Point(PAGE_W - MARGIN, PAGE_H - 32), color=COLORS["line"], width=0.5)
        footer = f"Daily Internet Intelligence Dossier - 2026-07-01 - Page {self.page_no}"
        self.page.insert_text((MARGIN, PAGE_H - 18), footer, fontsize=8, color=COLORS["muted"])
        if title:
            self.heading(title, level=1)

    def ensure(self, h: float) -> None:
        if self.y + h > PAGE_H - 56:
            self.new_page()

    def text(self, txt: str, size: int = 10, color=None, bold: bool = False, leading: float = 1.32, indent: float = 0) -> None:
        txt = clean(txt)
        color = color or COLORS["ink"]
        avg = size * 0.47
        width_chars = max(24, int((TEXT_W - indent) / avg))
        lines = []
        for para in txt.split("\n"):
            if para.strip():
                lines.extend(textwrap.wrap(para.strip(), width=width_chars))
            else:
                lines.append("")
        line_h = size * leading
        self.ensure(line_h * len(lines) + 4)
        font = "helv"
        if bold:
            font = "helv"
        for line in lines:
            self.page.insert_text((MARGIN + indent, self.y), line, fontsize=size, fontname=font, color=color)
            self.y += line_h
        self.y += 4

    def heading(self, txt: str, level: int = 2) -> None:
        txt = clean(txt)
        size = 18 if level == 1 else 13
        self.ensure(size * 2.2)
        if level == 1:
            self.page.draw_rect(fitz.Rect(MARGIN, self.y - 8, MARGIN + 5, self.y + 18), color=None, fill=COLORS["teal"])
        self.page.insert_text((MARGIN + (12 if level == 1 else 0), self.y), txt, fontsize=size, color=COLORS["navy"])
        self.y += size * 1.35
        if level == 1:
            self.page.draw_line(fitz.Point(MARGIN, self.y), fitz.Point(PAGE_W - MARGIN, self.y), color=COLORS["line"], width=0.6)
            self.y += 12

    def bullet_label(self, label: str, txt: str) -> None:
        self.ensure(34)
        self.page.insert_text((MARGIN, self.y), clean(label), fontsize=10.5, color=COLORS["teal"])
        self.y += 14
        self.text(txt, size=9.2, color=COLORS["ink"], indent=10)

    def visual(self, kind: str) -> None:
        self.ensure(108)
        x, y, w, h = MARGIN, self.y, TEXT_W, 92
        self.page.draw_rect(fitz.Rect(x, y, x + w, y + h), color=COLORS["line"], fill=COLORS["soft"], width=0.8)
        self.page.insert_text((x + 12, y + 16), f"Generated visual: {kind.replace('-', ' ')} signal map", fontsize=8, color=COLORS["muted"])
        if kind in {"dashboard", "actions"}:
            labels = [("Opportunity", 0.9, COLORS["green"]), ("Risk", 0.8, COLORS["red"]), ("Action", 0.9, COLORS["blue"])]
            bx = x + 24
            for name, val, col in labels:
                self.page.insert_text((bx, y + 42), name, fontsize=9, color=COLORS["ink"])
                self.page.draw_rect(fitz.Rect(bx, y + 52, bx + 130, y + 63), color=COLORS["line"], fill=(1, 1, 1))
                self.page.draw_rect(fitz.Rect(bx, y + 52, bx + 130 * val, y + 63), color=None, fill=col)
                self.page.insert_text((bx + 100, y + 79), f"{int(val*10)}/10", fontsize=12, color=col)
                bx += 170
        elif kind in {"frontier", "giants", "world"}:
            nodes = [(x + 90, y + 55, "Models"), (x + 240, y + 34, "Agents"), (x + 385, y + 58, "Compute"), (x + 510, y + 35, "Policy")]
            for i, (cx, cy, lab) in enumerate(nodes):
                self.page.draw_circle(fitz.Point(cx, cy), 24, color=COLORS["teal"], fill=(0.9, 0.98, 0.98), width=1)
                self.page.insert_text((cx - 18, cy + 4), lab, fontsize=8, color=COLORS["navy"])
                if i:
                    px, py, _ = nodes[i - 1][0], nodes[i - 1][1], nodes[i - 1][2]
                    self.page.draw_line(fitz.Point(px + 24, py), fitz.Point(cx - 24, cy), color=COLORS["amber"], width=1.2)
        elif kind in {"policy", "calendar"}:
            for i, lab in enumerate(["Inventory", "Human override", "Explainability", "Kill switch"]):
                yy = y + 28 + i * 14
                self.page.draw_rect(fitz.Rect(x + 22, yy - 8, x + 34, yy + 4), color=COLORS["green"], fill=(0.88, 0.97, 0.92), width=0.7)
                self.page.draw_line(fitz.Point(x + 24, yy - 2), fitz.Point(x + 28, yy + 2), color=COLORS["green"], width=1)
                self.page.draw_line(fitz.Point(x + 28, yy + 2), fitz.Point(x + 33, yy - 7), color=COLORS["green"], width=1)
                self.page.insert_text((x + 44, yy), lab, fontsize=10, color=COLORS["ink"])
        elif kind in {"money", "tech", "impact"}:
            vals = [56, 72, 41, 84, 63]
            for i, v in enumerate(vals):
                bx = x + 70 + i * 86
                self.page.draw_rect(fitz.Rect(bx, y + 80 - v * 0.55, bx + 42, y + 80), color=None, fill=[COLORS["blue"], COLORS["teal"], COLORS["amber"], COLORS["green"], COLORS["red"]][i])
            axis = [("Cost", 70), ("Trust", 156), ("Policy", 242), ("Security", 328), ("Chips", 414)]
            for label, off in axis:
                self.page.insert_text((x + off, y + 87), label, fontsize=7, color=COLORS["muted"])
        else:
            for i in range(8):
                cx = x + 55 + i * 62
                cy = y + 50 + (i % 3 - 1) * 14
                self.page.draw_circle(fitz.Point(cx, cy), 14 + (i % 3) * 3, color=COLORS["teal"], fill=(0.93, 0.96, 1), width=0.8)
                if i:
                    self.page.draw_line(fitz.Point(cx - 48, y + 50), fitz.Point(cx - 15, cy), color=COLORS["line"], width=1)
        self.y += h + 16

    def score_table(self) -> None:
        self.ensure(108)
        x, y = MARGIN, self.y
        headers = ["Signal", "Opportunity", "Risk", "Action"]
        rows = [
            ["Codex cost incident", "Spend tooling", "Trust erosion", "Interview users"],
            ["RBI framework", "Compliance SaaS", "Regulated liability", "Make checklist"],
            ["Agent malware demo", "Repo preflight", "Secret theft", "Build scanner"],
            ["Custom AI chips", "Cost routing", "Capacity shocks", "Benchmark tasks"],
        ]
        col_w = [170, 120, 120, 120]
        self.page.draw_rect(fitz.Rect(x, y, x + sum(col_w), y + 22), color=None, fill=COLORS["navy"])
        xx = x
        for i, h in enumerate(headers):
            self.page.insert_text((xx + 5, y + 15), h, fontsize=8.8, color=(1, 1, 1))
            xx += col_w[i]
        yy = y + 22
        for r, row in enumerate(rows):
            fill = (0.985, 0.99, 1) if r % 2 == 0 else (1, 1, 1)
            self.page.draw_rect(fitz.Rect(x, yy, x + sum(col_w), yy + 24), color=COLORS["line"], fill=fill, width=0.4)
            xx = x
            for i, cell in enumerate(row):
                self.page.insert_text((xx + 5, yy + 15), clean(cell), fontsize=8.2, color=COLORS["ink"])
                xx += col_w[i]
            yy += 24
        self.y = yy + 12

    def source_appendix(self) -> None:
        self.new_page("17. Source Appendix")
        self.text("Clickable source list grouped by section. Sources include primary arXiv papers where available and accessible secondary reporting for current company, market, and policy developments.", size=9.2, color=COLORS["muted"])
        for i, (title, publisher, date, url) in enumerate(sources, 1):
            self.ensure(34)
            line1 = f"{i}. {title} - {publisher}, {date}"
            self.page.insert_text((MARGIN, self.y), clean(line1), fontsize=9.0, color=COLORS["ink"])
            self.y += 12
            for url_line in textwrap.wrap(clean(url), width=112, break_long_words=True, break_on_hyphens=False):
                self.ensure(12)
                self.page.insert_text((MARGIN + 12, self.y), url_line, fontsize=7.5, color=COLORS["blue"])
                rect = fitz.Rect(MARGIN + 12, self.y - 8, min(PAGE_W - MARGIN, MARGIN + 12 + len(url_line) * 3.8), self.y + 3)
                self.page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": url})
                self.y += 10
            self.y += 8


def build_markdown() -> str:
    lines = [
        "# Daily Internet Intelligence Dossier - 2026-07-01",
        "",
        "Thesis: useful agents are colliding with compute accounting, privileged permissions, and regulator-visible operational risk. The founder opening is governable agent work in painful workflows.",
        "",
    ]
    for sec in sections:
        lines.append(f"## {sec['title']}")
        for label, body in sec["body"]:
            lines.append(f"### {label}")
            lines.append(clean(body))
            lines.append("")
    lines.append("## 17. Source Appendix")
    for title, publisher, date, url in sources:
        lines.append(f"- [{clean(title)}]({url}) - {publisher}, {date}")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    w = Writer()
    w.new_page()
    # Cover
    w.page.draw_rect(fitz.Rect(0, 0, PAGE_W, 210), color=None, fill=COLORS["navy"])
    w.page.insert_text((MARGIN, 72), "Daily Internet Intelligence Dossier", fontsize=25, color=(1, 1, 1))
    w.page.insert_text((MARGIN, 104), "For Aman - 2026-07-01", fontsize=13, color=(0.82, 0.95, 0.96))
    cover_thesis = "Thesis: agents are becoming operating infrastructure, but the bottleneck is now governance: cost, permissions, auditability, and shutdown."
    for i, line in enumerate(textwrap.wrap(cover_thesis, width=92)):
        w.page.insert_text((MARGIN, 146 + i * 16), line, fontsize=10.5, color=(1, 1, 1))
    w.y = 235
    w.visual("cover")
    w.text("This dossier scans current public signals across AI labs, policy, markets, security, research, and builder communities. It distinguishes facts from analysis and converts each major signal into founder implications for an ambitious AI builder in India with global ambitions.", size=10.5)
    w.score_table()
    w.text("Read time target: 15-25 minutes. Recommended use: pick one validation action, one technical prototype, and one public content angle today.", size=9.5, color=COLORS["muted"])

    for sec in sections:
        w.new_page(sec["title"])
        w.visual(sec["visual"])
        for label, body in sec["body"]:
            w.bullet_label(label, body)
    w.source_appendix()
    w.doc.set_metadata({
        "title": "Daily Internet Intelligence Dossier - 2026-07-01",
        "author": "Codex Automation for Aman",
        "subject": "Daily founder intelligence report",
        "keywords": "AI, agents, India, regulation, startups, intelligence",
        "creationDate": dt.datetime.now().strftime("D:%Y%m%d%H%M%S"),
    })
    w.doc.save(PDF_PATH, deflate=True, garbage=4)
    w.doc.close()
    MD_PATH.write_text(build_markdown(), encoding="utf-8")
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
