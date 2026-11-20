# FlowTap Rust 内核改造说明（副本）

本目录是 `D:/FlowTap` 的完整副本，所有改造只发生在这里，原项目未改动。

## 改造内容

1. **Rust 数值内核**（`rust_core/`）：用积分图 + 预计算模板均值/方差，替换 `core/vision.py` 的 `_score_at` / `_best_in_tolerance` 纯 Python 双重循环。C ABI 动态库，Python 用 ctypes 调用。
2. **动作协议校验层**（`rust_core/src/protocol.rs`）：用 serde_json 在边界校验 9 种动作，挡住损坏预设，保留所有 UI 专用字段。
3. **按需预热**（`engine/prewarm.py`）：任务里出现识图/读数节点时，后台加载对应组件，消除首次点击卡顿。

## 目录布局

```
根目录/
  main.py          v1 入口 + 两版共用的启动骨架（提权/DPI/崩溃弹窗）
  main_v2.py       v2 打包入口（薄壳）
  logger.py        共用日志
  启动新UI.bat / 启动旧UI.bat
  engine/          改造引入的运行时模块
    native_bridge.py   ctypes 桥接（加载 rust_core 的 DLL）
    prewarm.py         按需预热
  rust_core/       Rust crate（源码 + 编译产物 DLL）
  core/ config/ tasks/ ui/ ui_v2/   原项目代码（含少量改造分支）
```

## 启用方式

**无需任何开关**——Rust 已直接替换原 Python 实现，程序启动即走 Rust。

- 数值内核：`core/vision.py::_best_in_tolerance` 直接转发到 Rust，原 Python 版已删除。
- 协议校验：`ui_v2/runner.py::to_engine` 一律先过 Rust serde 校验；坏输入降级为空键动作（业务兜底，非 Python 备份）。
- **DLL 是硬依赖**：缺失或损坏时明确报错，不静默降级。这是"重写即替换、不留备份"的约定。

## 打包 / 分发

DLL 必须随程序一起分发，否则 Rust 功能报错：

- 源码运行：DLL 在 `rust_core/target/release/flowtap_core.dll`。
- 打包 exe：两个 spec 已把 DLL 作为 binaries 收进包根，并把 `engine` 加入 hiddenimports（函数内 import 静态分析扫不到）。打包后 `native_bridge` 从 `sys._MEIPASS` 找 DLL。
- git clone：仓库需包含 `engine/`（Python 源码）+ DLL。若 clone 后没编译 DLL，须先 `cargo build --release`。

## 改动的文件

- `core/vision.py`：删除 Python 版 `_score_at` / `_best_in_tolerance`，直接调 Rust。
- `ui_v2/runner.py`：`to_engine` 入口直接走 Rust 校验，删除开关与降级备份。
- `engine/native_bridge.py`：DLL 缺失明确报错，删除全部 Python 参考实现。
- 两入口 `main.py` / `ui_v2/main_v2.py` + `ui_v2/model.py` / `ui/keyboard_mode.py`：接入按需预热。
- `FlowTap.spec` / `FlowTap_onedir.spec`：加 engine 隐藏导入 + DLL 打包。

## 验证结果（实测）

- 数值一致性：逐点与微移结果与 Python 版零误差，坐标一致。
- 真实端到端（`match_once`，大模板 1866×331）：Python 约 512ms → Rust 约 114ms，**约 4.5×**。
- 小基准（`_best_in_tolerance`，真实 numpy 环境）：1.5×～3×，模板越大越明显。
- 协议层：合法动作字段补齐正确；损坏输入精确拒绝；UI 字段完整保留。
- 按需预热：空任务/纯按键不加载；加读数只加载 OCR；加识图才加载 cv2/PIL；幂等无错误。

## 重新编译

```bash
export PATH="/c/Users/KuangYu/.cargo/bin:$PATH"
cd rust_core && cargo build --release
```

产物：`rust_core/target/release/flowtap_core.dll`（`engine/native_bridge.py` 会自动到上一级找它）

## 未做/不建议

- 未动 OCR 推理（ONNX 已是原生）、未动 UI（Qt 已是原生）、未动 SendInput 注入。
- 打包体积不会减小：大头是 cv2 82MB + onnx 34MB + Qt 49MB，与本次改造无关。
- "随机偶尔卡一下"未定位到根因（怀疑 GIL 抢占/系统抖动），本次未处理。
