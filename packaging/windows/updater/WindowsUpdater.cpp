#include "WindowsUpdater.h"
#include "WindowsUpdateKey.h"
#include <winsparkle.h>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QMessageBox>
#include <QProcess>
#include <QStandardPaths>
#include <utility>

WindowsUpdater *WindowsUpdater::active = nullptr;

WindowsUpdater::WindowsUpdater(std::function<bool()> confirm, QObject *parent)
    : QObject(parent), confirmClose(std::move(confirm)) {
  const auto cache = QStandardPaths::writableLocation(QStandardPaths::CacheLocation)
                     + QStringLiteral("/updates");
  if (QDir().mkpath(cache)) {
    installerCopy = cache + QStringLiteral("/CedarLogic-setup.exe");
    QFile::remove(installerCopy); // Remove the previous completed update.
  }
}

WindowsUpdater::~WindowsUpdater() {
  // Join the worker while its callback target is still alive. QObject drops
  // queued handoffs if the app exits before they can run.
  if (initialized) {
    win_sparkle_cleanup();
    active = nullptr;
  }
  if (!installerLaunched && !installerCopy.isEmpty())
    QFile::remove(installerCopy);
}

void WindowsUpdater::start(const QString &feed, const QString &version,
                           const QString &build) {
  if (initialized || active)
    return;
  if (!win_sparkle_set_eddsa_public_key(CedarWindowsUpdatePublicKey))
    return;
  active = this;
  const auto display = version.toStdWString();
  const auto internal = build.toStdWString();
  win_sparkle_set_app_details(L"CedarLogic", L"CedarLogic", display.c_str());
  win_sparkle_set_app_build_version(internal.c_str());
  win_sparkle_set_registry_path("Software\\CedarLogic\\Updates");
  win_sparkle_set_appcast_url(feed.toUtf8().constData());
  win_sparkle_set_user_run_installer_callback(&WindowsUpdater::runInstaller);
  // Explicitly check once per launch, including the very first launch. The
  // automatic scheduler would throttle checks to an interval and ask permission.
  win_sparkle_set_automatic_check_for_updates(0);
  win_sparkle_init();
  initialized = true;
  win_sparkle_check_update_without_ui();
}

int __cdecl WindowsUpdater::runInstaller(const wchar_t *path) {
  auto updater = active;
  if (!updater || !path)
    return WINSPARKLE_RETURN_ERROR;
  // WinSparkle deletes its temporary download as soon as its dialog closes.
  // Preserve the already-verified bytes before returning to that dialog.
  const auto installer = updater->installerCopy;
  if (installer.isEmpty())
    return WINSPARKLE_RETURN_ERROR;
  QFile::remove(installer);
  if (!QFile::copy(QString::fromWCharArray(path), installer))
    return WINSPARKLE_RETURN_ERROR;
  // Called from WinSparkle's thread. Do not block that thread on the GUI,
  // because normal application shutdown joins it in win_sparkle_cleanup().
  if (!QMetaObject::invokeMethod(updater, [updater, installer] {
        updater->install(installer);
      }, Qt::QueuedConnection))
    return WINSPARKLE_RETURN_ERROR;
  return 1; // We handle the verified installer; bypass WinSparkle's auto-exit.
}

void WindowsUpdater::install(const QString &path) {
  if (!confirmClose())
    return;
  // The NSIS installer waits for this process to exit before replacing files.
  if (!QProcess::startDetached(path, {QStringLiteral("/UPDATEPID=%1").arg(
                                       QCoreApplication::applicationPid())})) {
    QMessageBox::warning(nullptr, QStringLiteral("CedarLogic update"),
                         QStringLiteral("The update installer could not be started. "
                                        "Your circuit is still open. Please try again later."));
    return;
  }
  installerLaunched = true; // Keep the launched EXE until the next app startup.
  QCoreApplication::quit();
}
