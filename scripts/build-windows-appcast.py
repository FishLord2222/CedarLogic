#!/usr/bin/env python3
"""Add the signed Windows installer appcast to the existing desktop Pages site."""
import argparse
import base64
from datetime import datetime
from email.utils import format_datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPARKLE = 'http://www.andymatuschak.org/xml-namespaces/sparkle'
ET.register_namespace('sparkle', SPARKLE)


def installer_version(data):
    """Read RT_VERSION through the PE resource tree, not code/data lookalikes.

    Layout: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
    """
    if data[:2] != b'MZ' or len(data) < 64:
        raise ValueError('Installer is not a Windows executable')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Installer has no PE header')
    section_count = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from('<H', data, optional)[0]
    if magic not in (0x10b, 0x20b):
        raise ValueError('Unsupported PE optional header')
    directories = optional + (96 if magic == 0x10b else 112)
    resource_rva, resource_size = struct.unpack_from('<II', data, directories + 16)
    sections = [struct.unpack_from('<IIII', data, optional + optional_size + i * 40 + 8)
                for i in range(section_count)]

    def offset(rva, size):
        for virtual_size, address, raw_size, raw in sections:
            if address <= rva < address + max(virtual_size, raw_size):
                result = raw + rva - address
                if rva - address + size <= raw_size and result + size <= len(data):
                    return result
        raise ValueError('Resource RVA is outside the executable sections')

    root = offset(resource_rva, resource_size)

    def entries(relative):
        if relative + 16 > resource_size:
            raise ValueError('Resource directory is out of bounds')
        named, numbered = struct.unpack_from('<HH', data, root + relative + 12)
        if relative + 16 + 8 * (named + numbered) > resource_size:
            raise ValueError('Resource entries are out of bounds')
        return [struct.unpack_from('<II', data, root + relative + 16 + i * 8)
                for i in range(named + numbered)]

    versions = set()

    def visit(relative, depth=0):
        if depth > 3:
            raise ValueError('Unexpected version resource nesting')
        for _, target in entries(relative):
            if target & 0x80000000:
                visit(target & 0x7fffffff, depth + 1)
            else:
                if target + 16 > resource_size:
                    raise ValueError('Version data entry is out of bounds')
                rva, size = struct.unpack_from('<II', data, root + target)
                start = offset(rva, size)
                blob = data[start:start + size]
                key = 'VS_VERSION_INFO\0'.encode('utf-16le')
                fixed = (6 + len(key) + 3) & ~3
                if blob[6:6 + len(key)] != key or blob[fixed:fixed + 4] != bytes.fromhex('bd04effe'):
                    raise ValueError('Invalid VS_VERSION_INFO resource')
                versions.add(struct.unpack_from('<II', blob, fixed + 16))

    for kind, target in entries(0):
        if kind == 16 and target & 0x80000000: # RT_VERSION
            visit(target & 0x7fffffff)
    if len(versions) != 1:
        raise ValueError('Installer needs one consistent Windows product version')
    major_minor, patch_revision = versions.pop()
    return '.'.join(str(number) for number in (
        major_minor >> 16, major_minor & 0xffff, patch_revision >> 16, patch_revision & 0xffff))


def sign(data, public_key):
    # WinSparkle's key file format is a base64-encoded 32-byte Ed25519 seed.
    seed = base64.b64decode(os.environ['CEDARLOGIC_WINDOWS_SIGNING_KEY'].strip(), validate=True)
    if len(seed) != 32:
        raise ValueError('Windows signing secret must contain a 32-byte Ed25519 seed')
    with tempfile.TemporaryDirectory(prefix='cedarlogic-eddsa-') as temporary:
        directory = Path(temporary)
        private = directory / 'key.der'
        with private.open('wb') as stream:
            os.chmod(private, 0o600)
            stream.write(bytes.fromhex('302e020100300506032b657004220420') + seed)
        public = subprocess.check_output(['openssl', 'pkey', '-inform', 'DER',
                                          '-in', str(private), '-pubout', '-outform', 'DER'])
        if public != bytes.fromhex('302a300506032b6570032100') + public_key:
            raise ValueError('Windows signing secret does not match the public key in the app')
        payload = directory / 'installer.exe'
        payload.write_bytes(data)
        signature = subprocess.check_output(['openssl', 'pkeyutl', '-sign', '-rawin',
                                             '-keyform', 'DER', '-inkey', str(private),
                                             '-in', str(payload)])
        (directory / 'public.der').write_bytes(public)
        (directory / 'signature').write_bytes(signature)
        subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin', '-pubin', '-keyform', 'DER',
                        '-inkey', str(directory / 'public.der'), '-in', str(payload),
                        '-sigfile', str(directory / 'signature')], check=True, stdout=subprocess.DEVNULL)
        return base64.b64encode(signature).decode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--installer', type=Path, help='Local installer for pipeline verification')
    parser.add_argument('--repository', default='FishLord2222/CedarLogic')
    args = parser.parse_args()
    if args.repository != 'FishLord2222/CedarLogic':
        parser.error('Configure the application trust anchor before publishing a fork')
    if not (args.output / 'rpm/x86_64/repodata/repomd.xml').is_file():
        parser.error('Build the RPM repository first; Windows publishing extends the same site')
    request = urllib.request.Request(
        f'https://api.github.com/repos/{args.repository}/releases/latest',
        headers={'User-Agent': 'CedarLogic-desktop-publisher',
                 **({'Authorization': f'Bearer {os.environ["GH_TOKEN"]}'} if os.environ.get('GH_TOKEN') else {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.load(response)
    if release['draft'] or release['prerelease']:
        raise ValueError('Only stable releases may be published')
    assets = [asset for asset in release['assets']
              if re.fullmatch(r'CedarLogic-[0-9][A-Za-z0-9.+_-]*-Windows-Setup\.exe', asset['name'])]
    if len(assets) != 1:
        raise ValueError('Latest stable release must have exactly one Windows Setup.exe asset')
    asset = assets[0]
    if args.installer:
        data = args.installer.read_bytes()
    else:
        with urllib.request.urlopen(asset['browser_download_url'], timeout=120) as response:
            data = response.read()
        if asset.get('digest') and asset['digest'] != 'sha256:' + hashlib.sha256(data).hexdigest():
            raise ValueError('GitHub Windows installer checksum mismatch')
    version = installer_version(data)
    public_path = ROOT / 'packaging/windows/windows-update-public-key.txt'
    public = base64.b64decode(public_path.read_text().strip(), validate=True)
    if len(public) != 32:
        raise ValueError('Invalid Windows update public key')
    signature = sign(data, public)
    destination = args.output / 'windows'
    destination.mkdir(parents=True, exist_ok=True)
    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'CedarLogic for Windows'
    ET.SubElement(channel, 'link').text = 'https://fishlord2222.github.io/CedarLogic/'
    ET.SubElement(channel, 'description').text = 'Stable Windows x64 updates'
    ET.SubElement(channel, 'language').text = 'en'
    item = ET.SubElement(channel, 'item')
    label = release['tag_name'].lstrip('v')
    if re.search(r'\bhotfix\b', release.get('name', ''), re.IGNORECASE):
        label += ' Hotfix'
    ET.SubElement(item, 'title').text = 'CedarLogic ' + label
    ET.SubElement(item, f'{{{SPARKLE}}}version').text = version
    ET.SubElement(item, f'{{{SPARKLE}}}shortVersionString').text = label
    # The 3.08 updater uses VerifyVersionInfo without a supportedOS manifest.
    # A Windows 10 minimum here silently hides updates from those existing
    # Windows 10/11 clients. Keep the migration feed free of that OS filter;
    # CedarLogic itself still targets Windows 10/11.
    ET.SubElement(item, 'pubDate').text = format_datetime(
        datetime.fromisoformat(release['published_at'].replace('Z', '+00:00')))
    ET.SubElement(item, 'description').text = (
        f'CedarLogic {label} is available. Install this update to get the latest stable version. '
        'CedarLogic will let you save your circuit before closing.')
    ET.SubElement(item, 'enclosure', {
        'url': asset['browser_download_url'], 'length': str(len(data)),
        'type': 'application/octet-stream',
        f'{{{SPARKLE}}}os': 'windows-x64',
        f'{{{SPARKLE}}}edSignature': signature})
    ET.indent(rss, space='  ')
    ET.ElementTree(rss).write(destination / 'appcast.xml', encoding='utf-8', xml_declaration=True)
    (destination / public_path.name).write_text(public_path.read_text())
    (destination / 'installer-sha256.txt').write_text(hashlib.sha256(data).hexdigest() + '  ' + asset['name'] + '\n')
    # Extend the Linux download page without replacing its repository contents.
    linux = next((args.output / 'rpm/x86_64/Packages').glob('cedarlogic-*.rpm')).relative_to(args.output).as_posix()
    (args.output / 'index.html').write_text('''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CedarLogic downloads and updates</title>
<style>body{font:17px/1.6 system-ui,sans-serif;max-width:760px;margin:60px auto;padding:0 24px;background:#111827;color:#f1f5f9}a{color:#93c5fd}.download{display:inline-block;background:#2563eb;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;margin:0 12px 12px 0}code{background:#1e293b;padding:3px 7px;border-radius:4px}h2{margin-top:32px}</style>
<h1>CedarLogic</h1><p>A digital logic simulator for Windows and Linux.</p>
''' + f'<p>Latest stable release: <strong>{html.escape(label)}</strong></p>'
        + f'<a class="download" href="{html.escape(asset["browser_download_url"], quote=True)}">Download for Windows</a>'
        + f'<a class="download" href="{linux}">Download Linux RPM</a>'
        + '<h2>Windows updates</h2><p>Install the refreshed 3.08 Windows setup once. CedarLogic checks on startup and shows a popup when an update is available. You choose when to install, and can save your circuit first.</p>'
        + '<h2>Linux updates</h2><p>Install the refreshed 3.08 RPM once to register the signed repository. Future stable releases are available through your normal DNF updates.</p><p><code>sudo dnf upgrade --refresh cedarlogic</code></p>'
        + '<p><a href="https://github.com/FishLord2222/CedarLogic/releases">All releases and AppImage downloads</a> · <a href="https://github.com/FishLord2222/CedarLogic">GitHub</a></p></html>')
    print(f'Verified and published Windows appcast: {version}')


if __name__ == '__main__':
    main()
