#!/usr/bin/env node
// Fills and submits a free-offer request form in its own headless browser.
// Jev decides what each field is, which button submits, and whether the page confirmed it; this script
// does the typing and clicking. It stops, without submitting, at a captcha, a payment field, a
// sweepstakes entry, or a required field it has no honest answer for.
// Usage: TYPESAFE_API_KEY=... node form_agent.js <url> [--dry] [--probe] [--id N]
//   --dry fills but never submits; --probe only prints the guard scores.
// Related reading: arXiv:2610.03036 (WebFovea: the model is right but the click is wrong).
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const DIR = __dirname;
const env = { JEV_API_KEY: process.env.TYPESAFE_API_KEY };
if (!env.JEV_API_KEY) { console.error("Set TYPESAFE_API_KEY to a TypeSafe AI key first."); process.exit(1); }
const profile = JSON.parse(fs.readFileSync(path.join(DIR, "profile.example.json"), "utf8"));
const [street, unit = ""] = profile.address_lines[0].split(/,\s*/);
const place = profile.address_lines[1].match(/^(.*),\s*([A-Z]{2})\s+(\d{5})/);
const me = {
  first_name: profile.name.split(" ")[0], last_name: profile.name.split(" ").slice(1).join(" "), full_name: profile.name,
  email: profile.email, street, unit, street_full: profile.address_lines[0],
  city: place[1], state: place[2], zip: place[3], country: "United States", shirt_size: profile.shirt_size || "",
  message: "I came across your brand and really like what you're doing. I'd love to try your products and share them with friends and family. Thank you!",
};
const STATE_NAMES = { FL: "Florida" };
const KINDS = {
  first_name: "First or given name only", last_name: "Last name or surname only", full_name: "Full name in one field",
  email: "Email address (including a confirm-email field)", phone: "Phone or mobile number",
  street: "Street address, line 1 only", unit: "Apartment, suite or unit (address line 2)",
  street_full: "A single box for the whole street address", city: "City or town", state: "State or province",
  zip: "ZIP or postal code", country: "Country", shirt_size: "Clothing or shirt size",
  message: "Free-text message, comment, or reason for the request", company: "Company, organization or job title",
  leave_blank: "Anything else: a search box, coupon code, date of birth, password, or an unknown field",
};
const BOXES = {
  agree_required: "A required agreement: terms, privacy policy, age confirmation, or confirming the address is correct",
  marketing_optin: "An optional opt-in to marketing emails, newsletters or texts",
  item_choice: "Chooses which free item or option the person wants", other: "Anything else",
};
const args = process.argv.slice(2), url = args[0], dry = args.includes("--dry");
const id = args.includes("--id") ? args[args.indexOf("--id") + 1] : "test";

async function jev(state, questions) {
  const r = await fetch("https://api.typesafe.ai/v1/systemone", {
    method: "POST", headers: { Authorization: "Bearer " + env.JEV_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "jev-latest", state, questions }),
  });
  if (!r.ok) throw new Error("Jev HTTP " + r.status);
  return (await r.json()).answers;
}

// Tag every visible control in every frame (embedded form widgets included) and describe it.
async function collect(page) {
  const fields = [], buttons = [];
  for (const [fi, frame] of page.frames().entries()) {
    let found;
    try {
      found = await frame.evaluate(fi => {
        const seen = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el); return r.width > 4 && r.height > 4 && s.visibility !== "hidden" && s.display !== "none"; };
        const text = el => (el ? el.innerText || el.textContent || "" : "").replace(/\s+/g, " ").trim();
        const labelOf = el => {
          const parts = [el.getAttribute("aria-label"), el.id && text(document.querySelector('label[for="' + CSS.escape(el.id) + '"]')), text(el.closest("label")),
            el.getAttribute("aria-labelledby") && text(document.getElementById(el.getAttribute("aria-labelledby").split(" ")[0])),
            el.placeholder, el.closest("td") && text(el.closest("td").previousElementSibling).replace(/^[\s*:]+$/, ""),
            el.closest("tr") && text(el.closest("tr").cells[0]).replace(/^[\s*:]+$/, ""),
            el.closest("tr") && el.closest("tr").previousElementSibling && text(el.closest("tr").previousElementSibling).slice(0, 80).replace(/^[\s*:]+$/, ""), text(el.closest("div,p,li")).slice(0, 90), el.name];
          return (parts.find(p => p && p.trim()) || "").slice(0, 110);
        };
        const out = { fields: [], buttons: [] };
        [...document.querySelectorAll("input,select,textarea")].forEach((el, i) => {
          const type = (el.getAttribute("type") || el.tagName).toLowerCase();
          if (["hidden", "submit", "button", "image", "reset", "file", "search"].includes(type) || !seen(el)) return;
          el.setAttribute("data-fb", fi + "-" + i);
          out.fields.push({ key: fi + "-" + i, form: fi + ":" + [...document.forms].indexOf(el.form), type, label: labelOf(el), name: el.name || "", required: el.required || /\*/.test(labelOf(el)),
            value: type === "checkbox" || type === "radio" ? el.checked : el.value,
            options: el.tagName === "SELECT" ? [...el.options].map(o => o.text.trim()).filter(Boolean).slice(0, 260) : null });
        });
        [...document.querySelectorAll("button,input[type=submit],input[type=button],[role=button]")].forEach((el, i) => {
          const label = (text(el) || el.value || el.getAttribute("aria-label") || "").slice(0, 60);
          if (!seen(el) || !label) return;
          el.setAttribute("data-fbb", fi + "-" + i);
          out.buttons.push({ key: fi + "-" + i, label, form: fi + ":" + [...document.forms].indexOf(el.form || el.closest("form")), kind: (el.getAttribute("type") || "").toLowerCase() });
        });
        return out;
      }, fi);
    } catch (e) { continue; }
    found.fields.forEach(f => fields.push({ ...f, frame }));
    found.buttons.forEach(b => buttons.push({ ...b, frame }));
  }
  return { fields, buttons };
}

function pickOption(options, kind) {
  const want = { state: [me.state, STATE_NAMES[me.state]], country: ["United States", "USA", "US", "United States of America", "U.S.A."], shirt_size: [me.shirt_size, "X-Large", "Extra Large"] }[kind] || [];
  for (const w of want) { const hit = options.find(o => w && o.toLowerCase() === w.toLowerCase()); if (hit) return hit; }
  return options.find(o => want.some(w => w && w.length > 2 && o.toLowerCase().includes(w.toLowerCase()))) || null;
}

(async () => {
  const out = { url, status: "failed", reason: "", filled: [], shots: [] };
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 1400 }, userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36" })).newPage();
  const shot = async tag => { const f = `shots/${id}-${tag}.png`; await page.screenshot({ path: path.join(DIR, f), fullPage: false }).catch(() => {}); out.shots.push(f); };
  const finish = async (status, reason) => { out.status = status; out.reason = reason; console.log(JSON.stringify(out)); await browser.close(); process.exit(0); };
  try {
    fs.mkdirSync(path.join(DIR, "shots"), { recursive: true });
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 40000 });
    await page.waitForTimeout(5000);
    let lastSignature = "";
    for (let step = 0; step < 4; step++) {
      const { fields, buttons } = await collect(page);
      // read every frame: an embedded form's text, and its thank-you message, live outside the top document
      const pageText = (await Promise.all(page.frames().map(f => f.evaluate(() => document.body.innerText).catch(() => "")))).join(" ").replace(/\s+/g, " ").slice(0, 2500);
      const html = await page.content();
      if (/recaptcha|hcaptcha|turnstile|captcha/i.test(page.frames().map(f => f.url()).join(" ")) && /g-recaptcha|h-captcha|cf-turnstile/i.test(html) && !/grecaptcha\.execute|invisible/i.test(html)
          || fields.some(f => /captcha|code as it appears|characters (shown|you see)|security code|verification code/i.test(f.label)))
        return finish("needs_you", "has a captcha");
      if (fields.some(f => /card number|credit card|cvv|cvc|expir/i.test(f.label + " " + f.name))) return finish("skipped", "asks for payment details");
      const open = fields.filter(f => !["checkbox", "radio"].includes(f.type) && !f.value);
      if (!fields.length && step === 0) return finish("failed", "no form fields found on the page; the form may be closed or did not load");
      if (!fields.length || (step && !open.length && !fields.some(f => f.type === "checkbox" && !f.value))) break;

      const questions = {
        offer: { type: "noul", instructions: "Is `page` a form where a person requests a free physical item (sample, stickers, fan pack, catalog) or free information, with no payment?" },
        sweepstakes: { type: "noul", instructions: "Is `page` an entry form for a sweepstakes, contest, raffle or prize drawing, where only chosen winners get something? A free item sent to everyone who asks is not one." },
        cause: { type: "noul", instructions: "Is `page` run by a political campaign, candidate, advocacy or activist group, petition, religious organization or charity fundraiser, or does sending the form sign the person up to support a cause?" },
        restricted: { type: "noul", instructions: "Is this offer only for businesses, trade professionals, employees, contractors, members of a program, or existing customers with an order, and not for the general public?" },
        excluded: { type: "noul", instructions: "Does `page` limit this offer to a place, such as one city, region or country, that would exclude someone living in " + me.city + ", " + (STATE_NAMES[me.state] || me.state) + ", USA?" },
      };
      const desc = {};
      fields.forEach((f, i) => {
        desc["f" + i] = { label: f.label, type: f.type, name: f.name, options: f.options ? f.options.slice(0, 8) : undefined };
        if (f.type === "checkbox" || f.type === "radio") questions["f" + i] = { type: "choice", instructions: "What is the checkbox or radio button `f" + i + "` in `fields` for?", criteria: BOXES };
        else questions["f" + i] = { type: "choice", instructions: "What information belongs in form field `f" + i + "` in `fields`?", criteria: KINDS };
      });
      const a = await jev({ page: pageText, fields: desc }, questions);
      if (step === 0) out.checks = Object.fromEntries(["offer", "sweepstakes", "cause", "restricted", "excluded"].map(k => [k, Math.round(a[k].noul * 100)]));
      if (step === 0 && process.argv.includes("--probe")) return finish("probe", "checks only");
      if (step === 0 && a.sweepstakes.noul >= 0.7) return finish("skipped", "looks like a sweepstakes entry, which must be entered by a person");
      if (step === 0 && a.excluded.noul >= 0.6) return finish("skipped", "the offer is limited to an area that does not include " + (STATE_NAMES[me.state] || me.state));
      if (step === 0 && a.cause.noul >= 0.4) return finish("skipped", "is a political, advocacy, religious or fundraising sign-up, which is yours to decide");
      if (step === 0 && a.restricted.noul >= 0.5) return finish("skipped", "is only for businesses, members or existing customers");
      if (step === 0 && a.offer.noul < 0.5) return finish("skipped", "does not look like a free-offer request form (" + Math.round(a.offer.noul * 100) + "%)");

      // the same fields coming back after a press means the form did not move on: never press twice
      const signature = fields.map(f => f.label + f.type).join("|");
      if (signature === lastSignature) {
        await shot("after");
        // some forms stay on screen and show a thank-you beside them
        const seen = (await jev({ page: pageText }, { ok: { type: "noul", instructions: "Does `page` show a confirmation that a form or request was submitted successfully, such as a thank-you message?" } })).ok.noul;
        out.confirm = Math.round(seen * 100);
        if (seen >= 0.6) return finish("done", "submitted and the page confirmed it");
        return finish("needs_you", "the form came back unchanged after pressing \"" + out.button + "\"; it may not have gone through");
      }
      lastSignature = signature;
      const tally = {};
      fields.forEach((f, i) => { if (!["leave_blank", "other", "marketing_optin"].includes(a["f" + i].choice)) tally[f.form] = (tally[f.form] || 0) + 1; });
      const main = Object.keys(tally).sort((x, y) => tally[y] - tally[x])[0];
      const hasUnit = fields.some((f, i) => f.form === main && a["f" + i].choice === "unit");
      for (const [i, f] of fields.entries()) {
        if (f.form !== main) continue;
        let kind = a["f" + i].choice;
        if (kind === "street" && !hasUnit) kind = "street_full";
        const loc = f.frame.locator('[data-fb="' + f.key + '"]');
        try {
          if (f.type === "checkbox") {
            if (kind === "agree_required" || kind === "item_choice") { await loc.check({ timeout: 4000 }); out.filled.push([f.label, "ticked (" + kind.replace("_", " ") + ")"]); }
            else if (kind === "marketing_optin" && f.value) { await loc.uncheck({ timeout: 4000 }); out.filled.push([f.label, "unticked marketing opt-in"]); }
          } else if (f.type === "radio") {
            if (kind === "item_choice" && !fields.some((g, j) => j < i && g.type === "radio" && g.name === f.name)) { await loc.check({ timeout: 4000 }); out.filled.push([f.label, "selected"]); }
          } else if (f.options) {
            let choice = pickOption(f.options, kind);
            if (!choice && me[kind] && f.options.length <= 250)
              choice = (await jev({ wanted: me[kind] }, { o: { type: "choice", instructions: "Which option means `wanted`?", criteria: Object.fromEntries(f.options.map(o => [o, null])) } })).o.choice;
            if (choice) { await loc.selectOption({ label: choice }, { timeout: 4000 }); out.filled.push([f.label, choice]); }
            else if (f.required) return finish("needs_you", "could not answer the required dropdown: " + f.label);
          } else if (me[kind]) {
            await loc.fill(me[kind], { timeout: 4000 });
            out.filled.push([f.label, kind === "message" ? "(short message)" : me[kind]]);
          } else if (f.required && !f.value) {
            return finish("needs_you", "asks for something I have no answer for: " + (f.label || kind));
          }
        } catch (e) { out.filled.push([f.label, "could not fill: " + e.message.split("\n")[0].slice(0, 60)]); }
      }
      await shot("filled" + (step || ""));
      // prefer the buttons inside the form that was filled; a lone submit button there needs no AI call
      let pool = buttons.filter(b => b.form === main);
      if (!pool.length) pool = buttons.filter(b => b.form.split(":")[0] === String(main).split(":")[0]);
      if (!pool.length) return finish("failed", "no button found to send the form");
      let button = pool.length === 1 ? pool[0] : pool.filter(b => b.kind === "submit").length === 1 ? pool.find(b => b.kind === "submit") : null;
      if (!button) {
        const options = Object.fromEntries(pool.slice(0, 30).map((b, i) => ["button " + i, b.label]));
        options["none"] = "None of these sends or continues the form";
        const pick = (await jev({ form_fields: out.filled.map(x => x[0]).slice(0, 12) }, { b: { type: "choice", instructions: "Which button sends the form with `form_fields`, or moves it to its next step? Typical labels: Submit, Send, Next, Continue, Request.", criteria: options } })).b.choice;
        if (pick === "none") return finish("failed", "could not tell which button sends the form: " + pool.slice(0, 6).map(b => b.label).join(" / "));
        button = pool[+pick.split(" ")[1]];
      }
      out.button = button.label;
      if (dry) return finish("dry_run", "filled but not submitted; would press \"" + button.label + "\"");
      const target = button.frame.locator('[data-fbb="' + button.key + '"]');
      // a cookie banner or overlay can sit on top of the button; fall back to pressing it directly
      await target.click({ timeout: 6000 }).catch(() => target.evaluate(el => el.click()));
      await page.waitForTimeout(5000);
      const challenge = await page.locator('iframe[src*="recaptcha"][src*="bframe"], iframe[src*="hcaptcha.com/captcha"], iframe[title*="challenge" i]').evaluateAll(
        els => els.some(el => { const r = el.getBoundingClientRect(); return r.width > 100 && r.height > 100 && getComputedStyle(el).visibility !== "hidden"; })).catch(() => false);
      if (challenge) { await shot("after"); return finish("needs_you", "a captcha appeared when the form was sent"); }
      // stop as soon as the page says thank you; otherwise the next loop could start on a different form
      const now = (await Promise.all(page.frames().map(f => f.evaluate(() => document.body.innerText).catch(() => "")))).join(" ").replace(/\s+/g, " ").slice(0, 3000);
      const thanks = (await jev({ page: now }, { ok: { type: "noul", instructions: "Does `page` show a confirmation that a form or request was submitted successfully, such as a thank-you message?" } })).ok.noul;
      if (thanks >= 0.6) { out.confirm = Math.round(thanks * 100); await shot("after"); return finish("done", "submitted and the page confirmed it"); }
    }
    await shot("after");
    const after = (await Promise.all(page.frames().map(f => f.evaluate(() => document.body.innerText).catch(() => "")))).join(" ").replace(/\s+/g, " ").slice(0, 3000);
    const c = await jev({ page: after }, { ok: { type: "noul", instructions: "Does `page` show a confirmation that a form or request was submitted successfully, such as a thank-you message?" },
      error: { type: "noul", instructions: "Does `page` show form validation errors or say that required information is missing?" } });
    out.confirm = Math.round(c.ok.noul * 100);
    if (c.ok.noul >= 0.6) return finish("done", "submitted and the page confirmed it");
    if (c.error.noul >= 0.6) return finish("needs_you", "the form rejected the submission; it needs a person to look");
    return finish("unconfirmed", "submitted, but the page showed no clear confirmation");
  } catch (e) {
    await shot("error");
    return finish("failed", e.message.split("\n")[0].slice(0, 160));
  }
})();
