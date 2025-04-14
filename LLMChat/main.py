from logger import init_db
from napcat.post import init_ws

def main():
    # 初始化消息记录数据库
    print("🚀 初始化数据库...")
    init_db()
    # 初始化 WebSocket 连接（注意：get.py 中会自动处理消息接收）
    print("🚀 初始化 WebSocket 连接...")
    init_ws()
    # 主线程休眠，保持程序运行
    import time
    print("✅ 初始化完成，主程序运行中...")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
