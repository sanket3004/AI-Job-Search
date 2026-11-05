"""Public-feed discovery and explained search relevance. No model or employer actions."""
import html
import json
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from toolkit import Workspace, utc, url

SOURCES = {
    'remotive': {'name': 'Remotive', 'url': 'https://remotive.com/api/remote-jobs', 'ttl': 21600,
                 'scope': 'Remote jobs; public listings are delayed by 24 hours.'},
    'jobicy': {'name': 'Jobicy', 'url': 'https://jobicy.com/api/jobs?count=200', 'ttl': 3600,
               'scope': 'Remote jobs published in the last 7 days; up to 5 feed pages per refresh.'},
    'arbeitnow': {'name': 'Arbeitnow', 'url': 'https://www.arbeitnow.com/api/job-board-api', 'ttl': 3600,
                  'scope': 'Europe-focused jobs, primarily Germany; up to 5 feed pages per refresh.'},
}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden += 1
        if tag in {'p', 'li', 'br', 'div'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def plain(value):
    parser = TextParser()
    parser.feed(str(value or ''))
    return re.sub(r'\n\s*\n+', '\n\n', html.unescape(''.join(parser.parts))).strip()


def normalized(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    value = re.sub(r'\b(?:united states(?: of america)?|u\.s\.a?\.?|usa)\b', 'us', value)
    value = re.sub(r'\b(?:united kingdom|u\.k\.?)\b', 'uk', value)
    return ' '.join(re.findall(r'\w+(?:[+#]+)?', value))


def tokens(value):
    return set(normalized(value).split()) - {'and', 'or', 'the', 'a', 'an', 'of', 'in', 'for'}


def posting_date(value):
    """Normalize a source publication date, never substitute retrieval time."""
    if value is None or value == '':
        return None
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            result = datetime.fromtimestamp(float(value), timezone.utc)
        else:
            result = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
            if result.tzinfo is None:
                result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def within_window(job, query, started_at):
    if query['posted_within'] == 'any':
        return True
    raw = job.get('discovery', {}).get('published_at')
    if not raw:
        return query['include_unknown_dates']
    posted = datetime.fromisoformat(raw)
    cutoff = started_at - timedelta(days=int(query['posted_within']))
    return cutoff <= posted <= started_at


def relevance(job, role, location):
    terms = tokens(role)
    title = tokens(job.get('title'))
    body = tokens(job.get('description'))
    title_points = round(45 * len(terms & title) / len(terms)) if terms else 0
    body_points = round(15 * len(terms & body) / len(terms)) if terms else 0
    place = normalized(job.get('location'))
    wanted = normalized(location)
    remote = job.get('discovery', {}).get('remote') is True or 'remote' in place.split()
    if not wanted:
        geo_points, geo = 0, 'No location query'
    elif wanted in {'remote', 'anywhere', 'worldwide'}:
        geo_points, geo = (40, 'Remote listing; check geographic eligibility') if remote else (0, 'Not identified as remote')
    elif wanted and re.search(r'(?<!\w)' + re.escape(wanted) + r'(?!\w)', place):
        geo_points, geo = 40, 'Location text matches; confirm eligibility'
    elif remote and any(x in place for x in ['worldwide', 'anywhere', 'global']):
        geo_points, geo = 30, 'Advertised worldwide remote; confirm eligibility'
    elif remote:
        geo_points, geo = 10, 'Remote geography needs review'
    else:
        geo_points, geo = 0, 'Location differs or is not specified'
    score = title_points + body_points + geo_points
    return {'score': score, 'band': 'Strong' if score >= 75 else 'Possible' if score >= 45 else 'Low',
            'location_note': geo, 'role': role, 'location': location, 'method': 'Search relevance, not AI fit',
            'breakdown': {'Title words (45 max)': title_points, 'Description words (15 max)': body_points,
                          'Location text (40 max)': geo_points},
            'explanation': 'Word overlap and location text only. This does not assess qualifications, seniority, work authorization, or hiring probability.'}


def rankings(state):
    runs = list(state.get('searches', {}).values())
    latest = runs[-1] if runs else {}
    targets = state.get('profile', {}).get('target_roles', [])
    role = latest.get('role') or (targets[0] if targets and isinstance(targets[0], str) else '')
    location = latest.get('location') or state.get('profile', {}).get('location', '')
    values = {j['id']: relevance(j, role, location) for j in state['jobs'].values()}
    ordered = sorted(values, key=lambda key: (-values[key]['score'], state['jobs'][key]['title'].casefold(), key))
    for rank, key in enumerate(ordered, 1):
        values[key]['rank'] = rank
    return values


def validate_query(data):
    if not isinstance(data, dict):
        raise ValueError('Enter a role and location.')
    result = {}
    for key in ('role', 'location'):
        value = data.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120 or any(ord(c) < 32 for c in value):
            raise ValueError(f'{key.capitalize()} must contain 1–120 characters.')
        result[key] = value.strip()
    if not tokens(result['role']):
        raise ValueError('Enter a job role with searchable words.')
    result['posted_within'] = data.get('posted_within', 'any')
    if not isinstance(result['posted_within'], str) or result['posted_within'] not in {'any', '1', '7', '30'}:
        raise ValueError('Choose any time, 24 hours, 7 days, or 30 days.')
    result['include_unknown_dates'] = data.get('include_unknown_dates', False)
    if type(result['include_unknown_dates']) is not bool:
        raise ValueError('Include unknown dates must be true or false.')
    return result


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('The public feed redirected; its connector needs review.')


def fetch_json(endpoint):
    allowed = {(urlsplit(s['url']).hostname, urlsplit(s['url']).path) for s in SOURCES.values()}
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or (parsed.hostname, parsed.path) not in allowed or parsed.username or parsed.password:
        raise ValueError('Unsupported public feed endpoint')
    req = Request(endpoint, headers={'User-Agent': 'CareerPilot/0.5 (local personal job discovery)', 'Accept': 'application/json'})
    with build_opener(NoRedirects()).open(req, timeout=20) as response:
        raw = response.read(32_000_001)
    if len(raw) > 32_000_000:
        raise ValueError('Public feed response exceeded 32 MB')
    result = json.loads(raw)
    if not isinstance(result, dict) or result.get('success') is False:
        raise ValueError('Public feed returned an unsuccessful response')
    return result


def normalize_job(source, item):
    if not isinstance(item, dict):
        raise ValueError('Invalid feed row')
    if source == 'remotive':
        title, company, description, location, published = (item.get(k) for k in ('title','company_name','description','candidate_required_location','publication_date'))
        remote = True
    elif source == 'jobicy':
        title, company, description, location, published = (item.get(k) for k in ('jobTitle','companyName','jobDescription','jobGeo','pubDate'))
        remote = True
    else:
        title, company, description, location, published = (item.get(k) for k in ('title','company_name','description','location','created_at'))
        remote = item.get('remote') is True
    if not title or not company:
        raise ValueError('Missing role or employer')
    valid_until = item.get('validThrough')
    if valid_until:
        try:
            expiry = datetime.fromisoformat(str(valid_until).replace('Z', '+00:00'))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                raise ValueError('Explicitly expired posting')
        except (TypeError, OverflowError):
            pass
    return {'title': plain(title), 'company': plain(company), 'description': plain(description) or 'Description not supplied by source.',
            'url': url(item.get('url')), 'location': plain(location) or 'Location not specified', 'source': SOURCES[source]['name'],
            'discovery': {'remote': remote, 'published_at': posting_date(published), 'published_raw': published,
                          'feed_id': str(item.get('id') or item.get('slug') or ''),
                          'availability': 'Recheck the posting before applying'}}


class FeedClient:
    def __init__(self, root, fetch=fetch_json):
        self.cache = Path(root) / 'search-cache'
        self.fetch = fetch

    def collect(self, key):
        source = SOURCES[key]
        self.cache.mkdir(parents=True, exist_ok=True)
        path = self.cache / (key + '.json')
        cached = {}
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                pass
        if time.time() - cached.get('at', 0) < source['ttl']:
            return cached.get('jobs', []), dict(cached['coverage'], cached=True)
        rows, pages, skipped, warning = [], 0, 0, ''
        endpoint, seen = source['url'], set()
        try:
            while endpoint and pages < 5:
                if endpoint in seen:
                    warning = 'Repeated pagination cursor; remaining pages were not fetched.'
                    break
                seen.add(endpoint)
                data = self.fetch(endpoint)
                batch = data.get('data' if key == 'arbeitnow' else 'jobs')
                if not isinstance(batch, list):
                    raise ValueError('Unexpected feed format')
                pages += 1
                for item in batch:
                    try:
                        rows.append(normalize_job(key, item))
                    except (ValueError, TypeError):
                        skipped += 1
                if key == 'jobicy' and data.get('nextCursor'):
                    endpoint = source['url'] + '&' + urlencode({'cursor': str(data['nextCursor'])})
                elif key == 'arbeitnow' and data.get('links', {}).get('next'):
                    # Construct only the documented endpoint; never follow a response-supplied URL.
                    endpoint = source['url'] + '?' + urlencode({'page': pages + 1})
                else:
                    endpoint = None
            if endpoint and not warning:
                warning = 'Reached the 5-page limit; additional feed pages may exist.'
        except Exception as exc:
            warning = f'{type(exc).__name__}: source unavailable or interrupted. Try again after the feed cache refreshes.'
        coverage = {'source': source['name'], 'scope': source['scope'], 'count': len(rows), 'pages': pages,
                    'skipped': skipped, 'warning': warning, 'cached': False, 'fetched_at': utc(),
                    'status': 'partial' if warning and rows else 'failed' if warning else 'complete'}
        # Cache failures too: repeated button clicks must not hammer an unavailable provider.
        payload = {'at': time.time(), 'jobs': rows, 'coverage': coverage}
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)
        return rows, coverage


class SearchManager:
    def __init__(self, root, client=None):
        self.ws = Workspace(root)
        self.client = client or FeedClient(root)
        self.lock = threading.Lock()
        self.active = None
        self.thread = None

    def start(self, data):
        query = validate_query(data)
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise RuntimeError('A search is already running. Wait for its results.')
            result = self.ws.mutate({'op': 'search-start', **query})
            self.active = result['search_id']
            self.thread = threading.Thread(target=self.run, args=(self.active, query), daemon=True)
            self.thread.start()
            return result

    def run(self, search_id, query):
        outcomes = []
        started_at = datetime.fromisoformat(self.ws.read()['searches'][search_id]['created_at'])
        try:
            for key in SOURCES:
                rows, coverage = self.client.collect(key)
                terms = tokens(query['role'])
                relevant = [j for j in rows if terms & tokens(j['title']) or normalized(query['role']) in normalized(j['description'])]
                candidates = [j for j in relevant if within_window(j, query, started_at)]
                coverage['role_candidates'] = len(relevant)
                coverage['date_excluded'] = len(relevant) - len(candidates)
                coverage['results'] = len(candidates)
                for job in candidates:
                    job['search_relevance'] = relevance(job, query['role'], query['location'])
                    job['discovery']['fetched_at'] = coverage['fetched_at']
                outcomes.append(coverage)
                self.ws.mutate({'op': 'search-results', 'search_id': search_id, 'jobs': candidates, 'coverage': coverage})
            status = 'failed' if all(c['status'] == 'failed' for c in outcomes) else 'partial' if any(c['status'] != 'complete' for c in outcomes) else 'complete'
            self.ws.mutate({'op': 'search-finish', 'search_id': search_id, 'status': status})
        except Exception:
            self.ws.mutate({'op': 'search-finish', 'search_id': search_id, 'status': 'failed',
                            'error': 'Search stopped unexpectedly. Saved results are preserved; start another search to retry.'})
        finally:
            self.active = None
