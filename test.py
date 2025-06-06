import websocket


def on_message(ws, message):
    print(f"Received: {message}")


def on_open(ws):
    print("Connection opened")
    ws.send("Hello WebSocket!")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: code={close_status_code}, msg={close_msg}")


if __name__ == "__main__":
    # Replace with any WebSocket echo server if you want, this one still works
    ws_url = (
        "ws://localhost:8000/realtime/collections/49f39295-2149-42ef-bcc7-65d363d0cf50"
    )

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    

    ws.run_forever()
