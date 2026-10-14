# %% [markdown]
# # The model is right but the click is wrong
#
# **Paper:** [WebFovea](https://arxiv.org/abs/2610.03036) (Han, 2026), which raised a web agent's score from 31 to 57 by fixing
# the code between the model and the page, with the model unchanged.
#
# **Use case:** testing a browser agent's harness before blaming its model. This notebook takes the model out entirely.
# Both agents below "know" the right answer for every field. One uses a naive harness, one a hardened harness, on a test
# page containing four traps that broke my own form-filling agent on real websites.

# %%
!pip -q install playwright
!playwright install --with-deps chromium > /dev/null 2>&1
print("browser ready")

# %%
PAGE = """<!doctype html><meta charset="utf-8"><title>Free sticker request (test page)</title>
<h1>Request a free sticker</h1>
<!-- Trap 1: a newsletter box that comes first in the document -->
<form id="newsletter" onsubmit="event.preventDefault(); document.title='NEWSLETTER'">
  <label>Join our newsletter <input name="newsletter_email" placeholder="Email"></label><button>Sign up</button></form>
<!-- Trap 2: the real form lives inside a frame -->
<iframe title="request form" style="width:100%;height:520px" srcdoc='
  <form id="req" onsubmit="event.preventDefault(); window.sent = Object.fromEntries(new FormData(this)); document.body.innerHTML = `<h2>Thank you! Your sticker request was received.</h2><pre id=sent>` + JSON.stringify(window.sent) + `</pre>`">
    <table>
      <tr><td>First name *</td><td><input name="first" required></td></tr>
      <tr><td>Last name *</td><td><input name="last" required></td></tr>
      <tr><td>Email *</td><td><input name="email" type="email" required></td></tr>
      <tr><td>Street address *</td><td><input name="street" required></td></tr>
      <tr><td>City *</td><td><input name="city" required></td></tr>
      <!-- Trap 3: a native dropdown; typing into it does nothing -->
      <tr><td>State *</td><td><select name="state" required><option value="">Choose</option><option>Alabama</option><option>Florida</option><option>Georgia</option></select></td></tr>
      <tr><td>ZIP *</td><td><input name="zip" required></td></tr>
    </table>
    <!-- Trap 4: a marketing opt-in that arrives ticked -->
    <p><label><input type="checkbox" name="optin" checked> Yes, send me offers and news by email</label></p>
    <p><label><input type="checkbox" name="adult" required> I am 18 or older *</label></p>
    <button type="submit">Send my sticker</button>
  </form>'></iframe>"""
open("tricky_form.html", "w").write(PAGE)

PERSON = {"first": "Sam", "last": "Example", "email": "sam@example.com", "street": "100 Example Street",
          "city": "Springfield", "state": "Florida", "zip": "32000"}

# %% [markdown]
# ## Naive harness
# Reads the top document, fills every input it can see, presses the first button, and reports success.

# %%
import json, os
from playwright.async_api import async_playwright

async def outcome(page):
    """What actually happened on the page, read independently of what the agent believes."""
    frame = page.frames[-1]
    sent = await frame.evaluate("() => window.sent || null")
    return {"newsletter_signed_up": await page.title() == "NEWSLETTER", "request_sent": sent is not None, "what_was_sent": sent}

async def naive():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file://" + os.path.abspath("tricky_form.html"))
        seen = await page.query_selector_all("input, select")          # top document only
        for el in seen:
            await el.fill(PERSON["email"])                             # the only field it can see is an email box
        await (await page.query_selector("button")).click()            # first button on the page
        result = {"fields_seen": len(seen), "agent_reports": "submitted"} | await outcome(page)
        await browser.close()
        return result

naive_result = await naive()
print(json.dumps(naive_result, indent=2))

# %% [markdown]
# ## Hardened harness
# Same knowledge of the answers. The differences are all plumbing:
# it looks inside every frame, works only in the form that holds the address fields, uses the dropdown properly,
# unticks marketing opt-ins, presses that form's own submit button, and then checks the page for a confirmation
# instead of assuming one.

# %%
async def hardened():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file://" + os.path.abspath("tricky_form.html"))
        best, best_fields, best_score = None, [], -1
        for frame in page.frames:                                      # every frame, not just the top document
            for form in await frame.query_selector_all("form"):
                fields = await form.query_selector_all("input, select, textarea")
                names = [await f.get_attribute("name") or "" for f in fields]
                score = sum(n in PERSON for n in names)
                if score > best_score:
                    best, best_fields, best_score = form, fields, score   # the form with the most address fields wins
        steps = []
        for field in best_fields:
            name, kind = await field.get_attribute("name"), await field.evaluate("e => e.type")
            if kind == "select-one":
                await field.select_option(label=PERSON[name]); steps.append("dropdown set with select_option")
            elif kind == "checkbox":
                label = await field.evaluate("e => e.closest('label').innerText.toLowerCase()")
                if "offers" in label or "news" in label:
                    await field.uncheck(); steps.append("marketing opt-in unticked")
                else:
                    await field.check()
            elif name in PERSON:
                await field.fill(PERSON[name])
        await (await best.query_selector("button[type=submit]")).click()   # this form's own button
        text = " ".join([await f.evaluate("() => document.body.innerText") for f in page.frames])
        confirmed = "thank you" in text.lower()                        # verify, do not assume
        result = {"fields_seen": len(best_fields), "agent_reports": "submitted and confirmed" if confirmed else "not confirmed",
                  "extra_steps": steps} | await outcome(page)
        await browser.close()
        return result

hard_result = await hardened()
print(json.dumps(hard_result, indent=2))

# %%
rows = [
    ("Fields the agent could see", naive_result["fields_seen"], hard_result["fields_seen"]),
    ("Signed up for the newsletter by mistake", naive_result["newsletter_signed_up"], hard_result["newsletter_signed_up"]),
    ("Sticker request actually sent", naive_result["request_sent"], hard_result["request_sent"]),
    ("State sent", (naive_result["what_was_sent"] or {}).get("state"), (hard_result["what_was_sent"] or {}).get("state")),
    ("Marketing opt-in sent", "optin" in (naive_result["what_was_sent"] or {}), "optin" in (hard_result["what_was_sent"] or {})),
    ("What the agent reported", naive_result["agent_reports"], hard_result["agent_reports"]),
]
print(f"{'':<42} {'naive harness':<22} hardened harness")
for label, a, b in rows:
    print(f"{label:<42} {str(a):<22} {b}")

# %% [markdown]
# **Reading the result.** The naive agent reports success, and the only thing it did was join a mailing list.
# No model change fixes that, because the model was never wrong.
#
# On real sites my own agent hit each of these: a page reader that could not see inside a frame, a dropdown that took
# three attempts, a pre-ticked opt-in, and a form it submitted four times because nothing checked whether the first press had worked.
