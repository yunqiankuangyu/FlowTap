//! FlowTap 数值内核：C ABI 动态库，由 Python ctypes 调用。
//! 目标：以与 TM_CCOEFF_NORMED 一致的语义，替换 vision.py 中
//! _score_at / _best_in_tolerance 的纯 Python 双重循环。

use std::os::raw::{c_char, c_double, c_int, c_void};
use std::ffi::{CStr, CString};

mod protocol;

// ─────────────────────────────────────────────────────────────
// 积分图：让任意矩形的 sum / sum_sq 在 O(1) 取出
// ─────────────────────────────────────────────────────────────

struct Integral {
    w: usize,
    data: Vec<u8>,
    sum: Vec<u64>,
    sum_sq: Vec<u64>,
}

impl Integral {
    fn new(data: &[u8], h: usize, w: usize) -> Self {
        let stride = w + 1;
        let mut sum = vec![0u64; (h + 1) * stride];
        let mut sum_sq = vec![0u64; (h + 1) * stride];

        for y in 0..h {
            let mut row_sum = 0u64;
            let mut row_sq = 0u64;
            let row_base = y * stride;
            let prev_base = (y + 1) * stride;
            for x in 0..w {
                let v = data[y * w + x] as u64;
                row_sum += v;
                row_sq += v * v;
                sum[prev_base + x + 1] = sum[row_base + x + 1] + row_sum;
                sum_sq[prev_base + x + 1] = sum_sq[row_base + x + 1] + row_sq;
            }
        }

        Self {
            w,
            data: data.to_vec(),
            sum,
            sum_sq,
        }
    }

    #[inline]
    fn rect(&self, x: i32, y: i32, rw: i32, rh: i32) -> (u64, u64) {
        let stride = self.w + 1;
        let x0 = x as usize;
        let y0 = y as usize;
        let x1 = (x + rw) as usize;
        let y1 = (y + rh) as usize;
        let i00 = y0 * stride + x0;
        let i10 = y0 * stride + x1;
        let i01 = y1 * stride + x0;
        let i11 = y1 * stride + x1;
        (
            self.sum[i11] - self.sum[i10] - self.sum[i01] + self.sum[i00],
            self.sum_sq[i11] - self.sum_sq[i10] - self.sum_sq[i01] + self.sum_sq[i00],
        )
    }
}

// ─────────────────────────────────────────────────────────────
// 模板：均值和 L2 范数只算一次（原版在 49 次循环里算了 49 次）
// ─────────────────────────────────────────────────────────────

struct Tpl {
    h: usize,
    w: usize,
    centered: Vec<f64>,
    norm2: f64,
}

impl Tpl {
    fn new(data: &[u8], h: usize, w: usize) -> Self {
        let n = (h * w) as f64;
        let sum: f64 = data.iter().map(|&v| v as f64).sum();
        let mean = sum / n;
        let centered: Vec<f64> = data.iter().map(|&v| v as f64 - mean).collect();
        let norm2: f64 = centered.iter().map(|v| v * v).sum();
        Self {
            h,
            w,
            centered,
            norm2,
        }
    }
}

#[inline]
fn score_at(img: &Integral, tpl: &Tpl, x: i32, y: i32) -> f64 {
    // 与 Python 原版逐字对齐：
    //   win = screen[y:y+h, x:x+w].astype(float64)
    //   iw  = win - win.mean()
    //   den = sqrt(sum(tw*tw) * sum(iw*iw))
    // 关键：窗口方差必须用「逐元素减均值再求和」计算，不能用积分图的
    // Σwin² - mean·Σwin —— 后者在纯色区域会因浮点残差得到极小正数，
    // 与 Python 的 den<=0 判定分歧（回归测试实测抓到过）。
    // 模板侧 tw/norm2 与位置无关，已预计算一次。
    let n = (tpl.h * tpl.w) as f64;
    let (s, _) = img.rect(x, y, tpl.w as i32, tpl.h as i32);
    let wmean = s as f64 / n;

    let mut dot = 0.0f64;   // Σ tw * iw
    let mut iw_norm2 = 0.0f64; // Σ iw²
    for ty in 0..tpl.h {
        let img_row = (y as usize + ty) * img.w + x as usize;
        let tpl_row = ty * tpl.w;
        for tx in 0..tpl.w {
            let iw = img.data[img_row + tx] as f64 - wmean;
            dot += tpl.centered[tpl_row + tx] * iw;
            iw_norm2 += iw * iw;
        }
    }

    let den = (tpl.norm2 * iw_norm2).sqrt();
    if den <= 0.0 {
        return -1.0;
    }
    dot / den
}

/// 与 vision.py::_best_in_tolerance 等价：在 ±tolerance 内逐像素微移取最高分。
///
/// # Safety
/// screen / tpl 必须分别指向 sh*sw / th*tw 个 u8；输出指针必须有效。
#[no_mangle]
pub unsafe extern "C" fn ft_best_in_tolerance(
    screen: *const u8,
    sh: c_int,
    sw: c_int,
    tpl: *const u8,
    th: c_int,
    tw: c_int,
    l: c_int,
    t: c_int,
    tolerance: c_int,
    out_score: *mut c_double,
    out_x: *mut c_int,
    out_y: *mut c_int,
) {
    if screen.is_null() || tpl.is_null() || out_score.is_null() || out_x.is_null() || out_y.is_null() {
        return;
    }
    let sh = sh as usize;
    let sw = sw as usize;
    let th = th as usize;
    let tw = tw as usize;
    if sh == 0 || sw == 0 || th == 0 || tw == 0 {
        *out_score = -1.0;
        return;
    }

    let screen_slice = std::slice::from_raw_parts(screen, sh * sw);
    let tpl_slice = std::slice::from_raw_parts(tpl, th * tw);
    let img = Integral::new(screen_slice, sh, sw);
    let tpl_ctx = Tpl::new(tpl_slice, th, tw);

    let mut best = -1.0f64;
    let mut best_x = 0i32;
    let mut best_y = 0i32;

    for dy in -tolerance..=tolerance {
        for dx in -tolerance..=tolerance {
            let x = l + dx;
            let y = t + dy;
            if x < 0 || y < 0 {
                continue;
            }
            if x + tw as i32 > sw as i32 || y + th as i32 > sh as i32 {
                continue;
            }
            let score = score_at(&img, &tpl_ctx, x, y);
            // 与 Python 原版一致：仅在严格大于时替换，平局保留先出现的（左上优先）
            if score > best {
                best = score;
                best_x = x;
                best_y = y;
            }
        }
    }

    *out_score = best;
    *out_x = best_x;
    *out_y = best_y;
}

/// 单点评分，供回归测试逐点比对。
#[no_mangle]
pub unsafe extern "C" fn ft_score_at(
    screen: *const u8,
    sh: c_int,
    sw: c_int,
    tpl: *const u8,
    th: c_int,
    tw: c_int,
    x: c_int,
    y: c_int,
) -> c_double {
    if screen.is_null() || tpl.is_null() {
        return -1.0;
    }
    let sh = sh as usize;
    let sw = sw as usize;
    let th = th as usize;
    let tw = tw as usize;
    if sh == 0 || sw == 0 || th == 0 || tw == 0 {
        return -1.0;
    }
    if x < 0 || y < 0 || x + tw as i32 > sw as i32 || y + th as i32 > sh as i32 {
        return -1.0;
    }
    let screen_slice = std::slice::from_raw_parts(screen, sh * sw);
    let tpl_slice = std::slice::from_raw_parts(tpl, th * tw);
    let img = Integral::new(screen_slice, sh, sw);
    let tpl_ctx = Tpl::new(tpl_slice, th, tw);
    score_at(&img, &tpl_ctx, x, y)
}

/// 校验并规范化动作列表 JSON。
/// 返回 C 字符串：成功为规范化 JSON 数组，失败以 "ERR:" 开头。
/// 调用方必须用 ft_free_string 释放返回值。
///
/// # Safety
/// input 必须指向 NUL 结尾的合法 UTF-8 C 字符串。
#[no_mangle]
pub unsafe extern "C" fn ft_validate_actions(input: *const c_char) -> *mut c_char {
    if input.is_null() {
        return into_c_string("ERR:输入指针为空".to_string());
    }
    let s = match CStr::from_ptr(input).to_str() {
        Ok(s) => s,
        Err(_) => return into_c_string("ERR:输入不是合法 UTF-8".to_string()),
    };
    into_c_string(protocol::validate_actions_json(s))
}

fn into_c_string(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// 释放由本库分配的字符串。
#[no_mangle]
pub unsafe extern "C" fn ft_free_string(p: *mut c_void) {
    if !p.is_null() {
        drop(CString::from_raw(p as *mut c_char));
    }
}

#[no_mangle]
pub extern "C" fn ft_add(a: i32, b: i32) -> i32 {
    a + b
}
