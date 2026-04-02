import { WS_URL } from "./api";
import { Storage } from "./storage";

export type SocketState = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED';

let socket: WebSocket | null = null;
let listeners: Record<string, ((data: any) => void)[]> = {};
let onStateChange: ((state: SocketState) => void) | null = null;
let currentState: SocketState = 'DISCONNECTED';
let reconnectAttempts = 0;
let reconnectTimer: any = null;
let heartbeatTimer: any = null;
let currentRideId: string | null = null;

const updateState = (state: SocketState) => {
    currentState = state;
    if (onStateChange) onStateChange(state);
    console.log(`[WS] State: ${state}`);
};

const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000); // 30s Heartbeat
};

const stopHeartbeat = () => {
    if (heartbeatTimer) clearInterval(heartbeatTimer);
};

export const SocketService = {

    setStateListener(callback: (state: SocketState) => void) {
        onStateChange = callback;
        callback(currentState);
    },

    async connect(rideId: string) {
        if (!rideId) {
            console.error("[WS] Cannot connect: rideId is missing");
            return;
        }

        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        currentRideId = rideId;
        updateState('CONNECTING');

        const token = await Storage.getToken();
        if (!token) {
            updateState('DISCONNECTED');
            return;
        }

        const url = `${WS_URL}rides/${rideId}/?token=${token}`;
        console.log(`[WS] Connecting to: ${url}`);
        
        socket = new WebSocket(url);

        socket.onopen = () => {
            console.log("[WS] Connected to ride", rideId);
            updateState('CONNECTED');
            reconnectAttempts = 0;
            startHeartbeat();
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const type = data.type || 'message';
                if (listeners[type]) {
                    listeners[type].forEach(callback => callback(data.payload || data));
                }
            } catch (e) {
                console.warn("[WS] Failed to parse message", event.data);
            }
        };

        socket.onclose = (event) => {
            console.log(`[WS] Closed: ${event.code} ${event.reason}`);
            socket = null;
            updateState('DISCONNECTED');
            stopHeartbeat();
            
            // Auto-reconnect logic
            if (reconnectAttempts < 5) {
                const delay = Math.pow(2, reconnectAttempts) * 1000;
                console.log(`[WS] Reconnecting in ${delay}ms...`);
                reconnectTimer = setTimeout(() => {
                    reconnectAttempts++;
                    if (currentRideId) SocketService.connect(currentRideId);
                }, delay);
            }
        };

        socket.onerror = (e) => {
            console.error("[WS] Error", e);
            updateState('DISCONNECTED');
        };
    },

    on(event: string, callback: (data: any) => void) {
        if (!listeners[event]) listeners[event] = [];
        listeners[event].push(callback);
        return () => {
            listeners[event] = listeners[event].filter(c => c !== callback);
        };
    },

    send(type: string, payload: any) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type, ...payload }));
        }
    },

    disconnect() {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        stopHeartbeat();
        if (socket) {
            socket.onclose = null; // Prevent reconnect on intentional close
            socket.close();
        }
        socket = null;
        updateState('DISCONNECTED');
        listeners = {};
        reconnectAttempts = 0;
    }
};
