#!/usr/bin/env python3
"""
utm-builder: Bulk UTM Link Generator for Marketers
Version 1.0.0

Stop building UTM links one at a time. Generate, validate, and audit
hundreds of UTM-tagged URLs from the command line in seconds.

Usage:
    python utm_builder.py generate -i urls.csv -o tagged_urls.csv
    python utm_builder.py quick --url https://example.com --source email --medium newsletter --campaign launch
    python utm_builder.py audit -i urls_to_check.csv
    python utm_builder.py template --save my_campaign
    python utm_builder.py template --list

License: Single-user license. Not for redistribution.
"""

import csv
import json
import os
import sys
import argparse
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, quote
from datetime import datetime
from pathlib import Path

# Fix Windows Unicode output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ─────────────────────────────────────────────
# COLORS for terminal output
# ─────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"

def supports_color():
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

def c(color, text):
    if supports_color():
        return f"{color}{text}{C.RESET}"
    return text

# ─────────────────────────────────────────────
# CONFIG & TEMPLATES
# ─────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".utm_builder"
TEMPLATES_FILE = CONFIG_DIR / "templates.json"

def ensure_config_dir():
    CONFIG_DIR.mkdir(exist_ok=True)
    if not TEMPLATES_FILE.exists():
        TEMPLATES_FILE.write_text(json.dumps({}, indent=2))

def load_templates():
    ensure_config_dir()
    return json.loads(TEMPLATES_FILE.read_text())

def save_templates(templates):
    ensure_config_dir()
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=2))

# ─────────────────────────────────────────────
# CORE UTM LOGIC
# ─────────────────────────────────────────────
UTM_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]
REQUIRED_PARAMS = ["utm_source", "utm_medium", "utm_campaign"]

COMMON_SOURCES = {
    "google", "facebook", "twitter", "linkedin", "instagram", "youtube",
    "email", "newsletter", "direct", "organic", "referral", "reddit",
    "bing", "tiktok", "pinterest", "snapchat", "quora"
}
COMMON_MEDIUMS = {
    "cpc", "cpm", "email", "social", "organic", "referral", "display",
    "banner", "affiliate", "video", "push", "sms", "newsletter", "paid",
    "earned", "owned"
}

def normalize_utm_value(value: str) -> str:
    """Normalize a UTM value: lowercase, replace spaces with underscores, strip."""
    if not value:
        return value
    return value.strip().lower().replace(" ", "_").replace("-", "_")

def validate_utm_value(param: str, value: str) -> list:
    """Return list of warnings for a UTM value."""
    warnings = []
    if not value:
        if param in REQUIRED_PARAMS:
            warnings.append(f"MISSING required parameter: {param}")
        return warnings

    if value != value.lower():
        warnings.append(f"{param}='{value}' has uppercase — recommend lowercase")
    if " " in value:
        warnings.append(f"{param}='{value}' has spaces — recommend underscores")
    if len(value) > 100:
        warnings.append(f"{param} value is very long ({len(value)} chars)")

    if param == "utm_source" and value.lower() not in COMMON_SOURCES:
        warnings.append(f"utm_source='{value}' is non-standard (common: {', '.join(sorted(COMMON_SOURCES)[:5])}...)")
    if param == "utm_medium" and value.lower() not in COMMON_MEDIUMS:
        warnings.append(f"utm_medium='{value}' is non-standard (common: {', '.join(sorted(COMMON_MEDIUMS)[:5])}...)")

    return warnings

def build_utm_url(base_url: str, source: str, medium: str, campaign: str,
                  content: str = "", term: str = "", normalize: bool = True) -> dict:
    """
    Build a UTM-tagged URL. Returns dict with url, warnings, and metadata.
    """
    result = {"original_url": base_url, "warnings": [], "error": None, "utm_url": ""}

    # Validate base URL
    try:
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = "https://" + base_url
            parsed = urlparse(base_url)
        if not parsed.netloc:
            result["error"] = f"Invalid URL: {base_url}"
            return result
    except Exception as e:
        result["error"] = str(e)
        return result

    # Normalize values
    params = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
    }
    if content:
        params["utm_content"] = content
    if term:
        params["utm_term"] = term

    if normalize:
        params = {k: normalize_utm_value(v) for k, v in params.items() if v}

    # Collect warnings
    for param, value in params.items():
        result["warnings"].extend(validate_utm_value(param, value))

    # Check for missing required
    for req in REQUIRED_PARAMS:
        if req not in params or not params[req]:
            result["warnings"].append(f"Missing required: {req}")

    # Build the URL
    # Preserve existing query params and add UTM params
    existing_qs = parse_qs(parsed.query, keep_blank_values=True)
    # Remove any existing UTM params (we'll override them)
    for utm in UTM_PARAMS:
        existing_qs.pop(utm, None)

    # Flatten existing params
    flat_qs = {k: v[0] for k, v in existing_qs.items()}
    # Merge UTM params
    flat_qs.update(params)

    new_query = urlencode(flat_qs)
    new_parsed = parsed._replace(query=new_query)
    result["utm_url"] = urlunparse(new_parsed)

    return result

def audit_url(url: str) -> dict:
    """Audit a URL for UTM parameters and return a report."""
    result = {
        "url": url,
        "has_utm": False,
        "utm_params": {},
        "missing_required": [],
        "warnings": [],
        "score": 0
    }

    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)

        utm_found = {}
        for param in UTM_PARAMS:
            if param in qs:
                utm_found[param] = qs[param][0]

        result["utm_params"] = utm_found
        result["has_utm"] = len(utm_found) > 0

        for param, value in utm_found.items():
            result["warnings"].extend(validate_utm_value(param, value))

        for req in REQUIRED_PARAMS:
            if req not in utm_found:
                result["missing_required"].append(req)

        # Score: 0-100
        score = 0
        if utm_found.get("utm_source"): score += 35
        if utm_found.get("utm_medium"): score += 35
        if utm_found.get("utm_campaign"): score += 20
        if utm_found.get("utm_content"): score += 5
        if utm_found.get("utm_term"): score += 5
        result["score"] = score

    except Exception as e:
        result["warnings"].append(f"Parse error: {e}")

    return result

# ─────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────
def cmd_generate(args):
    """Bulk generate UTM URLs from a CSV file."""
    input_file = args.input
    output_file = args.output or input_file.replace(".csv", "_utm_tagged.csv")
    normalize = not args.no_normalize

    print(c(C.CYAN, f"\n🔗 utm-builder — Bulk UTM Generator"))
    print(c(C.GRAY, f"   Input:  {input_file}"))
    print(c(C.GRAY, f"   Output: {output_file}"))
    print(c(C.GRAY, f"   Normalize: {normalize}\n"))

    if not os.path.exists(input_file):
        print(c(C.RED, f"✗ File not found: {input_file}"))
        print(c(C.YELLOW, "\nExpected CSV columns: url, source, medium, campaign, [content], [term]"))
        print(c(C.YELLOW, "Run: python utm_builder.py sample  to generate a sample CSV"))
        sys.exit(1)

    rows = []
    errors = 0
    warnings_total = 0

    try:
        with open(input_file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            # Normalize column names
            col_map = {col.strip().lower().replace(" ", "_"): col for col in fieldnames}

            required_cols = {"url", "source", "medium", "campaign"}
            found_cols = set(col_map.keys())

            # Check for required columns
            missing = required_cols - found_cols
            if missing:
                print(c(C.RED, f"✗ Missing required CSV columns: {', '.join(missing)}"))
                print(c(C.YELLOW, f"Found columns: {', '.join(fieldnames)}"))
                print(c(C.YELLOW, "Required: url, source, medium, campaign"))
                print(c(C.YELLOW, "Optional: content, term, name (row label)"))
                sys.exit(1)

            input_rows = list(reader)

    except Exception as e:
        print(c(C.RED, f"✗ Error reading CSV: {e}"))
        sys.exit(1)

    print(c(C.BOLD, f"Processing {len(input_rows)} URLs...\n"))

    output_rows = []
    for i, row in enumerate(input_rows, 1):
        # Get values using flexible column matching
        def get(key):
            for k, orig in col_map.items():
                if k == key:
                    return row.get(orig, "").strip()
            return ""

        url     = get("url")
        source  = get("source") or args.default_source
        medium  = get("medium") or args.default_medium
        campaign = get("campaign") or args.default_campaign
        content = get("content") or args.default_content
        term    = get("term")
        name    = get("name") or get("label") or f"Row {i}"

        if not url:
            print(c(C.YELLOW, f"  ⚠ Row {i}: Empty URL, skipping"))
            continue

        result = build_utm_url(url, source, medium, campaign, content, term, normalize)

        status = c(C.GREEN, "✓") if not result["error"] else c(C.RED, "✗")
        warn_count = len(result["warnings"])

        if result["error"]:
            print(f"  {status} [{i:03d}] {name}: {c(C.RED, result['error'])}")
            errors += 1
        else:
            warn_str = c(C.YELLOW, f" ({warn_count} warnings)") if warn_count else ""
            short_url = result["utm_url"][:70] + "..." if len(result["utm_url"]) > 70 else result["utm_url"]
            print(f"  {status} [{i:03d}] {name}: {c(C.GRAY, short_url)}{warn_str}")
            warnings_total += warn_count

            if args.verbose and result["warnings"]:
                for w in result["warnings"]:
                    print(c(C.YELLOW, f"       ⚠ {w}"))

        output_rows.append({
            "name":         name,
            "original_url": result["original_url"],
            "utm_url":      result["utm_url"] if not result["error"] else "ERROR",
            "utm_source":   source if normalize else source,
            "utm_medium":   medium if normalize else medium,
            "utm_campaign": campaign if normalize else campaign,
            "utm_content":  content,
            "utm_term":     term,
            "warnings":     "; ".join(result["warnings"]),
            "error":        result["error"] or "",
        })

    # Write output CSV
    if output_rows:
        with open(output_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
            writer.writeheader()
            writer.writerows(output_rows)

    success = len(output_rows) - errors
    print(f"\n{c(C.BOLD, '─' * 50)}")
    print(f"  {c(C.GREEN, f'✓ {success} URLs tagged successfully')}")
    if errors:
        print(f"  {c(C.RED, f'✗ {errors} errors')}")
    if warnings_total:
        print(f"  {c(C.YELLOW, f'⚠ {warnings_total} warnings (see output CSV)')}")
    print(f"  {c(C.CYAN, f'📄 Output: {output_file}')}")
    print(c(C.BOLD, '─' * 50) + "\n")


def cmd_quick(args):
    """Generate a single UTM URL interactively."""
    url = args.url
    source = args.source
    medium = args.medium
    campaign = args.campaign
    content = args.content or ""
    term = args.term or ""

    # Interactive prompts if not provided
    if not url:
        url = input(c(C.CYAN, "URL to tag: ")).strip()
    if not source:
        source = input(c(C.CYAN, "utm_source (e.g. facebook, email, reddit): ")).strip()
    if not medium:
        medium = input(c(C.CYAN, "utm_medium (e.g. social, cpc, email): ")).strip()
    if not campaign:
        campaign = input(c(C.CYAN, "utm_campaign (e.g. spring_launch_2026): ")).strip()
    if not content:
        content_input = input(c(C.CYAN, "utm_content [optional, press Enter to skip]: ")).strip()
        content = content_input if content_input else ""

    result = build_utm_url(url, source, medium, campaign, content, term, normalize=not args.no_normalize)

    print(f"\n{c(C.BOLD, '─' * 60)}")
    if result["error"]:
        print(c(C.RED, f"✗ Error: {result['error']}"))
    else:
        print(f"{c(C.GREEN, '✓ UTM URL Generated:')}\n")
        print(f"  {c(C.BOLD, result['utm_url'])}\n")
        if result["warnings"]:
            print(c(C.YELLOW, "Warnings:"))
            for w in result["warnings"]:
                print(c(C.YELLOW, f"  ⚠ {w}"))

    if args.copy:
        try:
            import subprocess
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=result["utm_url"].encode())
                print(c(C.GREEN, "\n📋 Copied to clipboard!"))
            elif sys.platform == "win32":
                subprocess.run(["clip"], input=result["utm_url"].encode())
                print(c(C.GREEN, "\n📋 Copied to clipboard!"))
            else:
                subprocess.run(["xclip", "-selection", "clipboard"], input=result["utm_url"].encode())
                print(c(C.GREEN, "\n📋 Copied to clipboard!"))
        except Exception:
            pass

    print(c(C.BOLD, '─' * 60) + "\n")


def cmd_audit(args):
    """Audit URLs for UTM completeness and consistency."""
    input_file = args.input

    print(c(C.CYAN, f"\n🔍 utm-builder — UTM Audit Report"))
    print(c(C.GRAY, f"   Input: {input_file}\n"))

    if not os.path.exists(input_file):
        print(c(C.RED, f"✗ File not found: {input_file}"))
        sys.exit(1)

    urls = []
    try:
        with open(input_file, newline='', encoding='utf-8-sig') as f:
            # Try CSV first, then plain text
            content = f.read()

        # Try to detect if it's CSV or plain text
        if ',' in content and '\n' in content:
            lines = content.strip().split('\n')
            first = lines[0].lower()
            if 'url' in first:
                # Has header
                reader = csv.DictReader(content.splitlines())
                col_map = {col.strip().lower(): col for col in reader.fieldnames or []}
                url_col = col_map.get("url") or col_map.get("urls") or col_map.get("link")
                for row in reader:
                    if url_col and row.get(url_col):
                        urls.append(row[url_col].strip())
            else:
                # Assume first column is URLs
                reader = csv.reader(content.splitlines())
                for row in reader:
                    if row:
                        urls.append(row[0].strip())
        else:
            # Plain text, one URL per line
            urls = [line.strip() for line in content.strip().splitlines() if line.strip()]

    except Exception as e:
        print(c(C.RED, f"✗ Error reading file: {e}"))
        sys.exit(1)

    if not urls:
        print(c(C.YELLOW, "No URLs found in file"))
        sys.exit(0)

    print(c(C.BOLD, f"Auditing {len(urls)} URLs...\n"))

    results = []
    scores = []
    missing_utm = 0
    incomplete = 0

    for url in urls:
        audit = audit_url(url)
        results.append(audit)

        score = audit["score"]
        scores.append(score)

        if not audit["has_utm"]:
            missing_utm += 1
            icon = c(C.RED, "✗")
            msg = "No UTM parameters"
        elif audit["missing_required"]:
            incomplete += 1
            icon = c(C.YELLOW, "⚠")
            missing_str = ", ".join(audit["missing_required"])
            msg = f"Missing: {missing_str}"
        else:
            icon = c(C.GREEN, "✓")
            msg = f"Score: {score}/100"
            if audit["warnings"]:
                msg += c(C.YELLOW, f" ({len(audit['warnings'])} warnings)")

        short_url = url[:55] + "..." if len(url) > 55 else url
        print(f"  {icon} {c(C.GRAY, short_url)}")
        print(f"      {msg}")

        if args.verbose and audit["warnings"]:
            for w in audit["warnings"]:
                print(c(C.YELLOW, f"      ⚠ {w}"))

    # Summary
    avg_score = sum(scores) / len(scores) if scores else 0
    fully_tagged = len(urls) - missing_utm - incomplete

    print(f"\n{c(C.BOLD, '─' * 55)}")
    print(c(C.BOLD, "  AUDIT SUMMARY"))
    print(c(C.BOLD, '─' * 55))
    print(f"  Total URLs:       {len(urls)}")
    print(f"  {c(C.GREEN, f'Fully tagged:     {fully_tagged}')}")
    print(f"  {c(C.YELLOW, f'Incomplete UTMs:  {incomplete}')}")
    print(f"  {c(C.RED, f'No UTM params:    {missing_utm}')}")
    print(f"  Average score:    {avg_score:.0f}/100")

    # Grade
    if avg_score >= 90:
        grade = c(C.GREEN, "A — Excellent attribution!")
    elif avg_score >= 70:
        grade = c(C.CYAN, "B — Good, minor improvements needed")
    elif avg_score >= 50:
        grade = c(C.YELLOW, "C — Fair, significant gaps")
    elif avg_score >= 30:
        grade = c(C.YELLOW, "D — Poor, most links untagged")
    else:
        grade = c(C.RED, "F — No tracking! Flying blind on attribution")

    print(f"  Attribution grade: {grade}")
    print(c(C.BOLD, '─' * 55) + "\n")

    # Write report if requested
    if args.output:
        with open(args.output, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "url", "has_utm", "utm_source", "utm_medium",
                "utm_campaign", "utm_content", "utm_term",
                "missing_required", "warnings", "score"
            ])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "url": r["url"],
                    "has_utm": r["has_utm"],
                    "utm_source": r["utm_params"].get("utm_source", ""),
                    "utm_medium": r["utm_params"].get("utm_medium", ""),
                    "utm_campaign": r["utm_params"].get("utm_campaign", ""),
                    "utm_content": r["utm_params"].get("utm_content", ""),
                    "utm_term": r["utm_params"].get("utm_term", ""),
                    "missing_required": ", ".join(r["missing_required"]),
                    "warnings": "; ".join(r["warnings"]),
                    "score": r["score"]
                })
        print(c(C.CYAN, f"📄 Audit report saved: {args.output}\n"))


def cmd_template(args):
    """Manage UTM campaign templates."""
    templates = load_templates()

    if args.list:
        if not templates:
            print(c(C.YELLOW, "\nNo templates saved yet."))
            print(c(C.GRAY, "Save a template with: python utm_builder.py template --save <name> --source <s> --medium <m> --campaign <c>\n"))
            return
        print(c(C.CYAN, f"\n📋 Saved Templates ({len(templates)}):\n"))
        for name, t in templates.items():
            print(c(C.BOLD, f"  [{name}]"))
            for k, v in t.items():
                if v:
                    print(c(C.GRAY, f"    {k}: {v}"))
            print()

    elif args.save:
        name = args.save
        template = {
            "source":   args.source or "",
            "medium":   args.medium or "",
            "campaign": args.campaign or "",
            "content":  args.content or "",
            "term":     args.term or "",
        }
        templates[name] = template
        save_templates(templates)
        print(c(C.GREEN, f"\n✓ Template '{name}' saved!\n"))
        print(c(C.GRAY, f"  Use it with: python utm_builder.py generate -i urls.csv --template {name}\n"))

    elif args.delete:
        name = args.delete
        if name in templates:
            del templates[name]
            save_templates(templates)
            print(c(C.GREEN, f"\n✓ Template '{name}' deleted.\n"))
        else:
            print(c(C.RED, f"\n✗ Template '{name}' not found.\n"))

    else:
        print(c(C.YELLOW, "Use --list, --save <name>, or --delete <name>"))


def cmd_sample(args):
    """Generate a sample input CSV."""
    output = args.output or "sample_urls.csv"
    rows = [
        {"name": "Homepage - Email Footer", "url": "https://example.com",         "source": "email",    "medium": "newsletter", "campaign": "spring_launch_2026", "content": "footer_cta",  "term": ""},
        {"name": "Pricing Page - Facebook", "url": "https://example.com/pricing", "source": "Facebook", "medium": "Social",     "campaign": "Q2 Promo",           "content": "carousel ad", "term": ""},
        {"name": "Blog Post - Twitter",     "url": "https://example.com/blog/seo-tips", "source": "twitter", "medium": "social", "campaign": "content_2026", "content": "", "term": ""},
        {"name": "Landing Page - Google Ads","url": "https://example.com/lp/offer","source": "google",  "medium": "cpc",        "campaign": "brand_kws",          "content": "headline_v2", "term": "utm builder"},
        {"name": "Product Hunt Launch",     "url": "https://example.com",         "source": "product_hunt", "medium": "referral", "campaign": "ph_launch",        "content": "",            "term": ""},
    ]
    with open(output, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url", "source", "medium", "campaign", "content", "term"])
        writer.writeheader()
        writer.writerows(rows)

    print(c(C.GREEN, f"\n✓ Sample CSV created: {output}"))
    print(c(C.GRAY,  f"\n  It contains 5 example rows with common UTM patterns."))
    print(c(C.GRAY,  f"  Notice rows 2-3 have capitalization issues — run generate to see warnings."))
    print(c(C.CYAN,  f"\n  Next: python utm_builder.py generate -i {output}\n"))


# ─────────────────────────────────────────────
# CLI SETUP
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="utm-builder",
        description=c(C.BOLD, "🔗 utm-builder — Bulk UTM Link Generator for Marketers"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate a sample CSV to get started:
    python utm_builder.py sample

  Bulk generate UTM URLs from a CSV:
    python utm_builder.py generate -i urls.csv -o tagged.csv

  Quick single URL:
    python utm_builder.py quick --url https://example.com --source email --medium newsletter --campaign launch

  Audit existing URLs:
    python utm_builder.py audit -i my_urls.csv -o audit_report.csv

  Save a campaign template:
    python utm_builder.py template --save q2_email --source email --medium newsletter --campaign q2_promo

  List saved templates:
    python utm_builder.py template --list
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- generate ---
    gen = subparsers.add_parser("generate", aliases=["gen", "g"],
                                 help="Bulk generate UTM URLs from a CSV")
    gen.add_argument("-i", "--input", required=True, metavar="FILE",
                     help="Input CSV file (columns: url, source, medium, campaign, [content], [term])")
    gen.add_argument("-o", "--output", metavar="FILE",
                     help="Output CSV file (default: input_utm_tagged.csv)")
    gen.add_argument("--template", metavar="NAME",
                     help="Load defaults from a saved template")
    gen.add_argument("--default-source", default="", metavar="SOURCE",
                     help="Default source if CSV column is empty")
    gen.add_argument("--default-medium", default="", metavar="MEDIUM",
                     help="Default medium if CSV column is empty")
    gen.add_argument("--default-campaign", default="", metavar="CAMPAIGN",
                     help="Default campaign if CSV column is empty")
    gen.add_argument("--default-content", default="", metavar="CONTENT",
                     help="Default content if CSV column is empty")
    gen.add_argument("--no-normalize", action="store_true",
                     help="Skip normalization (don't lowercase/replace spaces)")
    gen.add_argument("-v", "--verbose", action="store_true",
                     help="Show all warnings inline")

    # --- quick ---
    quick = subparsers.add_parser("quick", aliases=["q"],
                                   help="Generate a single UTM URL")
    quick.add_argument("--url", metavar="URL", help="Base URL to tag")
    quick.add_argument("--source", metavar="SOURCE", help="utm_source (e.g. email, facebook)")
    quick.add_argument("--medium", metavar="MEDIUM", help="utm_medium (e.g. newsletter, cpc)")
    quick.add_argument("--campaign", metavar="CAMPAIGN", help="utm_campaign")
    quick.add_argument("--content", metavar="CONTENT", help="utm_content (optional)")
    quick.add_argument("--term", metavar="TERM", help="utm_term (optional)")
    quick.add_argument("--copy", action="store_true", help="Copy result to clipboard")
    quick.add_argument("--no-normalize", action="store_true", help="Skip normalization")

    # --- audit ---
    aud = subparsers.add_parser("audit", aliases=["a"],
                                 help="Audit URLs for UTM completeness")
    aud.add_argument("-i", "--input", required=True, metavar="FILE",
                     help="Input file: CSV with 'url' column, or plain text (one URL per line)")
    aud.add_argument("-o", "--output", metavar="FILE",
                     help="Save audit report to CSV")
    aud.add_argument("-v", "--verbose", action="store_true",
                     help="Show all warnings inline")

    # --- template ---
    tmpl = subparsers.add_parser("template", aliases=["t"],
                                  help="Manage campaign templates")
    tmpl.add_argument("--list", action="store_true", help="List all saved templates")
    tmpl.add_argument("--save", metavar="NAME", help="Save a new template")
    tmpl.add_argument("--delete", metavar="NAME", help="Delete a template")
    tmpl.add_argument("--source", metavar="SOURCE")
    tmpl.add_argument("--medium", metavar="MEDIUM")
    tmpl.add_argument("--campaign", metavar="CAMPAIGN")
    tmpl.add_argument("--content", metavar="CONTENT")
    tmpl.add_argument("--term", metavar="TERM")

    # --- sample ---
    smp = subparsers.add_parser("sample", aliases=["s"],
                                 help="Generate a sample input CSV")
    smp.add_argument("-o", "--output", metavar="FILE",
                     help="Output filename (default: sample_urls.csv)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print(c(C.CYAN, "\n  Quick start: python utm_builder.py sample\n"))
        sys.exit(0)

    cmd = args.command

    if cmd in ("generate", "gen", "g"):
        # Load template defaults if specified
        if hasattr(args, "template") and args.template:
            templates = load_templates()
            if args.template in templates:
                t = templates[args.template]
                if not args.default_source:   args.default_source   = t.get("source", "")
                if not args.default_medium:   args.default_medium   = t.get("medium", "")
                if not args.default_campaign: args.default_campaign = t.get("campaign", "")
                if not args.default_content:  args.default_content  = t.get("content", "")
            else:
                print(c(C.YELLOW, f"⚠ Template '{args.template}' not found, ignoring"))
        cmd_generate(args)

    elif cmd in ("quick", "q"):
        cmd_quick(args)

    elif cmd in ("audit", "a"):
        cmd_audit(args)

    elif cmd in ("template", "t"):
        cmd_template(args)

    elif cmd in ("sample", "s"):
        cmd_sample(args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
