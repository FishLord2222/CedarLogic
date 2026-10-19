#pragma once
#include <QObject>
#include <QString>
#include <functional>

// WinSparkle owns its worker thread and popup; installer handoff returns to Qt.
class WindowsUpdater final : public QObject {
public:
  explicit WindowsUpdater(std::function<bool()> confirmClose,
                          QObject *parent = nullptr);
  ~WindowsUpdater() override;
  void start(const QString &feed = QStringLiteral(
      "https://fishlord2222.github.io/CedarLogic/windows/appcast.xml"),
      const QString &version = QStringLiteral(CEDAR_RELEASE_VERSION),
      const QString &build = QStringLiteral(CEDAR_WINDOWS_BUILD_VERSION));

private:
  static WindowsUpdater *active;
  static int __cdecl runInstaller(const wchar_t *path);
  void install(const QString &path);
  std::function<bool()> confirmClose;
  QString installerCopy;
  bool installerLaunched = false;
  bool initialized = false;
};
