"""Fill credentials in an existing, user-connected Playwright browser; never submit."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from private_settings import Settings, site_origin


def fill(page, settings, expected_url, purpose, fields):
    # The host must inspect the form and provide exact selectors, not page-supplied code.
    if page.url != expected_url:
        raise ValueError('Page changed; inspect the form again.')
    if not isinstance(fields, dict) or not fields or not set(fields) <= {
            'username', 'password', 'first_name', 'last_name', 'email', 'phone', 'city', 'country'}:
        raise ValueError('Provide a supported field-to-selector mapping.')
    credentials = settings.credentials(expected_url, purpose)
    for name, selector in fields.items():
        if not isinstance(selector, str) or not credentials.get(name):
            raise ValueError('Missing field selector or saved value.')
        locator = page.locator(selector)
        if locator.count() != 1:
            raise ValueError('Field selector must match exactly one visible input.')
        # Check form destinations before inserting secrets; cross-origin SSO needs its own approval.
        action = locator.evaluate('(e) => e.form ? e.form.action : location.href')
        if site_origin(action) != site_origin(expected_url):
            raise ValueError('Form submits to a different origin; manual review required.')
    for name, selector in fields.items():
        if page.url != expected_url:
            raise ValueError('Page changed; stop and inspect it again.')
        page.locator(selector).fill(credentials[name])
    return {'filled': list(fields), 'submitted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--cdp', required=True, help='Existing authorized loopback Chrome debugging endpoint')
    parser.add_argument('--url', required=True, help='Exact inspected page URL')
    parser.add_argument('--purpose', choices=['login', 'signup'], required=True)
    parser.add_argument('--fields', type=Path, required=True, help='JSON mapping of field names to inspected selectors; no secrets')
    args = parser.parse_args()
    endpoint = urlsplit(args.cdp)
    if endpoint.scheme != 'http' or endpoint.hostname not in ('127.0.0.1', 'localhost') or endpoint.username or endpoint.password:
        parser.error('Use an authorized local HTTP CDP endpoint.')
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as browser_tools:
            browser = browser_tools.chromium.connect_over_cdp(args.cdp)
            pages = [p for c in browser.contexts for p in c.pages if p.url == args.url]
            if len(pages) != 1:
                raise ValueError('Expected exactly one matching browser tab.')
            result = fill(pages[0], Settings(args.workspace.resolve()), args.url, args.purpose,
                          json.loads(args.fields.read_text(encoding='utf-8-sig')))
            print(json.dumps(result))
    except ImportError:
        print(json.dumps({'ok': False, 'error': 'Install the optional playwright Python package, or use browser password-manager autofill.'}))
        return 1
    except Exception:
        # Browser errors can echo fill values. Never print the exception or traceback.
        print(json.dumps({'ok': False, 'error': 'Credential fill stopped. Check site permissions, saved details, current page, and field selectors. Inspect before retrying.'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
