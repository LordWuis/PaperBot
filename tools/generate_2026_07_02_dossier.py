from __future__ import annotations

import os
import textwrap
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "daily-intelligence"
ASSET_DIR = OUT_DIR / "2026-07-02-assets"
PDF_PATH = OUT_DIR / "2026-07-02-daily-internet-intelligence-dossier.pdf"
MD_PATH = OUT_DIR / "2026-07-02-daily-internet-intelligence-dossier.md"


SOURCES = [
    ("OpenAI news index", "https://openai.com/news/"),
    ("Anthropic newsroom", "https://www.anthropic.com/news"),
    ("Anthropic - Redeploying Fable 5", "https://www.anthropic.com/news"),
    ("Anthropic - Claude Sonnet 5", "https://www.anthropic.com/news"),
    ("Anthropic - Claude Science", "https://www.anthropic.com/news"),
    ("NVIDIA newsroom", "https://nvidianews.nvidia.com/news"),
    ("NVIDIA - AI infrastructure buildout", "https://blogs.nvidia.com/"),
    ("NVIDIA - inference software token cost", "https://blogs.nvidia.com/"),
    ("NVIDIA - Claude on GB300 in Azure", "https://blogs.nvidia.com/"),
    ("Microsoft AI topic page", "https://news.microsoft.com/source/topics/ai/"),
    ("Microsoft - AI activity in investigations", "https://www.microsoft.com/"),
    ("Microsoft - AI brands as bait", "https://www.microsoft.com/"),
    ("EU AI Act overview", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"),
    ("EU GPAI Code of Practice", "https://digital-strategy.ec.europa.eu/en/policies/ai-code-practice"),
    ("NIST Artificial Intelligence", "https://www.nist.gov/artificial-intelligence"),
    ("RBI press releases", "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"),
    ("RBI model risk draft guidance", "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"),
    ("arXiv recent cs.AI", "https://arxiv.org/list/cs.AI/recent"),
    ("arXiv - AutoMem", "https://arxiv.org/abs/2607.01224"),
    ("arXiv - Open-world tool-use fragility", "https://arxiv.org/abs/2607.01084"),
    ("arXiv - Self-GC long-horizon agents", "https://arxiv.org/abs/2607.00692"),
    ("arXiv - Agri-SAGE", "https://arxiv.org/abs/2607.00454"),
    ("Hacker News front page", "https://news.ycombinator.com/news"),
    ("Senior SWE-Bench", "https://senior-swe-bench.snorkel.ai/"),
    ("Product Hunt categories", "https://www.producthunt.com/"),
    ("GitHub daily Python trending", "https://github.com/trending/python?since=daily"),
    ("Hugging Face blog", "https://huggingface.co/blog"),
]


IMAGES = {
    "cover": ASSET_DIR / "cover-generated.png",
    "governance": ASSET_DIR / "governance-generated.png",
    "pain": ASSET_DIR / "community-pain-generated.png",
    "infra": ASSET_DIR / "infrastructure-generated.png",
    "tech": ASSET_DIR / "technical-opportunity-generated.png",
    "action": ASSET_DIR / "action-plan-generated.png",
}


def md_link(label: str, url: str) -> str:
    return f"[{label}]({url})"


def p(text: str) -> str:
    return " ".join(textwrap.dedent(text).strip().split())


dashboard = [
    ("1", "Anthropic restarted Fable 5 globally after a U.S. directive pause, while also pushing a jailbreak-severity framework.", "A new category is forming: model access governance, not just model quality."),
    ("2", "OpenAI's public news page was reachable only behind a JavaScript/cookie challenge from this environment.", "Do not convert inaccessible lab pages into facts; use primary confirmation before acting on specific launch rumors."),
    ("3", "NVIDIA framed AI factories as continuously operating token-production infrastructure and invited capital partners into the buildout.", "AI economics are shifting from GPU ownership to dollar-per-token-per-watt financing."),
    ("4", "EU AI Act implementation is close to its August 2, 2026 broad applicability date; GPAI and transparency tooling are now operating context.", "Any India-to-EU SaaS product needs explainability, logging, labeling, and copyright posture from day one."),
    ("5", "RBI's recent press releases include draft model-risk guidance and digital transaction liability changes.", "Regulated Indian AI products need validation, monitoring, customer-liability, and audit artifacts as product features."),
    ("6", "arXiv's July 2 AI feed is heavy on memory, open-world tool-use fragility, agentic RAG uncertainty, long-horizon context, and scientific agents.", "The next product wedge is not a bigger chat box; it is measured, repairable, domain-specific agent execution."),
    ("7", "HN surfaced Senior SWE-Bench as a live topic, with discussion density around whether agents can do senior-level engineering.", "Evaluation is becoming distribution. Benchmarks are marketing, procurement, and product design inputs."),
    ("8", "Product Hunt category demand clusters around AI coding agents, AI code editors, notetakers, workflow automation, no-code, and code review.", "Crowded categories still reveal pain: trust, context handoff, pricing, governance, and implementation completeness."),
    ("9", "Microsoft continues to frame AI around investigations, security bait, tokenomics, and enterprise systems rather than standalone assistants.", "Enterprise buyers are asking for operating controls, forensics, and cost dashboards before they buy autonomy."),
    ("10", "Calendar access is unavailable in this automation run.", "The highest-leverage personal priority should be chosen from today's dossier actions, not inferred from private commitments."),
]


sections = [
    {
        "title": "Calendar And Personal Operating Context",
        "image": None,
        "body": [
            p("""Calendar connector access was not available and the user explicitly said calendar checking can be ignored. No private commitments, travel buffers, meeting preparation, or conflicts were inspected. This matters because the report should not invent personal context."""),
            p("""Default operating priority for Aman today: validate one governed-agent wedge rather than reading more AI news. The best use of the next two hours is to interview or message 5 regulated-domain operators about model-risk evidence, audit logs, approval workflows, and AI output liability."""),
        ],
        "bullets": [
            "15-minute action: pick one idea from the Billion-dollar Problem Radar and write the exact buyer, painful workflow, and proof needed.",
            "1-hour action: create a landing-page waitlist or outbound note for regulated AI audit trails.",
            "Deep-work action: prototype a tiny agent-run recorder that logs prompts, tools, outputs, reviewers, and exception reasons.",
        ],
    },
    {
        "title": "The World Changed Overnight",
        "image": "governance",
        "body": [
            p("""Fact: Anthropic's newsroom lists "Redeploying Fable 5" on June 30, 2026, saying Fable 5 returns globally on July 1, alongside an industry framework for jailbreak severity. The same page lists Claude Sonnet 5, Claude Science, Claude Tag, and earlier statements about a U.S. directive to suspend access to Fable 5 and Mythos 5."""),
            p("""Analysis: this is not just a model launch story. It makes model availability itself a policy surface. Customers will start asking whether their AI stack can survive access restriction, jurisdiction-specific controls, audit interruptions, and provider reversals."""),
            p("""Second-order effect: frontier capability will be sold with trust contracts, not just latency and benchmarks. A founder can build provider-neutral controls: model router policy, export-control-aware access, jailbreak severity scoring, and incident evidence packs."""),
            p("""Contrarian read: the winners may not be the labs with the most capable model. They may be the companies that make frontier AI boring enough for banks, hospitals, governments, and exporters to use without weekly legal escalations."""),
        ],
        "bullets": [
            "Opportunity score: 9/10. The governance layer is still underbuilt.",
            "Risk score: 8/10. Building directly on one frontier provider creates availability, policy, and pricing risk.",
            "Builder move: sell controls and observability around agents, not another generic agent shell.",
        ],
    },
    {
        "title": "AI Frontier Watch",
        "image": "tech",
        "body": [
            p("""OpenAI's public news index was not reliably accessible from this automation run because the page returned a JavaScript/cookie challenge. Treat any specific OpenAI launch names from secondary chatter as unconfirmed until checked from a browser or official post URL."""),
            p("""Anthropic's newsroom, which was directly accessible, shows Fable 5 redeployment after access controversy, Claude Sonnet 5, Claude Science, and a jailbreak-severity framing. NVIDIA's public newsroom and blogs remain important infrastructure references, but individual deployment claims should still be checked against the original post before commercial reliance."""),
            p("""arXiv's July 2 cs.AI page reinforces the same pattern from research: AutoMem for memory as a learned skill; work on tool-use agents failing to generalize to open worlds; Bayesian uncertainty propagation for agentic RAG; Self-GC for long-horizon context; Agri-SAGE for agriculture advisory; and managed autonomy for cyber-physical systems."""),
            p("""Inference: the frontier is converging on four product primitives: durable memory, trustworthy tool use, domain-auditable artifacts, and cost-governed inference. Any AI builder who is still selling "chat with your documents" without evals, traces, and exception handling is late."""),
        ],
        "bullets": [
            "Capability delta: better coding/professional agents, scientific workbenches, domain benchmarks, and optimized inference.",
            "Failure mode delta: tool-use agents remain brittle under open-world changes.",
            "MVP wedge: an eval harness that replay-tests agent workflows whenever model, prompt, tool, or policy changes.",
        ],
    },
    {
        "title": "AI Giants Pulse",
        "image": "governance",
        "body": [
            p("""OpenAI: inaccessible from this run beyond the public domain page challenge, so specific new claims were not treated as verified. Anthropic is signaling regulated-industry distribution, scientific workbenches, coding agents, global model access restoration, and policy proposals. NVIDIA is signaling token factories, capital partnerships, token cost, synthetic-data workflows, robotics infrastructure, and secure government/open-model deployments."""),
            p("""Microsoft's AI topic page currently emphasizes enterprise systems, investigations, AI brands as social-engineering bait, tokenomics, jobs, and agent platforms. That is a useful buyer signal: large organizations are not only asking "which model?" They are asking "how do we govern, investigate, price, and staff around this?"""),
            p("""Builder implication: sell the control plane around AI work. The largest customers are not short of demos; they are short of operating evidence, internal adoption playbooks, exception workflows, and proof that AI activity is reconstructable after something goes wrong."""),
        ],
        "bullets": [
            "Watch OpenAI: verify official posts from a browser because the news page was Cloudflare-blocked in automation.",
            "Watch Anthropic: Fable 5 access rules, Sonnet 5 coding quality, Claude Science adoption, regional compliance surfaces.",
            "Watch NVIDIA/Microsoft: AI factories, GB300 availability, Azure model hosting, token-cost claims.",
        ],
    },
    {
        "title": "Regulation And Policy Radar",
        "image": "governance",
        "body": [
            p("""EU: the AI Act overview says the Act is the first comprehensive legal framework for AI, with risk-based obligations; transparency rules come into effect in August 2026; GPAI rules became effective in August 2025; and the Act becomes broadly applicable on August 2, 2026 with exceptions. It also notes a May 2026 political agreement simplifying high-risk timelines, with some high-risk areas applying from December 2, 2027 and product-integrated systems from August 2, 2028."""),
            p("""India: RBI's recent page lists the June 24, 2026 draft "Guidance on Regulatory Principles for Model Risk Management" and amendments around digital-transaction liability. For Indian AI builders, model validation is moving from nice-to-have to procurement language in BFSI and adjacent sectors."""),
            p("""U.S./global: NIST and CISA remain core standards references, while lab-level model access restrictions show that export controls and security reviews can affect commercial model availability. In practice, compliance is becoming a feature category: provenance, logging, evals, user consent, red-team evidence, and content labeling."""),
            p("""Founder implication: build compliance artifacts into the workflow, not as a PDF afterthought. In regulated AI, the product that creates evidence while users work is stronger than a consulting service that reconstructs evidence later."""),
        ],
        "bullets": [
            "Affected customers: BFSI, health, education, HR, critical infrastructure, public-sector vendors, EU-facing SaaS.",
            "Timeline risk: August 2026 EU transparency applicability is immediate planning context.",
            "India wedge: RBI-style model-risk dashboards for AI-enabled lenders, insurers, NBFCs, and compliance teams.",
        ],
    },
    {
        "title": "Community Pain Map",
        "image": "pain",
        "body": [
            p("""Signals scanned: Hacker News front page, Product Hunt categories, GitHub trending page, Hugging Face blog, arXiv recent submissions, and public company/newsroom pages. Reddit/X login-gated or rate-limited surfaces were not deeply inspected in this run; conclusions from those sources are treated as weaker unless supported elsewhere."""),
            p("""Pain cluster 1 - coding agents: HN surfaced Senior SWE-Bench, which points to a buyer question: can agents perform senior engineering work, not just toy tasks? The unsolved pain is evaluation under realistic codebase mess, security constraints, review culture, and long-running context."""),
            p("""Pain cluster 2 - workflow automation: Product Hunt's visible categories cluster around AI coding agents, code editors, notetakers, workflow automation, no-code, and code review. This is crowded, but the crowding itself shows demand. The gap is operational reliability and governance."""),
            p("""Pain cluster 3 - scientific/domain agents: Claude Science, NVIDIA BioNeMo references, arXiv scientific-agent papers, and Agri-SAGE all point to domain workbenches. Users want agents that produce auditable artifacts, not persuasive paragraphs."""),
            p("""Pain cluster 4 - cost opacity: NVIDIA's token-cost messaging and Microsoft's tokenomics framing show that enterprises are worrying about cost per useful output. Teams need unit economics, budgets, caching, routing, and output-quality attribution by model."""),
        ],
        "bullets": [
            "Recurring complaint: agents are impressive until they must be trusted, audited, paid for, or repaired.",
            "Underserved buyer: operations leaders who need AI work reconstructed after failure.",
            "Content angle: " + '"The agent demo is dead; the agent incident report is the product."',
        ],
    },
    {
        "title": "Market And Money Signals",
        "image": "infra",
        "body": [
            p("""NVIDIA's July 1 newsroom items explicitly frame the next phase as capital-intensive AI infrastructure: AI factories operating continuously, token production at scale, U.S. manufacturing/supply chain/energy buildout, and inference software that reduces token cost per dollar, watt, and latency target."""),
            p("""This matters because AI startups are increasingly exposed to infrastructure economics. If inference cost drops, new high-volume workflows become viable. If power, chips, or access tighten, thin-margin AI wrappers die. The product opportunity is a CFO-grade view of AI spend tied to business outcomes."""),
            p("""RBI's July 2 and recent June releases show ordinary financial-market plumbing continuing beside AI model-risk guidance. That juxtaposition matters: AI founders often chase model news, but buyers in India buy through liquidity cycles, compliance rhythms, and budget gates."""),
            p("""India angle: build for regulated, cost-sensitive buyers. India has strong developer supply and price-sensitive SMB/BFSI demand, but weak tolerance for opaque recurring token bills. A usage-governed AI layer could be easier to sell than a premium AI seat."""),
        ],
        "bullets": [
            "Market signal: token cost is becoming a board-level metric.",
            "Capital signal: AI infra is blending with private credit, energy, manufacturing, and sovereign policy.",
            "Founder wedge: AI spend controller that routes models, predicts cost, enforces budgets, and links outputs to revenue or risk reduction.",
        ],
    },
    {
        "title": "Technical Opportunity Map",
        "image": "tech",
        "body": [
            p("""Today's research scan points to a practical stack: memory learning, open-world tool-use tests, uncertainty propagation in agentic RAG, context self-governance, simulator-agent diagnostics, scientific hypothesis generation, and agricultural advisory agents. The pattern is clear: agents need state, tools, uncertainty, and governance."""),
            p("""Most products still hide this behind a chat box. A better architecture exposes the run: objective, context, tool calls, permissions, citations, output diffs, uncertainty, human approvals, retries, and policy exceptions. That is both UX and compliance."""),
            p("""Technical wedge for Aman: build a lightweight "agent black box recorder" SDK. It instruments LangChain/LlamaIndex/OpenAI/Anthropic/Vercel AI SDK style flows, stores run evidence, flags risky steps, and generates a human-readable incident or audit pack."""),
        ],
        "bullets": [
            "Repo idea: agent-run-recorder with Python and TypeScript adapters.",
            "API surface: start_run, log_prompt, log_tool_call, log_output, log_human_review, close_run.",
            "Differentiator: regulator-readable evidence summaries, not just developer traces.",
        ],
    },
]


ideas = [
    ("AI Model Risk OS for India BFSI", "Risk/compliance teams at NBFCs, banks, fintechs", "RBI draft model-risk guidance and EU AI Act logging/transparency pressure", "High", "BFSI AI pilots need approval evidence", "Run registry + validation checklist + drift alerts", "Sell through compliance consultants and fintech CTO networks", "INR 50k-300k/month per institution", "Regulatory templates + workflow data", "ModelOp, Credo AI, spreadsheets", "Long sales cycles", "Interview 5 compliance heads; mock a model-risk dashboard", "Create a one-page RBI model-risk checklist today"),
    ("Agent Black Box Recorder", "AI SaaS teams shipping autonomous workflows", "Agent failures, benchmarks, Microsoft investigations framing", "High", "Autonomy creates post-incident reconstruction needs", "SDK that logs prompts/tools/outputs/approvals", "Open-source SDK + paid cloud dashboard", "$99-$999/month", "Trace schema + integrations + evidence UX", "LangSmith, Helicone, Langfuse", "Crowded observability market", "Instrument one existing workflow and publish replay", "Build a CLI that exports one run to PDF"),
    ("EU AI Act Transparency Kit", "India SaaS companies selling into EU", "August 2026 transparency rules", "High", "Cross-border SaaS teams are underprepared", "Checklist + labeling SDK + audit export", "Founder communities, Vercel/Next.js templates", "$49 template, $499/month SaaS", "Templates + legal/update cadence", "Legal consultancies, GRC tools", "Legal precision risk", "Talk to 10 EU-facing founders", "Draft a Next.js AI disclosure component"),
    ("Token CFO", "AI-heavy startups and agencies", "NVIDIA and Microsoft token-cost narratives", "Medium-high", "Inference spend is now margin risk", "Model routing + budget alerts + useful-output cost", "Product-led onboarding from API keys", "$29-$499/month", "Cost-quality dataset", "Portkey, OpenRouter dashboards", "Attribution is hard", "Benchmark one workflow across 4 models", "Make a public calculator"),
    ("Scientific Agent Workbench for Indian Labs", "Biotech, materials, university labs", "Claude Science, BioNeMo references, arXiv scientific agents", "Medium", "Research teams need auditable artifacts", "Notebook-integrated agent with citation and experiment logs", "Institution partnerships", "Per-lab subscription", "Domain workflows + reproducibility", "Benchling, Notion, Jupyter plugins", "Domain trust", "Interview 3 labs", "Prototype literature-to-experiment-plan export"),
    ("Agri Advisory Agent With Simulator Grounding", "Agri startups, cooperatives, input retailers", "Agri-SAGE and India agriculture demand", "Medium", "Generic advice is unsafe in local farming", "Multilingual advisory with local weather/crop constraints and confidence", "Partner with agri retailers", "Per-agent or per-acre SaaS", "Local data + feedback loop", "WhatsApp agritech bots", "Liability and data quality", "Test one crop-region script", "Call one agri operator"),
    ("Jailbreak Severity Scorer", "Enterprises adopting external LLMs", "Anthropic's proposed severity framework", "Medium-high", "Security teams need shared language for AI incidents", "Prompt attack test suite + severity report", "Security newsletters and OSS red-team community", "$199/month and services", "Attack corpus + scoring rubric", "Lakera, Garak", "Fast-moving standards", "Run on 3 public models", "Publish 20 test prompts with scoring"),
    ("AI Procurement Evidence Pack Generator", "Enterprise AI vendors", "Buyers now ask for system cards, evals, privacy, cost, controls", "Medium", "Sales cycles stall on security questionnaires", "Upload docs, generate buyer-specific evidence packet", "LinkedIn outbound to AI vendors", "$500/project or SaaS", "Questionnaire memory + evidence map", "Vanta, Drata, manual consultants", "Trust in generated answers", "Convert one vendor site into a pack", "Make a sample pack for your own product"),
]


micro = [
    "Chrome extension: capture AI app output with source, prompt, model, and approval status.",
    "Lead magnet: EU AI Act transparency checklist for Indian SaaS founders.",
    "Script: compare token cost per successful task across GPT, Claude, Gemini, and open models.",
    "Dataset: public examples of AI incident postmortems and remediation patterns.",
    "Template: RBI model-risk validation memo for LLM workflows.",
    "Tiny SaaS: webhook that blocks high-risk prompts from production agents until reviewed.",
    "Content: teardown of Fable 5 access reversal as a product-risk case study.",
    "Automation: daily arXiv agent-paper filter mapped to startup ideas.",
    "Tool: export Langfuse/LangSmith traces into regulator-readable PDFs.",
    "Community experiment: weekly office hours for Indian founders selling AI into regulated buyers.",
]


actions = [
    ("15 min", "Choose one regulated-agent wedge and write the painful workflow in one sentence."),
    ("15 min", "Send 5 messages to BFSI/compliance/operator contacts asking how they approve AI workflows."),
    ("15 min", "Create a watchlist note for Fable 5, EU AI Act transparency, RBI model risk, Senior SWE-Bench, and OpenAI official-post verification."),
    ("1 hour", "Build a static mockup of an agent black box recorder: run timeline, tool calls, citations, human approvals."),
    ("1 hour", "Publish a short post: why the next AI product category is evidence, not chat."),
    ("1 hour", "Benchmark one agent task across two models and record cost, failures, and review time."),
    ("Deep work", "Prototype the recorder SDK for one Python agent workflow and export a PDF evidence pack."),
    ("Deep work", "Interview 5 buyers and convert findings into a landing page with one CTA."),
]


contrarian = [
    ("Open source alone will not commoditize the AI app layer.", "Models may commoditize, but regulated workflows need evidence, liability allocation, domain templates, and distribution. Uncertainty: high if open-source agent frameworks rapidly standardize governance."),
    ("The best AI startup ideas today may look like compliance tools.", "When capability outruns trust, the bottleneck becomes permission. Permission is a budget line. Uncertainty: medium; pure consumer AI can still break out."),
    ("Benchmarks are becoming a go-to-market channel.", "Senior SWE-Bench and domain evals shape buyer perception. A startup can win by owning a credible benchmark for a painful workflow. Uncertainty: medium because benchmarks can be gamed."),
]


watchlist = [
    "Anthropic Fable 5 redeployment details and any new access restrictions.",
    "OpenAI official posts once accessible outside the JavaScript/cookie challenge.",
    "EU AI Act transparency guidance and AI-generated content labeling code.",
    "RBI model-risk guidance finalization and Indian BFSI AI procurement language.",
    "NVIDIA token-cost and AI factory financing announcements.",
    "Senior SWE-Bench adoption by coding-agent vendors.",
    "arXiv threads: memory, tool-use generalization, agentic RAG uncertainty, scientific agents.",
    "IndiaAI Mission procurement, GPU access, and startup program updates.",
]


def build_markdown() -> str:
    lines = []
    lines.append("# Daily Internet Intelligence Dossier - 2026-07-02")
    lines.append("")
    lines.append("Generated visuals: all major section images are original AI-generated raster images created for this dossier and stored in `reports/daily-intelligence/2026-07-02-assets/`.")
    lines.append("")
    lines.append("## Thesis Of The Day")
    lines.append(p("""AI is shifting from demo capability to governed execution. The important delta is not one lab beating another on a benchmark; it is that model availability, jailbreak severity, token economics, auditability, and regulated deployment are becoming the new product surface. For Aman, the most actionable founder direction is to build tools that make AI work traceable, compliant, cost-aware, and safe enough for real buyers in India and global markets."""))
    lines.append("")
    lines.append("## Executive Dashboard")
    for rank, fact, why in dashboard:
        lines.append(f"{rank}. **{fact}** Builder implication: {why}")
    lines.append("")
    for sec in sections:
        lines.append(f"## {sec['title']}")
        for para in sec["body"]:
            lines.append(para)
            lines.append("")
        if sec.get("bullets"):
            for b in sec["bullets"]:
                lines.append(f"- {b}")
            lines.append("")
    lines.append("## Personal Impact Analysis For Aman")
    lines.append(p("""Positive: Aman can arbitrage global regulatory and infrastructure confusion into practical India-first tooling. Negative: building another generic agent wrapper will face brutal substitution from labs and incumbents. Skill gaps to close: model-risk language, eval design, enterprise security evidence, and India/EU compliance basics. Threats: provider policy reversals, pricing shocks, and enterprise distrust of autonomous systems. Leverage: India's developer talent, regulated-sector digitization, and founder access to SMB pain. Ignore: model-ranking discourse that does not change buyer workflow, compliance burden, or distribution."""))
    lines.append("")
    lines.append("## Billion-Dollar Problem Radar")
    headers = ["Idea", "Customer", "Evidence", "Urgency", "Wedge MVP", "Distribution", "Pricing", "Moat", "Risk", "48-hour validation", "Action today"]
    for idea in ideas:
        lines.append(f"### {idea[0]}")
        for h, val in zip(headers[1:], idea[1:]):
            lines.append(f"- **{h}:** {val}")
        lines.append("")
    lines.append("## Micro-Opportunities")
    for item in micro:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Contrarian Corner")
    for title, body in contrarian:
        lines.append(f"- **{title}** {body}")
    lines.append("")
    lines.append("## Watchlist")
    for item in watchlist:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Today's Action Plan")
    for bucket, action in actions:
        lines.append(f"- **{bucket}:** {action}")
    lines.append("")
    lines.append("## Methodology Note")
    lines.append(p("""Scanned accessible public pages from official AI lab/company newsrooms, EU policy pages, RBI public releases, arXiv recent submissions, Hacker News, Product Hunt, GitHub trending, Hugging Face, and general current web search. Calendar was not checked by instruction. Reddit/X/deep community surfaces were only lightly represented because access can be login-gated or rate-limited. Private, paywalled, and inaccessible claims were not fabricated."""))
    lines.append("")
    lines.append("## Source Appendix")
    for label, url in SOURCES:
        lines.append(f"- [{label}]({url})")
    return "\n".join(lines) + "\n"


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=28, leading=33, alignment=TA_CENTER, textColor=colors.HexColor("#111827"), spaceAfter=14))
    base.add(ParagraphStyle("Deck", parent=base["BodyText"], fontSize=12.5, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#374151"), spaceAfter=12))
    base.add(ParagraphStyle("H1x", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), spaceBefore=12, spaceAfter=8))
    base.add(ParagraphStyle("H2x", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=5))
    base.add(ParagraphStyle("Bodyx", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.2, textColor=colors.HexColor("#1f2937"), spaceAfter=6))
    base.add(ParagraphStyle("Smallx", parent=base["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=colors.HexColor("#4b5563")))
    base.add(ParagraphStyle("TableHead", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=colors.white))
    base.add(ParagraphStyle("TableCell", parent=base["BodyText"], fontSize=7.1, leading=8.6, textColor=colors.HexColor("#111827")))
    return base


def bullet_list(items, sty):
    return ListFlowable(
        [ListItem(Paragraph(i, sty), leftIndent=10) for i in items],
        bulletType="bullet",
        start="circle",
        leftIndent=13,
        bulletFontSize=5,
        spaceAfter=8,
    )


def section_image(path: Path, caption: str):
    img = Image(str(path))
    img._restrictSize(6.9 * inch, 2.35 * inch)
    return [img, Paragraph(caption, styles()["Smallx"]), Spacer(1, 7)]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(doc.leftMargin, 0.38 * inch, "Daily Internet Intelligence Dossier - 2026-07-02")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf():
    st = styles()
    story = []
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="Daily Internet Intelligence Dossier - 2026-07-02",
        author="Codex",
    )

    story.append(Paragraph("Daily Internet Intelligence Dossier", st["CoverTitle"]))
    story.append(Paragraph("For Aman - Thursday, 2 July 2026", st["Deck"]))
    story.extend(section_image(IMAGES["cover"], "Generated image: founder intelligence command center."))
    story.append(Paragraph(p("""Thesis: AI is shifting from raw capability to governed execution. The important delta is not a single model announcement; it is that access controls, jailbreak severity, token economics, auditability, and regulated deployment are becoming product surfaces. For Aman, the highest-leverage action is to build evidence-producing AI systems for buyers who cannot afford untraceable autonomy."""), st["Deck"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Opportunity 9/10 | Risk 8/10 | Action 9/10", st["Deck"]))
    story.append(PageBreak())

    story.append(Paragraph("Executive Dashboard", st["H1x"]))
    rows = [[Paragraph("Rank", st["TableHead"]), Paragraph("What changed", st["TableHead"]), Paragraph("Why it matters to Aman", st["TableHead"])]]
    for rank, fact, why in dashboard:
        rows.append([Paragraph(rank, st["TableCell"]), Paragraph(fact, st["TableCell"]), Paragraph(why, st["TableCell"])])
    table = Table(rows, colWidths=[0.38 * inch, 3.25 * inch, 3.35 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(PageBreak())

    for sec in sections:
        block = [Paragraph(sec["title"], st["H1x"])]
        if sec.get("image"):
            block.extend(section_image(IMAGES[sec["image"]], f"Generated image for section: {sec['title']}."))
        for para in sec["body"]:
            block.append(Paragraph(para, st["Bodyx"]))
        if sec.get("bullets"):
            block.append(bullet_list(sec["bullets"], st["Bodyx"]))
        story.append(KeepTogether(block[:2]) if len(block) <= 2 else block[0])
        for item in block[1:]:
            story.append(item)

    story.append(Paragraph("Personal Impact Analysis For Aman", st["H1x"]))
    story.append(Paragraph(p("""Positive effects: Aman can arbitrage global regulatory and infrastructure confusion into practical India-first tooling. Negative effects: a generic agent wrapper will be crushed by labs, model-router platforms, and low-cost clones. Skill gaps: model-risk language, eval design, enterprise security evidence, and India/EU compliance basics. Threats: provider policy reversals, pricing shocks, and enterprise distrust. Leverage: India's developer talent, BFSI modernization, and global demand for cheaper compliance-aware AI implementation. Ignore: model-ranking chatter that does not alter buyer workflow, risk, or budget."""), st["Bodyx"]))

    story.append(Paragraph("Billion-Dollar Problem Radar", st["H1x"]))
    idea_rows = [[Paragraph("Idea", st["TableHead"]), Paragraph("Customer / evidence / wedge", st["TableHead"]), Paragraph("Risk + validation", st["TableHead"])]]
    for idea in ideas:
        idea_rows.append([
            Paragraph(idea[0], st["TableCell"]),
            Paragraph(f"<b>Customer:</b> {idea[1]}<br/><b>Evidence:</b> {idea[2]}<br/><b>Why now:</b> {idea[4]}<br/><b>MVP:</b> {idea[5]}<br/><b>Pricing:</b> {idea[7]}", st["TableCell"]),
            Paragraph(f"<b>Key risk:</b> {idea[10]}<br/><b>48-hour validation:</b> {idea[11]}<br/><b>Today:</b> {idea[12]}", st["TableCell"]),
        ])
    idea_table = Table(idea_rows, colWidths=[1.45 * inch, 3.4 * inch, 2.15 * inch], repeatRows=1)
    idea_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(idea_table)

    story.append(Paragraph("Micro-Opportunities", st["H1x"]))
    story.append(bullet_list(micro, st["Bodyx"]))

    story.append(Paragraph("Contrarian Corner", st["H1x"]))
    for title, body in contrarian:
        story.append(Paragraph(f"<b>{title}</b> {body}", st["Bodyx"]))

    story.append(Paragraph("Watchlist", st["H1x"]))
    story.append(bullet_list(watchlist, st["Bodyx"]))

    story.append(Paragraph("Today's Action Plan", st["H1x"]))
    story.extend(section_image(IMAGES["action"], "Generated image: today's ranked founder action plan."))
    rows = [[Paragraph("Time", st["TableHead"]), Paragraph("Action", st["TableHead"])]]
    for bucket, action in actions:
        rows.append([Paragraph(bucket, st["TableCell"]), Paragraph(action, st["TableCell"])])
    action_table = Table(rows, colWidths=[1 * inch, 6 * inch], repeatRows=1)
    action_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(action_table)

    story.append(Paragraph("Methodology Note", st["H1x"]))
    story.append(Paragraph(p("""Scanned accessible public pages from official AI lab/company newsrooms, EU policy pages, RBI public releases, arXiv recent submissions, Hacker News, Product Hunt, GitHub trending, Hugging Face, and general current web search. Calendar was not checked by instruction. Reddit/X/deep community surfaces were only lightly represented because access can be login-gated or rate-limited. Private, paywalled, and inaccessible claims were not fabricated. Facts, analysis, inference, and speculation are labeled in prose where material."""), st["Bodyx"]))

    story.append(Paragraph("Source Appendix", st["H1x"]))
    for label, url in SOURCES:
        story.append(Paragraph(f'<link href="{url}" color="blue">{label}</link> - {url}', st["Smallx"]))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(build_markdown(), encoding="utf-8")
    build_pdf()
    print(PDF_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
