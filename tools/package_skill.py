"""Build a portable skill ZIP containing only its canonical source files."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def package(destination):
    source = ROOT / 'skills' / 'careerpilot'
    paths = sorted(p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    destination = Path(destination).resolve()
    if destination.is_relative_to(source.resolve()):
        raise ValueError('Archive destination must be outside skill source')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, 'careerpilot/' + path.relative_to(source).as_posix())
    return {'archive': str(destination), 'files': len(paths), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'careerpilot.zip')
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))
