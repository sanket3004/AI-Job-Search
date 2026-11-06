"""Verified external-application discovery through host LinkedIn/Indeed access."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit

PORTALS = ('LinkedIn', 'Indeed')
INDEED = ('indeed.com', 'indeed.ca', 'indeed.co.uk', 'indeed.com.au', 'indeed.co.in', 'indeed.de', 'indeed.fr', 'indeed.ie', 'indeed.co.nz')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def under(host, domain):
    return host == domain or host.endswith('.' + domain)


def host(value):
    require(isinstance(value, str), 'Supply an HTTPS posting URL.')
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
            'Use HTTPS URLs without credentials.')
    return parsed.hostname.lower()


def source_url(source, value):
    name = host(value)
    require(under(name, 'linkedin.com') if source == 'LinkedIn' else any(under(name, d) for d in INDEED),
            'The source URL must belong to the declared portal.')
    return value


def route(value):
    require(isinstance(value, dict), 'Record observed application-route evidence.')
    require(value.get('type') == 'external' and value.get('employer_verified') is True and value.get('on_platform_available') is False,
            'Only verified employer/ATS applications are eligible.')
    name = host(value.get('url'))
    require(not any(under(name, d) for d in (*INDEED, 'linkedin.com', 'indeedapply.com', 'indeedassessments.com')),
            'On-platform applications are excluded.')
    require(isinstance(value.get('evidence'), str) and 0 < len(value['evidence'].strip()) <= 2000,
            'Include observed button and employer/role destination evidence.')
    checked = datetime.fromisoformat(str(value.get('checked_at', '')).replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    require(checked.tzinfo is not None and now-timedelta(days=1) <= checked <= now+timedelta(minutes=5),
            'Application-route verification must be from the last 24 hours.')
    return {k:value[k] for k in ('type','url','employer_verified','on_platform_available','evidence','checked_at')}


def apply(ws, state, data):
    from job_search import validate_query, posting_date, within_window, relevance
    from toolkit import utc
    op = data['op']
    if op == 'portal-search-start':
        query = validate_query(data)
        result = ws.apply(state, {'op':'search-start', **query})
        run = state['searches'][result['search_id']]
        run.update(kind='primary-portals', status='awaiting_agent', required_sources=list(PORTALS),
                   external_only=True, exclusions=[], source_checks={})
        return dict(result, status=run['status'])
    run = state.get('searches', {}).get(data.get('search_id'))
    require(run is not None and run.get('kind') == 'primary-portals', 'Unknown primary-portal search.')
    require(run['status'] in {'awaiting_agent','running'}, 'This portal search is finished.')
    if op == 'portal-search-begin':
        run.update(status='running', updated_at=utc())
        return {'search_id':run['id'], 'status':run['status']}
    if op == 'portal-search-results':
        require(run['status'] == 'running', 'Begin this search before recording observations.')
        source = data.get('source')
        require(source in PORTALS, 'LinkedIn and Indeed are the required primary portals.')
        require(source not in run['source_checks'], 'This portal is already marked finished for this run.')
        rows = data.get('jobs')
        require(isinstance(rows, list) and len(rows) <= 200, 'Supply at most 200 observations per batch.')
        accepted = 0
        for candidate in rows:
            require(isinstance(candidate, dict), 'Each observation must be an object.')
            original = source_url(source, candidate.get('source_url'))
            method = candidate.get('application_route', {})
            require(isinstance(method, dict), 'Invalid application route.')
            reason = ''
            if method.get('type') in {'easy_apply','indeed_apply','on_platform'}:
                reason = 'On-platform application excluded'
            elif method.get('type') != 'external' or method.get('employer_verified') is not True:
                reason = 'Application route unverified'
            else:
                try:
                    method = route(method)
                except ValueError as exc:
                    reason = str(exc)
            discovery = candidate.get('discovery', {})
            require(isinstance(discovery,dict), 'Invalid posting-date evidence.')
            published = posting_date(discovery.get('published_at'))
            job = dict(candidate, source=source, source_url=original,
                       discovery=dict(discovery, published_at=published, fetched_at=utc()))
            if not reason and not within_window(job, run, datetime.fromisoformat(run['created_at'])):
                reason = 'Outside posting-date window or unknown posting date'
            if reason:
                run['exclusions'].append({'source':source, 'source_url':original, 'reason':reason, 'at':utc()})
                continue
            job.update(url=method['url'], application_route=method,
                       search_relevance=relevance(job, run['role'], run['location']))
            result = ws.apply(state, dict(job,op='job-add'))
            jid = result['job_id']
            if jid not in run['job_ids']:
                run['job_ids'].append(jid)
            # Keep both portal citations when the same employer URL appears on both.
            previous = run['listings'].get(jid, {})
            citations = previous.get('portal_sources', [])
            citation = {'source':source, 'url':original}
            if citation not in citations:
                citations.append(citation)
            run['listings'][jid] = dict(job, id=jid, portal_sources=citations)
            if not result['duplicate']:
                state['jobs'][jid].update(discovery=job['discovery'], application_route=method, source_url=original)
            accepted += 1
        run['updated_at'] = utc()
        return {'search_id':run['id'], 'accepted':accepted, 'excluded':len(rows)-accepted}
    if op == 'portal-source-finish':
        source = data.get('source')
        require(source in PORTALS and data.get('status') in {'complete','partial','blocked','failed'}, 'Invalid source completion.')
        note = data.get('note')
        require(isinstance(note,str) and 0 < len(note.strip()) <= 2000, 'Record actual search scope, limits or blocker.')
        coverage = {'source':source, 'status':data['status'], 'scope':note, 'warning':note if data['status']!='complete' else '',
                    'fetched_at':utc(), 'results':sum(any(c['source']==source for c in j.get('portal_sources',[])) for j in run['listings'].values()),
                    'count':sum(e['source']==source for e in run['exclusions']), 'cached':False}
        coverage['count'] += coverage['results']
        run['source_checks'][source] = coverage
        run['coverage'] = list(run['source_checks'].values())
        run['updated_at'] = utc()
        return {'search_id':run['id'], 'source':source, 'status':coverage['status']}
    if op == 'portal-search-finish':
        require(all(s in run['source_checks'] for s in PORTALS), 'Record the outcome for both LinkedIn and Indeed; do not silently substitute feeds.')
        statuses = [run['source_checks'][s]['status'] for s in PORTALS]
        run['status'] = 'complete' if all(s=='complete' for s in statuses) else 'failed' if all(s in {'blocked','failed'} for s in statuses) else 'partial'
        run['updated_at'] = utc()
        return {'search_id':run['id'], 'status':run['status'], 'count':len(run['job_ids'])}
    raise ValueError('Unknown portal search operation.')
