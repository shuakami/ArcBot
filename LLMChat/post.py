import json
import websocket
import time
import threading
from config import CONFIG

ws_conn = None

def send_ws_message(message_dict):
    """
    通过 ws 连接发送 json 消息
    """
    global ws_conn
    try:
        ws_conn.send(json.dumps(message_dict))
    except Exception as e:
        print("ws发送消息出错:", e)

def set_input_status(user_id):
    """
    向 ws 发送设置输入状态的消息
    """
    status_payload = {
        "action": "set_input_status",
        "params": {
            "user_id": user_id,
            "event_type": 1
        }
    }
    send_ws_message(status_payload)

def init_ws():
    """
    初始化 ws 连接，并在独立线程中运行
    """
    global ws_conn
    def on_message(ws, message):
        # 将接收到消息交给 get.py 中的处理逻辑
        from get import handle_incoming_message
        handle_incoming_message(message)

    def on_error(ws, error):
        print("ws错误:", error)

    def on_close(ws, close_status_code, close_msg):
        print("ws连接关闭:", close_status_code, close_msg)
        time.sleep(5)
        connect_ws()

    def on_open(ws):
        print("ws连接已开启")

    def connect_ws():
        global ws_conn
        ws_conn = websocket.WebSocketApp(
            CONFIG["qqbot"]["ws_url"],
            header={"Authorization": CONFIG["qqbot"]["token"]},
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        ws_conn.run_forever()

    threading.Thread(target=connect_ws, daemon=True).start()
