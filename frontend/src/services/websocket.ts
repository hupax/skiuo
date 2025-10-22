/**
 * WebSocket client for receiving real-time AI analysis tokens
 */

const WS_URL = import.meta.env.VITE_ANALYSIS_WS_URL || 'ws://localhost:8080/ws/analysis';

class AnalysisWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private onToken: ((token: string) => void) | null = null;
  private onError: ((error: Error) => void) | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;

  /**
   * Connect to analysis WebSocket
   */
  connect(
    sessionId: string,
    onToken: (token: string) => void,
    onError: (error: Error) => void = console.error
  ): void {
    this.sessionId = sessionId;
    this.onToken = onToken;
    this.onError = onError;

    const wsUrl = `${WS_URL}/${sessionId}`;
    console.log('Connecting to analysis WebSocket:', wsUrl);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Analysis WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        // Received an analysis token from server
        const token = event.data;
        console.log('Received token:', token);
        this.onToken?.(token);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError?.(new Error('WebSocket error'));
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);

        // Attempt reconnection if not manually closed
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect();
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.onError?.(error as Error);
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    console.log(
      `Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms...`
    );

    setTimeout(() => {
      if (this.sessionId && this.onToken) {
        this.connect(this.sessionId, this.onToken, this.onError!);
      }
    }, delay);
  }

  /**
   * Manually close the WebSocket connection
   */
  close(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client closed');
      this.ws = null;
    }
    this.sessionId = null;
    this.onToken = null;
    this.reconnectAttempts = 0;
    console.log('Analysis WebSocket closed by client');
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export default AnalysisWebSocket;
