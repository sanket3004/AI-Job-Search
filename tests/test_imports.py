import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills' / 'careerpilot' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from import_profile import collect, extract, inventory, save_evidence
from toolkit import Workspace

def pdf_bytes(content='Test Candidate - SQL Analyst'):
    stream = f'BT /F1 12 Tf 40 100 Td ({content}) Tj ET'.encode('ascii') if content else b''
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    body = b'%PDF-1.4\n'
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f'{n} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(body)
    body += b'xref\n0 6\n0000000000 65535 f \n'
    body += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    return body + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()

class ImportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.root = Path(self.temp.name)
        self.ws = Workspace(self.root / 'workspace')
        self.ws.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def evidence(self):
        source = self.root / 'resume.txt'
        source.write_text('Test Candidate\nSQL analyst', encoding='utf-8')
        return save_evidence(self.ws.root, collect(source, 'resume'))['evidence_file']

    def preview(self, evidence=None):
        return self.ws.mutate({'op':'profile-preview','base_revision':self.ws.read()['profile_revision'],
            'profile':{'name':'Test Candidate','skills':['SQL'],'_provenance':{'name':'resume.txt / line 1'}},
            'evidence_files':[evidence or self.evidence()]})

    def test_resume_text_extraction_does_not_change_profile(self):
        path = self.evidence()
        result = json.loads(Path(path).read_text(encoding='utf-8'))
        self.assertIn('SQL analyst', result['documents'][0]['text'])
        self.assertEqual(self.ws.read()['profile'], {})
        self.assertFalse(result['profile_changed'])

    def test_docx_body_table_and_header(self):
        source = self.root / 'resume.docx'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Test Candidate</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SQL</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
            z.writestr('word/header1.xml', '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>candidate@example.invalid</w:t></w:r></w:p></w:hdr>')
        result = collect(source, 'resume')['documents'][0]['text']
        for value in ['Test Candidate', 'SQL', 'candidate@example.invalid']:
            self.assertIn(value, result)

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'Optional PDF dependency not installed')
    def test_pdf_text_and_blank_pdf_ocr_message(self):
        self.assertIn('SQL Analyst', extract('resume.pdf', pdf_bytes())['text'])
        with self.assertRaisesRegex(ValueError, 'OCR'):
            extract('scan.pdf', pdf_bytes(''))

    def test_linkedin_defaults_exclude_messages_and_connections(self):
        source = self.root / 'linkedin.zip'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('export/Profile.csv', 'First Name,Last Name,Headline\nTest,Candidate,Analyst\n')
            z.writestr('export/Positions.csv', 'Company Name,Title,Started On\nExample,Analyst,2024\n')
            z.writestr('export/Skills.csv', 'Name\nSQL\nPython\n')
            z.writestr('Messages.csv', 'Private content that must not be read')
            z.writestr('Connections.csv', 'Private contacts that must not be read')
        result = collect(source, 'linkedin')
        self.assertEqual(len(result['documents']), 3)
        self.assertEqual(result['skipped_files'], 2)
        self.assertNotIn('Private', json.dumps(result))
        self.assertEqual(result['documents'][0]['records'][0]['First Name'], 'Test')

    def test_indeed_requires_explicit_archive_selection(self):
        source = self.root / 'indeed.zip'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('profile/resume.txt', 'Test Candidate\nAnalyst')
            z.writestr('activity/messages.json', '{"private":"not selected"}')
        _, entries, container = inventory(source)
        self.assertEqual(container, 'zip')
        self.assertEqual(len(entries), 2)
        with self.assertRaisesRegex(ValueError, 'select relevant files'):
            collect(source, 'indeed')
        result = collect(source, 'indeed', ['profile/resume.txt'])
        self.assertEqual(result['skipped_files'], 1)
        self.assertNotIn('not selected', json.dumps(result))

    def test_archive_traversal_and_unknown_member_rejected(self):
        source = self.root / 'bad.zip'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('../resume.txt', 'Do not extract me')
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            collect(source, 'documents', ['../resume.txt'])
        with self.assertRaisesRegex(ValueError, 'absent'):
            collect(source, 'documents', ['missing.txt'])
        self.assertFalse((self.root / 'resume.txt').exists())

    def test_directory_csv_and_json_preserve_source_fields(self):
        folder = self.root / 'export'
        folder.mkdir()
        (folder / 'Skills.csv').write_text('Name\nSQL\n', encoding='utf-8-sig')
        (folder / 'profile.json').write_text('{"experience":[{"company":"Example"}]}', encoding='utf-8')
        result = collect(folder, 'documents', ['Skills.csv', 'profile.json'])
        self.assertEqual(result['documents'][0]['records'], [{'Name':'SQL'}])
        self.assertEqual(result['documents'][1]['data']['experience'][0]['company'], 'Example')

    def test_preview_confirmation_and_duplicate_apply(self):
        preview = self.preview()
        self.assertFalse(preview['profile_changed'])
        self.assertEqual(self.ws.read()['profile'], {})
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            self.ws.mutate({'op':'profile-apply','preview_id':preview['preview_id'],'user_confirmation':''})
        self.ws.mutate({'op':'profile-apply','preview_id':preview['preview_id'],'user_confirmation':'Synthetic test: I approve these facts'})
        self.assertEqual(self.ws.read()['profile']['skills'], ['SQL'])
        with self.assertRaisesRegex(ValueError, 'already applied'):
            self.ws.mutate({'op':'profile-apply','preview_id':preview['preview_id'],'user_confirmation':'Repeat'})

    def test_stale_profile_keeps_manual_changes(self):
        preview = self.preview()
        self.ws.mutate({'op':'profile-save','profile':{'name':'Manual change'}})
        with self.assertRaisesRegex(ValueError, 'Profile changed'):
            self.ws.mutate({'op':'profile-apply','preview_id':preview['preview_id'],'user_confirmation':'Synthetic approval'})
        self.assertEqual(self.ws.read()['profile']['name'], 'Manual change')

    def test_altered_evidence_blocks_apply(self):
        source = self.evidence()
        preview = self.preview(source)
        Path(source).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            self.ws.mutate({'op':'profile-apply','preview_id':preview['preview_id'],'user_confirmation':'Synthetic approval'})
        self.assertEqual(self.ws.read()['profile'], {})

    def test_source_outside_workspace_rejected(self):
        outside = self.root / 'outside.json'
        outside.write_text('{"schema_version":1,"documents":[]}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'imports folder'):
            self.preview(str(outside))

    def test_cli_extraction(self):
        source = self.root / 'cli-resume.txt'
        source.write_text('Test Candidate', encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'import_profile.py'), '--source', str(source), '--kind', 'resume', '--workspace', str(self.ws.root)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(json.loads(result.stdout)['evidence_file']).exists())
        self.assertEqual(self.ws.read()['profile'], {})

if __name__ == '__main__':
    unittest.main()
