# 🔗 utm-builder — Bulk UTM Link Generator for Marketers

**Stop building UTM links one at a time.**

`utm-builder` is a fast, no-BS command-line tool that bulk-generates UTM-tagged URLs from a CSV file in seconds. Validate naming conventions, audit existing links for tracking gaps, and save reusable campaign templates — all from your terminal.

---

## The Problem

Every marketer knows the pain:

- Google's UTM Builder does **one URL at a time** ❌
- You have 40 URLs to tag for Monday's campaign launch ❌
- Half your team writes `utm_source=Facebook`, the other half writes `facebook` ❌
- You can't tell if your last 3 months of links were even properly tagged ❌

One campaign = 30–60 minutes of manual copy-paste. Every. Single. Time.

**utm-builder turns that into 30 seconds.**

---

## Features

| Feature | Description |
|---|---|
| **Bulk generate** | Process 1 to 10,000 URLs from a CSV in one command |
| **Auto-normalize** | Lowercases values, replaces spaces with underscores, standardizes names |
| **Validation** | Warns about missing required params, non-standard sources/mediums |
| **Audit mode** | Scores your existing URL list for UTM completeness (0–100) |
| **Templates** | Save & reuse campaign configs (never retype the same values) |
| **Quick mode** | Generate a single URL interactively or via flags |
| **CSV output** | Clean output ready for Google Sheets, Notion, or your tracker |

---

## Quick Start

**Requirements:** Python 3.7+ (no pip installs needed — pure stdlib)

```bash
# 1. Download utm_builder.py

# 2. Generate a sample CSV to see the format
python utm_builder.py sample

# 3. Bulk generate UTM links
python utm_builder.py generate -i sample_urls.csv -o tagged.csv

# 4. Done! Open tagged.csv — all your URLs are tagged
```

---

## Commands

### `generate` — Bulk UTM Generation

```bash
python utm_builder.py generate -i urls.csv -o tagged_urls.csv
```

**Input CSV format** (minimum required columns):

```
name,url,source,medium,campaign,content,term
Homepage Email,https://example.com,email,newsletter,spring_2026,footer_cta,
Pricing Facebook,https://example.com/pricing,facebook,social,q2_promo,carousel,,
Blog Twitter,https://example.com/blog,twitter,social,content_2026,,
```

**Output CSV** includes:
- Original URL
- Fully tagged UTM URL
- All individual UTM values
- Warnings (capitalization issues, missing params, non-standard values)

**Options:**
```bash
# Use default values when CSV columns are empty
python utm_builder.py generate -i urls.csv --default-source email --default-medium newsletter

# Load defaults from a saved template
python utm_builder.py generate -i urls.csv --template q2_email

# Skip normalization (preserve original casing)
python utm_builder.py generate -i urls.csv --no-normalize

# Show all warnings inline
python utm_builder.py generate -i urls.csv -v
```

---

### `quick` — Single URL Generator

```bash
# Interactive (prompts you for values)
python utm_builder.py quick

# With flags (great for scripts/aliases)
python utm_builder.py quick \
  --url https://example.com/pricing \
  --source linkedin \
  --medium social \
  --campaign q2_launch \
  --content hero_cta \
  --copy   # copies result to clipboard!
```

---

### `audit` — Audit Existing URLs

Find out how many of your URLs are properly tagged — great for auditing a site or campaign archive.

```bash
# Audit from CSV (with 'url' column)
python utm_builder.py audit -i existing_links.csv -o audit_report.csv

# Audit from a plain text file (one URL per line)
python utm_builder.py audit -i urls.txt -o report.csv

# Show warnings inline
python utm_builder.py audit -i urls.csv -v
```

**Output includes:**
- ✓ / ⚠ / ✗ status per URL
- Which UTM params are missing
- Per-URL score (0–100)
- Overall attribution grade (A–F)

**Example output:**
```
Auditing 8 URLs...

  ✓ https://example.com?utm_source=email&utm_medium=...
      Score: 95/100
  ⚠ https://example.com/blog?utm_source=Twitter&utm_medium=Social...
      Score: 90/100 (2 warnings)
  ✗ https://example.com/pricing
      No UTM parameters

────────────────────────────────────────────
  AUDIT SUMMARY
────────────────────────────────────────────
  Total URLs:       8
  Fully tagged:     5
  Incomplete UTMs:  1
  No UTM params:    2
  Average score:    67/100
  Attribution grade: C — Fair, significant gaps
```

---

### `template` — Campaign Templates

Stop retyping the same source/medium/campaign values for every campaign.

```bash
# Save a template
python utm_builder.py template --save q2_email \
  --source email --medium newsletter --campaign q2_promo_2026

# List all templates
python utm_builder.py template --list

# Use a template in generate
python utm_builder.py generate -i my_urls.csv --template q2_email

# Delete a template
python utm_builder.py template --delete q2_email
```

Templates are saved to `~/.utm_builder/templates.json`.

---

### `sample` — Generate Sample CSV

```bash
python utm_builder.py sample
python utm_builder.py sample -o my_template.csv
```

---

## Real-World Workflow

**Scenario:** You're running a 3-channel launch campaign (email, Facebook, LinkedIn) across 8 landing pages.

Without `utm-builder`: Build 24 URLs one at a time in Google's UTM builder = ~25 minutes.

With `utm-builder`:
```bash
# 1. Prep your CSV (5 min in Google Sheets)
# 2. Run:
python utm_builder.py generate -i launch_urls.csv -o launch_tagged.csv
# 3. Done. All 24 URLs tagged, validated, and in a clean CSV. Total: 30 seconds.
```

**Time saved: ~24 minutes, every campaign.**

---

## Normalization Rules

When normalization is enabled (default), `utm-builder` automatically:
- Converts values to **lowercase** (`Facebook` → `facebook`)
- Replaces **spaces with underscores** (`Q2 Promo` → `q2_promo`)
- Strips leading/trailing whitespace

This ensures consistent naming so your GA4 reports don't split `facebook` and `Facebook` into separate channels.

---

## Who This Is For

- **Digital marketers** running multi-channel campaigns
- **Content marketers** tracking blog/social link performance
- **PPC/SEM specialists** tagging ad landing pages
- **Marketing agencies** managing UTMs across multiple clients
- **Email marketers** with complex link lists

---

## UTM Best Practices (Included Validation)

`utm-builder` warns you about violations of these standards:
1. **Always lowercase** — GA4 is case-sensitive; `Email` and `email` are different channels
2. **No spaces** — use underscores or hyphens
3. **Required params** — always include `utm_source`, `utm_medium`, `utm_campaign`
4. **Consistent naming** — use the same value everywhere (`facebook` not `fb`)
5. **Meaningful campaigns** — use dates or themes (`spring_2026` not `campaign1`)

---

## License

Single-user license. For personal and commercial use by the purchaser. Not for redistribution or resale.

---

*utm-builder v1.0.0 — Built for marketers who have better things to do than building UTM links manually.*
