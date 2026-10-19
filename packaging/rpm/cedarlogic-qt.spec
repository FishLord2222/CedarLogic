%global debug_package %{nil}
# Keep bundled Qt/QML libraries private and byte-identical to the tested stage.
%global __os_install_post %{nil}
Name: cedarlogic
Version: 3.08
Release: 5%{?dist}
Summary: Digital logic simulator with a Qt 6 interface
License: GPL-3.0-or-later AND BSD-3-Clause AND LGPL-3.0-only AND OFL-1.1 AND MIT
URL: https://github.com/emonte-cu/CedarLogic
Source0: cedarlogic-qt-%{version}.tar.gz
BuildArch: x86_64
# Qt, ICU, XCB and xkbcommon are bundled privately, not system providers.
AutoReqProv: no
Requires: glibc >= 2.35
Requires: libstdc++ >= 11
Requires: libgcc
Requires: fontconfig
Requires: freetype
Requires: glib2
Requires: dbus-libs
Requires: zlib
Requires: libzstd
Requires: krb5-libs
Requires: libglvnd-glx
Requires: libglvnd-egl
Requires: libX11
Requires: libX11-xcb
Requires: libXext
Requires: libXau
Requires: libXdmcp
Requires: libwayland-client
Requires: libwayland-cursor
Requires: libwayland-egl
Recommends: xdg-desktop-portal
Recommends: cups-libs
Recommends: openssl-libs

%description
CedarLogic 3.08 includes simulator, wire, parser and recovery stability fixes,
with local-only crash diagnostics and no automatic uploads.
CedarLogic is an educational digital logic simulator. Version 3.07 replaces
wxWidgets with Qt 6, adds sidebar search, six accents and system appearance,
and preserves the original circuit symbols and signal colors. Qt libraries
are bundled under a private application directory.

%prep
%setup -q -n cedarlogic-qt-%{version}

%build
# Built and tested separately with Qt 6.8.3 on Ubuntu 22.04.

%install
mkdir -p %{buildroot}%{_libdir}/cedarlogic
cp -a payload/. %{buildroot}%{_libdir}/cedarlogic/
install -Dpm0755 cedarlogic %{buildroot}%{_bindir}/cedarlogic
install -Dpm0644 CedarLogic.desktop %{buildroot}%{_datadir}/applications/io.github.emonte_cu.CedarLogic.desktop
install -Dpm0644 CedarLogic.png %{buildroot}%{_datadir}/icons/hicolor/64x64/apps/CedarLogic.png
install -Dpm0644 CedarLogic.xml %{buildroot}%{_datadir}/mime/packages/CedarLogic.xml
install -Dpm0644 io.github.emonte_cu.CedarLogic.metainfo.xml %{buildroot}%{_datadir}/metainfo/io.github.emonte_cu.CedarLogic.appdata.xml
install -Dpm0644 cedarlogic.repo %{buildroot}%{_sysconfdir}/yum.repos.d/cedarlogic.repo
install -Dpm0644 RPM-GPG-KEY-cedarlogic %{buildroot}%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-cedarlogic

%files
%{_bindir}/cedarlogic
%{_libdir}/cedarlogic/
%{_datadir}/applications/io.github.emonte_cu.CedarLogic.desktop
%{_datadir}/icons/hicolor/64x64/apps/CedarLogic.png
%{_datadir}/mime/packages/CedarLogic.xml
%{_datadir}/metainfo/io.github.emonte_cu.CedarLogic.appdata.xml
%config(noreplace) %{_sysconfdir}/yum.repos.d/cedarlogic.repo
%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-cedarlogic

%changelog
* Sun Oct 18 2026 CedarLogic contributors - 3.08-5
- Register the signed CedarLogic stable RPM repository for DNF updates.

* Sun Oct 18 2026 CedarLogic contributors - 3.08-4
- Synchronize the in-app, public and AppData 3.08 changelogs.

* Sat Oct 17 2026 CedarLogic contributors - 3.08-3
- Preserve internal wire routes during marquee-selected group movement.
- Restore blue connection feedback and clean moved-switch wire routes.

* Thu Oct 15 2026 CedarLogic contributors - 3.08-2
- Hide the floating sidebar thumbnail over the snapped canvas preview.

* Thu Oct 15 2026 CedarLogic contributors - 3.08-1
- Backport simulator, wire, parser and recovery stability fixes.
- Keep crash diagnostics local; remove upstream issue submission.

* Sun Oct 11 2026 CedarLogic contributors <noreply@example.invalid> - 3.07-29
- Introduce Qt 6 frontend for Linux and Windows
- Add sidebar search, toggleable part names, UI accents and system appearance
- Add saved decoder output polarity with active-low inversion circles
- Add themed dialogs, persistent part names and next-launch crash reports
- Remove the wxWidgets frontend and active build dependencies
- Optimize compact sidebar, editor lookups, previews and simulation data transfers
- Fix rotated TO/FROM labels for numeric angle formats
- Correct memory-file extension parsing, including uppercase CDM files
- Refresh disconnected wire states while paused without advancing time
