# Pledge API Research — GiveFund

Research date: May 2026. Sources: [Pledge APIs product page](https://www.pledge.to/products/apis), [Pledge developer guides](https://developer.pledge.to/) (docs.pledge.to was unavailable; developer.pledge.to is the live docs host).

## What Pledge Does

Pledge provides **embedded giving** infrastructure for apps and websites:

- **Donation widgets** — embeddable forms (`plg-donate`) with partner key + fundraiser ID, widget ID, or nonprofit **EIN**
- **Donate API** — programmatic donations, including micro-donations aggregated against a partner payment method
- **Fundraiser API** — create/update fundraisers via `POST`, `PATCH`, or `PUT`, then embed donation UI
- **Charity search** — access to a large database of **verified 501(c)(3)** nonprofits
- **Webhooks** — donation lifecycle events to your backend
- **Tax receipts, disbursement tracking, donor data** — handled by Pledge for compliant nonprofit giving

Authentication: `Authorization: Bearer YOUR_API_KEY`. Sandbox is separate from production (contact support for sandbox access per product FAQ).

## How the Donation API Works (High Level)

1. Partner signs up and receives API key + partner key for widgets.
2. You either:
   - **Create an API fundraiser** linked to one or more nonprofit organizations, then embed with `data-partner-key` + `data-item-id`, or
   - **Embed by EIN** with `data-partner-key` + `data-ein` (no pre-created fundraiser), or
   - Use **Impact Hub** fundraisers with `data-widget-id`.
3. Donor completes payment inside Pledge’s hosted form; your app receives `postMessage` (`DonateCompleted`) and/or **webhooks**.
4. Pledge disburses to the nonprofit(s) and issues tax documentation where applicable.

**Fees (from product FAQ):**

- API usage: no charge to use the API
- **Donate API:** 5% platform fee from the donation + payment processing fees
- **Fundraiser API:** optional donor tip model + payment processing fees

## Personal Crowdfunding vs Registered Nonprofits

| Use case | Pledge support |
|----------|----------------|
| Verified 501(c)(3) / registered charities | **Yes** — core product (EIN embed, charity search, nonprofit fundraisers) |
| Partner-created fundraisers for causes | **Yes** — Fundraiser API + embed |
| Arbitrary **individual** GoFundMe-style personal campaigns | **No** — not in Pledge’s model; funds flow to **nonprofits**, not to a private person’s bank account |

GiveFund’s catalog is mostly **personal and peer-to-peer** fundraisers (GoFundMe, LaunchGood personal projects, etc.). Pledge does **not** replace “donate to this person’s GoFundMe” unless that campaign is legally structured as giving to a registered nonprofit (e.g. charity classifier, EIN-backed org).

**Implication:** Pledge is a strong fit for the **nonprofit / charity** slice of GiveFund (e.g. `charity-fundraiser`, GlobalGiving, Donorbox org pages), not for the majority of individual medical/emergency personal campaigns.

## Could GiveFund Collect Payment via Pledge and Route to the Campaign?

**Partially, with major constraints:**

| Scenario | Feasibility |
|----------|-------------|
| Campaign is a **registered nonprofit** with known EIN | Embed `data-ein` or map to a Pledge API fundraiser; payment stays on GiveFund via iframe/widget |
| Campaign is **personal** on GoFundMe/LaunchGood | **Cannot** route proceeds to the individual through Pledge; would still require deep link to the platform |
| “Pass-through” to external GoFundMe URL after Pledge checkout | **Not supported** — Pledge settles to nonprofits in its network, not third-party P2P platforms |

A hybrid product could work:

1. **Detect** `category === charity` or platform nonprofit metadata.
2. **On-site donate** via Pledge when EIN/nonprofit ID is known.
3. **Otherwise** use smart deep links (current approach).

There is no documented API to “donate on Pledge, then forward to GoFundMe slug X.”

## Partnership / API Access Process

From public materials:

1. **Sandbox** — create account at Pledge sandbox; request API key via support (product FAQ: “contact our support team”).
2. **Production** — partner onboarding (Evite, Legacy.com, Price.com style integrations); likely sales/partnerships for volume.
3. **Developer path** — [Getting Started](https://developer.pledge.to/guides/getting-started/), [Creating/Updating Fundraisers](https://developer.pledge.to/guides/creating-updating-fundraisers/), [Donation Form Reference](https://developer.pledge.to/reference/donation-form/).

**Recommended outreach:**

- Email **support** for sandbox API key and clarification on marketplace/aggregator use cases.
- Ask **partnerships** whether a **discovery-only aggregator** (no payment capture) can later graduate to embedded donate for nonprofit rows only.
- Document GiveFund traffic metrics when pitching (see `PAYMENT_FRICTION.md`).

## Recommended Next Step

1. **Short term (now):** Ship smart deep links to platform `/donate` pages — done in `frontend/index.html` (`buildDonateUrl`).
2. **This month:** Apply for **sandbox API access**; prototype embed on one seeded **nonprofit** campaign with known EIN.
3. **If sandbox works:** Add optional “Donate here” Pledge iframe only when `platform` + metadata indicate 501(c)(3); keep deep link as default for personal campaigns.
4. **Do not block** on Pledge for MVP — personal campaigns remain platform deep links.

## References

- https://www.pledge.to/products/apis  
- https://developer.pledge.to/guides/getting-started/  
- https://developer.pledge.to/guides/creating-updating-fundraisers/  
- https://developer.pledge.to/widgets/donation-forms/  
- https://developer.pledge.to/reference/donation-form/  
- https://developer.pledge.to/reference/fundraiser-tracker/  
