# ArcBot Telegram 转发 & 多群分发 Bot ️🤖

> 一个基于 [Telethon](https://github.com/LonamiWebs/Telethon) 的 Python 脚本，用于监听指定 Telegram 频道，并自动将消息（含多图）转发到多个目标群。可配置关键词清理、尾部正则清理等功能。

## 功能概览 ⚡

- **监听指定频道**：实时监听 Telegram 上指定频道的新消息。  
- **相册多图处理**：相册消息仅在最后一条图片到达后，统一收集并发送一次，避免重复。  
- **可配置关键词清理**：在发送前，可自动清理文本中的指定关键词/表情。  
- **多群消息分发**：可将同一条消息同时发送到多个目标群。  
- **可选代理**：可使用 SOCKS5/HTTP 等代理连接 Telegram。  

## 文件结构 📁

```
.
├── main.py               # 主脚本，负责监听TG频道并处理消息
├── post_extension.py     # Napcat POST模块，负责将消息发送到目标群
└── config.json           # 配置文件，存放API及自定义参数
```

## 安装 & 部署 🚀

1. **克隆本仓库**  
   ```bash
   git clone https://github.com/XiaoXianHW/ArcBot.git
   cd ArcBot
   ```

2. **安装依赖**  
   建议使用 Python 3.7+  
   ```bash
   pip install -r requirements.txt
   ```

3. **配置 `config.json`**  
   将以下字段按需填写：

   ```jsonc
   {
     "api_id": "你的TG-API ID",
     "api_hash": "你的TG-API hash",
     "phone_number": "你的手机号（含+区号）",
     "channel_username": "要监听的频道用户名(不含@号)",
     "debug": false,
     "proxy": {
       "proxy_type": "socks5",    // 可改 "socks4" "http" 等
       "addr": "localhost",
       "port": 7890,
       "rdns": true
     },
     "napcat_url": "http://ip:port/send_group_msg",
     "napcat_token": "你的napcat http服务token",
     "napcat_group_ids": [
       "groupid1",
       "groupid2"
       // 可继续添加更多
     ],
     "removal_strings": [
       "投稿",
       "频道"
       // 可配置更多需要移除的文字或表情
     ]
   }
   ```
   - **api_id / api_hash**：在 [Telegram 开发者平台](https://my.telegram.org/) 申请  
   - **phone_number**：你的 Telegram 登录手机号，首次登录会请求验证码  
   - **channel_username**：监听的频道 `名称` (比如 https://t.me/xxxnews 则填 `xxxnews`)
   - **proxy**：若不需代理，改为 `null` 或在 `main.py` 里不传 `proxy`  
   - **removal_strings**：文本中需要清理的字符

4. **启动 Bot**  
   ```bash
   python main.py
   ```
   首次启动会提示输入 Telegram 验证码 / 2FA 密码。成功后即可开始监听频道。

5. **运行中**  
   - 当检测到频道新消息时，会根据逻辑将文本及图片（多图相册一次性收集）发送到你配置的多个群。  
   - 如果config开启debug选项，控制台会打印 JSON 数据，便于调试查看。  
   - 按下 `Ctrl + C` 即可退出。

## 使用场景 🌐

- **媒体采集**：把 Telegram 频道当作信息源，将内容分发到本地或其它消息平台  
- **自动发布**：一旦频道更新，Bot 自动给多个讨论群、业务接口等发送提醒  
- **文本清洗**：去除水印、表情、无关字符等，得到干净的新闻文本

## 常见问题 ❓

1. **首次启动提示验证码？**  
   - 这是正常的 Telegram 登录流程，需要你输入发送到 Telegram 客户端的验证码；如果有两步验证则还需输密码。之后会保留 session 文件，无需再次登录。

2. **相册消息为何只发一次？**  
   - 脚本会等待相册中最后一张图片到来后一次性发送，避免重复。

3. **如何指定多个频道监听？**  
   - 目前示例只监听一个 `channel_username`，若要扩展多频道，可以在 `main.py` 的事件注册时改为一个 `chats=[...]` 列表或添加更多 `@client.on()` 装饰器逻辑。

4. **如何改尾部清理逻辑？**  
   - 在 `main.py` 中可以自行修改 `re.sub(...)` 部分以适配你的需求。

## 鸣谢 & 许可 📜

- 感谢 [Telethon](https://github.com/LonamiWebs/Telethon) 提供强大的 Telegram API 接口封装  
- 依赖项目：  
  - `telethon`  
  - `requests`  
  - `pysocks`  
  - `pytz`  

> 如有问题或改进建议，欢迎提交 [Issues](#) 或发起 [Pull Requests](#)。祝使用愉快！  

---

**⭐ 如果你觉得这个项目对你有所帮助，记得点个 Star 支持我们哦！**  