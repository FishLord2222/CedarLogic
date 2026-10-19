# Windows startup updates

Download the refreshed **CedarLogic 3.08 Windows Setup** from
<https://github.com/FishLord2222/CedarLogic/releases/tag/v3.08> and install it once.
Existing Windows installations predate the updater and cannot discover this
first updater-enabled build automatically.

After installation, CedarLogic checks for updates shortly after its main window
opens, on every launch, including the first. A newer stable release produces the
WinSparkle update popup. A current version, an older offered version, an offline
connection, or an invalid feed stays quiet. No installer runs just because a
newer release was found: the user chooses **Install update**. WinSparkle also
offers postponing or skipping a version; a skipped version remains skipped.

Before launching the downloaded installer, CedarLogic runs its normal circuit
save/discard/cancel prompt on the GUI thread. Cancel keeps the app open and does
not start the installer. If the user continues, CedarLogic launches the verified
installer, closes normally, and the installer waits for that application process
to finish before replacing files. No silent installation is forced.

The appcast is hosted at
<https://fishlord2222.github.io/CedarLogic/windows/appcast.xml>. Installer downloads
remain in GitHub Releases. The shared download page is
<https://fishlord2222.github.io/CedarLogic/>.

## Signing and versions

Windows uses a dedicated Ed25519 update-signing key, separate from the Linux RPM
key. The public key in the app is:

```text
pJZlGmCDOBv37aaVdovOKw56U2pILQANOSWzEIBjh/c=
```

The private key is the encrypted repository Actions secret
`CEDARLOGIC_WINDOWS_SIGNING_KEY`. Its value is a base64-encoded 32-byte seed,
compatible with `winsparkle-tool`. The publishing script checks that this seed
matches the embedded public key, signs the exact installer bytes, verifies the
signature, and puts it in the appcast's `sparkle:edSignature` attribute.
WinSparkle checks that signature before permitting installation. These are
updater signatures, separate from Windows Authenticode certificate signing.

The initial updater-enabled build displays **3.08** and internally identifies
itself as **3.0.8.1**. The appcast reads the installer product version from its
Windows version resource. Each Windows rebuild must increase the four-part
internal version, even when the visible release name stays the same. Keep these
values synchronized in the maintained desktop source:

- `project(... VERSION ...)` and `CEDAR_WINDOWS_BUILD_REVISION` in CMake.
- `VIProductVersion` and the `FileVersion` value in `tools/windows-installer.nsi`.
- WinSparkle's build version, which CMake derives from the project version and
  Windows build revision.

Never rotate the public key during a routine release. Keep a secure private-key
backup. Losing it or replacing it without a migration prevents existing apps
from trusting future updates.

## Build and publish

The maintained Qt desktop source is included in the release's
`CedarLogic-3.08-Source.tar.gz` archive. The repository's older top-level source
tree is not the source used for the current desktop builds. The updater files
are also available under `packaging/windows/updater/` for review.

1. Fetch the pinned official WinSparkle SDK using `tools/fetch-winsparkle.py` in
   the desktop source. WinSparkle 0.9.4's SDK archive SHA-256 is
   `6037df37fc263bd1650a1c4949681a9d40ffe991d01f35892a406cb5d103c976`.
2. Configure the Qt Windows build with `WINSPARKLE_ROOT` pointing to that
   extracted `WinSparkle-0.9.4` directory. The app links the x64 import library
   and deploys the x64 `WinSparkle.dll` next to `CedarLogic.exe`.
3. Package the DLL and its notices in `licenses/WinSparkle/`. The installer
   builder rejects payloads missing the DLL. Never package test executables or
   the private signing key.
4. Build and test the new Windows installer and Linux RPM. Upload both assets
   to a draft stable release before publishing. Use the existing filenames:
   `CedarLogic-VERSION-Windows-Setup.exe` and `cedarlogic-VERSION-x86_64.rpm`.
5. Publish the release from a new version tag on `master`. **Publish desktop
   updates** rebuilds the Linux repository and Windows appcast together and
   atomically deploys the shared Pages site.

If assets are added or replaced after publishing, use **Actions → Publish
desktop updates → Run workflow** on `master`. Historical tags predating the
workflow also need a manual run. A failed build leaves the previous site live.

## Validation

The Windows updater was built with the MSVC-compatible x64 cross-toolchain and
tested with the real WinSparkle DLL under Wine. Integration scenarios cover a
newer version popup, two consecutive startup checks, current and older versions,
unavailable and malformed feeds, canceling the save/close handoff, a tampered
installer, and a verified installer that waits for the application to exit.
This session blocks 32-bit executables, so the NSIS installer stub could not
be executed end-to-end. Its full extracted payload was checked against staging,
and the packaged 64-bit application was launched under Wine. Native Windows
installation testing remains necessary before a wider rollout.
