"""Actual browser smoke test against the production HTML and a simulated local API.
No card or firmware operations. Run explicitly after installing Playwright/Chromium.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGE = Path(__file__).resolve().parents[1] / 'tools/v3lab/ui.html'
PATH = r"C:\Users\Example User\ü & O'Brien\koriki-v1.0.img"
state = dict(version='test', busy=False, problem=None, lines=[], mode='quiet',
             extra=dict(flash=dict(image=PATH, image_ready=True, removable=[dict(model='Spare', size_gb=64, bus='USB')],
                                   target_unique=True)),
             session=dict(id='test', current='flash', deviations=[], steps=[
                 dict(id='flash', title='Write Koriki', kind='physical', status='ready', checklist=['Confirmed spare'])]))

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def route(r):
        if r.request.url.endswith('/api/state'):
            r.fulfill(status=200, content_type='application/json', body=json.dumps(state))
        else:
            r.fulfill(status=200, content_type='text/html', body=PAGE.read_text(encoding='utf-8').replace('__TOKEN__','test'))

    page.route('http://127.0.0.1:8765/**', route)
    page.goto('http://127.0.0.1:8765/')
    page.locator('#copy-image-path').click()
    assert page.evaluate('navigator.clipboard.readText()') == PATH
    page.locator('#cl input').check()
    assert page.locator('#done').is_enabled()
    state['extra']['flash']['target_unique'] = False
    page.locator('h1').click()
    page.wait_for_function("document.getElementById('done').disabled")
    assert not errors, errors
    browser.close()
print('Browser smoke test passed')
