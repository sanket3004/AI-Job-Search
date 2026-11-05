'use strict';
let state = null, workspace = '', view = 'overview', selectedJob = null, lastPayload = '', busy = false;
let filter = 'All statuses', search = '', sort = 'relevance', band = 'All scores';
let rankData = {}, activeSearch = null, selectedSearch = 'latest', searchPending = false, formSeeded = false;
const titles = {email:'Email updates',settings:'Accounts & alerts', assistance:'Assistance',overview: 'Overview', jobs: 'Job pipeline', profile: 'My profile', documents: 'Documents', contacts: 'Contacts & drafts', activity: 'Activity', history: 'Search history'};
const $ = id => document.getElementById(id);
const jobs = () => Object.values(state?.jobs || {});
const label = value => String(value).replaceAll('_', ' ').replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
const date = value => value && !Number.isNaN(new Date(value).getTime()) ? new Date(value).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : 'Not recorded';
function el(tag, cls, text) { const node = document.createElement(tag); if(cls) node.className = cls; if(text !== undefined) node.textContent = String(text); return node; }
function add(parent, ...children) { children.filter(Boolean).forEach(child => parent.append(child)); return parent; }
function button(text, action, cls = 'quiet') { const b = el('button', cls, text); b.type = 'button'; b.addEventListener('click', action); return b; }
function external(text, url) { try { const u = new URL(url); if(!['http:','https:'].includes(u.protocol) || u.username || u.password) return el('span', 'muted', text); const a = el('a', '', text); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; } catch { return el('span', 'muted', text); } }
function pill(status) { const color = ['Ready for review','Offer','Interview'].includes(status) ? 'green' : ['Needs attention','Submission uncertain'].includes(status) ? 'amber' : ['Submitted','Filling','Submitting'].includes(status) ? 'blue' : ['Rejected','Expired','Withdrawn'].includes(status) ? 'red' : ''; return el('span', `pill ${color}`, status); }
function panel(title, subtitle) { const p = el('section','panel'); add(p, add(el('div','panel-head'), el('h2','',title), subtitle ? el('small','',subtitle) : null)); return p; }
function heading(title, subtitle, action) { return add(el('div','page-heading'), add(el('div'), el('div','eyebrow','YOUR JOB SEARCH'), el('h1','',title), el('p','',subtitle)), action); }
function empty(title, hint, action) { return add(el('div','empty'), el('strong','',title), el('p','',hint), action); }
function request(text) { $('prompt-text').value = `Use careerpilot with workspace "${workspace}". ${text}`; $('copy-status').textContent = ''; $('copy-prompt').textContent = 'Copy request'; $('prompt-dialog').showModal(); }
function ask(text, prompt, cls='primary') { return button(text, () => request(prompt), cls); }
function go(next, status) { view = next; if(status !== undefined) { filter = status; selectedSearch = 'all'; } document.querySelectorAll('[data-view]').forEach(n => { n.classList.toggle('active', n.dataset.view === view); if(n.dataset.view === view) n.setAttribute('aria-current','page'); else n.removeAttribute('aria-current'); }); $('breadcrumb').textContent = `Workspace / ${titles[view]}`; render(); }
function valueNode(value) {
  if(value === null || value === undefined || value === '') return el('span','muted','Not provided');
  if(Array.isArray(value)) { if(!value.length) return el('span','muted','None recorded'); const list = el('ul','value-list'); value.forEach(v => add(list, add(el('li'),valueNode(v)))); return list; }
  if(typeof value === 'object') { const dl = el('dl','facts'); Object.entries(value).forEach(([k,v]) => add(dl,el('dt','',label(k)),add(el('dd'),valueNode(v)))); return dl; }
  return el('span','prose',value);
}
function jobRow(job, showReason=false) { const row = el('div','row'); add(row, add(el('div'),button(job.title,()=>openJob(job.id),'text-button'),el('small','',`${job.company} · ${job.location || 'Location not recorded'}`),el('small','',`Relevance ${rankData[job.id]?.score ?? 0}/100 · Posted ${posted(job)?new Date(posted(job)).toLocaleDateString():'Unknown'}`),showReason ? el('p','muted',nextAction(job)) : null),pill(job.status)); return row; }
function nextAction(job) {
  if(job.status === 'Needs attention') return job.next_action || job.blocker || 'Review the blocker with your AI.';
  if(['Submission uncertain','Submitting'].includes(job.status)) return 'Check the application portal for confirmation before retrying.';
  if(job.status === 'Ready for review') return 'Review the saved answers and documents before submitting.';
  if(job.status === 'Saved') return 'Review fit and choose whether to prepare an application.';
  if(['Selected','Preparing'].includes(job.status)) return 'Prepare documents and continue the application.';
  if(job.status === 'Filling') return 'Reinspect the current form and continue from the saved checkpoint.';
  return 'Review the latest notes and any follow-up needed.';
}
function overview(root) {
  const all = jobs(), attention = all.filter(j=>['Needs attention','Submission uncertain','Submitting'].includes(j.status)), ready = all.filter(j=>j.status==='Ready for review');
  add(root,heading('Your next chapter, in view.','A clear picture of your search, from first match to final offer.',ask('Continue with AI','Show my current progress and continue the next eligible job.')));
  const hasProfile = Boolean(Object.keys(state.profile).length);
  add(root,add(el('section','hero'),add(el('div'),el('div','eyebrow',hasProfile ? 'KEEP MOVING FORWARD' : 'LET’S GET STARTED'),el('h2','',hasProfile ? (ready.length ? `${ready.length} application${ready.length===1?' is':'s are'} ready for your review.` : attention.length ? `${attention.length} application${attention.length===1?' needs':'s need'} your attention.` : 'Your search starts with the right opportunities.') : 'A good search starts with your story.'),el('p','',hasProfile ? 'Check your matches, see what needs attention, and pick up where you left off.' : 'Ask your AI to import a resume or guide you through a fresh profile. Your confirmed information will appear here.')),hasProfile ? button(ready.length?'Review applications':'Explore pipeline',()=>go('jobs',ready.length?'Ready for review':'All statuses'),'primary') : ask('Set up my profile','Help me create a fresh profile. Offer resume import, LinkedIn or Indeed export, or guided questions. Show me the proposed facts before saving.')));
  const stats = el('div','stats');
  [[all.length,'Saved opportunities','Every job in your workspace','All statuses'],[ready.length,'Ready for review','Prepared, awaiting your next step','Ready for review'],[attention.length,'Needs attention','Blocked or awaiting confirmation','Attention'],[all.filter(j=>['Submitted','Interview','Offer'].includes(j.status)).length,'Submitted & progressing','Submitted, interview, or offer','Progressing']].forEach(([n,title,hint,status])=>{const b=button('',()=>go('jobs',status),'stat');add(b,el('span','label',title),el('strong','',n),el('small','',hint));add(stats,b);}); add(root,stats);
  const grid = el('div','grid'), left=el('div'), right=el('div'); const recent=panel('Recent opportunities',`${all.length} total`);
  all.sort((a,b)=>b.updated_at.localeCompare(a.updated_at)).slice(0,5).forEach(j=>add(recent,jobRow(j)));
  if(!all.length) add(recent,empty('Your pipeline is clear.','Find jobs using your confirmed profile or give your AI a job link.',button('Search jobs',()=>{$('role-input').focus();$('role-input').scrollIntoView({behavior:'smooth',block:'center'});},'quiet'))); add(left,recent);
  const needs = panel('Next decisions', `${attention.length + ready.length} to review`);
  [...attention,...ready].slice(0,5).forEach(j=>add(needs,jobRow(j,true)));
  if(!attention.length && !ready.length) add(needs,el('p','muted','No blocked or ready applications right now. New decisions will appear as your search progresses.')); add(right,needs);
  const steps=panel('Your search, step by step'); const stepsList=el('div','steps');
  [[hasProfile,'Build your profile','Confirmed facts and job preferences.'],[all.length>0,'Find your matches','Evidence, strengths, and gaps.'],[all.some(j=>j.documents.length),'Prepare applications','Tailored documents and form answers.'],[all.some(j=>['Submitted','Interview','Offer'].includes(j.status)),'Review and follow through','Choose when to submit and track outcomes.']].forEach(([done,title,hint],i)=>add(stepsList,add(el('div',`step ${done?'done':''}`),el('span','step-num',done?'✓':i+1),add(el('div'),el('h3','',title),el('p','',hint))))); add(steps,stepsList);add(right,steps); add(root,add(grid,left,right));
}

const runs = () => Object.values(state?.searches || {});
function chosenRun() { return selectedSearch === 'all' ? null : selectedSearch === 'latest' ? runs().at(-1) : state.searches?.[selectedSearch]; }
function currentJobs() {
  const run = chosenRun();
  if(!run) return jobs();
  return run.job_ids.map(id => ({...state.jobs[id], ...run.listings[id], status:state.jobs[id]?.status || 'Saved'}));
}
function scoreFor(job) { return chosenRun()?.listings?.[job.id]?.search_relevance || rankData[job.id] || {score:0,band:'Low',location_note:'Run a search to compare location.'}; }
function fullDate(value) { return value && !Number.isNaN(new Date(value).getTime()) ? new Date(value).toLocaleString([], {year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : 'Unknown'; }
function posted(job) { return job.discovery?.published_at || null; }
function postedCell(job) {
  const raw = posted(job), p = el('span','posted-date');
  if(!raw) return add(p,el('span','','Unknown'),el('small','','Not provided by source'));
  const age = Math.max(0,Date.now()-new Date(raw).getTime()), days=Math.floor(age/86400000);
  add(p,el('span','',new Date(raw).toLocaleDateString([],{year:'numeric',month:'short',day:'numeric'})),el('small','',days===0?'Within 24 hours':days===1?'1 day ago':`${days} days ago`));p.title=fullDate(raw);return p;
}
function period(run) { return ({any:'Any posting date','1':'Last 24 hours','7':'Last 7 days','30':'Last 30 days'})[run.posted_within] || 'Any posting date'; }
function runStatus(run) { return run.status === 'running' && activeSearch !== run.id ? 'Interrupted' : label(run.status); }
function searchOverview(root, run) {
  if(!run) return;
  const p=el('section','run-summary');
  add(p,add(el('div'),el('h2','',`${run.role} · ${run.location}`),el('p','muted',`${period(run)} · Search started ${fullDate(run.created_at)} · ${runStatus(run)}`)),el('span','pill',`${run.job_ids.length} results`));
  if(run.error)add(p,el('p','warning-text',run.error));
  const details=el('details','coverage');add(details,el('summary','','Source fetch times & coverage'));
  run.coverage.forEach(c=>add(details,add(el('div','coverage-row'),el('strong','',c.source),el('span','',`${c.results ?? 0} results · ${c.count} feed listings · Fetched ${fullDate(c.fetched_at)}${c.cached?' · Cached':''}`),el('small','',`${c.scope} ${c.date_excluded||0} role candidates excluded by the posting-date filter. ${c.skipped||0} invalid/expired rows skipped.`),c.warning?el('p','warning-text',c.warning):null)));
  if(!run.coverage.length)add(details,el('p','muted',activeSearch===run.id?'Fetching public sources…':'No source results were saved.'));
  add(p,details);add(root,p);
}
function jobList(root) {
  add(root,heading('Every match. In perspective.','All retrieved role candidates are kept, including low scores and location mismatches.'));
  const run=chosenRun();searchOverview(root,run);
  const toolbar=el('div','toolbar'), input=el('input');input.type='search';input.placeholder='Filter these results…';input.setAttribute('aria-label','Filter results');input.value=search;
  const scope=el('select');scope.setAttribute('aria-label','Result list');
  [['all','All saved jobs'],['latest','Latest search'],...runs().slice().reverse().map(r=>[r.id,`${r.role} · ${fullDate(r.created_at)}`])].forEach(([v,t])=>{const o=el('option','',t);o.value=v;scope.append(o);});scope.value=selectedSearch;
  const scoreFilter=el('select');scoreFilter.setAttribute('aria-label','Score range');['All scores','Strong','Possible','Low'].forEach(s=>{const o=el('option','',s==='Low'?'Low matches (0–44)':s==='Possible'?'Possible (45–74)':s==='Strong'?'Strong (75–100)':s);o.value=s;scoreFilter.append(o);});scoreFilter.value=band;
  const status=el('select');status.setAttribute('aria-label','Filter job status');['All statuses','Attention','Progressing','Saved','Selected','Preparing','Filling','Ready for review','Needs attention','Submitting','Submission uncertain','Submitted','Interview','Offer','Rejected','Withdrawn','Expired'].forEach(s=>{const o=el('option','',s);o.value=s;status.append(o);});status.value=filter;
  const order=el('select');order.setAttribute('aria-label','Sort jobs');[['relevance','Highest relevance'],['lowest','Lowest relevance'],['newest','Newest posting'],['fit','Highest AI fit'],['company','Company A–Z']].forEach(([v,t])=>{const o=el('option','',t);o.value=v;order.append(o);});order.value=sort;
  const results=el('div');
  const update=()=>{
    results.replaceChildren();const all=currentJobs(), needle=search.toLowerCase();
    const ranked=[...all].sort((a,b)=>scoreFor(b).score-scoreFor(a).score||a.title.localeCompare(b.title)||a.id.localeCompare(b.id));const positions=new Map(ranked.map((j,i)=>[j.id,i+1]));
    const list=ranked.filter(j=>(band==='All scores'||scoreFor(j).band===band)&&(filter==='All statuses'||j.status===filter||(filter==='Attention'&&['Needs attention','Submitting','Submission uncertain'].includes(j.status))||(filter==='Progressing'&&['Submitted','Interview','Offer'].includes(j.status)))&&`${j.title} ${j.company} ${j.location} ${j.description}`.toLowerCase().includes(needle));
    list.sort((a,b)=>sort==='lowest'?scoreFor(a).score-scoreFor(b).score:sort==='newest'?(Date.parse(posted(b))||0)-(Date.parse(posted(a))||0):sort==='fit'?(b.evaluation?.score??-1)-(a.evaluation?.score??-1):sort==='company'?a.company.localeCompare(b.company):positions.get(a.id)-positions.get(b.id));
    add(results,el('div','count-label',`${list.length} of ${all.length} postings · ${all.filter(j=>scoreFor(j).band==='Low').length} low matches in this list · No minimum-score cutoff.`),el('p','ranking-note','Relevance is an automatic word-and-location comparison, not an AI assessment of your qualifications. Open a job to see the breakdown.'));
    if(!list.length)return add(results,empty('No postings in this view.',all.length?'Clear your filters to show every result.':'Try a broader role or date range. Check source coverage above; an empty list does not mean there are no jobs elsewhere.'));
    const table=el('table'), head=el('tr');['Rank','Opportunity','Relevance','Posted','Status'].forEach(t=>add(head,el('th','',t)));add(table,add(el('thead'),head));const body=el('tbody');
    list.forEach(j=>{const score=scoreFor(j), row=el('tr');add(row,el('td','rank-number',`#${positions.get(j.id)}`),add(el('td'),button(j.title,()=>openJob(j.id),'text-button'),el('small','company-line',j.company),el('small','',j.location||'Location not supplied'),external(j.source+' ↗',j.url)),add(el('td'),add(el('span',`score-value ${score.band.toLowerCase()}`),el('strong','',score.score),el('small','',' / 100')),el('small','',score.band+' relevance'),el('small','location-note',score.location_note),j.evaluation?.score!==undefined?el('small','',`AI fit: ${j.evaluation.score}/100`):null),add(el('td'),postedCell(j)),add(el('td'),pill(j.status)));add(body,row);});add(table,body);add(results,add(el('div','table-wrap'),table));
  };
  input.addEventListener('input',()=>{search=input.value;update();});status.addEventListener('change',()=>{filter=status.value;update();});order.addEventListener('change',()=>{sort=order.value;update();});scoreFilter.addEventListener('change',()=>{band=scoreFilter.value;update();});scope.addEventListener('change',()=>{selectedSearch=scope.value;search='';band='All scores';filter='All statuses';render();});add(root,add(toolbar,input,scope,scoreFilter,status,order),results);update();
}
function historyPage(root) {
  add(root,heading('Every search has a story.','Each run keeps its own dated result list. Running another search never replaces an earlier list.'));
  if(!runs().length)return add(root,empty('Your first search starts above.','Enter a role, a location, and a posting-date range. Your result lists will appear here.'));
  [...runs()].reverse().forEach(run=>{const p=panel(`${run.role} · ${run.location}`,runStatus(run));add(p,el('p','',`${fullDate(run.created_at)} · ${period(run)} · ${run.job_ids.length} postings`),el('p','muted',`Last saved ${fullDate(run.updated_at)}. Source fetch times are listed inside the result list.`),button('Open this result list',()=>{selectedSearch=run.id;search='';band='All scores';filter='All statuses';go('jobs');},'primary'));add(root,p);});
}
async function startSearch(event) {
  event.preventDefault();if(searchPending||activeSearch)return;searchPending=true;updateSearchStatus();
  try{
    const response=await fetch('api/search',{method:'POST',headers:{'Content-Type':'application/json','X-CareerPilot-Request':'search'},body:JSON.stringify({role:$('role-input').value,location:$('location-input').value,posted_within:$('posted-input').value,include_unknown_dates:$('unknown-dates').checked})});
    if(!response.ok)throw new Error(await response.text());const result=await response.json();selectedSearch=result.search_id;activeSearch=result.search_id;search='';filter='All statuses';band='All scores';sort='relevance';go('jobs');await refresh();
  }catch(error){$('search-feedback').textContent=error.message||'Search could not start. Check the server and try again.';}
  finally{searchPending=false;updateSearchStatus(false);}
}
function updateSearchStatus(updateText=true) {
  const running=searchPending||Boolean(activeSearch);$('start-search').disabled=running;$('start-search').textContent=running?'Searching…':'Search jobs ↗';
  if(!updateText)return;const latest=runs().at(-1);
  $('search-feedback').textContent=running?'Fetching public sources. Results appear as each source completes; you can browse while this runs.':latest?`${runStatus(latest)} · ${latest.job_ids.length} results saved · ${fullDate(latest.created_at)}. Open Search history for previous lists.`:'';
}
function profilePage(root) {
  add(root,heading('Your professional story',`Confirmed profile · Revision ${state.profile_revision}`,ask('Update with AI','Help me update my profile from a resume, profile export, or confirmed answers. Show the changes before applying them.')));
  if(!Object.keys(state.profile).length) add(root,empty('No profile saved yet.','Import a resume or answer a few questions with your AI.',ask('Create my profile','Help me create a fresh profile.')));
  const summary=panel('Profile & preferences'); const regular=Object.fromEntries(Object.entries(state.profile).filter(([k])=>!k.startsWith('_')));add(summary,valueNode(regular));if(Object.keys(regular).length)add(root,summary);
  if(state.profile._provenance) {const sources=panel('Sources behind your profile');add(sources,valueNode(state.profile._provenance));add(root,sources);}
  const imports=Object.values(state.profile_imports||{}); if(imports.length){const p=panel('Import review history');imports.reverse().forEach(record=>{const d=el('details');add(d,el('summary','',`${record.applied?'Applied':record.base_revision===state.profile_revision?'Awaiting review':'Stale preview'} · ${date(record.created_at)}`),valueNode({changes:record.changes,sources:record.sources,confirmation:record.user_confirmation||'Not confirmed'}));add(p,d);});add(root,p);}
}
function documentLink(job,doc) { const a=el('a','',`${label(doc.kind)} · ${doc.original_name} ↓`);a.href=`api/document?job=${encodeURIComponent(job.id)}&sha=${encodeURIComponent(doc.sha256)}`;a.download=doc.original_name;return a; }
function documentsPage(root) { add(root,heading('Documents for every opportunity','The exact registered files saved against each application.'));const all=jobs().filter(j=>j.documents.length);if(!all.length)return add(root,empty('No application documents yet.','Ask your AI to tailor a resume for a selected job.',ask('Prepare documents','Help me select jobs and prepare tailored application documents.')));all.forEach(j=>{const p=panel(j.company+' · '+j.title,j.status);j.documents.forEach(d=>add(p,add(el('div','row'),add(el('div'),documentLink(j,d),el('small','','Saved file · Download checks that its contents still match the registered version.')))));add(root,p);}); }
function contactCard(contact) { const c=el('div','detail-section');add(c,el('h3','',contact.name),el('p','',`${contact.role} · ${contact.company}`),pill(`${label(contact.relationship)} connection`),el('p','muted',contact.relevance));if(contact.email)add(c,el('p','',contact.email));add(c,add(el('div','link-row'),external('Source ↗',contact.source_url),contact.profile_url?external('Professional profile ↗',contact.profile_url):null,contact.email_source_url?external('Published email source ↗',contact.email_source_url):null),el('small','',`Checked ${date(contact.checked_at)}`));return c; }
function draftCard(draft) { return add(el('div','detail-section'),el('h3','',`Draft to ${draft.recipient}`),el('small','',`${draft.channel} · Draft only · ${date(draft.at)}`),el('p','prose',draft.text)); }
function contactsPage(root) { add(root,heading('People behind the opportunity','Sourced contacts and saved outreach drafts. Sending is a separate action.'));const all=jobs().filter(j=>j.contacts.length||j.outreach.length);if(!all.length)return add(root,empty('No contacts or drafts yet.','Your AI can research relevant recruiters and draft a message for a selected role.',ask('Research contacts','Help me select a role and research published recruiting contacts. Draft outreach without sending it.')));all.forEach(j=>{const p=panel(j.company+' · '+j.title);j.contacts.forEach(c=>add(p,contactCard(c)));j.outreach.forEach(d=>add(p,draftCard(d)));add(root,p);}); }
function activityPage(root) {
  add(root,heading('A record of your progress','Saved actions and permission history. This is not a live agent log.'));
  if(state.authorizations.length){const p=panel('Recorded submission permissions');add(p,el('p','muted','These are historical permission records. The agent must validate the current application and documents before submitting.'));[...state.authorizations].reverse().forEach(g=>{const d=el('details');const status=g.revoked?'Revoked':new Date(g.expires_at)<new Date()?'Expired':'Recorded';add(d,el('summary','',`${status} · Expires ${date(g.expires_at)}`),el('p','prose',g.user_instruction),valueNode({jobs:Object.keys(g.fingerprints).map(id=>state.jobs[id]?`${state.jobs[id].company} · ${state.jobs[id].title} (${id})`:id),used:g.used}));add(p,d);});add(root,p);}
  const p=panel('Workspace activity',`${state.events.length} saved actions`);if(!state.events.length)add(p,empty('A fresh start.','Your saved actions will appear here.'));
  [...state.events].reverse().forEach(e=>{const job=state.jobs[e.job_id];const entry=el('div','timeline-item');add(entry,el('span','date',date(e.at)),el('h3','',label(e.op)),job?button(`${job.company} · ${job.title}`,()=>openJob(job.id),'text-button'):null);const d=el('details');add(d,el('summary','','Saved result'),valueNode(e.result));add(entry,d);add(p,entry);});add(root,p);
}
function section(parent,title,...content){add(parent,add(el('section','detail-section'),el('h3','',title),...content));}
function renderJob() {
  const base=state.jobs[selectedJob]; const snapshot=chosenRun()?.listings?.[selectedJob]; const j=base ? {...base,...snapshot,status:base.status} : null; if(!j){$('detail').close();return;} const root=$('detail-content');root.replaceChildren();const title=el('h2','',j.title);title.id='detail-title';add(root,title,el('p','muted',`${j.company} · ${j.location||'Location not recorded'}`),add(el('div','detail-meta'),pill(j.status),el('small','',`Job ${j.id}`)),add(el('div','link-row'),external('Open posting ↗',j.url),j.checkpoint?external('Open application page ↗',j.checkpoint.page_url):null),el('p','muted',`Source: ${j.source} · Retrieved ${date(j.retrieved_at)}`));
  const callout=el('div',`callout ${['Needs attention','Submission uncertain','Submitting'].includes(j.status)?'warning':''}`);add(callout,el('h3','','Next step'),el('p','',nextAction(j)),j.status==='Needs attention'?el('p','',j.blocker):null,ask('Discuss with AI',`Review job ${j.id} (${j.title} at ${j.company}). Explain its current state and help with the next step. Do not submit or send outreach without my authorization.`,'quiet'));add(root,callout);
  if(j.email_update)section(root,'Latest company response',pill(j.email_update.status),el('p','muted',`Email received ${fullDate(j.email_update.received_at)}`),button('View email evidence',()=>{$('detail').close();go('email');}));
  section(root,'Posting & search details',valueNode({posted:fullDate(posted(j)),source_fetched:fullDate(j.discovery?.fetched_at),saved:fullDate(j.created_at)}));
  section(root,'Search relevance',valueNode(scoreFor(j)));
  section(root,'AI fit assessment',j.evaluation?valueNode(j.evaluation):el('p','muted','No assessment saved yet.'));
  section(root,'Application documents',...j.documents.map(d=>add(el('p'),documentLink(j,d))),!j.documents.length?el('p','muted','No documents registered.'):null);
  if(j.checkpoint){section(root,'Saved form review',el('p','',`${j.checkpoint.step} · ${date(j.checkpoint.recorded_at)}`),el('p','prose',j.checkpoint.observation),el('p','muted',`Profile revision ${j.checkpoint.profile_revision} · Current revision ${state.profile_revision}. Saved evidence does not guarantee the website session is still available.`),valueNode({answers:j.checkpoint.answers,unresolved:j.checkpoint.unresolved}));}
  if(j.contacts.length)section(root,'Recruiting contacts',...j.contacts.map(contactCard));if(j.outreach.length)section(root,'Outreach drafts',...j.outreach.map(draftCard));
  if(j.notes.length)section(root,'Notes & outcomes',...j.notes.map(n=>add(el('div','row'),add(el('div'),el('small','',`${date(n.at)}${n.kind?' · '+label(n.kind):''}`),el('p','prose',n.text)))));
  if(j.attempts.length)section(root,'Submission attempts',valueNode(j.attempts));
  const description=el('details');add(description,el('summary','','Full saved job description'),el('p','prose',j.description));add(root,description);
}
function openJob(id){selectedJob=id;renderJob();if(!$('detail').open)$('detail').showModal();}
function render(){if(!state)return;const root=$('content');root.replaceChildren();({overview,jobs:jobList,profile:profilePage,documents:documentsPage,contacts:contactsPage,activity:activityPage,history:historyPage,settings:settingsPage,assistance:assistancePage,email:emailPage})[view](root);if($('detail').open)renderJob();}
async function refresh(){
  if(busy)return;busy=true;
  try{const response=await fetch('api/state',{cache:'no-store'});if(!response.ok)throw new Error('Workspace unavailable');const payload=await response.json();const signature=JSON.stringify(payload);state=payload.state;workspace=payload.workspace;rankData=payload.rankings||{};activeSearch=payload.active_search||null;updateSearchStatus();if(!formSeeded){const last=runs().at(-1);$('role-input').value=last?.role||state.profile.target_roles?.[0]||'';$('location-input').value=last?.location||state.profile.location||'';$('posted-input').value=last?.posted_within||'any';$('unknown-dates').checked=last?.include_unknown_dates||false;formSeeded=true;}$('workspace').textContent=workspace;
    if(signature!==lastPayload && view!=='settings' && !(view==='email' && $('content').contains(document.activeElement))){lastPayload=signature;const active=document.activeElement;const isSearch=active?.type==='search';const caret=isSearch?active.selectionStart:null;render();if(isSearch){const input=document.querySelector('input[type="search"]');input?.focus();if(input&&caret!==null)input.setSelectionRange(caret,caret);}}
    $('sync').textContent=`Synced ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'})}`;$('error').hidden=true;
  }catch{ $('sync').textContent='Disconnected';$('error').hidden=false;$('error').textContent=state?'Connection lost. You are viewing the last successful snapshot. Restart the dashboard or refresh when the workspace is available.':'Cannot load this workspace. Check that the dashboard server is still running, then refresh.';}finally{busy=false;}
}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
document.querySelector('.brand').addEventListener('click',event=>{event.preventDefault();go('overview');});
$('job-search-form').addEventListener('submit',startSearch);
$('refresh').addEventListener('click',refresh);$('close-detail').addEventListener('click',()=>$('detail').close());$('close-prompt').addEventListener('click',()=>$('prompt-dialog').close());
$('copy-prompt').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('prompt-text').value);$('copy-status').textContent='Copied. Paste it into your AI chat.';}catch{$('prompt-text').focus();$('prompt-text').select();$('copy-status').textContent='Select and copy the request above, then paste it into your AI chat.';}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});setInterval(()=>{if(!document.hidden)refresh();},5000);refresh();

async function localAction(action, data) {
  const response=await fetch('api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-CareerPilot-Request':action},body:JSON.stringify(data)});
  if(!response.ok)throw new Error(await response.text());
  return response.json();
}
function settingField(form, name, title, value='', type='text') {
  const wrap=el('label','settings-field',title), input=el('input');input.name=name;input.type=type;
  if(type==='checkbox')input.checked=Boolean(value);else input.value=value;
  input.autocomplete=type==='password'?'new-password':'off';
  add(form,add(wrap,input));return input;
}
function settingsForm(root, title, kind, fields, description) {
  const p=panel(title), f=el('form','settings-form');add(p,el('p','muted',description));
  fields.forEach(args=>settingField(f,...args));
  const submit=el('button','primary','Save settings');submit.type='submit';const status=el('p');status.setAttribute('role','status');add(f,submit,status);
  f.addEventListener('submit',async event=>{event.preventDefault();submit.disabled=true;const data={kind};
    f.querySelectorAll('input').forEach(i=>data[i.name]=i.type==='checkbox'?i.checked:i.value);
    try{await localAction('settings',data);f.querySelectorAll('input[type=password]').forEach(i=>i.value='');status.textContent='Saved securely. Reload settings to see the updated site list.';}catch(e){status.textContent=e.message;}finally{submit.disabled=false;}
  });add(root,add(p,f));return p;
}
async function settingsPage(root) {
  add(root,heading('Accounts & phone alerts','Reusable signup details, site permissions, and Telegram delivery.'));
  try {
    const response=await fetch('api/settings',{cache:'no-store'});if(!response.ok)throw new Error('Could not unlock settings for this computer user.');
    const data=await response.json();if(view!=='settings'||!root.isConnected)return;
    if(!data.supported){add(root,el('p','warning-text','Secure settings require Windows. On other systems use browser password-manager autofill.'));return;}
    settingsForm(root,'Default signup details','signup',[
      ['first_name','First name',data.signup.first_name],['last_name','Last name',data.signup.last_name],['email','Account email',data.signup.email,'email'],['phone','Phone',data.signup.phone],['city','City',data.signup.city],['country','Country',data.signup.country]
    ],'Saved separately from your confirmed resume profile. Passwords are unique per career site.');
    settingsForm(root,'Approve or update a career site','site',[
      ['url','Exact career-site URL (https://…)'],['username','Login email / username (blank uses default email)'],['password','Password (blank keeps saved password; new signup generates one)','','password'],['allow_login','Allow the agent to log in',false,'checkbox'],['allow_signup','Allow the agent to create an account',false,'checkbox']
    ],'Permissions apply only to this exact HTTPS origin, including its subdomain. Saving replaces its permissions. Account creation does not authorize job submission.');
    const sites=panel('Approved sites');Object.entries(data.sites).forEach(([origin,site])=>add(sites,add(el('div','row'),add(el('div'),el('strong','',origin),el('p','muted',`${site.username||'Default email'} · Login ${site.allow_login?'allowed':'off'} · Signup ${site.allow_signup?'allowed':'off'} · Password ${site.password_saved?'saved':'not saved'}`)),button('Remove',async()=>{try{await localAction('settings',{kind:'remove-site',url:origin});render();}catch(e){alert(e.message);}}))));add(root,sites);
    const telegram=settingsForm(root,'Telegram phone notifications','telegram',[
      ['token','Bot token (blank keeps saved token)','','password'],['chat_id','Your private Telegram chat ID',data.telegram.chat_id],['enabled','Enable phone alerts',data.telegram.enabled,'checkbox']
    ],'In Telegram, create a bot with @BotFather (/newbot), then open your bot and send /start. Paste its token here, never in an AI chat. Use Find my Telegram chat below and select your own account. Only request and job IDs are sent; details remain on your laptop.');
    const pairing=el('div');add(telegram,button('Find my Telegram chat',async()=>{pairing.textContent='Looking for your /start message…';try{const result=await localAction('telegram-chats',{token:telegram.querySelector('[name=token]').value});pairing.replaceChildren();if(!result.chats.length)pairing.textContent='Send /start to your bot in Telegram, then try again.';result.chats.forEach(chat=>add(pairing,button(`Use ${chat.name} ${chat.username?'@'+chat.username:''} (${chat.id})`,()=>{telegram.querySelector('[name=chat_id]').value=chat.id;pairing.textContent='Chat selected. Enable alerts and Save settings.';})));}catch(e){pairing.textContent=e.message;}}),pairing);
    const testStatus=el('p');testStatus.setAttribute('role','status');add(telegram,button('Send test to my phone',async()=>{testStatus.textContent='Sending…';try{await localAction('telegram-test',{});testStatus.textContent='Telegram accepted the test. Check your phone.';}catch(e){testStatus.textContent=e.message;}}),testStatus);
    add(root,el('p','muted','Keep the laptop awake, online, and the application agent running. Chrome Remote Desktop must be set up separately. Alerts do not start or resume an AI session. Existing failed alerts can be retried from Assistance.'),button('Reload saved settings',()=>render()));
  }catch(e){add(root,el('p','warning-text',e.message));}
}
function assistancePage(root) {
  add(root,heading('A little help, then onward.','Resolve the blocker through Chrome Remote Desktop, then return the job to the queue.'));
  const items=Object.values(state.assistance||{}).reverse();
  if(!items.length)add(root,empty('No assistance requests','Blocked applications will appear here, with phone delivery status.'));
  items.forEach(item=>{const j=state.jobs[item.job_id],p=panel(j?`${j.title} · ${j.company}`:item.job_id,`${date(item.created_at)} · ${item.status}`);
    add(p,el('small','',`Request ${item.id} · Phone alert: ${item.delivery}`),el('p','prose',item.reason),el('p','muted',item.next_action),el('p','warning-text',item.status==='open'?(item.error||''):''));
    if(item.status==='open'){
      if(item.delivery!=='sent')add(p,button('Retry notification',async()=>{try{await localAction('assistance-retry',{request_id:item.id});await refresh();}catch(e){alert(e.message);}}));
      const note=el('input');note.placeholder='What did you resolve?';note.setAttribute('aria-label','Resolution note');
      add(p,note,button('Resolved — return to queue',async()=>{if(!note.value.trim()){note.focus();return;}try{await localAction('assistance-resume',{job_id:item.job_id,note:note.value});await refresh();}catch(e){alert(e.message);}},'primary'),ask('Continue with AI',`Inspect job ${item.job_id} and continue it after the blocker has been resolved.`,'quiet'));
    }add(root,p);
  });
}

function responseStatus(j){return ['Rejected','Offer','Withdrawn','Expired','Interview','Submitting','Submission uncertain'].includes(j.status)?j.status:(j.email_update?.status||j.status);}
function emailPage(root) {
  const tracking=state.email_tracking||{}, config=tracking.config||{}, checks=Object.values(tracking.checks||{}).reverse(), messages=Object.values(tracking.messages||{}).sort((a,b)=>b.received_at.localeCompare(a.received_at));
  add(root,heading('Hear back. Stay on track.','Company responses, matched applications, and the evidence behind each update.',ask('Check Gmail with AI','Run the CareerPilot Gmail email-review workflow for my configured account and saved applications. Use only read-only Gmail tools, record the check scope and evidence, and finish the check honestly. Do not send replies or change mailbox labels.')));
  const setup=panel('Gmail access & update preferences');
  add(setup,el('p','muted','Connect Gmail through your AI host, then save the account and enable review here. This screen does not connect Gmail or run a background agent. “Check Gmail with AI” gives you a prompt to run in your agent chat.'));
  const f=el('form','settings-form');const account=settingField(f,'account','Gmail account email',config.account||'','email');account.required=true;
  const enabled=settingField(f,'enabled','Allow read-only review of emails related to my saved applications',config.enabled||false,'checkbox');
  const automatic=settingField(f,'auto_apply','Automatically apply confirmed matches and clear outcomes',config.auto_apply||false,'checkbox');
  const save=el('button','primary','Save email preferences');save.type='submit';const feedback=el('p');feedback.setAttribute('role','status');add(f,save,feedback);
  f.addEventListener('submit',async event=>{event.preventDefault();save.disabled=true;try{await localAction('email-config',{account:account.value,enabled:enabled.checked,auto_apply:automatic.checked});feedback.textContent='Saved. Run Check Gmail with AI to review messages.';}catch(e){feedback.textContent=e.message;}finally{save.disabled=false;}});add(root,add(setup,f));
  const last=checks.find(c=>c.status!=='running');add(root,el('p','muted',last?`Last check: ${fullDate(last.finished_at)} · ${last.status} · ${last.count} new messages · ${last.note}`:'No email check has completed yet. No Gmail messages have been read by this dashboard.'));
  const stats=el('div','stats');['Interview','Offer','Rejected'].forEach(status=>add(stats,add(el('div','stat'),el('span','label',status),el('strong','',jobs().filter(j=>responseStatus(j)===status).length))));add(stats,add(el('div','stat'),el('span','label','Needs review'),el('strong','',messages.filter(m=>m.review==='pending').length)));add(root,stats);
  const applications=panel('Application status');
  jobs().filter(j=>j.email_update||['Submitted','Interview','Rejected','Offer','Withdrawn','Expired','Submission uncertain'].includes(j.status)).forEach(j=>add(applications,add(el('div','row'),button(`${j.title} · ${j.company}`,()=>openJob(j.id),'text-button'),pill(responseStatus(j)))));
  if(!applications.querySelector('.row'))add(applications,el('p','muted','Submitted applications and email-confirmed responses will appear here.'));
  add(root,applications);
  const toolbar=el('div','toolbar'), select=el('select');select.setAttribute('aria-label','Email review filter');['All messages','Needs review','Applied','Dismissed'].forEach(v=>add(select,el('option','',v)));add(root,add(toolbar,select));const list=el('div');add(root,list);
  const draw=()=>{list.replaceChildren();const filtered=messages.filter(m=>select.value==='All messages'||m.review===({'Needs review':'pending',Applied:'applied',Dismissed:'dismissed'})[select.value]);
    if(!filtered.length)add(list,empty('No matching email updates','Your agent will record relevant messages here after a Gmail check.'));
    filtered.forEach(m=>{const j=state.jobs[m.job_id],p=panel(m.subject,`${fullDate(m.received_at)} · ${m.review}`);
      add(p,pill(m.suggested_status),el('p','muted',`From ${m.sender} · ${m.account}`),el('p','',j?`${j.title} · ${j.company}`:'Application match needs review'),el('p','prose',m.summary),external('Open source email in Gmail ↗',m.source_url));
      const evidence=el('details');add(evidence,el('summary','','Evidence & matching'),el('p','prose',m.evidence),el('p','muted',m.match_reason),el('p','muted',`Match: ${m.match_confidence} · Outcome: ${m.classification_confidence}`));add(p,evidence);
      if(m.hold_reason)add(p,el('p','warning-text',m.hold_reason));
      if(m.review==='pending'){
        const choice=el('select');choice.setAttribute('aria-label','Application for '+m.subject);const placeholder=el('option','','Choose application');placeholder.value='';add(choice,placeholder);jobs().forEach(job=>{const o=el('option','',`${job.title} · ${job.company}`);o.value=job.id;add(choice,o);});choice.value=m.job_id||'';
        const note=el('input');note.placeholder='Review note';note.setAttribute('aria-label','Review note for '+m.subject);const status=el('p');status.setAttribute('role','status');
        const act=async action=>{if(!note.value.trim()){status.textContent='Add a review note first.';return;}try{await localAction(action,{email_id:m.id,job_id:choice.value,note:note.value});await refresh();render();}catch(e){status.textContent=e.message;}};
        add(p,choice,note,button('Apply status',()=>act('email-apply'),'primary'),button('Dismiss',()=>act('email-dismiss')),status);
      }add(list,p);
    });};select.addEventListener('change',draw);draw();
  if(checks.length){const history=panel('Email check history');checks.slice(0,20).forEach(c=>add(history,add(el('div','row'),add(el('div'),el('strong','',`${fullDate(c.started_at)} · ${c.status}`),el('p','muted',c.scope),el('small','',`${c.account} · ${c.count} new records${c.status==='running'?' · Completion not recorded; ask your agent to reconcile this run.':''}`)))));add(root,history);}
}
