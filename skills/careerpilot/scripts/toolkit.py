#!/usr/bin/env python3
"""Portable state, review, and local dashboard tools. No job-site automation."""
import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

VERSION = '0.6.0'
TERMINAL = {'Submitted', 'Interview', 'Rejected', 'Offer', 'Withdrawn', 'Expired'}
ACTIVE = {'Selected', 'Preparing', 'Filling', 'Ready for review'}

def utc():
    return datetime.now(timezone.utc).isoformat()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def text(value, name, optional=False):
    require(isinstance(value, str) and (optional or value.strip()), f'{name} must be a nonempty string')
    return value.strip()

def url(value):
    value = text(value, 'URL')
    parsed = urlsplit(value)
    require(parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username and not parsed.password, 'Use an http(s) URL without credentials')
    return value

def url_key(value):
    p = urlsplit(url(value))
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'gclid', 'fbclid'}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', urlencode(sorted(query)), ''))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fresh():
    return {'schema_version': 1, 'profile': {}, 'profile_revision': 0, 'jobs': {}, 'authorizations': [], 'events': []}

def summary(state):
    counts = {}
    for job in state['jobs'].values():
        counts[job['status']] = counts.get(job['status'], 0) + 1
    return {'version': VERSION, 'profile_present': bool(state['profile']), 'profile_revision': state['profile_revision'],
            'counts': counts, 'jobs': [{'id': j['id'], 'company': j['company'], 'title': j['title'],
            'status': j['status'], 'blocker': j.get('blocker', '')} for j in state['jobs'].values()]}

class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.db_path = self.root / 'toolkit.sqlite3'

    def initialize(self):
        self.root.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path)
        try:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
                db.execute('INSERT OR IGNORE INTO state VALUES (1, ?)', (json.dumps(fresh()),))
        finally:
            db.close()
        # Keep private runtime data ignored even when placed inside a Git checkout.
        ignore = self.root / '.gitignore'
        if not ignore.exists():
            ignore.write_text('*\n!.gitignore\n', encoding='utf-8')
        return {'workspace': str(self.root), 'initialized': True}

    def read(self):
        require(self.db_path.exists(), 'Workspace does not exist; run init first')
        db = sqlite3.connect(self.db_path)
        try:
            state = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
            require(state.get('schema_version') == 1, 'Unsupported workspace schema')
            return state
        finally:
            db.close()

    def mutate(self, request):
        require(isinstance(request, dict), 'Request must be an object')
        require(self.db_path.exists(), 'Workspace does not exist; run init first')
        db = sqlite3.connect(self.db_path, timeout=10)
        try:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT value FROM state WHERE id=1').fetchone()[0])
            require(state.get('schema_version') == 1, 'Unsupported workspace schema')
            result = self.apply(state, request)
            state['events'].append({'at': utc(), 'op': request['op'], 'job_id': request.get('job_id'), 'result': result})
            db.execute('UPDATE state SET value=? WHERE id=1', (json.dumps(state, ensure_ascii=False),))
            db.commit()
            if request.get('op') == 'pause' and result.get('request_id'):
                from private_settings import deliver
                try:
                    result['notification'] = deliver(self.root, result['request_id']).get('delivery', 'pending')
                except (ValueError, OSError, sqlite3.Error):
                    result['notification'] = 'pending'
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def fingerprint(self, state, job):
        for doc in job['documents']:
            path = (self.root / doc['path']).resolve()
            require(path.is_relative_to(self.root), 'Document escaped workspace')
            require(path.is_file() and file_digest(path) == doc['sha256'], 'Document changed or missing; register and review it again')
        return digest({'profile_revision': state['profile_revision'], 'url': job['url'], 'title': job['title'],
                       'company': job['company'], 'description': job['description'], 'documents': job['documents'],
                       'checkpoint': job.get('checkpoint')})

    def apply(self, state, data):
        op = text(data.get('op'), 'op')
        if op in {'assistance-claim', 'assistance-delivery', 'assistance-retry'}:
            item = state.get('assistance', {}).get(data.get('request_id'))
            require(item is not None, 'Unknown assistance request')
            if op == 'assistance-claim':
                if item['status'] != 'open' or item['delivery'] != 'pending':
                    return {'claimed': False}
                item['delivery'] = 'sending'
                item['attempted_at'] = utc()
                return {'claimed': True, 'job_id': item['job_id']}
            if op == 'assistance-retry':
                require(item['status'] == 'open', 'Request is already resolved')
                require(item['delivery'] != 'sent', 'Notification was already sent')
                if item['delivery'] == 'sending':
                    age = datetime.now(timezone.utc) - datetime.fromisoformat(item['attempted_at'])
                    require(age.total_seconds() > 60, 'Delivery is still in progress')
                item['delivery'] = 'pending'
            else:
                require(item['delivery'] == 'sending' and data.get('delivery') in {'sent','failed'}, 'No pending delivery')
                item['delivery'] = data['delivery']
                item['error'] = data.get('error', '')
            return {'request_id': item['id'], 'delivery': item['delivery']}
        if op == 'search-start':
            role, location = text(data.get('role'), 'role'), text(data.get('location'), 'location')
            require(len(role) <= 120 and len(location) <= 120, 'Search fields exceed 120 characters')
            window = data.get('posted_within', 'any')
            require(isinstance(window, str) and window in {'any', '1', '7', '30'}, 'Invalid posting-date window')
            require(type(data.get('include_unknown_dates', False)) is bool, 'Unknown-date option must be boolean')
            sid = uuid.uuid4().hex[:12]
            state.setdefault('searches', {})[sid] = {'id': sid, 'role': role, 'location': location,
                'posted_within': data.get('posted_within', 'any'), 'include_unknown_dates': data.get('include_unknown_dates', False),
                'status': 'running', 'created_at': utc(), 'updated_at': utc(), 'job_ids': [], 'listings': {}, 'coverage': []}
            return {'search_id': sid}
        if op in {'search-results', 'search-finish'}:
            run = state.get('searches', {}).get(data.get('search_id'))
            require(run is not None and run['status'] == 'running', 'Unknown or finished search')
            if op == 'search-results':
                require(isinstance(data.get('jobs'), list) and isinstance(data.get('coverage'), dict), 'Invalid search results')
                for candidate in data['jobs']:
                    result = self.apply(state, dict(candidate, op='job-add'))
                    jid = result['job_id']
                    if jid not in run['job_ids']:
                        run['job_ids'].append(jid)
                    run['listings'][jid] = dict(candidate, id=jid)
                    # A new discovery must not overwrite reviewed text, documents, or application state.
                    if not result['duplicate']:
                        state['jobs'][jid]['discovery'] = candidate.get('discovery', {})
                run['coverage'].append(data['coverage'])
            else:
                require(data.get('status') in {'complete', 'partial', 'failed'}, 'Invalid search status')
                run['status'] = data['status']
                run['error'] = data.get('error', '')
            run['updated_at'] = utc()
            return {'search_id': run['id'], 'status': run['status'], 'count': len(run['job_ids'])}
        if op == 'profile-preview':
            profile = data.get('profile')
            require(isinstance(profile, dict) and bool(profile), 'Proposed profile must be a nonempty object')
            require(data.get('base_revision') == state['profile_revision'], 'Profile changed; reload and rebuild the proposal')
            sources = data.get('evidence_files')
            require(isinstance(sources, list) and sources and all(isinstance(s, str) for s in sources), 'Supply extracted evidence file paths')
            provenance = []
            for source in sources:
                path = Path(source).expanduser().resolve()
                require(path.is_relative_to(self.root / 'imports') and path.is_file(), 'Evidence must be a file in this workspace imports folder')
                evidence = json.loads(path.read_text(encoding='utf-8'))
                require(evidence.get('schema_version') == 1 and isinstance(evidence.get('documents'), list), 'Invalid evidence file')
                provenance.append({'path': path.relative_to(self.root).as_posix(), 'sha256': file_digest(path)})
            changes = {k: {'before': state['profile'].get(k), 'after': profile.get(k)} for k in sorted(set(state['profile']) | set(profile))
                       if (k in state['profile']) != (k in profile) or state['profile'].get(k) != profile.get(k)}
            preview_id = uuid.uuid4().hex
            preview = {'id': preview_id, 'created_at': utc(), 'base_revision': state['profile_revision'],
                       'profile': profile, 'sources': provenance, 'changes': changes, 'applied': False}
            state.setdefault('profile_imports', {})[preview_id] = preview
            return {'preview_id': preview_id, 'changes': changes, 'profile_changed': False}
        if op == 'profile-apply':
            preview = state.get('profile_imports', {}).get(data.get('preview_id'))
            require(preview is not None and not preview['applied'], 'Unknown or already applied import preview')
            require(preview['base_revision'] == state['profile_revision'], 'Profile changed since preview; rebuild and review it again')
            confirmation = text(data.get('user_confirmation'), 'User confirmation of this preview')
            for source in preview['sources']:
                path = (self.root / source['path']).resolve()
                require(path.is_relative_to(self.root / 'imports') and path.is_file() and file_digest(path) == source['sha256'], 'Import evidence changed; create a new preview')
            result = self.apply(state, {'op': 'profile-save', 'profile': preview['profile']})
            preview['applied'] = True
            preview['applied_at'] = utc()
            preview['user_confirmation'] = confirmation
            return dict(result, preview_id=preview['id'])
        if op == 'profile-save':
            profile = data.get('profile')
            require(isinstance(profile, dict) and bool(profile), 'profile must be a nonempty object')
            state['profile'] = profile
            state['profile_revision'] += 1
            for j in state['jobs'].values():
                if j['status'] == 'Ready for review':
                    j['status'] = 'Preparing'
                    j['review'] = None
            return {'profile_revision': state['profile_revision']}
        if op == 'job-add':
            source_url = url(data.get('url'))
            key = url_key(source_url)
            for job in state['jobs'].values():
                if job['url_key'] == key:
                    return {'job_id': job['id'], 'duplicate': True}
            jid = uuid.uuid4().hex[:12]
            job = {'id': jid, 'title': text(data.get('title'), 'title'), 'company': text(data.get('company'), 'company'),
                   'url': source_url, 'url_key': key, 'description': text(data.get('description'), 'description'),
                   'source': text(data.get('source'), 'source'), 'location': text(data.get('location', ''), 'location', True),
                   'retrieved_at': utc(), 'status': 'Saved', 'documents': [], 'contacts': [], 'notes': [],
                   'outreach': [], 'attempts': [], 'created_at': utc(), 'updated_at': utc()}
            state['jobs'][jid] = job
            return {'job_id': jid, 'duplicate': False}
        if op == 'authorize':
            ids = data.get('job_ids')
            require(isinstance(ids, list) and ids and all(isinstance(i, str) for i in ids) and len(set(ids)) == len(ids), 'Supply distinct exact job_ids')
            statement = text(data.get('user_instruction'), 'Actual user authorization')
            expires = datetime.fromisoformat(text(data.get('expires_at'), 'expires_at').replace('Z', '+00:00'))
            require(expires.tzinfo is not None and expires > datetime.now(timezone.utc), 'Authorization must have a future timezone-aware expiry')
            fingerprints = {}
            for jid in ids:
                require(jid in state['jobs'], 'Unknown job ID')
                job = state['jobs'][jid]
                require(job['status'] == 'Ready for review', 'Only reviewed jobs can be authorized')
                fingerprint = self.fingerprint(state, job)
                require(job.get('review') == fingerprint, 'Review is stale')
                fingerprints[jid] = fingerprint
            aid = uuid.uuid4().hex
            state['authorizations'].append({'id': aid, 'user_instruction': statement, 'expires_at': expires.isoformat(),
                                           'fingerprints': fingerprints, 'used': [], 'revoked': False})
            return {'authorization_id': aid, 'job_ids': ids, 'expires_at': expires.isoformat()}
        if op == 'revoke':
            grants = [g for g in state['authorizations'] if g['id'] == data.get('authorization_id')]
            require(grants, 'Unknown authorization')
            grants[0]['revoked'] = True
            return {'revoked': grants[0]['id']}
        jid = data.get('job_id')
        require(isinstance(jid, str) and jid in state['jobs'], 'Unknown job_id')
        job = state['jobs'][jid]
        old_status = job['status']
        if op == 'evaluate':
            evaluation = data.get('evaluation')
            require(isinstance(evaluation, dict), 'evaluation must be an object')
            for k in ['strengths', 'gaps', 'unknowns', 'evidence']:
                require(isinstance(evaluation.get(k), list), f'evaluation.{k} must be an array')
            text(evaluation.get('recommendation'), 'recommendation')
            if 'score' in evaluation:
                require(type(evaluation['score']) in (int, float) and 0 <= evaluation['score'] <= 100, 'score must be 0 to 100')
                text(evaluation.get('rationale'), 'score rationale')
            job['evaluation'] = evaluation
        elif op == 'select':
            require(old_status == 'Saved', 'Only saved jobs can be selected')
            job['status'] = 'Selected'
        elif op == 'start':
            require(old_status in {'Selected', 'Preparing'}, 'Job is not eligible to start; resume paused jobs explicitly')
            job['status'] = 'Filling'
        elif op == 'document-add':
            require(old_status not in TERMINAL | {'Submitting', 'Submission uncertain'}, 'Cannot change documents during or after submission')
            kind = data.get('kind')
            require(kind in {'resume', 'cover_letter', 'other'}, 'Unknown document kind')
            source = Path(text(data.get('path'), 'document path')).expanduser().resolve()
            require(source.is_file() and source.suffix.lower() in {'.pdf', '.docx', '.txt', '.md', '.html'}, 'Use an existing PDF, DOCX, TXT, MD or HTML file')
            require(source.stat().st_size <= 25_000_000, 'Document exceeds 25 MB')
            sha = file_digest(source)
            relative = Path('artifacts') / jid / f'{kind}-{sha}{source.suffix.lower()}'
            target = self.root / relative
            require(target.resolve().is_relative_to(self.root), 'Artifact destination escaped workspace')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            job['documents'] = [d for d in job['documents'] if d['kind'] != kind or kind == 'other']
            record = {'kind': kind, 'path': relative.as_posix(), 'sha256': sha, 'original_name': source.name}
            if record not in job['documents']:
                job['documents'].append(record)
            job['review'] = None
            if old_status == 'Ready for review':
                job['status'] = 'Preparing'
        elif op == 'checkpoint':
            require(old_status in ACTIVE, 'Cannot checkpoint this job; resume it first if paused')
            checkpoint = data.get('checkpoint')
            require(isinstance(checkpoint, dict), 'checkpoint must be an object')
            url(checkpoint.get('page_url'))
            text(checkpoint.get('step'), 'step')
            text(checkpoint.get('observation'), 'observed form evidence')
            require(isinstance(checkpoint.get('answers'), list) and isinstance(checkpoint.get('unresolved'), list), 'answers and unresolved must be arrays')
            require(type(checkpoint.get('complete')) is bool, 'complete must be a boolean')
            for answer in checkpoint['answers']:
                require(isinstance(answer, dict), 'Each answer must be an object')
                for k in ['field', 'value', 'source']:
                    text(answer.get(k), f'answer.{k}')
            job['checkpoint'] = dict(checkpoint, recorded_at=utc(), profile_revision=state['profile_revision'])
            job['review'] = None
            job['status'] = 'Filling'
        elif op == 'pause':
            require(old_status in ACTIVE, 'Cannot pause a terminal or uncertain submission')
            job['resume_status'] = 'Preparing'
            job['blocker'] = text(data.get('reason'), 'pause reason')
            job['next_action'] = text(data.get('next_action'), 'next action')
            job['status'] = 'Needs attention'
            rid = uuid.uuid4().hex[:12]
            state.setdefault('assistance', {})[rid] = {'id': rid, 'job_id': jid, 'status': 'open',
                'created_at': utc(), 'reason': job['blocker'], 'next_action': job['next_action'],
                'delivery': 'pending', 'error': ''}
            job['assistance_id'] = rid
        elif op == 'resume':
            require(old_status == 'Needs attention', 'Job is not paused')
            job['notes'].append({'at': utc(), 'text': text(data.get('note'), 'resolution note')})
            job['status'] = 'Preparing'
            job['blocker'] = ''
            for item in state.get('assistance', {}).values():
                if item['job_id'] == jid and item['status'] == 'open':
                    item['status'] = 'resolved'
                    item['resolved_at'] = utc()
            job['review'] = None
        elif op == 'ready':
            require(old_status == 'Filling', 'Job must be filled before review')
            checkpoint = job.get('checkpoint', {})
            require(checkpoint.get('complete') is True and not checkpoint.get('unresolved'), 'Required fields are incomplete or unresolved')
            require(checkpoint.get('profile_revision') == state['profile_revision'], 'Profile changed; inspect and checkpoint the form again')
            job['review'] = self.fingerprint(state, job)
            job['status'] = 'Ready for review'
        elif op == 'submit-begin':
            require(old_status == 'Ready for review', 'Submission requires a ready, reviewed job')
            grants = [g for g in state['authorizations'] if g['id'] == data.get('authorization_id')]
            require(grants, 'Explicit authorization is required')
            grant = grants[0]
            require(not grant['revoked'] and datetime.fromisoformat(grant['expires_at']) > datetime.now(timezone.utc), 'Authorization expired or revoked')
            require(jid not in grant['used'] and grant['fingerprints'].get(jid) == self.fingerprint(state, job) == job.get('review'), 'Authorization does not cover this snapshot or was already used')
            grant['used'].append(jid)
            job['attempts'].append({'at': utc(), 'authorization_id': grant['id'], 'snapshot': job['review']})
            job['status'] = 'Submitting'
        elif op in {'submitted', 'uncertain', 'resolve', 'manual-submitted'}:
            if op == 'submitted':
                require(old_status == 'Submitting', 'No pending submission attempt')
                job['status'] = 'Submitted'
            elif op == 'uncertain':
                require(old_status == 'Submitting', 'Only an in-flight submission can become uncertain')
                job['status'] = 'Submission uncertain'
            elif op == 'resolve':
                require(old_status in {'Submitting', 'Submission uncertain'}, 'No uncertain submission to resolve')
                require(data.get('result') in {'submitted', 'not_submitted'}, 'Resolution must be submitted or not_submitted')
                job['status'] = 'Submitted' if data['result'] == 'submitted' else 'Preparing'
                job['review'] = None
            else:
                require(old_status not in TERMINAL, 'Application already has a terminal outcome')
                job['status'] = 'Submitted'
            evidence = text(data.get('evidence'), 'observed confirmation or user statement')
            job['notes'].append({'at': utc(), 'text': evidence, 'kind': 'user-reported' if op == 'manual-submitted' else op})
        elif op == 'contact-add':
            contact = data.get('contact')
            require(isinstance(contact, dict), 'contact must be an object')
            for k in ['name', 'role', 'company', 'relevance']:
                text(contact.get(k), f'contact.{k}')
            url(contact.get('source_url'))
            require(contact.get('relationship') in {'confirmed', 'likely', 'unknown'}, 'Label the relationship confirmed, likely, or unknown')
            if contact.get('profile_url'):
                url(contact['profile_url'])
            if contact.get('email'):
                require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', contact['email']), 'Invalid email')
                url(contact.get('email_source_url'))
                text(contact.get('email_evidence'), 'published email evidence')
            job['contacts'].append(dict(contact, checked_at=utc()))
        elif op == 'outreach-draft':
            job['outreach'].append({'at': utc(), 'recipient': text(data.get('recipient'), 'recipient'),
                                   'channel': text(data.get('channel'), 'channel'), 'text': text(data.get('text'), 'draft'), 'status': 'Draft only'})
        elif op == 'note':
            job['notes'].append({'at': utc(), 'text': text(data.get('text'), 'note')})
        elif op == 'outcome':
            require(old_status not in {'Submitting', 'Submission uncertain'}, 'Resolve the submission before recording an outcome')
            require(data.get('status') in TERMINAL - {'Submitted'}, 'Invalid outcome')
            job['status'] = data['status']
            job['notes'].append({'at': utc(), 'text': text(data.get('evidence'), 'outcome evidence')})
        else:
            raise ValueError(f'Unknown operation: {op}')
        job['updated_at'] = utc()
        return dict({'job_id': jid, 'status': job['status']}, **({'request_id': job['assistance_id']} if op == 'pause' else {}))

    def report(self):
        state = self.read()
        esc = lambda v: html.escape(str(v), quote=True)
        cards = []
        for j in state['jobs'].values():
            docs = ''.join(f'<li><a href="../{esc(d["path"])}">{esc(d["kind"])}: {esc(d["original_name"])}</a></li>' for d in j['documents'])
            contacts = ''.join(f'<li>{esc(c["name"])} — {esc(c["role"])} ({esc(c["relationship"])}) · <a href="{esc(c["source_url"])}">Evidence</a></li>' for c in j['contacts'])
            checkpoint = j.get('checkpoint', {})
            answers = ''.join(f'<tr><td>{esc(a["field"])}</td><td>{esc(a["value"])}</td><td>{esc(a["source"])}</td></tr>' for a in checkpoint.get('answers', []))
            cards.append(f'<article><span class="badge">{esc(j["status"])}</span><h2>{esc(j["title"])}</h2><p>{esc(j["company"])} · {esc(j["location"])} · {esc(j["id"])}</p><a href="{esc(j["url"])}">Open posting ↗</a><p>{esc(j.get("blocker", ""))}</p><p>{esc(j.get("next_action", ""))}</p><details><summary>Fit assessment</summary><pre>{esc(json.dumps(j.get("evaluation", {}), indent=2, ensure_ascii=False))}</pre></details><details><summary>Form review & documents</summary><p>{esc(checkpoint.get("observation", "No browser observation saved."))}</p><table><tr><th>Field</th><th>Answer</th><th>Source</th></tr>{answers}</table><p>Unresolved: {esc(", ".join(map(str, checkpoint.get("unresolved", []))))}</p><ul>{docs}</ul></details><details><summary>Recruiting contacts</summary><ul>{contacts}</ul></details><details><summary>Notes and outreach drafts</summary><pre>{esc(json.dumps({"notes":j["notes"],"outreach":j["outreach"]}, indent=2, ensure_ascii=False))}</pre></details></article>')
        content = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>CareerPilot · Review</title><style>body{font:15px system-ui;background:#f4f6f0;color:#243d31;max-width:1050px;margin:45px auto;padding:0 24px}header{background:#193b2d;color:#edf4dc;padding:32px;border-radius:16px;margin-bottom:25px}h1{margin:8px 0;font-size:34px}h2{margin:10px 0}article{background:white;border:1px solid #dce4d5;border-radius:12px;padding:24px;margin:16px 0}.badge{float:right;background:#e9efd9;border-radius:8px;padding:6px 10px;font-size:12px}a{color:#357447}details{border-top:1px solid #e4eadf;padding:14px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px system-ui}table{width:100%;text-align:left;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}small{color:#b7cbb4}</style><header><small>CAREERPILOT · PRIVATE WORKSPACE</small><h1>Your application review</h1><p>Saved evidence, documents, and next steps.</p></header>'
        content += f'<p>Generated {esc(utc())}. Read-only snapshot; browser forms may have changed. No actions run from this report.</p>'
        content += ''.join(cards) or '<article>No jobs saved yet. Ask your AI to set up a fresh profile or save a job.</article>'
        content += '</html>'
        folder = self.root / 'reports'
        folder.mkdir(exist_ok=True)
        path = folder / 'review.html'
        path.write_text(content, encoding='utf-8')
        return {'report': str(path)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['init', 'status', 'next', 'report', 'export', 'accounts']:
        sub.add_parser(name)
    dashboard = sub.add_parser('dashboard', help='Serve the live local read-only dashboard')
    dashboard.add_argument('--port', type=int, default=8765)
    dashboard.add_argument('--open', action='store_true', help='Open in the default browser')
    show = sub.add_parser('show')
    show.add_argument('--job')
    run = sub.add_parser('run')
    run.add_argument('--input', required=True, help='JSON file path, or - for stdin')
    args = parser.parse_args()
    try:
        ws = Workspace(args.workspace)
        if args.command == 'dashboard':
            from dashboard import serve
            serve(ws.root, args.port, args.open)
            return 0
        elif args.command == 'init':
            result = ws.initialize()
        elif args.command == 'run':
            payload = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8-sig')
            result = ws.mutate(json.loads(payload))
        elif args.command == 'accounts':
            ws.read()
            from private_settings import Settings
            result = Settings(ws.root).public()
        elif args.command == 'report':
            result = ws.report()
        else:
            state = ws.read()
            if args.command == 'status':
                result = summary(state)
            elif args.command == 'next':
                result = {'job': next((j for j in state['jobs'].values() if j['status'] in {'Selected', 'Preparing'}), None),
                          'in_flight': [j['id'] for j in state['jobs'].values() if j['status'] in {'Filling', 'Submitting', 'Submission uncertain'}]}
            elif args.command == 'show':
                require(not args.job or args.job in state['jobs'], 'Unknown job ID')
                result = state['jobs'][args.job] if args.job else state
            else:
                folder = ws.root / 'exports'
                folder.mkdir(exist_ok=True)
                path = folder / f'workspace-{uuid.uuid4().hex[:12]}.json'
                path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
                result = {'export': str(path), 'note': 'State only; copy the workspace artifacts directory for a complete backup.'}
        print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
