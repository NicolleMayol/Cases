#!/usr/bin/env python3.11
"""
Cynet Community Case Scraper v3
================================
Scrapes all cases from the Cynet Community portal where creation/update date is 2026.
Extracts:
  - All table fields (Case Number, Account, Subject, Contact, Severity, Status, Dates)
  - Web Information (Email, Service For, Description, etc.)
  - Full list of emails with their complete body content
  - Files attached to each case

Usage:
  1. Install dependencies:
       pip install playwright
       playwright install chromium
  2. Run: python3.11 cynet_scraper_v3.py
  3. A browser window will open - log in manually to Cynet Community
  4. Press ENTER in the terminal once you're on the case list page
  5. The scraper will automatically process all cases and save to JSON

Output: cynet_cases_2026_complete.json
"""

import asyncio
import json
import re
import sys
import os
from datetime import datetime


OUTPUT_FILE = "cynet_cases_2026_complete.json"
BASE_URL = "https://cynet.my.site.com"
CASE_LIST_URL = f"{BASE_URL}/Community/s/case-list-all-cases"


async def main():
    from playwright.async_api import async_playwright

    # Use persistent context so login state is saved between runs
    user_data_dir = os.path.join(os.path.expanduser("~"), ".cynet_scraper_profile")

    async with async_playwright() as p:
        # Launch browser - HEADED so user can log in
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Navigate to case list
        print("\n" + "=" * 60)
        print("  CYNET COMMUNITY CASE SCRAPER v3")
        print("=" * 60)
        print(f"\n  Navigating to: {CASE_LIST_URL}")
        await page.goto(CASE_LIST_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Check if login is needed
        if "login" in page.url.lower():
            print("\n  ⚠️  LOGIN REQUIRED")
            print("  Please log in to the Cynet Community portal in the browser window.")
            print("  Once you see the case list, come back here.\n")
            input("  >>> Press ENTER when you are logged in and on the case list page... ")
            await page.goto(CASE_LIST_URL, wait_until="domcontentloaded")
            await asyncio.sleep(5)
        else:
            print("  ✅ Already logged in (using saved session)!")
            await asyncio.sleep(3)

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Extract all case URLs from the table (with scrolling)
        # ═══════════════════════════════════════════════════════════════
        print("\n  📋 STEP 1: Loading case list...")

        # Wait for table to load
        try:
            await page.wait_for_selector("table[role='grid'] tbody tr", timeout=30000)
        except:
            print("  ⚠️  Table not found. Make sure you're on the case list page.")
            input("  >>> Press ENTER to retry... ")
            await page.goto(CASE_LIST_URL, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            await page.wait_for_selector("table[role='grid'] tbody tr", timeout=30000)

        await asyncio.sleep(2)

        # Scroll the page to load all rows (infinite scroll)
        previous_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 30

        while scroll_attempts < max_scroll_attempts:
            rows = await page.query_selector_all("table[role='grid'] tbody tr")
            current_count = len(rows)

            if current_count == previous_count and scroll_attempts > 2:
                break

            previous_count = current_count
            scroll_attempts += 1

            # Scroll the page down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)

        print(f"  Found {previous_count} rows in the table")

        # Extract data from all rows
        all_case_data = []
        rows = await page.query_selector_all("table[role='grid'] tbody tr")

        for row in rows:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 8:
                    continue

                cell_texts = []
                for cell in cells:
                    text = await cell.inner_text()
                    cell_texts.append(text.strip())

                # Get case URL
                case_link = await row.query_selector("a[href*='/Community/s/case/']")
                case_url = ""
                if case_link:
                    href = await case_link.get_attribute("href")
                    if href:
                        case_url = f"{BASE_URL}{href}" if href.startswith("/") else href

                # Parse: CaseNumber, Account, Subject, Contact, Severity, Status, LastUpdate, DateOpened
                case_entry = {
                    "case_number": cell_texts[0] if cell_texts[0] else "",
                    "account_name": cell_texts[1] if len(cell_texts) > 1 else "",
                    "subject": cell_texts[2] if len(cell_texts) > 2 else "",
                    "contact_name": cell_texts[3] if len(cell_texts) > 3 else "",
                    "severity": cell_texts[4] if len(cell_texts) > 4 else "",
                    "status": cell_texts[5] if len(cell_texts) > 5 else "",
                    "last_update": cell_texts[6] if len(cell_texts) > 6 else "",
                    "date_opened": cell_texts[7] if len(cell_texts) > 7 else "",
                    "url": case_url,
                }

                # Filter: only 2026 cases
                if "2026" in case_entry.get("last_update", "") or "2026" in case_entry.get("date_opened", ""):
                    all_case_data.append(case_entry)

            except Exception as e:
                continue

        print(f"  ✅ Extracted {len(all_case_data)} cases from 2026\n")

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Visit each case to get full details + emails
        # ═══════════════════════════════════════════════════════════════
        print(f"  📄 STEP 2: Extracting details from each case...")
        print(f"  {'─' * 50}")

        all_cases_complete = []

        for idx, case_entry in enumerate(all_case_data):
            case_url = case_entry.get("url", "")
            if not case_url:
                print(f"  [{idx+1}/{len(all_case_data)}] ⚠️  No URL for case {case_entry.get('case_number')}, skipping")
                all_cases_complete.append(case_entry)
                continue

            print(f"  [{idx+1}/{len(all_case_data)}] Case {case_entry.get('case_number')}...", end="", flush=True)

            try:
                await page.goto(case_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                # Wait for page to fully render
                try:
                    await page.wait_for_selector("text=Case Information", timeout=15000)
                except:
                    await asyncio.sleep(3)

                # Extract case details
                case_detail = await extract_case_detail(page)

                # Get email links
                email_links = await get_email_links(page)

                # Navigate to each email to get full content
                emails_full = []
                for email_url in email_links:
                    try:
                        full_url = f"{BASE_URL}{email_url}" if email_url.startswith("/") else email_url
                        await page.goto(full_url, wait_until="domcontentloaded")
                        await asyncio.sleep(2)

                        try:
                            await page.wait_for_selector("text=Message Content", timeout=10000)
                        except:
                            await asyncio.sleep(2)

                        email_data = await extract_email_detail(page, full_url)
                        emails_full.append(email_data)
                    except Exception as e:
                        emails_full.append({"url": email_url, "error": str(e)})

                # Merge everything
                case_complete = {**case_entry, **case_detail}
                case_complete["emails_full"] = emails_full
                all_cases_complete.append(case_complete)

                email_count = len(emails_full)
                files_count = case_detail.get("files_count", 0)
                print(f" ✅ ({email_count} emails, {files_count} files)")

            except Exception as e:
                print(f" ❌ Error: {str(e)[:60]}")
                case_entry["error"] = str(e)
                all_cases_complete.append(case_entry)

            # Save progress every 5 cases
            if (idx + 1) % 5 == 0:
                save_json(all_cases_complete, OUTPUT_FILE)
                print(f"  💾 Progress saved ({idx+1}/{len(all_case_data)} cases)")

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Save final output
        # ═══════════════════════════════════════════════════════════════
        save_json(all_cases_complete, OUTPUT_FILE)

        # Print summary
        total_emails = sum(len(c.get("emails_full", [])) for c in all_cases_complete)
        cases_with_desc = sum(1 for c in all_cases_complete if c.get("web_information", {}).get("description"))
        cases_with_files = sum(1 for c in all_cases_complete if c.get("files_count", 0) > 0)

        print(f"\n  {'═' * 50}")
        print(f"  ✅ SCRAPING COMPLETE!")
        print(f"  {'═' * 50}")
        print(f"  Total cases scraped:       {len(all_cases_complete)}")
        print(f"  Cases with description:    {cases_with_desc}")
        print(f"  Cases with files:          {cases_with_files}")
        print(f"  Total emails extracted:    {total_emails}")
        print(f"  Output file:               {OUTPUT_FILE}")
        print(f"  {'═' * 50}\n")

        await context.close()


async def extract_case_detail(page):
    """Extract all details from a case detail page"""
    detail = {
        "web_information": {},
        "files": [],
        "files_count": 0,
        "emails_count": 0,
        "emails_metadata": [],
    }

    try:
        # Get full page text
        text = await page.evaluate("() => document.body.innerText")

        # ── Web Information ──
        web_info = {}

        patterns = {
            "web_email": r'Web Email\n(.+?)(?:\n|$)',
            "service_for": r'Service For\n(.+?)(?:\n|$)',
            "account_name": r'Account Name\n(.+?)(?:\n|$)',
            "date_opened": r'Date/Time Opened\n(.+?)(?:\n|$)',
            "date_closed": r'Date/Time Closed\n(.+?)(?:\n|$)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                web_info[key] = match.group(1).strip()

        # Contact Name (avoid "Open X Preview" text)
        match = re.search(r'Contact Name\n(.+?)(?:\n|$)', text)
        if match:
            val = match.group(1).strip()
            if 'Open' not in val and 'Edit' not in val:
                web_info["contact_name"] = val

        # Severity
        match = re.search(r'Severity\s*\n(?:Help Severity\s*\n)?(.+?)(?:\n|$)', text)
        if match:
            val = match.group(1).strip()
            if val in ['Low', 'Medium', 'High', 'Critical']:
                web_info["severity"] = val

        # Grant Access
        match = re.search(r"Grant Access to Cynet's Engineers\s*\n(.+?)(?:\n|$)", text)
        if match:
            val = match.group(1).strip()
            if val in ['Yes', 'No', '--']:
                web_info["grant_access"] = val

        # Subject (from Description section)
        match = re.search(r'Subject\n(.+?)\nDescription', text)
        if match:
            web_info["subject"] = match.group(1).strip()

        # Description - find the last "Description\n" and extract text after it
        desc_positions = [m.end() for m in re.finditer(r'Description\n', text)]
        if desc_positions:
            desc_start = desc_positions[-1]
            desc_text = text[desc_start:].strip()
            # Stop at common page endings
            for stop_marker in ['\nThe case is', '\nOpen New Case', '\nCopyright ©', '\nIncluded Team']:
                if stop_marker in desc_text:
                    desc_text = desc_text[:desc_text.index(stop_marker)]
            web_info["description"] = desc_text.strip()

        detail["web_information"] = web_info

        # ── Files ──
        files_match = re.search(r'Files\s*\((\d+)\)', text)
        if files_match:
            detail["files_count"] = int(files_match.group(1))

        # Extract file names/details
        file_items = await page.query_selector_all("ul[class*='slds-grid'] li, [class*='fileCardItem']")
        for item in file_items:
            file_text = await item.inner_text()
            if file_text.strip():
                detail["files"].append(file_text.strip())

        # ── Emails metadata from table ──
        emails_match = re.search(r'Emails\s*\((\d+)\)', text)
        if emails_match:
            detail["emails_count"] = int(emails_match.group(1))

        # Extract email rows
        email_table = await page.query_selector_all("table[role='grid'] tbody tr")
        for row in email_table:
            cells = await row.query_selector_all("td")
            if len(cells) >= 5:
                cell_texts = [await c.inner_text() for c in cells]
                cell_texts = [t.strip() for t in cell_texts]
                if len(cell_texts) >= 5 and "@" in cell_texts[1]:
                    detail["emails_metadata"].append({
                        "subject": cell_texts[0],
                        "from_address": cell_texts[1],
                        "to_address": cell_texts[2],
                        "message_date": cell_texts[3],
                        "status": cell_texts[4],
                    })

    except Exception as e:
        detail["extraction_error"] = str(e)

    return detail


async def get_email_links(page):
    """Get all unique email links from the current case page"""
    email_links = []
    try:
        links = await page.query_selector_all("a[href*='/Community/s/emailmessage/']")
        seen = set()
        for link in links:
            href = await link.get_attribute("href")
            if href and href not in seen:
                seen.add(href)
                email_links.append(href)
    except:
        pass
    return email_links


async def extract_email_detail(page, url):
    """Extract full email details from an email detail page"""
    email = {
        "url": url,
        "related_to": "",
        "status": "",
        "from_name": "",
        "message_date": "",
        "from_address": "",
        "to_address": "",
        "cc_address": "",
        "bcc_address": "",
        "subject": "",
        "html_body": "",
        "text_body": "",
    }

    try:
        text = await page.evaluate("() => document.body.innerText")

        patterns = {
            "related_to": r'Related To\n(.+?)(?:\n|$)',
            "status": r'Status\n(.+?)(?:\n|$)',
            "from_name": r'From Name\n(.+?)(?:\n|$)',
            "message_date": r'Message Date\n(.+?)(?:\n|$)',
            "from_address": r'From Address\n(.+?)(?:\n|$)',
            "to_address": r'To Address\n(.+?)(?:\n|$)',
            "cc_address": r'CC Address\n(.+?)(?:\n|$)',
            "bcc_address": r'BCC Address\n(.+?)(?:\n|$)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                email[key] = match.group(1).strip()

        # Subject
        match = re.search(r'Subject\n(.+?)(?:\nHTML Body|\nText Body|\n\n)', text)
        if match:
            email["subject"] = match.group(1).strip()

        # HTML Body
        match = re.search(r'HTML Body\n(.+?)(?:\nText Body|\nCopyright|\Z)', text, re.DOTALL)
        if match:
            body = match.group(1).strip()
            # Clean up page artifacts
            body = re.sub(r'Copyright © \d+ Cynet.*$', '', body, flags=re.DOTALL).strip()
            body = re.sub(r'^Loading.*?\n', '', body).strip()
            email["html_body"] = body

        # Text Body fallback
        if not email["html_body"]:
            match = re.search(r'Text Body\n(.+?)(?:\nCopyright|\Z)', text, re.DOTALL)
            if match:
                email["text_body"] = match.group(1).strip()

        # Also try to get raw HTML of the email body
        try:
            body_el = await page.query_selector(".forceOutputRichText, .slds-rich-text-editor__output, [class*='htmlBody']")
            if body_el:
                raw_html = await body_el.inner_html()
                if raw_html and len(raw_html) > 10:
                    email["html_body_raw"] = raw_html
        except:
            pass

    except Exception as e:
        email["extraction_error"] = str(e)

    return email


def save_json(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    print("\n  Starting Cynet Community Scraper v3...")
    print("  Make sure you have installed:")
    print("    pip install playwright")
    print("    playwright install chromium\n")
    asyncio.run(main())
