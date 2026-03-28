import asyncio
import os
import re
import json
import aiohttp
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from scripts.config import (
    BASE_SEARCH_URL, SEARCH_SORT, DATA_DIR, ISSUES_DIR, INDEX_FILE, 
    QUEUE_FILE, BOUNTY_KEYWORDS, HEADLESS, TIMEOUT, CONCURRENCY_LIMIT, 
    DELAY_BETWEEN_ISSUES
)
from scripts.utils import logger, save_json, load_json, update_index, download_file

class ScaledScraper:
    def __init__(self, headless=HEADLESS):
        self.headless = headless
        self.semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self.browser = None
        self.context = None

    async def start_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def stop_browser(self):
        if self.browser:
            await self.browser.close()

    async def discover_ids(self):
        """Phase 1: Discover all issue IDs from search results."""
        logger.info("Starting Discovery Phase...")
        page = await self.context.new_page()
        search_query = f"{BASE_SEARCH_URL}{SEARCH_SORT}"
        logger.info(f"Navigating to: {search_query}")
        
        issue_ids = set()
        page_count = 0
        
        # Load existing queue if it exists
        existing_queue = load_json(QUEUE_FILE) or []
        issue_ids.update(existing_queue)

        try:
            await page.goto(search_query, wait_until="networkidle", timeout=TIMEOUT)
            
            while True:
                await asyncio.sleep(5) # Allow dynamic content to load
                
                # Extract IDs from all current links
                links = await page.locator("a").evaluate_all("elements => elements.map(e => e.href)")
                found_new = 0
                for link in links:
                    match = re.search(r'/issues/(\d+)', link)
                    if match:
                        issue_id = match.group(1)
                        if issue_id not in ["0"] and issue_id not in issue_ids:
                            issue_ids.add(issue_id)
                            found_new += 1
                
                logger.info(f"Discovered {found_new} NEW IDs. Total unique IDs: {len(issue_ids)}")
                save_json(QUEUE_FILE, list(issue_ids))

                # Pagination
                next_button = page.locator("button[aria-label='Go to next page']")
                if await next_button.is_visible() and await next_button.is_enabled():
                    logger.info("Clicking 'Go to next page'...")
                    await next_button.click()
                    await page.wait_for_load_state("networkidle")
                    page_count += 1
                else:
                    logger.info("Reached end of search results (Next button disabled or missing).")
                    break
        finally:
            await page.close()
        
        return list(issue_ids)

    def extract_text(self, data):
        """Flatten JSON strings for bounty detection."""
        extracted = []
        if isinstance(data, dict):
            for v in data.values(): extracted.extend(self.extract_text(v))
        elif isinstance(data, list):
            for i in data: extracted.extend(self.extract_text(i))
        elif isinstance(data, str):
            extracted.append(data)
        return extracted

    async def process_issue(self, issue_id):
        """Phase 2: Extract artifacts and attachments for one issue."""
        report_path = os.path.join(ISSUES_DIR, issue_id, "report.json")
        if os.path.exists(report_path):
            # logger.info(f"Issue {issue_id} already exists. Skipping.")
            return True

        async with self.semaphore:
            logger.info(f"Extrating data for: {issue_id}")
            url = f"https://issues.chromium.org/issues/{issue_id}"
            
            captured = {"updates": None, "metadata": None}
            
            async def on_response(response):
                try:
                    if "updates" in response.url or "getIssue" in response.url:
                        if "json" in response.headers.get("content-type", ""):
                            body = await response.text()
                            if body.startswith(")]}'"): body = body[4:].strip()
                            data = json.loads(body)
                            if "updates" in response.url: captured["updates"] = data
                            else: captured["metadata"] = data
                except: pass

            page = await self.context.new_page()
            page.on("response", on_response)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=TIMEOUT)
                await asyncio.sleep(8) # Wait for API cycles
                
                # Check for Bounty
                all_text = " ".join(self.extract_text(captured))
                bounty_patterns = ["award you", "reward you", "VRP Panel", "Congratulations!"]
                has_bounty = any(p.lower() in all_text.lower() for p in bounty_patterns)
                
                if not has_bounty:
                    # logger.info(f"No bounty for {issue_id}.")
                    return False

                logger.info(f"!!! BOUNTY DETECTED: {issue_id}")
                
                # Metadata extraction
                title = await page.title()
                status = "Unknown"
                status_el = page.locator(".status-chip, .issue-status")
                if await status_el.count() > 0: status = await status_el.first.inner_text()
                
                # Attachment discovery
                attachments = await page.locator("a[href*='/attachments/']").evaluate_all(
                    "elements => elements.map(e => ({'name': e.innerText, 'url': e.href}))"
                )

                # Save Data
                issue_dir = os.path.join(ISSUES_DIR, issue_id)
                os.makedirs(issue_dir, exist_ok=True)
                
                report = {
                    "id": issue_id, "url": url, "title": title, "status": status,
                    "bounty_confirmed": True, "attachments": attachments
                }
                save_json(report_path, report)
                save_json(os.path.join(issue_dir, "raw_updates.json"), captured["updates"])
                save_json(os.path.join(issue_dir, "raw_metadata.json"), captured["metadata"])

                # Downloads
                att_dir = os.path.join(issue_dir, "attachments")
                for att in attachments:
                    fname = re.sub(r'[^\w\.-]', '_', att['name'].strip()) or f"file_{att['url'].split('/')[-1]}"
                    await download_file(att['url'], os.path.join(att_dir, fname))

                # Structured snippet for the index
                snippet = all_text[max(0, all_text.lower().find("award you")-50) : 300] if "award you" in all_text.lower() else "Bounty message detected in history."

                update_index(INDEX_FILE, {
                    "id": issue_id, "title": title, "url": url, "status": status, 
                    "local_path": f"issues/{issue_id}", "bounty": True,
                    "bounty_info": snippet.strip()
                })
                return True

            except Exception as e:
                logger.error(f"Error processing {issue_id}: {e}")
                return False
            finally:
                await page.close()

async def main():
    scraper = ScaledScraper()
    await scraper.start_browser()
    
    try:
        # Phase 1: Discovery
        ids = await scraper.discover_ids()
        logger.info(f"Discovered total of {len(ids)} issues.")

        # Phase 2: Extraction Pool
        logger.info("Starting Extraction Phase...")
        tasks = [scraper.process_issue(iid) for iid in ids]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r)
        logger.info(f"Extraction complete. Found {success_count} bounty reports.")
        
    finally:
        await scraper.stop_browser()

if __name__ == "__main__":
    asyncio.run(main())
