"""Encrypted local account and Telegram settings; never part of workspace exports."""
import ctypes
from contextlib import closing
import json
import os
import re
import secrets
import sqlite3
import string
from ctypes import wintypes
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


def site_origin(value):
    if not isinstance(value, str):
        raise ValueError("Use an HTTPS career-site URL.")
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Use an exact HTTPS career-site URL without credentials or a custom port.')
    return 'https://' + p.hostname.encode('idna').decode().lower()


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise ValueError('Encrypted settings currently require Windows. Use your browser password manager on other systems.')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ValueError('Windows could not unlock private settings for this user.')
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(outgoing.data)


class Settings:
    def __init__(self, root):
        self.path = root / 'private-settings.sqlite3'

    def read(self):
        if not self.path.exists():
            return {'signup': {}, 'sites': {}, 'telegram': {}}
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute('SELECT value FROM private WHERE id=1').fetchone()
        return json.loads(protect(row[0], True))

    def change(self, update):
        # Serialize read-modify-write across dashboard and browser helpers.
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS private(id INTEGER PRIMARY KEY, value BLOB NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM private WHERE id=1').fetchone()
            data = json.loads(protect(row[0], True)) if row else {'signup': {}, 'sites': {}, 'telegram': {}}
            update(data)
            db.execute('INSERT OR REPLACE INTO private VALUES(1,?)', (protect(json.dumps(data).encode()),))
            db.commit()
        return self.public()

    def public(self):
        data = self.read()
        return {'signup': data['signup'], 'supported': os.name == 'nt',
                'sites': {k: {f: v for f, v in s.items() if f != 'password'} | {'password_saved': bool(s.get('password'))}
                          for k, s in data['sites'].items()},
                'telegram': {'configured': bool(data['telegram'].get('token') and data['telegram'].get('chat_id')),
                             'enabled': data['telegram'].get('enabled', False),
                             'chat_id': data['telegram'].get('chat_id', '')}}

    def save(self, request):
        def update(data):
            kind = request.get('kind')
            if kind == 'signup':
                fields = ('first_name', 'last_name', 'email', 'phone', 'city', 'country')
                data['signup'] = {k: str(request.get(k, '')).strip()[:200] for k in fields}
            elif kind in ('site', 'remove-site'):
                origin = site_origin(request.get('url', ''))
                if kind == 'remove-site':
                    data['sites'].pop(origin, None)
                    return
                for field in ('allow_login', 'allow_signup'):
                    if type(request.get(field)) is not bool:
                        raise ValueError('Site permissions must be explicit checkbox choices.')
                previous = data['sites'].get(origin, {})
                password = request.get('password') or previous.get('password', '')
                if not isinstance(password, str) or len(password) > 1024:
                    raise ValueError('Invalid password.')
                data['sites'][origin] = {'username': str(request.get('username', '')).strip()[:200],
                    'password': password, 'allow_login': request['allow_login'], 'allow_signup': request['allow_signup']}
            elif kind == 'telegram':
                token = request.get('token') or data['telegram'].get('token', '')
                chat = str(request.get('chat_id', '')).strip()
                if not isinstance(token, str) or not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}', token) or not re.fullmatch(r'[1-9]\d*', chat):
                    raise ValueError('Enter a valid bot token and your positive private-chat ID.')
                if type(request.get('enabled')) is not bool:
                    raise ValueError('Choose whether notifications are enabled.')
                data['telegram'] = {'token': token, 'chat_id': chat, 'enabled': request['enabled']}
            else:
                raise ValueError('Unknown settings action.')
        return self.change(update)

    def credentials(self, page_url, purpose='login'):
        origin = site_origin(page_url)
        if purpose not in ('login', 'signup'):
            raise ValueError('Choose login or signup.')
        def prepare(data):
            site = data['sites'].get(origin, {})
            if not site.get('allow_' + purpose):
                raise ValueError('This exact career-site origin is not approved for this action.')
            if purpose == 'signup' and not site.get('password'):
                alphabet = string.ascii_letters + string.digits + '!@#$%'
                site['password'] = 'Aa1!' + ''.join(secrets.choice(alphabet) for _ in range(24))
        self.change(prepare)
        data = self.read()
        site = data['sites'][origin]
        username = site.get('username') or data['signup'].get('email')
        if not username or not site.get('password'):
            raise ValueError('Save the account email and password first.')
        return dict(data['signup'], username=username, password=site['password'])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Notification redirect refused.')


def send_telegram(root, message):
    config = Settings(root).read()['telegram']
    if not config.get('enabled') or not config.get('token') or not config.get('chat_id'):
        raise ValueError('Telegram is not configured and enabled.')
    payload = json.dumps({'chat_id': config['chat_id'], 'text': message, 'protect_content': True}).encode()
    request = Request('https://api.telegram.org/bot' + config['token'] + '/sendMessage', data=payload,
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            result = json.loads(response.read(100_000))
        if not result.get('ok'):
            raise ValueError('Rejected')
    except Exception:
        # HTTP errors contain the secret URL; never propagate their text.
        raise ValueError('Telegram delivery failed. Check token, chat ID, /start, and connectivity; retry in Assistance.') from None


def deliver(root, request_id):
    from toolkit import Workspace
    ws = Workspace(root)
    result = ws.mutate({'op': 'assistance-claim', 'request_id': request_id})
    if not result['claimed']:
        return result
    # Only fixed text and generated IDs leave the machine. No arbitrary page text or OTPs.
    message = ('CareerPilot needs your assistance.\nRequest: ' + request_id + '\nJob: ' + result['job_id'] +
               '\nOpen Chrome Remote Desktop and check CareerPilot â†’ Assistance. Other eligible jobs can continue.')
    try:
        send_telegram(root, message)
        status, error = 'sent', ''
    except (ValueError, OSError):
        status, error = 'failed', 'Not delivered. Check Telegram settings and use Retry notification.'
    return ws.mutate({'op': 'assistance-delivery', 'request_id': request_id, 'delivery': status, 'error': error})


def telegram_chats(root, token):
    token = token or Settings(root).read()['telegram'].get('token', '')
    if not isinstance(token, str) or not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}', token):
        raise ValueError('Enter your bot token first.')
    try:
        request = Request('https://api.telegram.org/bot' + token + '/getUpdates',
                          data=json.dumps({'timeout':0, 'limit':100}).encode(),
                          headers={'Content-Type':'application/json'}, method='POST')
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            data = json.loads(response.read(1_000_000))
        if not data.get('ok'):
            raise ValueError('Rejected')
        chats = {}
        for update in data.get('result', []):
            message = update.get('message', {})
            chat = message.get('chat', {})
            if chat.get('type') == 'private' and message.get('text', '').split(' ')[0] == '/start':
                chats[str(chat['id'])] = {'id':str(chat['id']), 'name':chat.get('first_name',''), 'username':chat.get('username','')}
        return {'chats':list(chats.values())}
    except Exception:
        raise ValueError('Could not find chats. Check the bot token, send /start to your bot, and try again. Use a dedicated bot without a webhook.') from None
