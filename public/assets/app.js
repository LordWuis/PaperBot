"use strict";
const root = document.querySelector("#root");
const S = {
  session: null,
  view: "create",
  kind: "internship_letter",
  forms: {},
  draft: null,
  job: null,
  running: false,
};
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const $ = (s) => document.querySelector(s);
const brand =
  '<div class="brand"><span class="brand-icon">P</span><div>PaperBot<small>A little less paperwork.</small></div></div>';
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function api(path, options = {}) {
  const headers = { "X-PaperBot": "1", ...options.headers };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch("/api" + path, { ...options, headers });
  let data;
  try {
    data = await res.json();
  } catch {
    throw Error("Unexpected server response. Please retry.");
  }
  if (!res.ok) {
    const e = Error(data.error || "Request failed.");
    e.status = res.status;
    throw e;
  }
  return data;
}
function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.style.display = "block";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.style.display = "none"), 6000);
}
function showError(message) {
  const el =
    document.querySelector("dialog[open] .dialog-error") || $("#error");
  if (el) {
    el.textContent = message;
    el.classList.remove("hidden");
  } else toast(message);
}
async function action(button, fn) {
  const oldLabel = button?.innerHTML;
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = "One moment…";
  }
  try {
    await fn();
  } catch (e) {
    showError(e.message);
    if (e.status === 402) {
      S.session.active = false;
      S.view = "pay";
      shell();
    }
  } finally {
    if (button) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.innerHTML = oldLabel;
    }
  }
}
function confirmAction(title, text, label = "Confirm") {
  return new Promise((resolve) => {
    const d = document.createElement("dialog");
    d.innerHTML = `<h2>${esc(title)}</h2><p class="muted">${esc(text)}</p><div class="row"><button data-no>Cancel</button><button class="primary" data-yes>${esc(label)}</button></div>`;
    document.body.append(d);
    const done = (v) => {
      d.close();
      d.remove();
      resolve(v);
    };
    d.querySelector("[data-no]").onclick = () => done(false);
    d.querySelector("[data-yes]").onclick = () => done(true);
    d.oncancel = (e) => {
      e.preventDefault();
      done(false);
    };
    d.showModal();
  });
}
async function boot() {
  if (location.pathname === "/verification") {
    await verifyPage();
    return;
  }
  try {
    S.session = await api("/session");
    S.view =
      location.pathname === "/pay" || !S.session.active ? "pay" : "create";
    shell();
    if (location.pathname === "/join") await joinInvitation();
    else if (S.session.offer_due) supportPopup();
  } catch (e) {
    if (e.status === 401) login();
    else
      root.innerHTML = `<main class="loading">${brand}<h2>Setup needs attention</h2><p>${esc(e.message)}</p><p>Connect Postgres and configure environment variables in Vercel.</p><button id="reload">Try again</button></main>`;
    if ($("#reload")) $("#reload").onclick = () => location.reload();
  }
}
function login() {
  root.innerHTML = `<div class="login"><section class="login-art">${brand}<div><div class="eyebrow">DOCUMENTS, DONE BEAUTIFULLY</div><h1>Make it official.<br><em>In a few clicks.</em></h1><div class="login-paper-stack" aria-hidden="true"><span>LETTER</span><b>✦</b></div></div></section><section class="login-form"><div class="login-card"><div class="eyebrow">PAPERBOT</div><h1>Welcome back.</h1><p class="muted">A sign-in code will arrive by email.</p><div id="error" class="error hidden"></div><form id="login"><div class="field"><label for="name">Name</label><input id="name" name="name" autocomplete="name" required maxlength="150" placeholder="Your name"></div><div class="field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" required placeholder="you@company.com"></div><button class="primary full">Continue <span>→</span></button></form><form id="otp" class="hidden"><div class="field"><label for="code">Sign-in code</label><input id="code" name="code" pattern="[0-9]{6}" maxlength="6" inputmode="numeric" autocomplete="one-time-code" placeholder="000000" required></div><button class="primary full">Sign in →</button><button type="button" id="again" class="full">Try another email</button></form><p class="help">Code expires in 10 minutes.</p></div></section></div>`;
  $("#login").onsubmit = (e) => {
    e.preventDefault();
    action(e.submitter, async () => {
      await api("/auth/request", {
        method: "POST",
        body: Object.fromEntries(new FormData(e.target)),
      });
      $("#login").classList.add("hidden");
      $("#otp").classList.remove("hidden");
      $("#error").classList.add("hidden");
      $("#code").focus();
      toast("Code sent. Check your inbox.");
    });
  };
  $("#otp").onsubmit = (e) => {
    e.preventDefault();
    action(e.submitter, async () => {
      await api("/auth/verify", {
        method: "POST",
        body: { code: $("#code").value },
      });
      await boot();
    });
  };
  $("#again").onclick = login;
}
function shell() {
  const u = S.session.user;
  const menu = [
    ["create", "✦", "Create"],
    ["bulk", "▤", "Batch"],
    ["history", "◷", "History"],
    ["pay", "♡", "Access & support"],
  ];

  root.innerHTML = `<div class="layout"><aside class="sidebar">${brand}<div><div class="nav-label">WORKSPACE</div><nav class="nav">${menu.map(([key, icon, label]) => `<button data-view="${key}" aria-current="${S.view === key ? "page" : "false"}" class="${S.view === key ? "selected" : ""}"><span class="symbol">${icon}</span>${label}</button>`).join("")}</nav></div><div class="account"><strong>${esc(u.name)}</strong><p>${esc(u.email)}</p><span class="tag">${S.session.user.free_role ? "Free access" : S.session.active ? "Active access" : "Payment required"}</span><br><button id="logout">Sign out ↗</button></div></aside><main class="main"><header class="topbar"><span>Workspace <span aria-hidden="true">/</span> ${esc(menu.find((m) => m[0] === S.view)?.[2] || "Documents")}</span><span>Persevex · PaperBot</span></header><div id="content"></div></main></div>`;
  root.querySelectorAll("[data-view]").forEach(
    (b) =>
      (b.onclick = () => {
        rememberForm();
        S.view = b.dataset.view;
        if (!S.session.active && ["create", "bulk"].includes(S.view))
          S.view = "pay";
        shell();
      }),
  );
  $("#logout").onclick = () =>
    action($("#logout"), async () => {
      S.running = false;
      await api("/auth/logout", { method: "POST" });
      S.session = null;
      S.forms = {};
      S.draft = null;
      S.job = null;
      login();
    });
  (
    ({
      create: renderCreate,
      bulk: renderBulk,
      history: renderHistory,
      pay: renderPay,
    })[S.view] || renderCreate
  )();
}
function hero(title, subtitle, tag = "PAPERBOT") {
  return `<section class="hero"><div><div class="eyebrow">${tag}</div><h1>${title}</h1>${subtitle ? `<p class="muted">${subtitle}</p>` : ""}</div><span class="tag">● ${S.session.active ? "Ready" : "Access needed"}</span></section><div id="error" class="error hidden"></div>`;
}
function typeOptions() {
  return Object.entries(S.session.schema)
    .map(
      ([k, s]) =>
        `<option value="${k}" ${S.kind === k ? "selected" : ""}>${esc(s.label)}</option>`,
    )
    .join("");
}
function renderCreate() {
  const schema = S.session.schema[S.kind];
  $("#content").innerHTML =
    hero("Create a document", "Choose a template to begin.") +
    `<div class="document-picker" role="group" aria-label="Choose a document">${Object.entries(
      Object.fromEntries(
        Object.entries(S.session.schema).filter(
          ([key]) => !key.startsWith("saved_"),
        ),
      ),
    )
      .map(
        ([key, item], i) =>
          `<button type="button" data-kind="${key}" aria-pressed="${key === S.kind}" class="document-tile ${key === S.kind ? "chosen" : ""}"><span class="tile-icon" aria-hidden="true">${{ ca_certificate: "⚑", ca_letter: "✉", course_certificate: "↗", internship_letter: "✧", offer_letter: "★", lor: "❝" }[key] || "✦"}</span><span>${esc(item.short_label)}</span>${key === S.kind ? '<span class="tile-check" aria-hidden="true">✓</span>' : ""}</button>`,
      )
      .join(
        "",
      )}</div><div class="field"><label for="saved-template">Certificate library · 9 saved designs</label><select id="saved-template"><option value="">Choose a saved certificate template…</option>${Object.entries(
      S.session.schema,
    )
      .filter(([key]) => key.startsWith("saved_"))
      .map(
        ([key, item]) =>
          `<option value="${key}" ${S.kind === key ? "selected" : ""}>${esc(item.label)} · ${esc(item.source)}</option>`,
      )
      .join(
        "",
      )}</select></div><div class="workflow" aria-label="Document steps"><span class="current">01 <b>Details</b></span><i></i><span>02 <b>Review</b></span><i></i><span>03 <b>Send</b></span></div><div class="workspace"><section class="panel form-panel"><div class="panel-head"><h2>${esc(schema.label)}</h2><span class="step">01</span></div><div class="panel-body"><form id="document-form">${S.kind === "internship_letter" ? internshipChoice(S.forms[S.kind]?.internship_variant) : ""}${schema.fields.map((f) => `<div class="field"><label for="f-${f.name}">${esc(f.label)}</label>${f.type === "select" ? `<select id="f-${f.name}" name="${f.name}" required>${f.options.map(([value, label]) => `<option value="${esc(value)}" ${S.forms[S.kind]?.[f.name] === value ? "selected" : ""}>${esc(label)}</option>`).join("")}</select>` : `<input id="f-${f.name}" name="${f.name}" type="${f.type}" placeholder="${esc(f.placeholder)}" value="${esc(S.forms[S.kind]?.[f.name] || "")}" required maxlength="250">`}</div>`).join("")}<div class="info">${esc(schema.helper_text)}</div><button class="primary full" type="submit">Preview document <span>→</span></button><button type="button" id="clear" class="full">Clear</button></form></div></section><section class="panel preview-panel"><div class="panel-head"><h2>Preview</h2><span class="step">02</span></div><div id="preview"></div></section></div>`;
  document.querySelectorAll("[data-kind]").forEach(
    (button) =>
      (button.onclick = () => {
        rememberForm();
        S.kind = button.dataset.kind;
        S.draft = null;
        renderCreate();
      }),
  );
  $("#saved-template").onchange = (e) => {
    if (!e.target.value) return;
    rememberForm();
    S.kind = e.target.value;
    S.draft = null;
    renderCreate();
  };
  $("#document-form").oninput = rememberForm;
  const picker = $(".document-picker");
  const chosen = picker?.querySelector(".chosen");
  if (chosen && picker.scrollWidth > picker.clientWidth)
    picker.scrollLeft = chosen.offsetLeft - picker.offsetLeft - 22;
  $("#document-form").onsubmit = (e) => {
    e.preventDefault();
    rememberForm();
    action(e.submitter, async () => {
      S.draft = await api("/drafts", {
        method: "POST",
        body: { kind: S.kind, form: S.forms[S.kind] },
      });
      renderPreview();
      $("#preview")
        .closest(".panel")
        .scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "auto"
            : "smooth",
          block: "start",
        });
      $("#preview").setAttribute("tabindex", "-1");
      $("#preview").focus({ preventScroll: true });
      toast("Ready. Check the PDF and recipient before sending.");
    });
  };
  $("#clear").onclick = () => {
    S.forms[S.kind] = {};
    S.draft = null;
    renderCreate();
  };
  renderPreview();
}
function rememberForm() {
  if ($("#document-form"))
    S.forms[S.kind] = Object.fromEntries(new FormData($("#document-form")));
}
function renderPreview() {
  const target = $("#preview");
  if (!target) return;
  const d = S.draft;
  document.querySelectorAll(".workflow > span").forEach((step, index) => {
    const current = d ? (d.state === "submitted" ? 2 : 1) : 0;
    step.classList.toggle("current", index === current);
    if (index === current) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
  });
  if (!d) {
    target.innerHTML =
      '<div class="preview-empty"><div><div class="paper"><b></b><i></i><i></i><i></i></div><h3>Your preview appears here.</h3></div></div>';
    return;
  }
  target.innerHTML = `<img class="preview-image" src="/api/drafts/${esc(d.id)}/preview/0" alt="First page of generated document"><div class="preview-tools"><a class="button" href="/api/drafts/${esc(d.id)}/pdf" target="_blank" rel="noopener">Review all pages ↗</a><a class="button" href="/api/drafts/${esc(d.id)}/pdf?download=1">Download PDF ↓</a></div><div class="email-review"><p><strong>To</strong> ${esc(d.recipient.name)} &lt;${esc(d.recipient.email)}&gt;</p><p><strong>From</strong> ${esc(d.email.from)}</p><p><strong>Bcc</strong> ${esc((d.email.bcc || []).join(", ") || "None")}</p><p><strong>Subject</strong> ${esc(d.email.subject)}</p><details><summary>Review email body</summary><div class="email-body" id="email-body"></div></details></div><div class="panel-body"><button id="send" class="primary full" ${d.state === "submitted" ? "disabled" : ""}>${d.state === "submitted" ? "Submitted to email provider ✓" : "Approve & send email →"}</button><p class="help">Review every PDF page and the recipient before approving. Provider acceptance does not confirm delivery.</p></div>`;
  // This HTML is our server-owned template; all dynamic recipient fields are escaped server-side.
  $("#email-body").innerHTML = d.email.html;
  $("#send").onclick = () =>
    action($("#send"), async () => {
      if (
        !(await confirmAction(
          "Send this document?",
          `Send the reviewed ${d.recipient.letter_type} to ${d.recipient.email}, with the sender and Bcc shown above?`,
          "Approve & send",
        ))
      )
        return;
      const result = await api(`/drafts/${d.id}/send`, {
        method: "POST",
        body: { sha256: d.sha256 },
      });
      S.draft = { ...d, ...result };
      renderPreview();
      toast("Accepted by Resend. Check provider tracking for delivery.");
    });
}
async function renderHistory() {
  $("#content").innerHTML =
    hero("Document history", "Open a document or check its status.") +
    '<div id="history-list" class="panel panel-body muted">Loading documents…</div>';
  try {
    const data = await api("/drafts");
    if (S.view !== "history") return;
    $("#history-list").className = "panel";
    $("#history-list").innerHTML = data.drafts.length
      ? `<div class="table-wrap"><table><thead><tr><th>Recipient</th><th>Document</th><th>Created</th><th>Status</th><th></th></tr></thead><tbody>${data.drafts.map((d) => `<tr><td class="name">${esc(d.recipient.name)}<small>${esc(d.recipient.email)}</small></td><td>${esc(S.session.schema[d.kind].short_label)}</td><td>${new Date(d.created * 1000).toLocaleDateString()}</td><td><span class="pill ${esc(d.state)}">${esc(d.state)}</span>${d.provider_id ? `<small>${esc(d.provider_id)}</small>` : ""}</td><td><button data-draft="${d.id}">Open →</button></td></tr>`).join("")}</tbody></table></div>`
      : '<div class="panel-body muted">Your prepared documents will appear here.</div>';
    document.querySelectorAll("[data-draft]").forEach(
      (b) =>
        (b.onclick = () =>
          action(b, async () => {
            S.draft = await api("/drafts/" + b.dataset.draft);
            S.kind = S.draft.kind;
            S.forms[S.kind] = S.draft.form;
            S.view = "create";
            shell();
          })),
    );
  } catch (e) {
    showError(e.message);
  }
}
function offerCard() {
  const support = S.session.support || {};
  const date = support.due_at
    ? new Date(support.due_at * 1000).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "Asia/Kolkata",
      })
    : "the 5th of next month";
  if (
    ["scheduled", "due", "thanks", "free", "waiting"].includes(support.phase)
  ) {
    const title =
      support.phase === "due"
        ? "Your support reminder"
        : support.phase === "scheduled"
          ? "Your choice is saved."
          : support.phase === "thanks"
            ? "Thank you for your support."
            : "Make yourself at home.";
    const message =
      support.phase === "due"
        ? `You chose to contribute ₹${support.amount}. Your reminder date is ${date}. Pay whenever you’re ready; your access stays free.`
        : support.phase === "scheduled"
          ? `You chose ₹${support.amount}. Nothing to pay now. We’ll remind you in the app on ${date}, or when you next return.`
          : support.phase === "thanks"
            ? "Your contribution was received. Your full access continues."
            : "Enjoy your full workspace. There’s nothing to pay now.";
    return `<section class="panel panel-body"><h2>${title}</h2><p>${message}</p><div class="dialog-error error hidden" role="alert"></div>${support.phase === "due" ? `<button class="primary" id="support-build">Pay ₹${support.amount} →</button>` : ""}${["scheduled", "due"].includes(support.phase) ? '<button id="support-free">Choose free access instead · ₹0</button>' : ""}<p class="help">Optional support. No automatic charge or access expiry.</p></section>`;
  }

  return `<section class="support-card"><div class="support-art" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="art-letter"><span>made with care</span><i></i><i></i><b>✦</b><em>Aman</em></div><span class="art-star">✳</span><span class="art-burger">🍔</span><div class="art-note">Less paperwork.<br>More good things.</div></div><div class="support-copy"><span class="eyebrow">A LITTLE NOTE FROM THE MAKER</span><h2>Keep the good<br>things going<span class="accent">.</span></h2><div class="dialog-error error hidden" role="alert"></div><p>I rebuilt PaperBot to make your work a little easier. If it saves you time, here’s a way to say thanks.</p><button class="support-main" id="support-build"><span><small>BACK THE WORK</small><strong>Support Aman</strong></span><span class="support-price">₹1,000 <b>↗</b></span></button><button class="support-small" id="support-burger"><span>🍔 &nbsp; Buy me a burger instead</span><strong>₹349 ↗</strong></button><div class="support-fine">Choose now. Pay on the 5th of next month.<br>Nothing is charged today. Your full access stays free.</div><button class="support-free" id="support-free">Continue for free <span>₹0 →</span></button><p class="support-signature">Built by Aman. Made for your everyday.</p></div></section>`;
}
async function openPayment(button, purpose, seat_id) {
  await action(button, async () => {
    const d = await api("/payment-link", {
      method: "POST",
      body: { purpose, seat_id },
    });
    const url = new URL(d.url);
    if (url.protocol !== "https:") throw Error("Invalid payment URL");
    location.assign(url.href);
  });
}
function bindOffer(container, close) {
  const save = (button, amount) =>
    action(button, async () => {
      S.session.support = await api("/support/choice", {
        method: "POST",
        body: { amount },
      });
      S.session.offer_due = false;
      if (close) close();
      else shell();
      toast(
        amount
          ? "Choice saved. Nothing to pay now; we’ll remind you on the 5th of next month."
          : "Your full access stays free.",
      );
    });
  const main = container.querySelector("#support-build");
  if (main)
    main.onclick = (e) =>
      S.session.support?.phase === "due"
        ? openPayment(
            e.currentTarget,
            S.session.support.amount === 349 ? "donation" : "support",
          )
        : save(e.currentTarget, 1000);
  const burger = container.querySelector("#support-burger");
  if (burger) burger.onclick = (e) => save(e.currentTarget, 349);
  const free = container.querySelector("#support-free");
  if (free) free.onclick = (e) => save(e.currentTarget, 0);
}
function supportPopup() {
  const d = document.createElement("dialog");
  d.className = "support-dialog";
  d.setAttribute("aria-label", "Optional support for Aman");
  d.innerHTML =
    `<button class="dialog-close" aria-label="Close support message">×</button>` +
    offerCard();
  d.querySelector(".dialog-close").onclick = () => {
    d.close();
    d.remove();
  };
  document.body.append(d);
  bindOffer(d, () => {
    d.close();
    d.remove();
  });
  d.oncancel = () => d.remove();
  d.showModal();
}
async function joinInvitation() {
  const token = new URLSearchParams(location.search).get("token");
  if (!token) {
    toast("This invitation is incomplete.");
    return;
  }
  if (
    !(await confirmAction(
      "Accept this invitation?",
      "The person who invited you pays for this account's access. This link can be used by one person only.",
      "Accept invitation",
    ))
  )
    return;
  await api("/invitations/claim", { method: "POST", body: { token } });
  history.replaceState(null, "", "/app");
  await boot();
}
async function renderPay() {
  const u = S.session.user,
    isMain = u.free_role === "main";
  const end = u.access_until
    ? new Date(u.access_until * 1000).toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
      }) + " IST"
    : u.expiry;
  $("#content").innerHTML =
    hero(
      "Access & support",
      "Manage your plan and people.",
      "ACCESS & SUPPORT",
    ) +
    (isMain
      ? offerCard()
      : `<section class="panel pay-card panel-body"><h2>${u.free_role ? "Your developer account is free." : u.sponsored ? "Your access is paid for by the person who invited you." : "₹1,000 per month"}</h2>${end ? `<p>Access ${S.session.active ? "until" : "ended"}: ${esc(end)}</p>` : ""}${!u.free_role && !u.sponsored && !S.session.active ? '<p>Pay first to unlock all letters, certificates and bulk operations.</p><button id="pay" class="primary">Pay ₹1,000 →</button>' : ""}${u.sponsored && !S.session.active ? "<p>Ask the person who invited you to renew your access.</p>" : ""}</section>`) +
    (isMain
      ? `<section class="panel panel-body"><h2>Add another person</h2><p>You pay ₹1,000 per person for one month starting on the payment date. After payment, share their single-use invitation. Each person gets a separate workspace.</p><button id="add-person">Pay ₹1,000 & add a person</button><div class="divider"></div>${S.session.seats.map((s) => `<div class="seat-row"><strong>${esc(s.email || "Invitation waiting to be used")}</strong><p>${s.expires_at ? "Access until " + esc(new Date(s.expires_at * 1000).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })) + " IST" : "Payment needed"}</p>${s.token ? `<button data-copy="${esc(s.token)}">Copy invitation link</button>` : ""}${!s.expires_at || s.expires_at * 1000 <= Date.now() ? `<button data-renew="${esc(s.id)}">Renew · ₹1,000</button>` : ""}</div>`).join("")}</section>`
      : "") +
    '<p><button id="check-payment">Refresh payment status</button></p><p class="help">Access activates after Razorpay confirms your payment. Returning from checkout alone does not activate it.</p>';
  if (isMain) {
    bindOffer($("#content"));
    $("#add-person").onclick = (e) => openPayment(e.currentTarget, "seat");
    document
      .querySelectorAll("[data-renew]")
      .forEach(
        (b) => (b.onclick = () => openPayment(b, "seat", b.dataset.renew)),
      );
    document.querySelectorAll("[data-copy]").forEach(
      (b) =>
        (b.onclick = () =>
          action(b, async () => {
            const link =
              location.origin +
              "/join?token=" +
              encodeURIComponent(b.dataset.copy);
            try {
              await navigator.clipboard.writeText(link);
              toast("Invitation link copied.");
            } catch {
              const input = document.createElement("input");
              input.readOnly = true;
              input.value = link;
              b.after(input);
              input.select();
            }
          })),
    );
  }
  if ($("#pay"))
    $("#pay").onclick = (e) => openPayment(e.currentTarget, "access");
  $("#check-payment").onclick = (e) =>
    action(e.currentTarget, async () => {
      S.session = await api("/session");
      renderPay();
      toast("Payment status refreshed.");
    });
}
function internshipChoice(value = "without_stipend") {
  return `<fieldset class="internship-choice"><legend>Stipend mentioned in the letter?</legend><label><input type="radio" name="internship_variant" value="without_stipend" ${value === "without_stipend" ? "checked" : ""}> Without stipend</label><label><input type="radio" name="internship_variant" value="with_stipend" ${value === "with_stipend" ? "checked" : ""}> With stipend</label></fieldset>`;
}
async function renderBulk() {
  $("#content").innerHTML =
    hero("Create in bulk", "Upload a CSV, review, and send.", "BATCH STUDIO") +
    `<div class="stack"><section class="panel"><div class="panel-head"><h2>New batch</h2><span class="tag">Up to 500</span></div><div class="panel-body"><form id="batch-upload"><div class="field"><label for="batch-kind">Document</label><select id="batch-kind" name="kind">${typeOptions()}</select><p class="help">CSV columns: <code id="csv-headers"></code></p></div><div id="batch-variant"></div><div class="dropzone"><label for="csv-file">Choose CSV</label><input id="csv-file" name="file" type="file" accept=".csv,text/csv" required><p class="help">UTF-8 · maximum 2 MB</p></div><button class="primary">Prepare batch →</button></form></div></section><div id="batch"></div><section class="panel"><div class="panel-head"><h2>Recent batches</h2></div><div id="batch-list" class="panel-body muted">Loading…</div></section></div>`;
  const headers = () => {
    $("#batch-variant").innerHTML =
      $("#batch-kind").value === "internship_letter" ? internshipChoice() : "";
    $("#csv-headers").textContent = S.session.schema[
      $("#batch-kind").value
    ].fields
      .map((f) => f.name)
      .join(",");
  };
  headers();
  $("#batch-kind").onchange = headers;
  $("#batch-upload").onsubmit = (e) => {
    e.preventDefault();
    action(e.submitter, async () => {
      const result = await api("/jobs", {
        method: "POST",
        body: new FormData(e.target),
      });
      S.job = await api("/jobs/" + result.id);
      drawBatch();
      runBatch();
    });
  };
  try {
    const data = await api("/jobs");
    if (S.view !== "bulk") return;
    $("#batch-list").innerHTML = data.jobs.length
      ? data.jobs
          .map(
            (j) =>
              `<div class="row space"><span>${esc(S.session.schema[j.kind].short_label)} · ${new Date(j.created * 1000).toLocaleString()} · ${esc(j.state)}</span><button data-job="${j.id}">Open batch →</button></div>`,
          )
          .join("")
      : "Batches will appear here.";
    document.querySelectorAll("[data-job]").forEach(
      (b) =>
        (b.onclick = () =>
          action(b, async () => {
            S.job = await api("/jobs/" + b.dataset.job);
            drawBatch();
          })),
    );
    if (S.job) drawBatch();
  } catch (e) {
    showError(e.message);
  }
}
function drawBatch() {
  if (!$("#batch") || !S.job) return;
  const j = S.job;
  const processed = j.rows.filter(
    (r) => !["pending", "working"].includes(r.state),
  ).length;
  $("#batch").innerHTML =
    `<section class="panel"><div class="panel-head"><h2>Batch review</h2><span class="pill">${esc(j.state)}</span></div><div class="batch-status"><div class="row space"><strong>${j.state === "preparing" ? processed : j.submitted} / ${j.total} ${j.state === "preparing" ? "prepared" : "submitted"}</strong><span class="muted">${j.failed} need attention</span></div><progress max="${j.total}" value="${j.state === "preparing" ? processed : j.submitted}"></progress><p class="help">Keep this workspace open while processing. Reopen a saved batch to resume after closing it.</p><div class="row">${["preparing", "sending"].includes(j.state) ? `<button id="batch-run" class="primary">${S.running ? "Pause after this row" : "Resume processing →"}</button>` : ""}${j.state === "review" ? '<button id="batch-approve" class="primary">Approve ready documents & send →</button>' : ""}${j.state === "completed" && j.rows.some((r) => r.state === "retry") ? '<button id="batch-retry">Retry unconfirmed submissions</button>' : ""}<a class="button" href="/api/jobs/${j.id}/failed.csv">Export failed rows ↓</a></div></div><div class="table-wrap"><table><thead><tr><th>Row</th><th>Recipient</th><th>Status</th><th>Review</th></tr></thead><tbody>${j.rows.map((r) => `<tr><td>${r.position}</td><td class="name">${esc(r.recipient?.name || r.form.name)}<small>${esc(r.recipient?.email || r.form.email || "Resolved from onboarding during preparation")}</small>${r.error ? `<small>${esc(r.error)}</small>` : ""}</td><td><span class="pill ${esc(r.state)}">${esc(r.state)}</span></td><td>${r.draft_id ? `<a class="button" target="_blank" href="/api/drafts/${r.draft_id}/pdf" rel="noopener">PDF ↗</a> <button data-review="${r.draft_id}">Email</button>` : ""}</td></tr>`).join("")}</tbody></table></div></section>`;
  if ($("#batch-run"))
    $("#batch-run").onclick = () => {
      if (S.running) {
        S.running = false;
        drawBatch();
      } else runBatch();
    };
  if ($("#batch-approve"))
    $("#batch-approve").onclick = () =>
      action($("#batch-approve"), async () => {
        const n = j.rows.filter((r) => r.state === "ready").length;
        if (
          !(await confirmAction(
            "Send this batch?",
            `Approve the ${n} ready documents and their resolved recipients shown in this batch. ${j.failed} failed rows will not be sent.`,
            "Approve batch",
          ))
        )
          return;
        await api("/jobs/" + j.id + "/approve", {
          method: "POST",
          body: { confirm: true },
        });
        S.job = await api("/jobs/" + j.id);
        runBatch();
      });
  if ($("#batch-retry"))
    $("#batch-retry").onclick = () =>
      action($("#batch-retry"), async () => {
        await api("/jobs/" + j.id + "/retry", { method: "POST" });
        S.job = await api("/jobs/" + j.id);
        runBatch();
      });
  document.querySelectorAll("[data-review]").forEach(
    (b) =>
      (b.onclick = () =>
        action(b, async () => {
          const d = await api("/drafts/" + b.dataset.review);
          await confirmAction(
            "Email details",
            `To: ${d.email.to.join(", ")}. From: ${d.email.from}. Bcc: ${(d.email.bcc || []).join(", ")}. Subject: ${d.email.subject}.`,
            "Close",
          );
        })),
  );
}
async function runBatch() {
  if (S.worker || !S.job) return;
  S.worker = true;
  S.running = true;
  const id = S.job.id;
  drawBatch();
  try {
    while (
      S.running &&
      S.job?.id === id &&
      ["preparing", "sending"].includes(S.job.state)
    ) {
      const j = await api("/jobs/" + id + "/step", { method: "POST" });
      if (S.job?.id !== id) break;
      S.job = j;
      drawBatch();
      await wait(1100);
    }
  } catch (e) {
    showError(e.message);
  } finally {
    S.worker = false;
    S.running = false;
    drawBatch();
  }
}
async function verifyPage() {
  root.innerHTML =
    '<main class="verification panel">' +
    brand +
    '<div id="verify-content" class="panel-body">Checking certificate…</div></main>';
  const id = new URLSearchParams(location.search).get("id");
  try {
    if (!id) throw Error("Provide a certificate ID in the verification link.");
    const d = await api("/verification/" + encodeURIComponent(id));
    $("#verify-content").innerHTML =
      `<span class="tag">VERIFIED RECORD</span><h1>${esc(d.name)}</h1><p>${esc(d.domain)}</p><p class="muted">Issued ${esc(d.date)}</p><p class="help">Certificate ID: ${esc(id)}</p>`;
  } catch (e) {
    $("#verify-content").textContent = e.message;
  }
}
boot();
