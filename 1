# -*- coding: utf-8 -*-
"""
同花顺博主发言监控 / 云端归档
监控对象：全能的野人（uid=639669238）

数据源：同花顺社区公开接口（无需登录、无需 token）
归档位置：data/YYYY-MM-DD.md（按北京时间分日）

飞书同步（两种方式可任选，都不配则只做本地归档）：
  1) FEISHU_WEBHOOK      群自定义机器人 webhook，有新发言立刻推到飞书群
  2) FEISHU_APP_ID + FEISHU_APP_SECRET + FEISHU_DOC_ID
                         自建应用凭证，把新发言追加进指定飞书文档

用法：
    python ths_watch.py          本机持续监控（每 INTERVAL 秒）
    python ths_watch.py --once   只跑一次就退出（GitHub Actions 用这个）
"""

import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# ---------- 配置 ----------
UID = "639669238"
NICKNAME = "全能的野人"
INTERVAL = 180                      # 本机持续模式下的轮询间隔（秒）
API = "https://t.10jqka.com.cn/lgt/post/open/api/user/post"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATE_DIR = os.path.join(ROOT, "state")
SEEN_FILE = os.path.join(STATE_DIR, "seen.json")
MAX_SEEN = 5000

CST = timezone(timedelta(hours=8))  # GitHub runner 是 UTC，必须显式指定北京时间

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "").strip()
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "").strip()
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "").strip()
FEISHU_DOC_ID = os.environ.get("FEISHU_DOC_ID", "").strip()

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                   "Mobile/15E148 Safari/604.1"),
    "Referer": "https://c.10jqka.com.cn/",
    "Accept": "application/json, text/plain, */*",
}


# ---------- 工具 ----------

def log(msg):
    print(f"[{datetime.now(CST):%H:%M:%S}] {msg}", flush=True)


def clean_text(raw):
    """把社区富文本转成纯文本，股票标签保留 $名称(代码)$ 形式。"""
    s = raw or ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract_stocks(raw):
    """抽取 $名称(代码)$ 里的股票，返回 [(名称, 代码)]。"""
    out, seen = [], set()
    for name, code in re.findall(r"\$([^$()]{1,30})\((\d{6})\)\$", raw or ""):
        if code not in seen:
            seen.add(code)
            out.append((name.strip(), code))
    return out


def post_images(post):
    return ((post.get("ext") or {}).get("att_img") or {}).get("img_urls") or []


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return None                      # None 表示首次运行
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return None


def save_seen(ids):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids)[-MAX_SEEN:], f, ensure_ascii=False)


# ---------- 抓取 ----------

def fetch_posts():
    r = requests.get(API, params={"uid": UID, "page": 1, "page_size": 15},
                     headers=HEADERS, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("status_code") != 0:
        raise RuntimeError(f"接口返回异常: {j.get('status_code')} {j.get('status_msg')}")
    return j.get("data") or []


# ---------- 本地 Markdown 归档 ----------

def render_entry(post):
    dt = datetime.fromtimestamp(post.get("ctime") or 0, CST)
    body = clean_text(post.get("content"))
    ip = (post.get("ip_location") or {}).get("province_name") or ""
    stat = post.get("stat") or {}

    lines = [f"### {dt:%H:%M:%S}　{ip}".rstrip(), "", body]

    imgs = post_images(post)
    if imgs:
        lines.append("")
        for i, u in enumerate(imgs, 1):
            lines.append(f"- [图片{i}]({u})")

    stocks = extract_stocks(post.get("content"))
    if stocks:
        lines.append("")
        lines.append("股票：" + "、".join(f"{n}({c})" for n, c in stocks))

    link = post.get("jump_url") or post.get("pc_jump_url") or ""
    meta = f"评论 {stat.get('reply', 0)} · 赞 {stat.get('like', 0)}"
    if link:
        meta += f" · [原文]({link})"
    lines += ["", f"> {meta}", ""]
    return dt, "\n".join(lines)


def append_to_day(post):
    dt, entry = render_entry(post)
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{dt:%Y-%m-%d}.md")

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {NICKNAME} · {dt:%Y-%m-%d}\n\n")

    with open(path, encoding="utf-8") as f:
        old = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(old.rstrip("\n") + "\n\n" + entry)
    return path


# ---------- 飞书：群机器人推送 ----------

def notify_webhook(post):
    if not FEISHU_WEBHOOK:
        return False
    dt = datetime.fromtimestamp(post.get("ctime") or 0, CST)
    body = clean_text(post.get("content"))
    stocks = extract_stocks(post.get("content"))
    link = post.get("jump_url") or ""

    text = f"{dt:%Y-%m-%d %H:%M:%S}  {NICKNAME}\n\n{body}"
    if stocks:
        text += "\n\n提及：" + "、".join(f"{n}({c})" for n, c in stocks)
    if link:
        text += f"\n\n{link}"

    payload = {"msg_type": "text", "content": {"text": text}}
    try:
        r = requests.post(FEISHU_WEBHOOK, json=payload, timeout=15)
        ok = r.json().get("code") == 0
        if not ok:
            log(f"飞书群推送失败：{r.text[:150]}")
        return ok
    except Exception as e:
        log(f"飞书群推送异常：{e}")
        return False


# ---------- 飞书：写入文档 ----------

def tenant_token():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
                      timeout=15)
    j = r.json()
    if j.get("code") != 0:
        raise RuntimeError(f"取 token 失败：{j}")
    return j["tenant_access_token"]


def _text_block(text, style=None):
    return {
        "block_type": 2,
        "text": {
            "style": style or {},
            "elements": [{"text_run": {"content": text}}],
        },
    }


def _heading_block(text):
    return {
        "block_type": 5,   # heading3
        "heading3": {
            "style": {},
            "elements": [{"text_run": {"content": text}}],
        },
    }


def append_to_feishu_doc(token, post):
    dt = datetime.fromtimestamp(post.get("ctime") or 0, CST)
    ip = (post.get("ip_location") or {}).get("province_name") or ""
    body = clean_text(post.get("content"))
    stocks = extract_stocks(post.get("content"))
    link = post.get("jump_url") or ""
    imgs = post_images(post)

    children = [_heading_block(f"{dt:%Y-%m-%d %H:%M:%S}　{ip}".rstrip())]

    for chunk in [body[i:i + 1500] for i in range(0, max(len(body), 1), 1500)]:
        if chunk.strip():
            children.append(_text_block(chunk))

    if stocks:
        children.append(_text_block("提及：" + "、".join(f"{n}({c})" for n, c in stocks)))
    for i, u in enumerate(imgs, 1):
        children.append(_text_block(f"图片{i}：{u}"))
    if link:
        children.append(_text_block(f"原文：{link}"))
    children.append(_text_block("—" * 10))

    url = (f"https://open.feishu.cn/open-apis/docx/v1/documents/{FEISHU_DOC_ID}"
           f"/blocks/{FEISHU_DOC_ID}/children")
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json={"children": children, "index": -1}, timeout=20)
    j = r.json()
    if j.get("code") != 0:
        log(f"飞书文档写入失败：{str(j)[:200]}")
        return False
    return True


# ---------- 主流程 ----------

def deliver(post, token):
    """把一条新发言落到本地 + 飞书。"""
    append_to_day(post)
    notify_webhook(post)
    if token:
        append_to_feishu_doc(token, post)


def poll(seen, token):
    posts = fetch_posts()
    new = [p for p in posts if str(p.get("id")) not in seen]
    new.sort(key=lambda p: p.get("ctime") or 0)

    for p in new:
        deliver(p, token)
        dt = datetime.fromtimestamp(p.get("ctime") or 0, CST)
        preview = clean_text(p.get("content")).replace("\n", " ")
        log(f"新增 [{dt:%m-%d %H:%M:%S}] {preview[:50]}")
        seen.add(str(p.get("id")))

    if new:
        save_seen(seen)
    return len(new)


def main():
    once = "--once" in sys.argv
    log(f"开始监控「{NICKNAME}」(uid={UID})"
        + ("（单次模式）" if once else f"，间隔 {INTERVAL} 秒"))

    token = None
    if FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_DOC_ID:
        try:
            token = tenant_token()
            log("飞书文档同步已启用")
        except Exception as e:
            log(f"飞书文档同步不可用：{e}")

    seen = load_seen()
    if seen is None:
        # 首次运行：归档当前可见发言作为基线，不推送（避免一上来刷屏）
        try:
            posts = sorted(fetch_posts(), key=lambda p: p.get("ctime") or 0)
            for p in posts:
                append_to_day(p)
            seen = {str(p.get("id")) for p in posts}
            save_seen(seen)
            log(f"首次运行：已归档 {len(posts)} 条作为基线（不推送）")
        except Exception as e:
            log(f"初始归档失败：{e}")
            seen = set()

    while True:
        try:
            n = poll(seen, token)
            if not n:
                log("无更新")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log(f"本次抓取失败：{e}")
        if once:
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        main()
    except KeyboardInterrupt:
        log("已停止")
