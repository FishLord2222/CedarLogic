Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!include "WordFunc.nsh"

!ifndef PAYLOAD
  !define PAYLOAD "stage"
!endif
!ifndef OUTPUT
  !define OUTPUT "CedarLogic-3.08-Windows-Setup.exe"
!endif
!ifndef SOURCE
  !define SOURCE ".."
!endif
!define APPKEY "Software\CedarLogic"
!define UNINSTALLKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\CedarLogic"
Name "CedarLogic 3.08"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\CedarLogic"
InstallDirRegKey HKCU "${APPKEY}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "3.0.8.1"
VIAddVersionKey /LANG=1033 "ProductName" "CedarLogic"
VIAddVersionKey /LANG=1033 "ProductVersion" "3.08"
VIAddVersionKey /LANG=1033 "FileVersion" "3.0.8.1"
VIAddVersionKey /LANG=1033 "FileDescription" "CedarLogic 3.08 Setup"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Cedarville University and CedarLogic contributors"
!define MUI_ICON "${SOURCE}/res/icon.ico"
!define MUI_UNICON "${SOURCE}/res/icon.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\CedarLogic.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}/LICENSE-CedarLogic"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "CedarLogic (required)" SecApp
  SectionIn RO
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  !include "${SOURCE}/tools/windows-legacy-files.nsh"
  File /r "${PAYLOAD}/*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${APPKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayName" "CedarLogic 3.08"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayVersion" "3.08"
  WriteRegStr HKCU "${UNINSTALLKEY}" "Publisher" "CedarLogic contributors"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayIcon" "$INSTDIR\CedarLogic.exe,0"
  WriteRegStr HKCU "${UNINSTALLKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALLKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINSTALLKEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINSTALLKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALLKEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${UNINSTALLKEY}" "EstimatedSize" $0
  CreateDirectory "$SMPROGRAMS\CedarLogic"
  CreateShortcut "$SMPROGRAMS\CedarLogic\CedarLogic.lnk" "$INSTDIR\CedarLogic.exe"
  CreateShortcut "$SMPROGRAMS\CedarLogic\Uninstall CedarLogic.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Microsoft Visual C++ runtime (if needed)" SecRuntime
  SetRegView 64
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ReadRegStr $1 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Version"
  SetRegView 32
  StrCpy $2 $1 1
  ${If} $2 == "v"
    StrCpy $1 $1 "" 1
  ${EndIf}
  ${VersionCompare} "$1" "14.44.35211.0" $2
  ${If} $0 != 1
  ${OrIf} $2 == 2
    DetailPrint "Installing the Microsoft Visual C++ x64 runtime..."
    ExecWait '"$INSTDIR\vc_redist.x64.exe" /install /quiet /norestart' $0
    ${If} $0 == 3010
      SetRebootFlag true
    ${ElseIf} $0 != 0
    ${AndIf} $0 != 1638
      MessageBox MB_OK|MB_ICONEXCLAMATION "The Microsoft runtime could not be installed (code $0). Run vc_redist.x64.exe in the installation folder before starting CedarLogic."
    ${EndIf}
  ${EndIf}
SectionEnd

Section "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\CedarLogic.lnk" "$INSTDIR\CedarLogic.exe"
SectionEnd

Section "Associate .cdl circuit files" SecAssociation
  ReadRegStr $0 HKCU "Software\Classes\.cdl" ""
  ${If} $0 != "CedarLogic.Project"
    WriteRegStr HKCU "${APPKEY}" "PreviousCdlProgID" "$0"
  ${EndIf}
  WriteRegStr HKCU "Software\Classes\.cdl" "" "CedarLogic.Project"
  WriteRegStr HKCU "Software\Classes\.cdl\OpenWithProgids" "CedarLogic.Project" ""
  WriteRegStr HKCU "Software\Classes\CedarLogic.Project" "" "CedarLogic Circuit"
  WriteRegStr HKCU "Software\Classes\CedarLogic.Project\DefaultIcon" "" "$INSTDIR\CedarLogic.exe,0"
  WriteRegStr HKCU "Software\Classes\CedarLogic.Project\shell\open\command" "" '"$INSTDIR\CedarLogic.exe" "%1"'
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SecApp} "Application, Qt libraries, help, licenses, and debug symbols. Installs for your Windows account."
!insertmacro MUI_DESCRIPTION_TEXT ${SecRuntime} "Install the bundled Microsoft Visual C++ x64 runtime if missing. Windows may request administrator permission for this Microsoft component."
!insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Add CedarLogic to your desktop."
!insertmacro MUI_DESCRIPTION_TEXT ${SecAssociation} "Register CedarLogic to open .cdl circuit files. Windows may ask you to choose a default app."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  ReadRegStr $0 HKCU "Software\Classes\.cdl" ""
  ${If} $0 == "CedarLogic.Project"
    ReadRegStr $1 HKCU "${APPKEY}" "PreviousCdlProgID"
    ${If} $1 == ""
      DeleteRegValue HKCU "Software\Classes\.cdl" ""
    ${Else}
      WriteRegStr HKCU "Software\Classes\.cdl" "" "$1"
    ${EndIf}
  ${EndIf}
  DeleteRegValue HKCU "Software\Classes\.cdl\OpenWithProgids" "CedarLogic.Project"
  DeleteRegKey /ifempty HKCU "Software\Classes\.cdl\OpenWithProgids"
  DeleteRegKey /ifempty HKCU "Software\Classes\.cdl"
  DeleteRegKey HKCU "Software\Classes\CedarLogic.Project"
  DeleteRegKey HKCU "${UNINSTALLKEY}"
  DeleteRegKey HKCU "${APPKEY}"
  Delete "$DESKTOP\CedarLogic.lnk"
  Delete "$SMPROGRAMS\CedarLogic\CedarLogic.lnk"
  Delete "$SMPROGRAMS\CedarLogic\Uninstall CedarLogic.lnk"
  RMDir "$SMPROGRAMS\CedarLogic"
  !include "${MANIFEST}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
SectionEnd

Function .onInit
  ; An updater-launched installer waits until the verified application's normal
  ; shutdown has released its executable and DLLs. Ordinary installs skip this.
  ${GetParameters} $0
  ${GetOptions} $0 "/UPDATEPID=" $1
  ${If} $1 != ""
    System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i r1) p.r2'
    ${If} $2 != 0
      System::Call 'kernel32::WaitForSingleObject(p r2, i 30000) i.r3'
      System::Call 'kernel32::CloseHandle(p r2)'
      ${If} $3 != 0
        MessageBox MB_OK|MB_ICONEXCLAMATION "CedarLogic is still closing. Please close it and run this installer again."
        Quit
      ${EndIf}
    ${EndIf}
  ${EndIf}
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "CedarLogic 3.08 requires 64-bit Windows."
    Quit
  ${EndIf}
FunctionEnd
