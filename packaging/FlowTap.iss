; FlowTap 安装包脚本
; 编译: ISCC /DAppVersion=3.8.3 packaging\FlowTap.iss
#ifndef AppVersion
  #define AppVersion "dev"
#endif

[Setup]
AppId={{B7E2C4A1-5D38-4F6E-9A17-FlowTap000001}
AppName=FlowTap
AppVersion={#AppVersion}
AppPublisher=FlowTap
DefaultDirName={localappdata}\Programs\FlowTap
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=FlowTap-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
CloseApplications=yes
DisableProgramGroupPage=yes

[Languages]
; 第一条为兜底默认(匹配不上系统语言时用中文), ShowLanguageDialog=no 时按用户UI语言自动选
Name: "chinesesimplified"; MessagesFile: "Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
chinesesimplified.TasksDesc=附加任务:
english.TasksDesc=Additional tasks:
chinesesimplified.DesktopIcon=创建桌面快捷方式
english.DesktopIcon=Create desktop shortcut
chinesesimplified.LaunchApp=启动 FlowTap
english.LaunchApp=Launch FlowTap

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:TasksDesc}"

[Files]
Source: "..\dist\FlowTap\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\FlowTap"; Filename: "{app}\FlowTap.exe"
Name: "{autodesktop}\FlowTap"; Filename: "{app}\FlowTap.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FlowTap.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时清掉运行期生成的数据(模板/预设/日志)
Type: filesandordirs; Name: "{app}\templates"
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\settings.json"
