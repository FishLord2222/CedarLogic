#include "Appearance.h"
#include "CrashReporter.h"
#include "Canvas.h"
#include "Editor.h"
#include "GateLibrary.h"
#include "Keyboard.h"
#include "Settings.h"
#include "render/SkiaProbe.h"
#ifdef Q_OS_WIN
#include "WindowsUpdater.h"
#endif
#include <QApplication>
#include <QCommandLineParser>
#include <QDir>
#include <QFileInfo>
#include <QFontDatabase>
#include <QIcon>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QStyleFactory>
#include <QStyleHints>
#include <QTimer>
#include <cstdio>
int main(int argc, char **argv) {
#ifdef CEDAR_PORTAL_THEME
  // Bundled Qt cannot load desktop plugins built against the system's different
  // Qt version. Its bundled portal plugin delegates to the desktop's own picker.
  if (qEnvironmentVariable("QT_QPA_PLATFORM") != "offscreen" &&
      qEnvironmentVariable("QT_QPA_PLATFORM") != "minimal")
    qputenv("QT_QPA_PLATFORMTHEME", "xdgdesktopportal");
#endif
  // The legacy retained model is mutated on the GUI thread. Use Qt's basic
  // render loop until a snapshot-based threaded scene backend is introduced.
  qputenv("QSG_RENDER_LOOP", "basic");
  QQuickStyle::setStyle("Basic");
  QApplication app(argc, argv);
  app.setOrganizationName("CedarLogic");
  app.setOrganizationDomain("io.github.emonte_cu");
  app.setDesktopFileName("io.github.emonte_cu.CedarLogic");
  app.setApplicationName("CedarLogic-Qt");
  app.setApplicationVersion(CEDAR_RELEASE_VERSION);
  CrashReporter::install();
  QCommandLineParser parser;
  parser.setApplicationDescription("CedarLogic Qt Quick frontend");
  parser.addHelpOption();
  parser.addVersionOption();
  parser.addPositionalArgument("circuit", "Circuit to open");
  parser.addOption({"screenshot", "Save a UI screenshot and exit", "path"});
  parser.addOption(
      {"theme", "Appearance override for this session: light or dark", "mode"});
  parser.addOption({"preferences", "Open Preferences on startup"});
  parser.process(app);
  QString resources =
      QDir(QCoreApplication::applicationDirPath()).filePath("res");
  if (!QFileInfo::exists(resources + "/cl_gatedefs.xml"))
    resources = QDir(QCoreApplication::applicationDirPath())
                    .filePath("../share/CedarLogic/res");
  if (!QFileInfo::exists(resources + "/cl_gatedefs.xml"))
    resources = QStringLiteral(CEDAR_SOURCE_RES);
  app.setWindowIcon(QIcon(resources + "/icon.png"));
  QFontDatabase::addApplicationFont(resources + "/InterfaceFont-Bold.ttf");
  auto fontId =
      QFontDatabase::addApplicationFont(resources + "/InterfaceFont.ttf");
  if (fontId >= 0) {
    auto families = QFontDatabase::applicationFontFamilies(fontId);
    if (!families.isEmpty()) {
      QFont font(families.first());
      font.setPixelSize(13);
      app.setFont(font);
    }
  }
  appConfig().resourcesDir = resources.toStdString();
  cl::render::setFontSearchDir(
      (QFileInfo(resources).absolutePath() + "/").toUtf8().constData());
  try {
    gateLibrary().libParser =
        LibraryParse((resources + "/cl_gatedefs.xml").toStdString());
  } catch (const std::exception &e) {
    fprintf(stderr, "%s\n", e.what());
    return 1;
  }
  Appearance theme;
  if (parser.isSet("theme"))
    theme.setSessionMode(parser.value("theme"));
  Editor editor(&theme);
  // The original frontend starts its simulation timer on launch.
  editor.setRunning(true);
  qmlRegisterType<Waveforms>("CedarLogic", 1, 0, "Waveforms");
  qmlRegisterType<Canvas>("CedarLogic", 1, 0, "CircuitCanvas");
  qmlRegisterUncreatableType<Editor>("CedarLogic", 1, 0, "Editor",
                                     "Created by the application");
  qmlRegisterUncreatableType<Appearance>("CedarLogic", 1, 0, "Appearance",
                                         "Created by the application");
  QQmlApplicationEngine engine;
  Keyboard keyboard;
  QObject::connect(
      &engine, &QQmlEngine::warnings, [](const QList<QQmlError> &errors) {
        for (auto &e : errors)
          fprintf(stderr, "%s\n", e.toString().toUtf8().constData());
      });
  engine.rootContext()->setContextProperty("backend", &editor);
  engine.rootContext()->setContextProperty("keyboard", &keyboard);
  engine.rootContext()->setContextProperty("releaseVersion", app.applicationVersion());
  engine.rootContext()->setContextProperty("theme", &theme);
  engine.addImageProvider("gates", new GateImages);
  engine.addImageProvider("icons", new Icons);
  engine.load(QUrl("qrc:/qml/Main.qml"));
  if (engine.rootObjects().isEmpty())
    return 2;
  keyboard.setWindow(qobject_cast<QQuickWindow *>(engine.rootObjects()[0]));
  if (!parser.isSet("screenshot")) QTimer::singleShot(0, &app, &CrashReporter::showPending);
  if (!parser.positionalArguments().isEmpty())
    QTimer::singleShot(100, &editor, [&] {
      editor.openPath(parser.positionalArguments()[0]);
    });
  else if (!parser.isSet("screenshot"))
    QTimer::singleShot(100, &editor, &Editor::checkRecovery);
  if (parser.isSet("preferences"))
    QTimer::singleShot(300, [&] {
      QMetaObject::invokeMethod(engine.rootObjects()[0], "openPreferences");
    });
  if (parser.isSet("screenshot")) {
    auto path = parser.value("screenshot");
    QTimer::singleShot(1500, [&, path] {
      auto window = qobject_cast<QQuickWindow *>(engine.rootObjects()[0]);
      if (!window || !window->grabWindow().save(path)) {
        fprintf(stderr, "Screenshot failed\n");
        app.exit(3);
      } else
        app.quit();
    });
  }
#ifdef Q_OS_WIN
  WindowsUpdater updater([&editor] { return editor.confirmClose(); });
  if (!parser.isSet("screenshot"))
    QTimer::singleShot(750, &updater, [&updater] { updater.start(); });
#endif
  return app.exec();
}
