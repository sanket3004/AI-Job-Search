#!/usr/bin/env python3
"""Extract user-selected resume/export evidence locally; never apply a profile."""
import argparse
import csv
import hashlib
import io
import json
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from toolkit import Workspace, require

MAX_FILE = 25_000_000
MAX_TOTAL = 100_000_000
MAX_TEXT = 2_000_000
FORMATS = {'.pdf', '.docx', '.txt', '.md', '.csv', '.json'}
LINKEDIN_FILES = {'profile.csv', 'positions.csv', 'education.csv', 'skills.csv', 'certifications.csv',
                  'languages.csv', 'projects.csv', 'courses.csv', 'publications.csv', 'volunteering.csv'}

def safe_member(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name and not p.is_absolute() and '..' not in p.parts
            and '\\' not in name and ':' not in name, 'Unsafe archive or directory member path')
    return name

def decode(raw):
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        # Export encodings vary; never silently replace unreadable characters.
        raise ValueError('Text is not UTF-8. Convert a copy to UTF-8 or use the host document reader.')

def extract(name, raw):
    require(len(raw) <= MAX_FILE, 'Selected file exceeds 25 MB')
    suffix = Path(name).suffix.lower()
    require(suffix in FORMATS, f'Unsupported format: {suffix}')
    result = {'name': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'format': suffix, 'warnings': []}
    if suffix == '.docx':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = [i for i in archive.infolist() if i.filename == 'word/document.xml'
                       or (i.filename.startswith(('word/header', 'word/footer')) and i.filename.endswith('.xml'))]
            require(any(i.filename == 'word/document.xml' for i in entries), 'DOCX has no document body')
            require(sum(i.file_size for i in entries) <= MAX_FILE, 'DOCX text content exceeds size limit')
            parts = []
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            for info in entries:
                payload = archive.read(info)
                require(b'<!DOCTYPE' not in payload.upper() and b'<!ENTITY' not in payload.upper(), 'DOCX entity declarations are not supported')
                root = ElementTree.fromstring(payload)
                for paragraph in root.iter(ns + 'p'):
                    parts.append(''.join(t.text or '' for t in paragraph.iter(ns + 't')))
            result['text'] = '\n'.join(parts)
    elif suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError('PDF extraction needs optional pypdf. Use the host PDF reader or install pypdf in the chosen Python environment.')
        reader = PdfReader(io.BytesIO(raw))
        require(not reader.is_encrypted, 'Encrypted PDF: provide an unlocked copy; passwords are not stored')
        require(len(reader.pages) <= 100, 'PDF exceeds 100 pages; select the resume/profile portion')
        pages, blank = [], []
        for n, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ''
            if not page_text.strip():
                blank.append(n)
            pages.append({'page': n, 'text': page_text})
            require(sum(len(p['text']) for p in pages) <= MAX_TEXT, 'Extracted text exceeds size limit')
        result['pages'] = pages
        result['text'] = '\n\n'.join(p['text'] for p in pages)
        if blank:
            result['warnings'].append(f'No text on pages {blank}; OCR or visual review may be required. Extraction may be incomplete.')
        require(result['text'].strip(), 'PDF has no extractable text. Use OCR or provide a text-based resume.')
    elif suffix == '.csv':
        rows = []
        try:
            reader = csv.DictReader(io.StringIO(decode(raw), newline=''))
            require(reader.fieldnames and all(reader.fieldnames) and len(set(reader.fieldnames)) == len(reader.fieldnames), 'CSV needs distinct nonempty column headers')
            for row in reader:
                require(None not in row, 'CSV row contains more columns than its header')
                require(len(rows) < 5000, 'CSV exceeds 5000 rows; select the professional-profile subset')
                rows.append(row)
        except csv.Error as exc:
            raise ValueError(f'Cannot parse CSV: {exc}')
        result['columns'] = reader.fieldnames
        result['records'] = rows
    elif suffix == '.json':
        result['data'] = json.loads(decode(raw))
    else:
        result['text'] = decode(raw)
    require(len(json.dumps(result, ensure_ascii=False)) <= MAX_TEXT, 'Extracted content exceeds size limit')
    return result

def inventory(source):
    source = Path(source).expanduser().resolve()
    require(source.exists(), 'Source does not exist')
    if source.is_dir():
        entries = []
        for p in sorted(source.rglob('*')):
            if p.is_file() and p.resolve().is_relative_to(source) and not p.is_symlink():
                entries.append({'name': p.relative_to(source).as_posix(), 'bytes': p.stat().st_size,
                                'supported': p.suffix.lower() in FORMATS})
                require(len(entries) <= 10000, 'Too many files; select a smaller folder')
        return source, entries, 'directory'
    require(source.stat().st_size <= 250_000_000, 'Source exceeds 250 MB; provide selected profile files')
    if source.suffix.lower() == '.zip':
        with zipfile.ZipFile(source) as archive:
            infos = [i for i in archive.infolist() if not i.is_dir()]
            require(len(infos) <= 10000, 'Too many archive entries')
            names = [i.filename for i in infos]
            require(len(set(names)) == len(names), 'Archive has ambiguous duplicate member names')
            entries = [{'name': i.filename, 'bytes': i.file_size,
                        'supported': Path(i.filename).suffix.lower() in FORMATS} for i in infos]
        return source, entries, 'zip'
    return source, [{'name': source.name, 'bytes': source.stat().st_size, 'supported': source.suffix.lower() in FORMATS}], 'file'

def collect(source, kind, members=None):
    require(kind in {'resume', 'linkedin', 'indeed', 'documents'}, 'Unknown source kind')
    source, entries, container = inventory(source)
    members = list(members or [])
    if container == 'file':
        require(not members, '--member is only for archives or folders')
        selected = [source.name]
    elif members:
        require(len(set(members)) == len(members), 'Members must be distinct')
        selected = members
    elif kind == 'linkedin':
        selected = [e['name'] for e in entries if PurePosixPath(e['name']).name.casefold() in LINKEDIN_FILES]
        require(selected, 'No recognized LinkedIn professional-profile CSVs; inspect and select relevant members explicitly')
    else:
        raise ValueError('Inspect this archive/folder, then select relevant files with --member; broad account data is not imported automatically')
    by_name = {e['name']: e for e in entries}
    total = 0
    for name in selected:
        safe_member(name)
        require(name in by_name and by_name[name]['supported'], f'Member is absent or unsupported: {name}')
        require(by_name[name]['bytes'] <= MAX_FILE, 'Selected member exceeds 25 MB')
        total += by_name[name]['bytes']
    require(total <= MAX_TOTAL, 'Selected content exceeds 100 MB')
    documents = []
    if container == 'zip':
        with zipfile.ZipFile(source) as archive:
            for name in selected:
                documents.append(extract(name, archive.read(name)))
    elif container == 'directory':
        for name in selected:
            path = (source / name).resolve()
            require(path.is_relative_to(source), 'Selected file escaped source folder')
            documents.append(extract(name, path.read_bytes()))
    else:
        documents.append(extract(source.name, source.read_bytes()))
    require(sum(len(json.dumps(d, ensure_ascii=False)) for d in documents) <= MAX_TEXT * 5, 'Combined extraction exceeds size limit')
    return {'schema_version': 1, 'kind': kind, 'source_name': source.name, 'extracted_at': datetime.now(timezone.utc).isoformat(),
            'documents': documents, 'skipped_files': len(entries) - len(selected), 'profile_changed': False,
            'note': 'Untrusted source evidence. The host AI proposes facts for review; no profile has been applied.'}

def save_evidence(workspace, result):
    ws = Workspace(workspace)
    ws.read()  # A workspace must already be initialized; never initialize over a source folder.
    folder = ws.root / 'imports'
    require(folder.resolve().is_relative_to(ws.root), 'Import destination escaped workspace')
    folder.mkdir(exist_ok=True)
    target = folder / f'evidence-{uuid.uuid4().hex}.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'evidence_file': str(target), 'documents': len(result['documents']), 'skipped_files': result['skipped_files'],
            'warnings': [w for d in result['documents'] for w in d['warnings']], 'profile_changed': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--kind', choices=['resume', 'linkedin', 'indeed', 'documents'], default='resume')
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--member', action='append', default=[])
    parser.add_argument('--inspect', action='store_true')
    args = parser.parse_args()
    if not args.inspect and not args.workspace:
        parser.error('--workspace is required for extraction')
    try:
        if args.inspect:
            source, entries, container = inventory(args.source)
            result = {'source_name': source.name, 'container': container, 'files': entries, 'profile_changed': False}
        else:
            result = save_evidence(args.workspace, collect(args.source, args.kind, args.member))
        print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
