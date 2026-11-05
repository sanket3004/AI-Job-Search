"""Evidence-backed email updates supplied by an authorized host mail connector."""
import hashlib
import re
import uuid
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

STATUSES = {'Application received', 'Under review', 'Assessment', 'Interview', 'Rejected', 'Offer', 'Withdrawn', 'Unknown'}
CANONICAL = {'Application received':'Submitted', 'Interview':'Interview', 'Rejected':'Rejected', 'Offer':'Offer', 'Withdrawn':'Withdrawn'}
ORDER = {'Application received':0, 'Under review':1, 'Assessment':2, 'Interview':3, 'Offer':4}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def string(data, key, limit=1000):
    value = data.get(key)
    check(isinstance(value, str) and bool(value.strip()) and len(value) <= limit, 'Invalid ' + key)
    return value.strip()


def blocked(job, item):
    if job['status'] in {'Submitting', 'Submission uncertain'}:
        return 'Resolve the uncertain submission before applying an email outcome.'
    previous = job.get('email_update', {})
    if previous and item['received_at'] <= previous['received_at']:
        return 'This email is older than or equal to the latest applied email.'
    old = previous.get('status')
    target = CANONICAL.get(item['suggested_status'])
    if job['status'] in {'Rejected','Offer','Withdrawn','Expired'} and target != job['status']:
        return 'This conflicts with a final application outcome; review with your agent.'
    current_stage = old or {'Submitted':'Application received', 'Interview':'Interview', 'Offer':'Offer'}.get(job['status'])
    if current_stage in ORDER and item['suggested_status'] in ORDER and ORDER[item['suggested_status']] < ORDER[current_stage]:
        return 'This would move the application backward; review with your agent.'
    return ''


def apply_update(state, item, job_id):
    check(job_id in state['jobs'], 'Choose a saved application.')
    check(item['suggested_status'] != 'Unknown', 'Unknown outcomes cannot change application status.')
    job = state['jobs'][job_id]
    reason = blocked(job, item)
    check(not reason, reason)
    item.update(job_id=job_id, review='applied', applied_at=stamp())
    job['email_update'] = {'status':item['suggested_status'], 'received_at':item['received_at'], 'email_id':item['id']}
    target = CANONICAL.get(item['suggested_status'])
    if target:
        job['status'] = target
        job['review'] = None
        job['blocker'] = ''
        for assistance in state.get('assistance', {}).values():
            if assistance['job_id'] == job_id and assistance['status'] == 'open':
                assistance.update(status='resolved', resolved_at=stamp())
    job['notes'].append({'at':stamp(), 'kind':'email-update', 'text':item['summary'], 'email_id':item['id']})
    job['updated_at'] = stamp()


def apply(state, data):
    op = data['op']
    tracking = state.setdefault('email_tracking', {'config':{}, 'checks':{}, 'messages':{}})
    config = tracking['config']
    if op == 'email-config':
        account = string(data, 'account', 254).lower()
        check(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', account), 'Enter your Gmail account email.')
        check(type(data.get('enabled')) is bool and type(data.get('auto_apply')) is bool, 'Use explicit enable and auto-update choices.')
        tracking['config'] = {'provider':'gmail', 'account':account, 'enabled':data['enabled'], 'auto_apply':data['auto_apply'],
                              'revision':config.get('revision',0)+1, 'updated_at':stamp()}
        return {'configured':True, 'enabled':data['enabled']}
    if op == 'email-check-start':
        check(config.get('enabled'), 'Enable Gmail review in the dashboard first.')
        check(data.get('account', '').lower() == config['account'], 'Connected Gmail account differs from the approved account.')
        ids = data.get('job_ids')
        check(isinstance(ids,list) and bool(ids) and all(isinstance(i,str) and i in state['jobs'] for i in ids), 'Supply exact saved job IDs for this check.')
        cid = uuid.uuid4().hex[:12]
        tracking['checks'][cid] = {'id':cid, 'account':config['account'], 'config_revision':config['revision'],
            'job_ids':list(dict.fromkeys(ids)), 'scope':string(data,'scope',2000), 'started_at':stamp(), 'status':'running', 'count':0}
        return {'check_id':cid}
    if op == 'email-check-finish':
        run = tracking['checks'].get(data.get('check_id'))
        check(run is not None and run['status']=='running', 'Unknown or finished email check.')
        check(data.get('status') in {'complete','partial','failed'}, 'Invalid email check status.')
        run.update(status=data['status'], finished_at=stamp(), note=string(data,'note',2000))
        return {'check_id':run['id'], 'status':run['status']}
    if op == 'email-record':
        run = tracking['checks'].get(data.get('check_id'))
        check(run is not None and run['status']=='running', 'Start an email check first.')
        check(config.get('enabled') and run['config_revision']==config['revision'], 'Mail permission changed; start a new check.')
        mid = string(data,'message_id',128)
        check(re.fullmatch(r'[a-fA-F0-9]+',mid), 'Use the Gmail API message ID, not an RFC Message-ID header.')
        key = hashlib.sha256((run['account']+'|'+mid.lower()).encode()).hexdigest()[:24]
        if key in tracking['messages']:
            return {'email_id':key, 'duplicate':True}
        status = data.get('suggested_status')
        check(status in STATUSES, 'Invalid suggested email status.')
        received = datetime.fromisoformat(string(data,'received_at',50).replace('Z','+00:00'))
        check(received.tzinfo is not None and received <= datetime.now(timezone.utc)+timedelta(minutes=5), 'Use the actual timezone-aware message receipt time.')
        jid = data.get('job_id')
        check(jid is None or jid in run['job_ids'], 'Email match must belong to this check scope.')
        for field in ('match_confidence','classification_confidence'):
            check(data.get(field) in {'confirmed','uncertain'}, 'Label confidence confirmed or uncertain.')
        item = {'id':key, 'account':run['account'], 'message_id':mid, 'check_id':run['id'], 'job_id':jid,
                'source_url':'https://mail.google.com/mail/u/'+quote(run['account'], safe='@')+'/#all/'+mid,
                'received_at':received.astimezone(timezone.utc).isoformat(), 'recorded_at':stamp(),
                'sender':string(data,'sender',500), 'subject':string(data,'subject',500),
                'summary':string(data,'summary',2000), 'evidence':string(data,'evidence',2000),
                'match_reason':string(data,'match_reason',2000), 'suggested_status':status,
                'match_confidence':data['match_confidence'], 'classification_confidence':data['classification_confidence'], 'review':'pending'}
        tracking['messages'][key] = item
        run['count'] += 1
        if jid and status != 'Unknown':
            item['hold_reason'] = blocked(state['jobs'][jid], item)
            if config['auto_apply'] and not item['hold_reason'] and item['match_confidence']=='confirmed' and item['classification_confidence']=='confirmed':
                apply_update(state,item,jid)
        return {'email_id':key, 'duplicate':False, 'review':item['review']}
    if op in {'email-apply','email-dismiss'}:
        item = tracking['messages'].get(data.get('email_id'))
        check(item is not None and item['review']=='pending', 'Unknown or already reviewed email.')
        item['review_note'] = string(data,'note',1000)
        if op == 'email-dismiss':
            item.update(review='dismissed', reviewed_at=stamp())
        else:
            apply_update(state,item,data.get('job_id') or item['job_id'])
        return {'email_id':item['id'], 'review':item['review']}
    raise ValueError('Unknown email operation.')
