import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1360, "height": 900})
    page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("requestfailed", lambda req: errors.append(f"requestfailed: {req.url} {req.failure}"))

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("#view-landing:not(.hidden)", timeout=10000)
    page.screenshot(path=".scratch/01_landing.png", full_page=True)

    page.click('[data-nav="login"]')
    page.wait_for_selector("#view-login:not(.hidden)", timeout=5000)
    page.screenshot(path=".scratch/02_login.png")

    page.fill("#login-email", "admin@moict.go.ug")
    page.fill("#login-password", "ChangeMe123!")
    page.click("#login-submit")
    page.wait_for_selector("#view-dashboard:not(.hidden)", timeout=10000)
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/03_dashboard.png")

    page.click('[data-nav="chat"]')
    page.wait_for_selector("#view-chat:not(.hidden)", timeout=5000)
    page.wait_for_timeout(300)
    page.fill("#chat-input", "What is the purpose of the National ICT Policy? Please summarize the key objectives.")
    page.click("#chat-send-btn")
    page.wait_for_selector(".chat-status-badge", timeout=20000)
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/04_chat_answer.png")
    # click a source chip to test expand
    chip = page.query_selector(".source-chip")
    if chip:
        chip.click()
        page.wait_for_timeout(300)
        page.screenshot(path=".scratch/05_chat_source_expanded.png")

    page.click('[data-nav="knowledge"]')
    page.wait_for_selector("#view-knowledge:not(.hidden)", timeout=5000)
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/06_knowledge.png")

    page.click('[data-nav="upload"]')
    page.wait_for_selector("#view-upload:not(.hidden)", timeout=5000)
    page.wait_for_timeout(300)
    page.screenshot(path=".scratch/07_upload.png")

    page.click('[data-nav="assistant"]')
    page.wait_for_selector("#view-assistant:not(.hidden)", timeout=5000)
    page.wait_for_timeout(300)
    page.screenshot(path=".scratch/08_assistant.png")

    page.click('[data-nav="admin"]')
    page.wait_for_selector("#view-admin:not(.hidden)", timeout=5000)
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/09_admin_overview.png")

    page.click('[data-subtab="users"]')
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/10_admin_users.png")

    page.click('[data-subtab="logs"]')
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/11_admin_logs.png")

    page.click('[data-subtab="insights"]')
    page.wait_for_timeout(500)
    page.screenshot(path=".scratch/12_admin_insights.png")

    # test logout -> back to landing
    page.click('[data-nav="dashboard"]')
    page.wait_for_timeout(300)
    page.click("#logout-btn")
    page.wait_for_selector("#view-landing:not(.hidden)", timeout=5000)

    browser.close()

print("CONSOLE_ERRORS:", errors if errors else "NONE")
if errors:
    sys.exit(1)
