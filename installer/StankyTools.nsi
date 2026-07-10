Unicode True

!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef APP_VERSION
    !define APP_VERSION "0.0.0"
!endif

!define APP_NAME "StankyTools"
!define COMPANY_NAME "TheStankylegTools"
!define APP_EXE "StankyTools.exe"

Name "${APP_NAME}"
OutFile "release_artifacts\StankyTools-Setup-v${APP_VERSION}.exe"

InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "Software\${COMPANY_NAME}\${APP_NAME}" "InstallLocation"

RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64

VIProductVersion "0.0.0.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "CompanyName" "${COMPANY_NAME}"
VIAddVersionKey "FileDescription" "${APP_NAME} Windows Installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Var InstalledExe

Function FindAppExe
    StrCpy $InstalledExe ""

    IfFileExists "$INSTDIR\StankyTools.exe" 0 +3
        StrCpy $InstalledExe "$INSTDIR\StankyTools.exe"
        Return

    IfFileExists "$INSTDIR\StankyTools\StankyTools.exe" 0 +3
        StrCpy $InstalledExe "$INSTDIR\StankyTools\StankyTools.exe"
        Return

    IfFileExists "$INSTDIR\dist\StankyTools.exe" 0 +3
        StrCpy $InstalledExe "$INSTDIR\dist\StankyTools.exe"
        Return

    IfFileExists "$INSTDIR\dist\StankyTools\StankyTools.exe" 0 +3
        StrCpy $InstalledExe "$INSTDIR\dist\StankyTools\StankyTools.exe"
        Return
FunctionEnd

Section "Install StankyTools" SEC_MAIN
    SetOutPath "$INSTDIR"

    ; Package the entire PyInstaller dist directory regardless of its structure.
    File /r "dist\*.*"

    Call FindAppExe

    StrCmp $InstalledExe "" 0 AppFound
        MessageBox MB_ICONSTOP \
            "StankyTools.exe was not found after installation."
        Abort

    AppFound:

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    WriteRegStr HKCU "Software\${COMPANY_NAME}\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${COMPANY_NAME}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayIcon" "$InstalledExe"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"

    CreateShortcut \
        "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$InstalledExe"

    CreateShortcut \
        "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
        "$INSTDIR\Uninstall.exe"

    CreateShortcut \
        "$DESKTOP\${APP_NAME}.lnk" \
        "$InstalledExe"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    RMDir /r "$INSTDIR"

    DeleteRegKey HKCU "Software\${COMPANY_NAME}\${APP_NAME}"

    DeleteRegKey HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd