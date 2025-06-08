import asyncio
import base64
import json
import re
from datetime import timezone
from typing import List

import pytz
import socks
from telethon import TelegramClient, events

from post_extension import load_config, send_msg_to_group
from text_formatter import process_markdown_links_and_add_references
from telethon.tl.types import MessageMediaPoll

# ────────────────── 配置 ──────────────────
config = load_config()

api_id = config["api_id"]
api_hash = config["api_hash"]
phone_number = config["phone_number"]
channel_username = config["channel_username"]
proxy_cfg = config["proxy"]

client = TelegramClient(
    f"./sessions/{api_id}",
    api_id,
    api_hash,
    proxy={
        "proxy_type": getattr(socks, proxy_cfg["proxy_type"].upper()),
        "addr": proxy_cfg["addr"],
        "port": proxy_cfg["port"],
        "rdns": proxy_cfg["rdns"],
    },
)

import logging
logging.basicConfig(level=logging.DEBUG if config.get("debug") else logging.INFO)
logging.getLogger('telethon').setLevel(logging.DEBUG if config.get("debug") else logging.INFO)

# ────────────────── 图片下载为 base64 ──────────────────
async def download_images_as_base64(message) -> List[str]:
    imgs: List[str] = []

    async def _dl(m):
        if m.photo:
            b = await m.download_media(file=bytes)
            imgs.append(base64.b64encode(b).decode())

    if message.grouped_id:
        recent = await client.get_messages(channel_username, limit=20)
        grouped = [m for m in recent if m.grouped_id == message.grouped_id]
        for m in grouped:
            await _dl(m)
    else:
        await _dl(message)

    return imgs


async def keep_alive():
    """
    每 5 秒向 Telegram 来一次极轻量的 get_me()，
    如果底层 socket 已被对方掐断，Telethon 会立刻抛出
    ConnectionError 并自动重连。
    """
    while True:
        try:
            await client.get_me()
        except Exception as e:
            print("⚠️  keep-alive: reconnecting", e)
        await asyncio.sleep(5)

# ────────────────── 主 ──────────────────
async def main():
    print("🚀 监听启动")
    await client.start(phone_number)
    channel = await client.get_entity(channel_username)

    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        msg = event.message
        if config.get("debug"):
            print(f"收到消息：{msg}")

        if (getattr(msg, "poll", None) or isinstance(msg.media, MessageMediaPoll)):
            return
        
        raw_text = msg.message or ""
        removal_strings = config.get("removal_strings", [])

        # 相册只处理最后一条
        if msg.grouped_id:
            recent = await client.get_messages(channel_username, limit=20)
            grouped = [m for m in recent if m.grouped_id == msg.grouped_id]
            if msg.id != max(m.id for m in grouped):
                return
            raw_text = "\n".join((m.message or "") for m in grouped)

        # 去掉尾部杂空行
        raw_text = re.sub(r"(\s*\n+\s*\S*\s*\n*\s*)$", "", raw_text).rstrip()

        # 链接解析 + 过滤
        body, refs = process_markdown_links_and_add_references(
            raw_text,
            entities=msg.entities,
            removal_strings=removal_strings,
        )
        text_for_send = f"{body}\n\n{refs}" if refs else body

        # 北京时间
        utc_dt = msg.date.replace(tzinfo=timezone.utc)
        cn_dt = utc_dt.astimezone(pytz.timezone("Asia/Shanghai"))
        time_str = cn_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 图片
        images = await download_images_as_base64(msg)

        if config.get("debug"):
            print(
                json.dumps(
                    {
                        "text": text_for_send, 
                        "time": time_str, 
                        "images": images
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        await asyncio.to_thread(send_msg_to_group, text_for_send, time_str, images)

    print(f"✅ 监听频道：{channel.title}（Ctrl+C 退出）")
    await client.run_until_disconnected()


try:
    with client:
        client.loop.create_task(keep_alive())
        client.loop.run_until_complete(main())
except KeyboardInterrupt:
    print("✅ Bye!")
