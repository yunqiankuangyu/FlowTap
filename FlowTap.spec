# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['cv2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtPdf',
              'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtVirtualKeyboard'],
    noarchive=False,
    optimize=0,
)
# FlowTap 只用 QtWidgets/Gui/Core——以下为打包器自动收集的未引用模块, 剔除省约10MB
_GONE = ("qml", "qt6quick", "qtquick", "qt6pdf", "qtpdf", "qt6network", "qtnetwork",
         "qt6opengl", "qtopengl", "virtualkeyboard",
         "plugins\\tls", "plugins\\networkinformation", "plugins\\generic", "qpdf.dll")
def _drop(entries):
    return [e for e in entries
            if not any(g in e[0].replace("/", "\\").lower() for g in _GONE)]
a.binaries = _drop(a.binaries)
a.datas = _drop(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FlowTap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
