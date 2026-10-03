# -*- mode: python ; coding: utf-8 -*-
# 安装版专用: onedir 目录形态, 由 packaging/FlowTap.iss 压缩为安装包
from PyInstaller.utils.hooks import collect_data_files

# OCR(rapidocr)在函数内延迟导入, 静态分析扫不到, 必须显式声明(只列RapidOCR实际用到的子模块, 不用collect_submodules以免牵入torch/CUDA)
_hidden = [
    'cv2',
    'rapidocr_onnxruntime',
    'rapidocr_onnxruntime.main',
    'rapidocr_onnxruntime.cal_rec_boxes',
    'rapidocr_onnxruntime.ch_ppocr_cls',
    'rapidocr_onnxruntime.ch_ppocr_cls.text_cls',
    'rapidocr_onnxruntime.ch_ppocr_det',
    'rapidocr_onnxruntime.ch_ppocr_det.text_detect',
    'rapidocr_onnxruntime.ch_ppocr_rec',
    'rapidocr_onnxruntime.ch_ppocr_rec.text_recognize',
    'rapidocr_onnxruntime.utils',
    'rapidocr_onnxruntime.utils.infer_engine',
]
# onnx模型与字典文件(collect_data_files只收数据文件, 不牵模块依赖)
_datas = [('packaging/FlowTap.ico', 'packaging')] + collect_data_files('rapidocr_onnxruntime')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtPdf',
              'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtVirtualKeyboard',
              'torch', 'torchvision', 'torchaudio', 'tensorflow', 'jax', 'llvmlite', 'IPython'],
    noarchive=False,
    optimize=0,
)

# 打包瘦身排除表——PyInstaller 自动收集但 FlowTap 从不使用的
#   opencv_videoio_ffmpeg_*.dll  29MB —— 视频编解码器, FlowTap只截图做模板匹配, 从不处理视频
#   opengl32sw.dll                 20MB —— Mesa纯软件渲染兜底, FlowTap用QtWidgets不走OpenGL
#   PIL/_avif*.pyd                7.5MB —— AVIF图片解码, 截图走PNG/BMP用不上
# 合计省约 56MB (297MB -> 240MB)
# libscipy_openblas(19MB) 不可排除: numpy._core._multiarray_umath.pyd 静态链接了它,
#   抽掉会导致 numpy import 失败, 程序无法启动
# 保留不动: cv2.pyd 82MB / onnxruntime 34MB / Qt 49MB / 三个ONNX模型 15MB —— 都是OCR或UI必需
_GONE = (
    # Qt 未引用模块
    "qml", "qt6quick", "qtquick", "qt6pdf", "qtpdf", "qt6network", "qtnetwork",
    "qt6opengl", "qtopengl", "virtualkeyboard", "qpdf.dll",
    "plugins\\tls", "plugins\\networkinformation", "plugins\\generic",
    # OpenCV / Qt / PIL 的无用部分
    "opencv_videoio_ffmpeg", "opengl32sw", "_avif.cp3",
)
def _drop(entries):
    return [e for e in entries
            if not any(g in e[0].replace("/", "\\").lower() for g in _GONE)]
a.binaries = _drop(a.binaries)
a.datas = _drop(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlowTap',
    icon='packaging/FlowTap.ico',
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FlowTap',
)
