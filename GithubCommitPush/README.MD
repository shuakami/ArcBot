# 🚀 ArcBot - GitHub Webhook Push Bot 🔔

> 一个基于 [NapcatQQ](https://github.com/NapNeko/NapCatQQ) 的轻量级服务，用于监听 **GitHub** 仓库的 `push` 事件，并自动将提交信息发送到多个QQ目标群。

- **快速 & 简洁**：无多余依赖，轻松部署  
- **可配置**：`config.json` 里集中管理监听地址、Token、群号、需清理的字符等  
- **自动格式化提交信息**：支持显示作者、commit id、变动详情  
- **多群支持**：一次 Push，可同时转发到多个群  
- **可扩展**：若需处理更多事件或自定义消息格式，可在代码中灵活修改  

---

## ✨ 功能清单 

1. **GitHub Push 监听**：只在仓库有新提交时触发  
2. **提交合并 & 关键字清理**：自动合并多条提交，去除多余字符或表情   
4. **多群消息分发**：同一推送，自动发送到 `config.json` 中配置的全部群组  
5. **简易配置**：只需修改 `config.json` 即可个性化 Bot  
6. **可选安全校验**：若在 GitHub Webhook 中配置了 Secret，可对请求签名做对比，防止伪造请求（代码里可自定义实现）

---

## 🗂 文件结构 

```
.
├── config.json
├── main.py
├── post_extension.py
└── README.md
```

- **`config.json`**：配置文件，存储Webhook监听端口、目标接口、群号、需清理字符等  
- **`main.py`**：核心 Flask 入口，负责监听 `/gh/webhook` 接口，解析 GitHub Push 数据  
- **`post_extension.py`**：封装发送消息的方法，将文本推送到指定群  
- **`README.md`**：使用说明（本文件）

---

## 🛠 安装与使用 

1. **克隆或下载本项目**
   ```bash
   git clone https://github.com/XiaoXianHW/GitHubWebhookBot.git
   cd GitHubWebhookBot
   ```

2. **安装必要依赖**
   
   ```bash
   pip install flask requests
   ```
   - 仅需 `Flask`（启动 Web 服务器）和 `requests`（发送 HTTP 请求）
   
3. **配置 `config.json`**
   ```jsonc
   {
    "webhook_host": "0.0.0.0",
    "webhook_port": 60000,
    "webhook_secret": "xxx",
    "napcat_url": "http://ip:port/send_group_msg",
    "napcat_token": "xxx",
    "napcat_group_ids": [
        "10001"
    ],
    "removal_strings": [
        "Exmaple"
    ]
   }
   ```

4. **在 GitHub 仓库创建 Webhook**
   - 进入仓库 Settings → Webhooks → “Add webhook”
   - `Payload URL` = `http://服务器IP:60000/gh/webhook`  
   - `Content type` = `application/json`  
   - 只勾选 `push` 事件  
   - （可选）填写 Secret：若需要防刷，可在服务端对签名做 HMAC 校验  
   - 点击 “Add webhook”，完成后即可检测 Push

5. **测试效果**
   - 在本地对仓库进行 `git push`，查看本项目的控制台输出日志  
   - 如果成功，会把提交者、commit 信息、变动文件等发送到 `napcat_group_ids` 中的所有群组

## ❓ 常见问题 

1. **能否添加安全校验？**  
   - 可以。GitHub Webhook 的 Secret 校验主要通过 `X-Hub-Signature-256` 头进行 HMAC-SHA256 对比，请参考官方文档或在 `main.py` 里自行扩展。

2. **如何支持更多事件？**  
   - 打开 `main.py`，在 `/webhook` 路由中根据 `event = request.headers.get('X-GitHub-Event')` 判断分支，做不同处理即可。

3. **兼容 Python 版本？**  
   - Python 3.7+ 推荐。若版本过旧可能报兼容性错误。

4. **如何调试？**  
   - 启动后，用 `curl` 或 Postman 向 `http://localhost:60000/gh/webhook` 发送模拟数据，或在 GitHub Webhook 中点 “Test push” 进行验证。

---

## 🌱 可能的扩展想法 

- **Pull Request / Issues 集成**：在同一路由里处理 PR、Issue 的开/关事件，发送到群里讨论  
- **CI/CD 流程**：在 push 后自动构建并在群内通报结果  
- **多种消息格式**：根据需要支持富文本（富文本 JSON 或 HTML 等）

---

欢迎大家使用并根据需求做灵活定制！如有问题或改进建议，欢迎在本仓库提 [Issues](#) 或提交 [Pull Requests](#)。祝使用愉快！  
