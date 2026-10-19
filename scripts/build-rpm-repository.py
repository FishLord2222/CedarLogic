#!/usr/bin/env python3
"""Publish signed RPMs from the latest stable GitHub release to a Pages artifact.

The downloaded release assets are never overwritten. Only signed copies go to
Pages. A local --rpm argument exercises the same signing and metadata pipeline.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.check_output([str(arg) for arg in args], text=True).strip()


def fingerprint(key):
    result = run('gpg', '--batch', '--with-colons', '--show-keys', key)
    return next(line.split(':')[9] for line in result.splitlines() if line.startswith('fpr:'))


def download(url, destination):
    request = urllib.request.Request(url, headers={'User-Agent': 'CedarLogic-RPM-publisher'})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open('wb') as target:
        shutil.copyfileobj(response, target)


def release_asset(repository):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repository}/releases/latest',
        headers={'User-Agent': 'CedarLogic-RPM-publisher',
                 'Accept': 'application/vnd.github+json',
                 **({'Authorization': f'Bearer {os.environ["GH_TOKEN"]}'} if os.environ.get('GH_TOKEN') else {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.load(response)
    if release['draft'] or release['prerelease']:
        raise SystemExit('Refusing to publish a draft or prerelease')
    assets = [asset for asset in release['assets']
              if re.fullmatch(r'cedarlogic-[0-9][A-Za-z0-9.+_-]*-x86_64\.rpm', asset['name'])]
    if len(assets) != 1:
        raise SystemExit('Latest stable release must contain exactly one cedarlogic-*-x86_64.rpm asset; upload it and run this workflow again')
    return release, assets[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='FishLord2222/CedarLogic')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rpm', type=Path, help='Use a local RPM for an offline pipeline test')
    args = parser.parse_args()
    if args.repository != 'FishLord2222/CedarLogic':
        parser.error('Update the repository configuration and signing identity before publishing a fork')
    output = args.output.resolve()
    if output.exists():
        parser.error('Output directory must not already exist')
    key = ROOT / 'packaging/rpm/RPM-GPG-KEY-cedarlogic'
    signer = fingerprint(key)
    # Require the exact private key matching the checked-in public trust anchor.
    secret_keys = run('gpg', '--batch', '--with-colons', '--list-secret-keys', signer)
    if not any(line.startswith('sec:') for line in secret_keys.splitlines()):
        raise SystemExit('The dedicated CedarLogic private signing key is unavailable')
    with tempfile.TemporaryDirectory(prefix='cedarlogic-repository-') as temporary:
        temporary = Path(temporary)
        source = temporary / 'release.rpm'
        if args.rpm:
            shutil.copy2(args.rpm, source)
            label = 'Local verification build'
        else:
            release, asset = release_asset(args.repository)
            download(asset['browser_download_url'], source)
            if asset.get('digest'):
                actual = 'sha256:' + hashlib.sha256(source.read_bytes()).hexdigest()
                if actual != asset['digest']:
                    raise SystemExit('GitHub release asset checksum mismatch')
            label = release['tag_name']
        fields = run('rpm', '-qp', '--qf', '%{NAME}\n%{VERSION}\n%{RELEASE}\n%{ARCH}', source).splitlines()
        if len(fields) != 4 or fields[0] != 'cedarlogic' or fields[3] != 'x86_64':
            raise SystemExit('Unexpected RPM name or architecture')
        if not all(re.fullmatch(r'[A-Za-z0-9._+~^-]+', field) for field in fields):
            raise SystemExit('Unsafe RPM identity')
        paths = set(run('rpm', '-qpl', source).splitlines())
        required = {'/etc/yum.repos.d/cedarlogic.repo',
                    '/etc/pki/rpm-gpg/RPM-GPG-KEY-cedarlogic'}
        if not required.issubset(paths):
            raise SystemExit('RPM must bundle the repository configuration and public key; use the refreshed 3.08-5 installer or later')
        name, version, revision, arch = fields
        repo = output / 'rpm' / arch
        packages = repo / 'Packages'
        packages.mkdir(parents=True)
        package = packages / f'{name}-{version}-{revision}.{arch}.rpm'
        shutil.copy2(source, package)
        run('rpmsign', '--define', f'_gpg_name {signer}',
            '--define', f'_openpgp_sign_id {signer}',
            '--define', '_openpgp_sign gpg', '--define', '__gpg /usr/bin/gpg',
            '--define', f'_gpg_path {os.environ["GNUPGHOME"]}', '--addsign', package)
        # Use a fresh RPM database, never the runner's or user's system trust store.
        database = temporary / 'rpmdb'
        run('rpm', '--dbpath', database, '--initdb')
        run('rpm', '--dbpath', database, '--import', key)
        verification = run('rpmkeys', '--dbpath', database, '--checksig', '--verbose', package)
        if not re.search(r'Signature.*: OK', verification, re.IGNORECASE):
            raise SystemExit('RPM signature was not verified')
        run('createrepo_c', '--checksum', 'sha256', '--general-compress-type', 'gz', repo)
        metadata = repo / 'repodata/repomd.xml'
        run('gpg', '--batch', '--yes', '--armor', '--local-user', signer,
            '--detach-sign', '--output', str(metadata) + '.asc', metadata)
        run('gpg', '--batch', '--verify', str(metadata) + '.asc', metadata)
        shutil.copy2(key, output / key.name)
        shutil.copy2(ROOT / 'packaging/rpm/cedarlogic.repo', output / 'cedarlogic.repo')
        relative = package.relative_to(output).as_posix()
        checksum = hashlib.sha256(package.read_bytes()).hexdigest()
        (output / 'SHA256SUMS').write_text(f'{checksum}  {relative}\n')
        (output / '.nojekyll').touch()
        (output / 'index.html').write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>CedarLogic RPM updates</title><h1>CedarLogic RPM updates</h1>'
            f'<p>Stable release: {html.escape(label)}; RPM {html.escape(version + "-" + revision)}.</p>'
            f'<p><a href="{relative}">Download the signed CedarLogic RPM</a>. '
            'Install this RPM once to enable future DNF updates.</p>'
            '<p>After installation, run <code>sudo dnf upgrade cedarlogic</code>.</p>'
            f'<p>Signing key fingerprint: <code>{signer}</code></p>'
            '<p><a href="RPM-GPG-KEY-cedarlogic">Public signing key</a> · '
            '<a href="cedarlogic.repo">Repository configuration</a> · '
            '<a href="SHA256SUMS">SHA-256 checksum</a></p>'
            '<p><a href="https://github.com/FishLord2222/CedarLogic">Source and releases</a></p></html>')
        print(f'Verified signed RPM and repository metadata: {output}')


if __name__ == '__main__':
    main()
