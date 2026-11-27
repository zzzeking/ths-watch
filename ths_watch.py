# -*- coding: utf-8 -*-
"""
同花顺博主发言监控 / 云端归档
监控对象：全能的野人（uid=639669238）

数据源：同花顺社区公开接口（无需登录、无需 token）
归档位置：data/YYYY-MM-DD.md（按北京时间分日）

飞书同步（配了哪个就走哪个，都不配则只做本地归档）：
  FEISHU_WEBHOOK                       群自定义机器人，有新发言推送到群
  FEISHU_APP_ID + FEISHU_APP_SECRET    自建应用凭证，用于上传图片（消息里直接显示图）
  FEISHU_DOC_ID                        可选，配了就把发言追加进这个飞书文档（含图片）

用法：
    python ths_watch.py          本机持续监控
    python ths_watch.py --once   只跑一次就退出（GitHub Actions 用这个）
    python ths_watch.py --test   发一条测试消息到飞书，验证通道是否打通
"""

import base64
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
INTERVAL = 180
API = "https://t.10jqka.com.cn/lgt/post/open/api/user/post"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATE_DIR = os.path.join(ROOT, "state")
SEEN_FILE = os.path.join(STATE_DIR, "seen.json")
MAX_SEEN = 5000

CST = timezone(timedelta(hours=8))

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

IMG_HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}


# ---------- 工具 ----------

def log(msg):
    print(f"[{datetime.now(CST):%H:%M:%S}] {msg}", flush=True)


def clean_text(raw):
    s = raw or ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract_stocks(raw):
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
        return None
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


def fetch_image(url, timeout=30):
    """下载图片，失败返回 None 而不是抛错。"""
    try:
        r = requests.get(url, headers=IMG_HEADERS, timeout=timeout)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        log(f"图片下载失败 {url[:60]}: {e}")
    return None


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
        for u in imgs:
            lines.append(f"![]({u})")
        lines.append("")

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


# ---------- 飞书：鉴权 ----------

def tenant_token():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
                      timeout=15)
    j = r.json()
    if j.get("code") != 0:
        raise RuntimeError(f"取 token 失败：{j}")
    return j["tenant_access_token"]


def upload_im_image(token, content, filename="img.jpg"):
    """上传图片到飞书，拿到 image_key，用于消息里直接显示图。"""
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            data={"image_type": "message"},
            files={"image": (filename, content, "image/jpeg")},
            timeout=40,
        )
        j = r.json()
        if j.get("code") == 0:
            return j["data"]["image_key"]
        log(f"飞书图片上传失败：{str(j)[:160]}")
    except Exception as e:
        log(f"飞书图片上传异常：{e}")
    return None


def upload_docx_image(token, content, filename="img.jpg"):
    """上传图片到飞书文档素材库，拿到 file_token，用于文档内嵌图片。"""
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "file_name": filename,
                "parent_type": "docx_image",
                "parent_node": FEISHU_DOC_ID,
                "size": str(len(content)),
            },
            files={"file": (filename, content, "image/jpeg")},
            timeout=60,
        )
        j = r.json()
        if j.get("code") == 0:
            return j["data"]["file_token"]
        log(f"飞书文档图片上传失败：{str(j)[:160]}")
    except Exception as e:
        log(f"飞书文档图片上传异常：{e}")
    return None


# ---------- 飞书：群机器人推送 ----------

def notify_webhook(post, token=None):
    if not FEISHU_WEBHOOK:
        return False

    dt = datetime.fromtimestamp(post.get("ctime") or 0, CST)
    body = clean_text(post.get("content"))
    stocks = extract_stocks(post.get("content"))
    link = post.get("jump_url") or ""
    imgs = post_images(post)
    title = f"{NICKNAME} · {dt:%m-%d %H:%M:%S}"

    tail = ""
    if stocks:
        tail += "\n\n提及：" + "、".join(f"{n}({c})" for n, c in stocks)
    if link:
        tail += f"\n原文：{link}"

    # 有应用凭证：上传图片，用富文本消息把图直接显示出来
    image_keys = []
    if token and imgs:
        for i, u in enumerate(imgs, 1):
            data = fetch_image(u)
            if not data:
                continue
            key = upload_im_image(token, data, f"{post.get('id')}_{i}.jpg")
            if key:
                image_keys.append(key)

    if image_keys:
        content = [[{"tag": "text", "text": body}]]
        for k in image_keys:
            content.append([{"tag": "img", "image_key": k}])
        if tail.strip():
            content.append([{"tag": "text", "text": tail.strip()}])
        payload = {
            "msg_type": "post",
            "content": {"post": {"zh_cn": {"title": title, "content": content}}},
        }
    else:
        text = f"{title}\n\n{body}{tail}"
        if imgs:
            text += "\n\n图片：\n" + "\n".join(imgs)
        payload = {"msg_type": "text", "content": {"text": text}}

    try:
        r = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20)
        j = r.json()
        ok = j.get("code") == 0 or j.get("StatusCode") == 0
        if not ok:
            log(f"飞书群推送失败：{str(j)[:160]}")
        return ok
    except Exception as e:
        log(f"飞书群推送异常：{e}")
        return False


# ---------- 飞书：写入文档 ----------

def _text_block(text):
    return {"block_type": 2, "text": {"style": {}, "elements": [{"text_run": {"content": text}}]}}


def _heading_block(text):
    return {"block_type": 5, "heading3": {"style": {}, "elements": [{"text_run": {"content": text}}]}}


def _image_block(file_token):
    return {"block_type": 27, "image": {"token": file_token}}


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

    for i, u in enumerate(imgs, 1):
        data = fetch_image(u)
        ft = upload_docx_image(token, data, f"{post.get('id')}_{i}.jpg") if data else None
        if ft:
            children.append(_image_block(ft))
        else:
            children.append(_text_block(f"图片{i}：{u}"))

    if stocks:
        children.append(_text_block("提及：" + "、".join(f"{n}({c})" for n, c in stocks)))
    if link:
        children.append(_text_block(f"原文：{link}"))
    children.append(_text_block("—" * 10))

    url = (f"https://open.feishu.cn/open-apis/docx/v1/documents/{FEISHU_DOC_ID}"
           f"/blocks/{FEISHU_DOC_ID}/children")
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json={"children": children, "index": -1}, timeout=30)
    j = r.json()
    if j.get("code") != 0:
        log(f"飞书文档写入失败：{str(j)[:200]}")
        return False
    return True


# ---------- 主流程 ----------

def deliver(post, token):
    append_to_day(post)
    notify_webhook(post, token)
    if token and FEISHU_DOC_ID:
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


def send_test(token):
    log("发送飞书测试消息…")
    post = {
        "id": "test",
        "ctime": int(time.time()),
        "content": "这是一条测试消息。如果你在飞书里看到了它，说明推送通道已经打通。",
        "jump_url": "",
        "ip_location": {"province_name": "本地"},
        "stat": {"reply": 0, "like": 0},
        "ext": {},
    }
    ok = notify_webhook(post, token)
    log("群推送结果：" + ("成功" if ok else "失败/未配置"))
    if token and FEISHU_DOC_ID:
        ok2 = append_to_feishu_doc(token, post)
        log("文档写入结果：" + ("成功" if ok2 else "失败"))


def main():
    once = "--once" in sys.argv
    test = "--test" in sys.argv
    log(f"开始监控「{NICKNAME}」(uid={UID})" + ("（单次模式）" if once else f"，间隔 {INTERVAL} 秒"))

    token = None
    if FEISHU_APP_ID and FEISHU_APP_SECRET:
        try:
            token = tenant_token()
            log("飞书应用凭证有效，图片上传已启用"
                + ("，文档同步已启用" if FEISHU_DOC_ID else "，未配置文档 ID"))
        except Exception as e:
            log(f"飞书应用凭证不可用：{e}")

    if test:
        send_test(token)
        return

    seen = load_seen()
    if seen is None:
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
