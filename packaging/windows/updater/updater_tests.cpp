#include "WindowsUpdater.h"
#include <winsparkle.h>
#include <QApplication>
#include <QElapsedTimer>
#include <QFile>
#include <QScreen>
#include <QPixmap>
#include <QStandardPaths>
#include <QThread>
#include <QTimer>
#include <QWidget>
#include <atomic>
#include <cstdio>
#include <windows.h>

namespace {
std::atomic<bool> found{false}, current{false}, failed{false};
void __cdecl didFind() { found = true; }
void __cdecl didNotFind() { current = true; }
void __cdecl error() { failed = true; }
HWND updateWindow() {
  HWND result = nullptr;
  EnumWindows([](HWND window, LPARAM data) -> BOOL {
    DWORD pid = 0;
    GetWindowThreadProcessId(window, &pid);
    wchar_t title[256] = {};
    GetWindowTextW(window, title, 256);
    if (pid == GetCurrentProcessId() && IsWindowVisible(window)
        && QString::fromWCharArray(title) == QStringLiteral("Software Update"))
      *reinterpret_cast<HWND *>(data) = window;
    return TRUE;
  }, reinterpret_cast<LPARAM>(&result));
  return result;
}
HWND installButton(HWND window) {
  HWND result = nullptr;
  EnumChildWindows(window, [](HWND child, LPARAM data) -> BOOL {
    wchar_t title[256] = {}, kind[128] = {};
    GetWindowTextW(child, title, 256);
    GetClassNameW(child, kind, 128);
    if (QString::fromWCharArray(kind).compare(QStringLiteral("Button"), Qt::CaseInsensitive) == 0
        && QString::fromWCharArray(title).contains(QStringLiteral("Install update"), Qt::CaseInsensitive)
        && IsWindowVisible(child) && IsWindowEnabled(child))
      *reinterpret_cast<HWND *>(data) = child;
    return TRUE;
  }, reinterpret_cast<LPARAM>(&result));
  return result;
}
}

int main(int argc, char **argv) {
  QApplication app(argc, argv);
  app.setOrganizationName("CedarLogicUpdateTests");
  app.setApplicationName("StartupUpdater");
  if (argc < 3) return 2;
  const auto mode = QString::fromLocal8Bit(argv[1]);
  const auto feed = QString::fromLocal8Bit(argv[2]);
  QWidget host;
  host.setWindowTitle("CedarLogic update integration test");
  host.resize(640, 360);
  host.show();
  int confirmations = 0;
  bool mainThread = true;
  WindowsUpdater updater([&] {
    ++confirmations;
    mainThread = QThread::currentThread() == app.thread();
    return mode == "install";
  });
  win_sparkle_set_lang("en");
  win_sparkle_set_did_find_update_callback(didFind);
  win_sparkle_set_did_not_find_update_callback(didNotFind);
  win_sparkle_set_error_callback(error);
  QElapsedTimer elapsed;
  elapsed.start();
  int clicks = 0;
  bool capturing = false;
  qint64 lastClick = -1000;
  QTimer timer;
  QObject::connect(&timer, &QTimer::timeout, [&] {
    auto popup = updateWindow();
    auto pass = [&](const char *message) {
      printf("PASS: %s\n", message);
      fflush(stdout);
      app.exit(0);
    };
    if (mode == "newer" && found && popup) {
      if (!capturing) {
        capturing = true;
        QTimer::singleShot(750, [&] {
          if (argc > 3) app.primaryScreen()->grabWindow(0).save(QString::fromLocal8Bit(argv[3]));
          printf("PASS: newer release produces a startup popup\n");
          app.exit(0);
        });
      }
    } else if (mode == "current" && current && elapsed.elapsed() > 1500) {
      if (popup) app.exit(3);
      else pass("same or older version stays quiet");
    } else if (mode == "offline" && failed && elapsed.elapsed() > 1500) {
      if (popup) app.exit(4);
      else pass("failed startup check stays quiet");
    } else if ((mode == "cancel" || mode == "install" || mode == "corrupt") && popup) {
      if (mode == "corrupt" && failed) {
        if (confirmations != 0) app.exit(5);
        else pass("tampered installer rejected before installation handoff");
      }
      auto button = installButton(popup);
      if (button && clicks < 2 && elapsed.elapsed() - lastClick > 500) {
        PostMessageW(button, BM_CLICK, 0, 0);
        lastClick = elapsed.elapsed();
        ++clicks;
      }
    }
    if (mode == "cancel" && confirmations == 1) {
      if (!mainThread || !QFile::exists(QStandardPaths::writableLocation(QStandardPaths::CacheLocation)
                                      + "/updates/CedarLogic-setup.exe")) app.exit(6);
      else pass("cancel keeps app open; verified installer survives popup cleanup");
    }
    if (elapsed.elapsed() > 20000) {
      fprintf(stderr, "Timed out: found=%d current=%d error=%d popup=%p clicks=%d confirmations=%d\n",
              int(found.load()), int(current.load()), int(failed.load()), popup, clicks, confirmations);
      app.exit(7);
    }
  });
  timer.start(100);
  QTimer::singleShot(200, &updater, [&] { updater.start(feed); });
  const auto result = app.exec();
  if (mode == "install" && result == 0) {
    if (confirmations != 1 || !mainThread) return 8;
    printf("PASS: verified installer launched after confirmation on the GUI thread\n");
  }
  return result;
}
