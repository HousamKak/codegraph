/**
 * WebSocket client for real-time graph updates
 */

export type WebSocketEventType =
  | 'connected'
  | 'file_changed'
  | 'file_error'
  | 'graph_update'
  | 'validation_result';

export interface WebSocketMessage {
  type: WebSocketEventType;
  timestamp?: string;
  [key: string]: any;
}

export interface FileChangeMessage extends WebSocketMessage {
  type: 'file_changed';
  file_path: string;
  reindexing: {
    entities_indexed: number;
    relationships_indexed: number;
    nodes_marked_changed: number;
  };
  propagation: {
    callers: number;
    callees: number;
    importers: number;
    subclasses: number;
  };
  validation: {
    is_valid: boolean;
    errors: number;
    warnings: number;
    violations: Array<{
      type: string;
      severity: string;
      message: string;
      file_path?: string;
      line_number?: number;
    }>;
  };
  changed_node_ids: string[];
}

export interface FileErrorMessage extends WebSocketMessage {
  type: 'file_error';
  file_path: string;
  error: string;
}

type EventListener = (data: WebSocketMessage) => void;

export class GraphWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<WebSocketEventType | 'all', EventListener[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private reconnectTimer: number | null = null;
  private isIntentionallyClosed = false;
  private url: string;

  constructor(url?: string) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = import.meta.env.VITE_API_BASE_URL
      ? new URL(import.meta.env.VITE_API_BASE_URL).host
      : window.location.host.replace(/:\d+/, ':8000');

    this.url = url || `${wsProtocol}//${wsHost}/ws`;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      console.log('[WebSocket] Already connected or connecting');
      return;
    }

    this.isIntentionallyClosed = false;

    try {
      console.log(`[WebSocket] Connecting to ${this.url}...`);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] Message received:', data.type, data);

          // Call specific listeners for this event type
          const typeListeners = this.listeners.get(data.type);
          if (typeListeners) {
            typeListeners.forEach((listener) => listener(data));
          }

          // Call 'all' listeners
          const allListeners = this.listeners.get('all');
          if (allListeners) {
            allListeners.forEach((listener) => listener(data));
          }
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Closed:', event.code, event.reason);

        if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);

    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    console.log('[WebSocket] Disconnected');
  }

  /**
   * Send a message to the server
   */
  send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof message === 'string' ? message : JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }

  /**
   * Send a ping to keep the connection alive
   */
  ping(): void {
    this.send({ type: 'ping' });
  }

  /**
   * Register an event listener
   */
  on(event: WebSocketEventType | 'all', callback: EventListener): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  /**
   * Unregister an event listener
   */
  off(event: WebSocketEventType | 'all', callback: EventListener): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection state
   */
  getState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Singleton instance
let wsInstance: GraphWebSocket | null = null;

export function getWebSocket(): GraphWebSocket {
  if (!wsInstance) {
    wsInstance = new GraphWebSocket();
  }
  return wsInstance;
}

export function disconnectWebSocket(): void {
  if (wsInstance) {
    wsInstance.disconnect();
    wsInstance = null;
  }
}
