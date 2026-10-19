#!/usr/bin/env python3
"""Fetch the pinned official WinSparkle SDK for a CedarLogic Windows build."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path,
                    default=Path(__file__).resolve().parents[2]/'cache/winsparkle')
args = parser.parse_args()
url = 'https://github.com/vslavik/winsparkle/releases/download/v0.9.4/WinSparkle-0.9.4.zip'
with urllib.request.urlopen(url, timeout=120) as response:
    data = response.read()
if hashlib.sha256(data).hexdigest() != '6037df37fc263bd1650a1c4949681a9d40ffe991d01f35892a406cb5d103c976':
    raise SystemExit('WinSparkle SDK checksum mismatch')
args.output.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    for name in archive.namelist():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise SystemExit('Unsafe path in WinSparkle SDK archive')
    archive.extractall(args.output)
print(args.output/'WinSparkle-0.9.4')
