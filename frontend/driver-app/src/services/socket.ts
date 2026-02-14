import { Storage } from "./storage";
import { WS_URL } from "./api";

class SocketManager {
    private static instance: SocketManager;
    private ws: WebSocket | null = null;
    private listeners: Map<string, Function[]> = new Map();

    private constructor() { }

    public static getInstance(): SocketManager {
        if (!SocketManager.instance) {
            SocketManager.instance = new SocketManager();
        }
        return SocketManager.instance;
    }

    public async connect(rideId: number): Promise<void> {
        const token = await Storage.getToken();
        if (!token) return;

        if (this.ws) {
            this.disconnect();
        }

        const wsUrl = `${WS_URL}/rides/${rideId}/?token=${token}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log("WebSocket connected");
            this.emit("connected", {});
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.emit(data.type, data.payload);
            } catch (err) {
                console.error("Failed to parse WS message", err);
            }
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket error", error);
        };

        this.ws.onclose = () => {
            console.log("WebSocket disconnected");
            this.emit("disconnected", {});
        };
    }

    public disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    public on(event: string, callback: Function): void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event)!.push(callback);
    }

    public off(event: string, callback: Function): void {
        const callbacks = this.listeners.get(event);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    private emit(event: string, data: any): void {
        const callbacks = this.listeners.get(event);
        if (callbacks) {
            callbacks.forEach((cb) => cb(data));
        }
    }
}

export default SocketManager;
