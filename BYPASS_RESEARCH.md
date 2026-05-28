# Payment Friction Research — Creative Bypass Paths

**Date:** May 2026  
**Scope:** Research only — no product implementation.  
**Goal:** Get as close as possible to *"donor saves card once on GiveFund, clicks Give Now, donation completes"* without platform partnerships, without becoming a money transmitter, and without actions that invite blocking or litigation.

**Critical constraint:** GiveFund must remain a **referral/discovery layer**. Funds must flow **donor → platform → beneficiary**. Any path that pools money, re-routes settlement, or impersonates the platform's checkout is out of scope.

---

## Shipped product path (May 2026)

What we **can** ship without breaking ToS or platform APIs:

| Feature | Path | Value |
|---------|------|--------|
| **Express Give** | `give.html` + `GET /campaigns/{id}/checkout` | Deep `/donate` links, email prefill (Givebutter, Donorbox, …), Link hints |
| **Stripe wallet** | `POST /wallet/setup` (setup mode, **no charge**) | Seeds Stripe Link for other merchants |
| **Discovery** | 24k+ index + live search | Finding the campaign (core value) |

What we **cannot** ship: passing GiveFund's payment token into GoFundMe/LaunchGood checkout. No public API exists. True one-click requires **platform partnership** (Tier B) or **Pledge embed** for nonprofits only (`PLEDGE_RESEARCH.md`).

There is no hidden technical bypass (extension, webview injection, VCN paste) that is both reliable and safe to operate as GiveFund.

---

## Executive summary

| Angle | Feasibility | Legal/ToS | Platform block risk | Build effort | Priority |
|-------|-------------|-----------|---------------------|--------------|----------|
| 1 — Stripe Link | Partial (not universal) | Clean for GiveFund | Low–medium (they control UX) | Days–weeks (GiveFund Checkout) | **Pursue now** (with realistic expectations) |
| 2 — Browser extension | Technically partial | Gray → **red** if GiveFund ships it | High | Months | **Skip** (donor-owned password manager OK) |
| 3 — Stripe Issuing VCN | High technically | Gray (program compliance) | Medium–high (fraud/BIN) | Months + sales/legal | **Explore** (not first ship) |
| 4 — Webview injection | Low for card fields | Red | High | Months | **Skip** |
| 5 — Magic checkout URLs | Low on core targets | Clean | None | Days (deep links only) | **Pursue now** (deep links + UTM) |

**Ranked path to near-seamless giving (fastest, lowest risk):**

1. **Ship Stripe Checkout on GiveFund with Link enabled** — builds donor Link identity and powers *GiveFund-native* flows (tips, subscriptions to GiveFund, future "give on GiveFund" products). Cross-platform benefit is **indirect**: faster checkout only on **other merchants that use Stripe + Link**, same email, donor still on their site.
2. **Maximize deep links + prepopulation** where platforms allow (GoFundMe `/donate`, LaunchGood `/donate`, Donorbox/Givebutter campaign link builders) — already aligned with `PAYMENT_FRICTION.md`.
3. **Educate donors once:** "Use the same email on checkout; if you see **Link**, sign in — your card may already be saved from another site."
4. **Do not ship** extension, webview injection, or Issuing VCN until partnerships or a clearly compliant Issuing program exist.
5. **Partnerships** (LaunchGood referral, nonprofit APIs like Pledge) remain the only path to true one-click on arbitrary campaigns.

---

## Platform payment stack matrix (research findings)

Public sources do **not** expose a per-merchant "Link enabled: yes/no" flag. Status below is **inferred** from processor relationships and product docs.

| Platform | Donor checkout processor | Stripe used? | Stripe Link likely on donor checkout? | Notes |
|----------|-------------------------|--------------|--------------------------------------|-------|
| **GoFundMe** | **Adyen** and **Stripe** (dual; organizer payout partner varies) | Yes (Connect, NA expansion per [Stripe newsroom](https://stripe.com/newsroom/news/gofundme)) | **Uncertain / partial** | Consumer donate UI may run on Adyen in many regions ([Adyen press](https://www.adyen.com/press-and-media/adyen-for-platforms-simplifies-the-payments-value-chain-for-platforms)). Link only applies where checkout is Stripe **and** Link is enabled on that Stripe account. |
| **LaunchGood** | LaunchGood / payment partners (not merchant-branded Stripe) | Not for donor-facing checkout | **No** | 2.9% + $0.30 card pricing; [support](https://support.launchgood.com/support/solutions/articles/35000182910-what-payment-methods-can-i-use-to-donate-) describes LG-processed cards, ACH, Apple/Google Pay — not "pay with Stripe Link." |
| **Fundly** | **SignUpGenius Donations → Stripe** | Yes | **Likely yes** on successor product | Fundly campaigns closed Dec 2025; donations moved to [SignUpGenius Donations (Stripe)](https://donations.signupgenius.com/). |
| **Givebutter** | **Dedicated Stripe Express** (Givebutter-owned) | Yes | **Likely yes** | Cannot connect your own Stripe account; [Givebutter FAQ](https://givebutter.com/nonprofit-payment-processing) — Link typically appears on Stripe Payment Element when enabled in Dashboard. |
| **JustGiving** | Mixed (platform + charity integrations; Stripe cited for some flows) | Partial | **Unknown** | Charity-dependent; no public evidence of Link on all consumer checkouts. |
| **Donorbox** | Org's Stripe (OmniGive forms) | Yes | **Yes (OmniGive)** | [Donorbox blog](https://donorbox.org/nonprofit-blog/collect-stripe-link-donations): Link on OmniGive forms when org uses Stripe. Not a magic auth URL from GiveFund. |

**Implication:** The premise "all our platforms use Stripe, therefore one Link signup covers all" is **false** for LaunchGood and **only partially true** for GoFundMe.

---

## Angle 1 — Stripe Link as the shared card layer

### How it works technically

**Stripe Link** is Stripe's cross-merchant saved checkout identity (wallet), not a portable `payment_method` ID you can send to GoFundMe's API.

1. Donor enrolls in Link on **any Link-enabled business** (email + OTP; card stored by Stripe).
2. On a **different** Link-enabled business, Stripe's Payment Element / Link UI recognizes the email and offers one-tap fill after OTP (device/session dependent).
3. Stripe documents: *"You can autofill information for any logged-in customer already using Link, **regardless of whether they initially saved their information in Link with another business**."* ([Payment Element + Link](https://docs.stripe.com/payments/link/payment-element-link))
4. **Triggering autofill:** Recommended integration passes `defaultValues.billingDetails.email` into the Payment Element; alternatively donor types email in the Element and Link login/signup UI appears. Prefill tool can detect email elsewhere on the page (session-only, not cookie-stored until consent).
5. **Merchant opt-in:** Link is configured per Stripe account (Dashboard: Settings → Payment methods → Link). Merchants using Payment Element get Link in the card flow by default; domain registration required for live mode.
6. **What Link is not:** It does **not** export a reusable card token to GiveFund that GiveFund can charge on GoFundMe's Connect account. Settlement always happens on the **merchant of record** for that checkout (GoFundMe, Givebutter, etc.).

**GiveFund implementation (if pursued):**

- Stripe Checkout or Payment Element on GiveFund with Link enabled.
- Collect email early (account-less donor profile) → pass to Element.
- Optional: small "save my card for faster giving" copy pointing to Link, not GiveFund vaulting PANs.

### If GiveFund collects email + card via Stripe Checkout with Link — does card autofill on GoFundMe next time?

**Sometimes, not guaranteed.**

- **Yes (best case):** Donor used the **same email**, GoFundMe's donate flow uses **Stripe** (not Adyen) with **Link enabled**, donor completes Link OTP on GoFundMe → card fields prefilled.
- **No:** GoFundMe serves **Adyen** checkout, Link absent, donor uses different email, Link disabled on GFM's Stripe account, or region/product path without Link.
- **GiveFund saving card does not create a shared credential on GoFundMe's servers** — only a Link identity Stripe recognizes on other Link-enabled Stripe checkouts.

### Donor experience if it works (steps saved)

Typical GoFundMe/LaunchGood flow today: land on donate → amount → (account/login) → name/email → card → 3DS → confirm.

With Link on a **compatible** Stripe checkout:

| Step | Without Link | With Link (returning) |
|------|--------------|------------------------|
| Amount / intent | Required | Required |
| Platform account | Often required / prompted | Often still required |
| Name / billing | Manual | Partially prefilled |
| Card PAN/exp/CVC | Manual | **Skipped** (Link autofill) |
| Link OTP | — | **+1 step** (SMS/email OTP) |
| 3DS | Sometimes | Sometimes |

**Net savings:** ~1–2 minutes and 8–16 keystrokes on card entry — meaningful but **not** "click Give Now on GiveFund and done."

### Can GoFundMe or LaunchGood block this?

| Actor | Can they block? | How |
|-------|-----------------|-----|
| **Stripe / Link** | N/A — feature Stripe offers to merchants | — |
| **GoFundMe** | Indirectly | Disable Link in Dashboard; route more traffic to Adyen; add friction (force account before payment). |
| **LaunchGood** | N/A for Link | Does not use donor-facing Stripe Link. |
| **GiveFund** | — | Cannot force Link on third-party pages. |

GoFundMe **cannot** block a donor who legitimately uses Link on GFM's own checkout. They **can** block GiveFund if GiveFund violates ToS (scraping, automation) — separate from Link.

### Assessment — Angle 1

| Dimension | Rating |
|-----------|--------|
| Technical feasibility | **High** on GiveFund; **partial** cross-platform |
| Legal/ToS risk | **Clean** (standard Stripe integration; no circumvention) |
| Platform block risk | **Low** for Link itself; **medium** if bundled with scrapers/automation |
| Build complexity | **Days–weeks** (Checkout + Link + donor email capture) |
| **Recommendation** | **Pursue now** — implement on GiveFund; set messaging expectations; measure Link appearance on outbound platforms via manual QA matrix |

**Do not market as:** "Save card on GiveFund, auto-pay GoFundMe."  
**Do market as:** "Save once with Link — works on many sites that show Link at checkout."

---

## Angle 2 — Browser extension autofill

### Proposed design

1. Donor saves card once on GiveFund (or extension vault).
2. Extension matches donate URLs (`gofundme.com/*/donate`, `launchgood.com/.../donate`, etc.).
3. Content script fills amount, name, email, card fields.

### Legal / ToS

| Topic | Finding |
|-------|---------|
| **Password managers (1Password, Bitwarden, LastPass)** | User-operated tools filling **user's own** credentials; generally lawful; PCI scope stays with user/device. GiveFund **building and distributing** an extension that automates **third-party** checkout is different: facilitation + brand risk. |
| **GoFundMe ToS** | Prohibits *"bots, automated scripts, software, or any other method not expressly authorized"* and *"scraping or similar data gathering"* ([Terms](https://www.gofundme.com/c/terms)). Autofill on donate pages is **legally gray for the user**, **red for GiveFund as publisher** of the extension. |
| **LaunchGood** | Similar automation restrictions likely; no public "extension OK" policy found. |
| **PCI** | Storing **raw PAN** in extension storage → GiveFund likely in scope (SAQ D / significant compliance). Storing **only** `pm_xxx` PaymentMethod ID → **useless** on non-Stripe pages (GoFundMe Adyen, LaunchGood). |
| **Chrome Web Store policy** | Broad host permissions + payment autofill → review scrutiny, limited permissions (`activeTab` + user gesture) reduce reach. |

### Can platforms block extension autofill?

| Mechanism | Effect |
|-----------|--------|
| **Cross-origin iframes** (Stripe Elements, Adyen secured fields) | Content script **cannot** read/write PAN inside isolated iframe — industry standard. |
| **CSP, field `autocomplete="off"`, shadow DOM** | Breaks naive autofill |
| **Checkout redesign** | Breaks selectors overnight |
| **ToS enforcement** | Account bans (rare for password managers; higher risk if tied to GiveFund brand) |

### Manifest V3 — is it still possible?

**Yes, with limits.**

- Inject via `chrome.scripting.executeScript` + `activeTab` / host permissions ([Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)).
- `all_frames: true` can target `https://js.stripe.com/v3/elements-inner-card*` in **dev** contexts; production autofill into Stripe iframes is fragile and may violate Stripe's expectations for card data entry.
- MV3 service worker replaces background page; storage via `chrome.storage.local` encrypted optional.

### Build sketch

```
manifest.json (MV3)
  permissions: storage, scripting, activeTab
  optional_host_permissions: https://*.gofundme.com/*, https://*.launchgood.com/*
background service worker: match URL patterns, badge
content script (on click or auto): query DOM for input[name=...], dispatch input events
popup: "Fill donation" — never store PAN in plaintext; prefer OS keychain
```

**PaymentMethod ID in extension:** Does **not** avoid PCI if you never had PAN; also **does not work** on Adyen/LaunchGood native forms.

### Assessment — Angle 2

| Dimension | Rating |
|-----------|--------|
| Technical feasibility | **Partial** (non-iframe fields only) |
| Legal/ToS risk | **Red** if GiveFund ships; **gray** if user uses generic password manager |
| Platform block risk | **High** (DOM + iframe barriers + ToS) |
| Build complexity | **Months** + ongoing breakage |
| **Recommendation** | **Skip** as GiveFund product; optionally document "use Bitwarden/1Password" in FAQ |

---

## Angle 3 — Stripe Issuing virtual card per donation

### Concept

Fund a **single-use virtual Visa** from donor's saved payment method; donor copies PAN into platform checkout or adds to Apple/Google Wallet.

### Stripe Issuing — access and cost

| Item | Detail |
|------|--------|
| **Eligibility** | US businesses can self-serve per [Stripe blog](https://stripe.com/blog/issuing-self-serve); docs still say [contact sales](https://stripe.com/contact/baas) for program design. Use case must fit **commercial prepaid / B2B spend**, not disguised consumer money transmission. |
| **Fees** | ~**$0.10/virtual card**; **$3.50** physical; **0.2% + $0.20** per auth after promo volume ([pricing](https://stripe.com/pricing)) + interchange pass-through |
| **Controls** | `spending_limits` per auth/day/month; `allowed_categories` / `blocked_categories`; `blocked_card_presences`; merchant ID allowlists **private preview** ([spending controls](https://docs.stripe.com/issuing/controls/spending-controls)). Real-time auth webhooks can decline by merchant — **approximates** single-merchant lock, not always exact MCC match. |
| **Apple / Google Wallet** | Stripe Issuing supports [digital wallet provisioning](https://stripe.com/issuing) for virtual/physical cards. |
| **GoFundMe fraud** | Many single-use VCNs from one Issuing BIN may trigger **issuer/MCC/velocity** rules on GFM or card networks — **medium–high risk** of declines or holds. |
| **Regulatory** | Stripe holds issuing licenses; GiveFund runs a **card program** with KYC, dispute, fraud, and marketing compliance — **heavy** even if GiveFund is not a state money transmitter. Funding VCN from donor card → **looks like pass-through** to regulators if marketed as "pay any fundraiser through GiveFund card." |

### Assessment — Angle 3

| Dimension | Rating |
|-----------|--------|
| Technical feasibility | **High** (APIs mature) |
| Legal/ToS risk | **Gray** — program compliance + pass-through perception |
| Platform block risk | **Medium–high** (fraud, BIN blocking) |
| Build complexity | **Months** + Stripe Issuing approval + ops |
| **Recommendation** | **Explore** with Stripe solutions team; **do not** ship as MVP; wrong fit for "aggregator referral" positioning |

---

## Angle 4 — Webview with injected credentials (mobile)

### Technical reality

| Surface | Injectable? |
|---------|-------------|
| Same-origin HTML inputs (amount, name, email) | **Often yes** (WKWebView `evaluateJavaScript`, Android `evaluateJavascript`) |
| **Stripe Elements / Adyen secured fields** (cross-origin iframe) | **No** — SOP blocks parent page JS from touching card PAN |
| **Apple Pay / Google Pay buttons** | **No** injection |

### ToS / legal

Same as extension: automating third-party checkout without authorization → **red**. App Store review may flag credential injection into third-party financial flows.

### Precedent at scale

Coupon/shopping assistants (Honey) inject **codes**, not PCI fields. Neobank **browser extensions** for **their own** checkout. No credible public example of a mainstream app **injecting PAN into GoFundMe's webview** at scale without partnership.

### Assessment — Angle 4

| Dimension | Rating |
|-----------|--------|
| Technical feasibility | **Low** for card; **medium** for non-PCI fields |
| Legal/ToS risk | **Red** |
| Platform block risk | **High** |
| Build complexity | **Months** |
| **Recommendation** | **Skip** |

---

## Angle 5 — Email-triggered / tokenized checkout links

### What exists

| Platform | Pre-auth / magic donate URL? | What exists instead |
|----------|------------------------------|---------------------|
| **GoFundMe** | **No public donor auth token URL** found | `/donate` deep link; donor must complete GFM checkout |
| **LaunchGood** | **No** | `/donate` deep link; saved payment on **LaunchGood account** for challenges/recurring |
| **Fundly / SignUpGenius** | **No** | Stripe checkout; donors need not create SUG account ([payments FAQ](https://www.signupgenius.com/payments)) |
| **Givebutter** | **No** magic link from external email | Contacts API / Zapier; internal saved donors on Givebutter |
| **Donorbox** | **No session token for returning donor** | Pre-filled **amount** via link builder; post-donation redirect query params (`amount`, `email`, etc.) — **after** payment, not before |
| **FundraisingBox** | Prepopulation via GET params (`fundraiser_email`, `goal`, …) | Form prepopulation, not payment auth ([docs](https://developer.fundraisingbox.com/reference/prepopulation-for-fundraising-pages)) |
| **Givebutter / Donorbox "magic"** | Partner-only or org-dashboard features | Not available to GiveFund as third-party referrer |

### GiveFund action

- Continue **`buildDonateUrl`** patterns (`PAYMENT_FRICTION.md`).
- Add UTM parameters for partnership analytics.
- For Donorbox/Givebutter campaigns in catalog: link to org-generated prefilled campaign URLs when available.

### Assessment — Angle 5

| Dimension | Rating |
|-----------|--------|
| Technical feasibility | **High** (links only) |
| Legal/ToS risk | **Clean** |
| Platform block risk | **None** |
| Build complexity | **Days** |
| **Recommendation** | **Pursue now** (already partly shipped) |

---

## Cross-cutting: what GiveFund must never do

1. **Charge a GoFundMe campaign via GiveFund's Stripe** without GFM as merchant of record / Connect arrangement.
2. **Store raw card numbers** in GiveFund DB, extension, or mobile app.
3. **Pool donations** then disburse (money transmitter / charitable solicitation risk).
4. **Scrape payment credentials** or bypass platform login walls.
5. **Imply GiveFund processed the donation** when the donor left the site.

---

## Ranked recommendation — fastest path to near-seamless giving

### Tier A — Ship now (weeks, clean)

1. **Stripe Checkout + Link on GiveFund** for any future GiveFund-collected payments (tips, featured giving, nonprofit pilots).
2. **Deep links + honest copy** (done / extend UTM).
3. **Donor education:** Link explainer on FAQ — same email, look for Link on checkout.

### Tier B — Explore (months, partnership or compliance)

4. **LaunchGood / GoFundMe partnership** — referred donor SSO or embedded widget (only true one-click).
5. **Pledge / Donorbox** for nonprofit subset ([PLEDGE_RESEARCH.md](./PLEDGE_RESEARCH.md)).
6. **Stripe Issuing** only if legal/compliance signs off on program positioning (e.g. corporate matching, not consumer passthrough).

### Tier C — Skip

7. GiveFund-branded **browser extension** with card autofill.
8. **Webview credential injection** on mobile.
9. Marketing Issuing VCN as "paste card into GoFundMe" without fraud/ops readiness.

### Combined strategy sentence

**Implement Stripe Link on GiveFund to seed the only standards-based cross-merchant wallet that exists today; aggressively optimize outbound deep links; pursue platform partnerships for true one-click; treat extension, webview injection, and Issuing VCN as high-risk distractions unless the business model changes.**

---

## Sources (non-exhaustive)

- [Stripe Link — Payment Element](https://docs.stripe.com/payments/link/payment-element-link)
- [Stripe Issuing — spending controls](https://docs.stripe.com/issuing/controls/spending-controls)
- [Stripe Issuing pricing](https://stripe.com/pricing)
- [GoFundMe Terms of Service](https://www.gofundme.com/c/terms)
- [GoFundMe + Stripe (newsroom)](https://stripe.com/newsroom/news/gofundme)
- [GoFundMe + Adyen (press)](https://www.adyen.com/press-and-media/adyen-for-platforms-simplifies-the-payments-value-chain-for-platforms)
- [LaunchGood — payment methods](https://support.launchgood.com/support/solutions/articles/35000182910-what-payment-methods-can-i-use-to-donate-)
- [SignUpGenius Donations — Stripe](https://donations.signupgenius.com/)
- [Givebutter — Stripe Express](https://givebutter.com/nonprofit-payment-processing)
- [Donorbox — Stripe Link](https://donorbox.org/nonprofit-blog/collect-stripe-link-donations)
- [Chrome Extensions — content scripts (MV3)](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)

---

*This document is research opinion based on public documentation as of May 2026. Payment stacks change; validate with live checkout inspection and Stripe/legal counsel before shipping.*
