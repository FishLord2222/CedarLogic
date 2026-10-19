# CedarLogic RPM updates

The stable RPM repository is published at
<https://fishlord2222.github.io/CedarLogic/>.

## Enable updates on Fedora

Download the refreshed **CedarLogic 3.08 RPM** from
<https://github.com/FishLord2222/CedarLogic/releases/tag/v3.08> or the repository
page, then install it:

```sh
sudo dnf install ./cedarlogic-3.08-x86_64.rpm
```

The refreshed installer is internally version **3.08-5**. Earlier 3.08 RPMs
do not register the update repository, so existing users need to install this
refreshed RPM once. It installs `/etc/yum.repos.d/cedarlogic.repo` and the public
signing key at `/etc/pki/rpm-gpg/RPM-GPG-KEY-cedarlogic`.

Future stable releases are available with your normal system updates, or:

```sh
sudo dnf upgrade --refresh cedarlogic
```

DNF may ask you to trust the signing key on the first repository refresh. Its
full fingerprint is:

```text
2D7C47342B44240A1A4321037FDBD9FA8CDCBA4C
```

Both RPM signatures and repository metadata signatures are checked. The
repository offers x86_64 Linux RPMs only. It does not schedule automatic updates;
your system's DNF update settings control when updates are installed.

To stop receiving repository updates, set `enabled=0` in
`/etc/yum.repos.d/cedarlogic.repo`. RPM upgrades preserve edits to this file.

## Publish a stable update

1. Build and test the new RPM with a strictly higher RPM version/release than
   the previous stable package. Even a same-version rebuild needs a higher
   internal `Release` value. See `packaging/rpm/cedarlogic-qt.spec`.
2. Include `cedarlogic.repo` and `RPM-GPG-KEY-cedarlogic` from `packaging/rpm/`
   in the source packaging directory. The spec installs them into `/etc`.
   These public files are safe to ship; never bundle the private key.
3. Upload both the Windows installer and Linux RPM before publishing; the
   shared Pages deployment builds updates for both platforms. Create new release tags from the maintained `master` branch so the tag
   contains the publishing workflow. Upload the RPM as
   `cedarlogic-VERSION-x86_64.rpm` to a stable GitHub release.
   Upload assets before publishing the release when possible.
4. Publish the release. The **Publish desktop updates** workflow downloads the
   latest stable release RPM, signs a copy, verifies it, creates repository
   metadata, signs that metadata, and deploys the result with GitHub Pages.

If an asset was uploaded after the release was published, run **Actions →
Publish desktop updates → Run workflow** after the upload finishes. Replacing a
release asset by itself does not trigger a workflow. Editing a stable release
also triggers publishing. Drafts and prereleases are excluded.
For historical tags that predate this workflow, use **Run workflow** on
`master`; editing such a release may not start the workflow automatically.

The publisher always uses GitHub's latest stable release, including when an
older release is edited. Failed builds leave the previously deployed site in
place. Only the latest stable RPM is retained on Pages; historical download
assets remain in GitHub Releases. Do not publish older packages as “latest.”

The workflow does not change the original download assets. If the release RPM
also needs a signature, sign it before uploading; the initial 3.08-5 RPM was
signed locally. The repository uses filenames containing the full internal RPM
release, so a same-version rebuild does not reuse the previous package URL.

## GitHub configuration

- **Settings → Pages → Build and deployment → Source:** GitHub Actions.
- **Settings → Secrets and variables → Actions:** the repository secret
  `CEDARLOGIC_RPM_SIGNING_KEY` contains the dedicated ASCII-armored private
  signing key. It is imported only in the publishing job and removed afterward.
- The `github-pages` deployment environment permits the default `master`
  branch and version tags matching `v*`. Publishing uses the maintained scripts
  on the default branch, even when a release tag predates this workflow.
  The build job can read repository contents; the deploy job receives
  only the Pages and OIDC permissions needed for deployment.

The public key is checked into `packaging/rpm/`. The matching private key is
dedicated to this project and has no passphrase so Actions can sign unattended;
GitHub's encrypted Actions secret protects the uploaded copy. Limit repository
write access because maintainers able to edit workflows can use that secret.

Keep the local private backup and revocation certificate in a secure backup
outside this repository. Do not regenerate the signing key during routine
releases. Key rotation needs a separate migration: ship the new public key to
existing users while the previous key can still authenticate that update.

## Local verification

With `rpm`, `rpmsign`, `rpmkeys`, `createrepo_c`, and GnuPG available, and the
dedicated key imported into a private `GNUPGHOME`:

```sh
python3 scripts/build-rpm-repository.py \
  --rpm /path/to/cedarlogic-3.08-x86_64.rpm \
  --output /tmp/cedarlogic-repository-test
```

The output directory must not exist. Verification uses a temporary RPM key
database and does not modify your system RPM trust store. The public output
contains a signed RPM, signed metadata, the public key, repository configuration,
checksums, and a download page. It contains no private signing material.

The released 3.08 desktop build is maintained separately from the older source
tree in this GitHub repository. This publishing workflow distributes tested
release assets; it does not rebuild the desktop application from this tree.

The same deployment publishes the [Windows startup update feed](Windows-updates.md).
