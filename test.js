console.log("Connecting to WebSocket server...");

const ws = new WebSocket("ws://localhost:8000/realtime/collections/49f39295-2149-42ef-bcc7-65d363d0cf50");

ws.onopen = () => {
  console.log("🚀 Connection opened");

  const tokenMessage = { token: "my token" };
  ws.send(JSON.stringify(tokenMessage));
  console.log("📤 Token sent:", tokenMessage);
};

ws.onmessage = (event) => {
  console.log("✅ Received:", event.data);
};

ws.onerror = (error) => {
  console.error("❌ Error:", error);
};

ws.onclose = (event) => {
  console.warn(`🔌 Connection closed: code=${event.code}, reason=${event.reason}`);
};
