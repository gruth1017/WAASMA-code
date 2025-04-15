import React, { createContext, useEffect, useState } from "react";
import { io } from "socket.io-client";

// Create WebSocket context so children can use the socket
export const WebSocketContext = createContext(null);

// URL of your backend WebSocket server
const SOCKET_SERVER_URL = "http://localhost:5000";

const WebSocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    // Create WebSocket connection with cookies enabled
    const socketInstance = io(SOCKET_SERVER_URL, {
      transports: ["websocket"],
      withCredentials: true // Very important for Flask-SocketIO auth with cookies
    });

    // Save socket instance to state
    setSocket(socketInstance);

    // Debug logs
    socketInstance.on("connect", () => {
      console.log("✅ Connected to WebSocket");
    });

    socketInstance.on("disconnect", () => {
      console.log("❌ Disconnected from WebSocket");
    });

    // Clean up on unmount
    return () => {
      socketInstance.disconnect();
    };
  }, []);

  return (
    <WebSocketContext.Provider value={socket}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketProvider;
