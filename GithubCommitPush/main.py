import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
import hmac
import hashlib
from post_extension import load_config, send_msg_to_group

app = Flask(__name__)

config = load_config()
removal_strings = config.get("removal_strings", [])
webhook_host = config.get("webhook_host", "0.0.0.0")
webhook_port = config.get("webhook_port", 60000)
webhook_secret = config.get("webhook_secret", "")

@app.route('/gh')
def index():
    return "GitHub Webhook Bot is running!", 200

@app.route('/gh/webhook', methods=['POST'])
def github_webhook():
    """
    GitHub 仓库 push 事件时，POST 到此地址
    """
     # 1. 取出 GitHub 在头里带的签名
    #    一般是 X-Hub-Signature-256: sha256=<HMAC-SHA256 值>
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        return "Missing signature", 403

    # 2. 计算本地签名
    body = request.get_data()
    local_signature = "sha256=" + hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    # 3. 比较本地签名与头部签名
    if not hmac.compare_digest(local_signature, signature_header):
        return "Invalid signature", 403
    
    data = request.json
    event = request.headers.get('X-GitHub-Event', '')
    if event != 'push':
        return jsonify({"msg": "not a push event"}), 200
    
    # 分支名
    ref = data.get('ref', 'refs/heads/???')
    branch = ref.split('/')[-1] if 'refs/heads/' in ref else ref

    # 仓库信息
    repository = data.get('repository', {})
    # 仓库名
    repo_name = repository.get('full_name', 'UnknownRepo')
    # 是否私有仓库
    privete_repo = repository.get('private', 'Unknown')

    # 推送/提交者信息
    pusher = data.get('pusher', {}).get('name', 'UnknownPusher')
    commits = data.get('commits', [])
    if not commits:
        return jsonify({"msg": "no commits"}), 200

    # 整理所有提交信息
    commit_messages = []
    for c in commits:
        url = c.get('url', '')
        msg = c.get('message', '')
        author = c.get('author', {}).get('name', 'UnknownAuthor')
        time = c.get('timestamp', '')

        # 对消息做关键字移除
        for r in removal_strings:
            msg = msg.replace(r, "")

        commit_id = c.get('id', '')[:7]  # 取前7位
        commit_messages.append(f"- {author} 于 {datetime.fromisoformat(time).strftime('%Y/%m/%d %H:%M:%S')} 提交 [{commit_id}]:\n| {url}\n| {msg} ")

    # 拼装要发送的文本
    final_text = (
        f"🌐 仓库：{repo_name}\n"
        f"📄 分支：{branch}\n"
        f"🤔 推送：{pusher}\n\n"
        "📂 提交详情：\n" +
        "\n".join(commit_messages)
    )

    # 时间字符串
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 调用发送函数；此处用 asyncio.to_thread 避免阻塞
    asyncio.run(asyncio.to_thread(send_msg_to_group, final_text, time_str))

    return jsonify({"msg": "ok"}), 200

def run_server():
    app.run(host=webhook_host, port=webhook_port, debug=False)

if __name__ == '__main__':
    print("✅ GitHub Webhook Bot 启动中...")
    run_server()
