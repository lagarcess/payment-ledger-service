import asyncio
from playwright.async_api import async_playwright

ARTIFACTS_DIR = "/Users/garces/.gemini/antigravity/brain/a41476ee-2763-4d40-96ce-00d978143b8e"

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(1000)
        
        # 1. Initial State Screenshot
        await page.screenshot(path=f"{ARTIFACTS_DIR}/dashboard.png", full_page=True)
        
        # 2. Setup: Check if DB needs reset
        await page.click("text='Reset Database'")
        await page.wait_for_timeout(500)
        
        # 3. Success Payment
        # Ensure 'Auto-generate key' is unchecked so we can force idempotency later
        await page.uncheck("#auto-key")
        await page.fill("#idem-key-input", "PAY-PLAYWRIGHT-01")
        
        await page.click("text='Execute Payment'")
        await page.wait_for_selector(".toast.success")
        await page.screenshot(path=f"{ARTIFACTS_DIR}/success.png", full_page=True)
        
        # Hide the success toast so it doesn't overlap the next ones
        await page.evaluate("document.querySelector('.toast.success').remove()")
        
        # 4. Idempotency Error
        # Click execute again with the same key
        await page.click("text='Execute Payment'")
        await page.wait_for_selector(".toast.error")
        await page.screenshot(path=f"{ARTIFACTS_DIR}/idempotency.png", full_page=True)
        
        # Hide the error toast
        await page.evaluate("document.querySelector('.toast.error').remove()")
        
        # 5. Overdraft Error
        # Try to send $1M
        await page.fill("#amount", "1000000")
        await page.check("#auto-key") # fresh key so it doesn't fail on idempotency
        await page.click("text='Execute Payment'")
        await page.wait_for_selector(".toast.error")
        await page.screenshot(path=f"{ARTIFACTS_DIR}/overdraft.png", full_page=True)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
