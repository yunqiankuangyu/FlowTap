"""
预设管理模块
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import USER_DIR, ensure_user_dir, migrate_legacy, _app_dir

PRESETS_FILE = os.path.join(USER_DIR, "presets.json")   # 与 settings.json 同居 userdata/


def load_presets():
    """加载预设"""
    migrate_legacy("presets.json")   # 旧根目录文件一次性搬进 userdata/
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}


def save_presets(presets):
    """保存预设"""
    ensure_user_dir()
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def delete_preset(name):
    """删除预设"""
    presets = load_presets()
    if name in presets:
        del presets[name]
        save_presets(presets)
    return presets


#预设引用到的模板相对路径集合(wait_image.tpl + branch.options[].tpl, 去重)
def _tpl_refs(presets):
    refs = set()
    for p in (presets or {}).values():
        if not isinstance(p, dict):
            continue
        for t in p.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            for a in t.get("actions") or []:
                if not isinstance(a, dict):
                    continue
                if a.get("type") == "wait_image" and a.get("tpl"):
                    refs.add(a["tpl"])
                if a.get("type") == "branch":
                    for o in a.get("options") or []:
                        if isinstance(o, dict) and o.get("tpl"):
                            refs.add(o["tpl"])
    return refs


#模板组收集: png 与同名 json(框选bbox) 必须成对 —— 少 json 固定位置匹配会静默退化;
#源机器上本来就没 json 的旧模板只带 png, 导入端与源端行为一致(走全屏搜索)
def _collect_templates(refs):
    data = {}
    root = _app_dir()
    for rel in sorted(refs):
        base, _ext = os.path.splitext(rel)
        for one in (rel, base + ".json"):
            full = os.path.join(root, one)
            if not os.path.isfile(full):
                continue
            try:
                with open(full, "rb") as f:
                    data[one.replace(os.sep, "/")] = base64.b64encode(f.read()).decode("ascii")
            except Exception:
                pass
    return data


#导出文件的完整内容: flowtap_presets 原样保留(旧导入兜底分支靠它), 图内嵌在新键 flowtap_templates
def export_data():
    presets = load_presets()
    return {"flowtap_presets": presets,
            "flowtap_templates": _collect_templates(_tpl_refs(presets))}


#拆导入文件 → (预设字典, 模板字典); 老格式(无图键)模板给空 dict, 不报错
def import_split(data):
    if not isinstance(data, dict):
        raise ValueError
    tpls = data.get("flowtap_templates")
    if not isinstance(tpls, dict):
        tpls = {}
    incoming = data.get("flowtap_presets",
                        {k: v for k, v in data.items() if k != "flowtap_templates"})
    if not isinstance(incoming, dict):
        raise ValueError
    return incoming, tpls


#模板解码写回 templates/, 已存在的不覆盖 → (写入数, 跳过数)
def write_templates(tpls):
    ok = skip = 0
    root = _app_dir()
    tpl_root = os.path.join(root, "templates")
    for rel, b64 in (tpls or {}).items():
        rel = str(rel).replace("\\", "/").lstrip("/")
        if not rel.startswith("templates/"):
            continue
        full = os.path.normpath(os.path.join(root, rel.replace("/", os.sep)))
        if not full.startswith(tpl_root + os.sep):   # 防御: 只允许写回 templates/ 内
            continue
        if os.path.isfile(full):
            skip += 1
            continue
        try:
            raw = base64.b64decode(b64)   # 先解码: open("wb") 会先截断创建, 解码失败会留0字节残文件占住"不覆盖"名额
        except Exception:
            continue
        try:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(raw)
            ok += 1
        except Exception:
            pass
    return ok, skip
