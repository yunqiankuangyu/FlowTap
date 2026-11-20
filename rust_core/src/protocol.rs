//! 动作协议校验层：用 serde_json 在边界处把损坏/恶意预设挡住。
//! C ABI: ft_validate_actions(json) -> 返回新分配的字符串指针（成功=规范化 JSON，
//! 失败=以 "ERR:" 开头的中文错误）；调用方必须用 ft_free_string 释放。

use serde_json::{json, Value};

const KINDS: &[&str] = &["combo", "key", "wait", "branch", "jump", "read", "varset", "cond"];

fn err(msg: String) -> String {
    format!("ERR:{}", msg)
}

fn as_f64(v: Option<&Value>, field: &str, default: f64, path: &str) -> Result<f64, String> {
    match v {
        None => Ok(default),
        Some(Value::Number(n)) => n.as_f64().ok_or_else(|| {
            err(format!("{} 字段 {} 不是有效数字", path, field))
        }),
        Some(_) => Err(err(format!("{} 字段 {} 类型错误: 需要数字", path, field))),
    }
}

fn as_i64(v: Option<&Value>, field: &str, default: i64, path: &str) -> Result<i64, String> {
    match v {
        None => Ok(default),
        Some(Value::Number(n)) => n.as_i64().ok_or_else(|| {
            err(format!("{} 字段 {} 不是整数", path, field))
        }),
        Some(_) => Err(err(format!("{} 字段 {} 类型错误: 需要整数", path, field))),
    }
}

fn as_str<'a>(v: Option<&'a Value>, field: &str, default: &'a str, path: &str) -> Result<&'a str, String> {
    match v {
        None => Ok(default),
        Some(Value::String(s)) => Ok(s.as_str()),
        Some(_) => Err(err(format!("{} 字段 {} 类型错误: 需要字符串", path, field))),
    }
}

fn normalize_action(a: &Value, idx: usize) -> Result<Value, String> {
    let path = format!("actions[{}]", idx);
    let obj = a.as_object().ok_or_else(|| err(format!("{} 不是对象", path)))?;
    let kind = as_str(obj.get("kind"), "kind", "", &path)?;
    if !KINDS.contains(&kind) {
        return Err(err(format!("{} 未知动作类型 '{}'，合法值: {}", path, kind, KINDS.join("/"))));
    }

    // 保留 UI 专用字段（name/wait/run/pick/sx/sy/rel/options/_lid 等）：
    // 从原对象克隆，只覆盖校验过的字段并补齐默认值，绝不洗掉界面状态。
    let mut out = obj.clone();
    out.insert("kind".into(), json!(kind));

    match kind {
        "combo" => {
            let vks = obj.get("vks").ok_or_else(|| err(format!("{} 缺少必需字段 vks", path)))?;
            let arr = vks.as_array().ok_or_else(|| err(format!("{} vks 必须是数组", path)))?;
            let mut keys = Vec::new();
            for (i, v) in arr.iter().enumerate() {
                let k = v.as_i64().ok_or_else(|| err(format!("{} vks[{}] 不是整数键码", path, i)))?;
                if !(0..=255).contains(&k) {
                    return Err(err(format!("{} vks[{}] 键码 {} 越界(0-255)", path, i, k)));
                }
                keys.push(json!(k));
            }
            out.insert("vks".into(), Value::Array(keys));
            out.insert("a".into(), json!(as_f64(obj.get("a"), "a", 0.0, &path)?));  // hold
            out.insert("b".into(), json!(as_f64(obj.get("b"), "b", 0.5, &path)?));  // delay
        }
        "key" => {
            out.insert("key".into(), json!(as_str(obj.get("key"), "key", "", &path)?));
            if let Some(v) = obj.get("vk") {
                let k = v.as_i64().ok_or_else(|| err(format!("{} vk 不是整数", path)))?;
                out.insert("vk".into(), json!(k));
            }
            for f in ["x", "y"] {
                out.insert(f.into(), json!(as_i64(obj.get(f), f, 0, &path)?));
            }
            out.insert("a".into(), json!(as_f64(obj.get("a"), "a", 0.0, &path)?));
            out.insert("b".into(), json!(as_f64(obj.get("b"), "b", 0.5, &path)?));
        }
        "wait" | "branch" => {
            out.insert("tpl".into(), json!(as_str(obj.get("tpl"), "tpl", "", &path)?));
            out.insert("timeout".into(), json!(as_f64(obj.get("timeout"), "timeout", 0.0, &path)?));
            out.insert("after".into(), json!(as_str(obj.get("after"), "after", "跳过", &path)?));
            out.insert("delay".into(), json!(as_f64(obj.get("delay"), "delay", 0.0, &path)?));
        }
        "jump" => {
            let to = as_i64(obj.get("to"), "to", 1, &path)?;
            if to < 1 {
                return Err(err(format!("{} 跳转目标 to={} 必须从 1 开始", path, to)));
            }
            out.insert("to".into(), json!(to));
            out.insert("delay".into(), json!(as_f64(obj.get("delay"), "delay", 0.0, &path)?));
        }
        "read" => {
            let region = obj.get("region").ok_or_else(|| err(format!("{} 缺少必需字段 region", path)))?;
            let arr = region.as_array().ok_or_else(|| err(format!("{} region 必须是数组", path)))?;
            if arr.len() != 4 {
                return Err(err(format!("{} region 需要 4 个坐标，实际 {} 个", path, arr.len())));
            }
            let coords: Result<Vec<i64>, String> = arr.iter().enumerate().map(|(i, v)| {
                v.as_i64().ok_or_else(|| err(format!("{} region[{}] 不是整数", path, i)))
            }).collect();
            out.insert("region".into(), json!(coords?));
            out.insert("var".into(), json!(as_str(obj.get("var"), "var", "", &path)?));
            out.insert("delay".into(), json!(as_f64(obj.get("delay"), "delay", 0.0, &path)?));
        }
        "varset" | "cond" => {
            out.insert("var".into(), json!(as_str(obj.get("var"), "var", "", &path)?));
            if kind == "varset" {
                out.insert("op".into(), json!(as_str(obj.get("op"), "op", "+", &path)?));
            } else {
                out.insert("cmp".into(), json!(as_str(obj.get("cmp"), "cmp", ">=", &path)?));
            }
            out.insert("val".into(), json!(as_f64(obj.get("val"), "val", 0.0, &path)?));
            out.insert("delay".into(), json!(as_f64(obj.get("delay"), "delay", 0.0, &path)?));
        }
        _ => unreachable!(),
    }
    Ok(Value::Object(out))
}

/// 校验并规范化动作列表。输入 JSON 数组，输出同样长度的数组（字段补齐默认值）。
pub fn validate_actions_json(input: &str) -> String {
    let parsed: Value = match serde_json::from_str(input) {
        Ok(v) => v,
        Err(e) => return err(format!("JSON 解析失败: {}", e)),
    };
    let arr = match parsed.as_array() {
        Some(a) => a,
        None => return err("顶层必须是动作数组".into()),
    };
    let mut out = Vec::with_capacity(arr.len());
    for (i, a) in arr.iter().enumerate() {
        match normalize_action(a, i) {
            Ok(v) => out.push(v),
            Err(e) => return e,
        }
    }
    serde_json::to_string(&Value::Array(out)).unwrap_or_else(|e| err(format!("序列化失败: {}", e)))
}
