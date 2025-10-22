/**
 * WebRTC Client for StreamMind
 * Handles camera/microphone access and WebRTC connection to signaling server
 */

const SIGNALING_URL = import.meta.env.VITE_SIGNALING_WS_URL || 'ws://localhost:3000';

interface SignalingMessage {
  type: string;
  sdp?: string;
  candidate?: RTCIceCandidate;
  message?: string;
}

class WebRTCClient {
  private peerConnection: RTCPeerConnection | null = null;
  private localStream: MediaStream | null = null;
  private signalingWs: WebSocket | null = null;
  private sessionId: string | null = null;
  private onError: ((error: Error) => void) | null = null;

  /**
   * Start WebRTC session
   */
  async start(sessionId: string, onError: (error: Error) => void = console.error): Promise<boolean> {
    this.sessionId = sessionId;
    this.onError = onError;

    try {
      // Get user media (camera + microphone)
      await this.getUserMedia();

      // Connect to signaling server
      await this.connectSignaling();

      // Create peer connection
      await this.createPeerConnection();

      // Create and send offer
      await this.createOffer();

      return true;
    } catch (error) {
      console.error('Failed to start WebRTC:', error);
      this.onError?.(error as Error);
      return false;
    }
  }

  /**
   * Get camera and microphone access
   */
  async getUserMedia(): Promise<MediaStream> {
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: true
      });

      console.log('Got user media:', this.localStream);
      return this.localStream;
    } catch (error) {
      console.error('Error accessing media devices:', error);
      throw new Error('无法访问摄像头或麦克风，请检查权限设置');
    }
  }

  /**
   * Connect to signaling server via WebSocket
   */
  connectSignaling(): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `${SIGNALING_URL}/signaling/${this.sessionId}`;
      console.log('Connecting to signaling server:', wsUrl);

      this.signalingWs = new WebSocket(wsUrl);

      this.signalingWs.onopen = () => {
        console.log('Signaling WebSocket connected');
        resolve();
      };

      this.signalingWs.onerror = (error) => {
        console.error('Signaling WebSocket error:', error);
        reject(new Error('无法连接到信令服务器'));
      };

      this.signalingWs.onmessage = (event) => {
        const message: SignalingMessage = JSON.parse(event.data);
        this.handleSignalingMessage(message);
      };

      this.signalingWs.onclose = () => {
        console.log('Signaling WebSocket closed');
      };

      // Timeout after 5 seconds
      setTimeout(() => {
        if (this.signalingWs!.readyState !== WebSocket.OPEN) {
          reject(new Error('连接信令服务器超时'));
        }
      }, 5000);
    });
  }

  /**
   * Create RTCPeerConnection
   */
  async createPeerConnection(): Promise<void> {
    const config: RTCConfiguration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    };

    this.peerConnection = new RTCPeerConnection(config);

    // Add local stream tracks to peer connection
    this.localStream!.getTracks().forEach(track => {
      this.peerConnection!.addTrack(track, this.localStream!);
    });

    // Handle ICE candidates
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendSignalingMessage({
          type: 'ice-candidate',
          candidate: event.candidate
        });
      }
    };

    // Connection state changes
    this.peerConnection.onconnectionstatechange = () => {
      console.log('Connection state:', this.peerConnection!.connectionState);
      if (this.peerConnection!.connectionState === 'failed') {
        this.onError?.(new Error('WebRTC连接失败'));
      }
    };

    console.log('Peer connection created');
  }

  /**
   * Create SDP offer and send to signaling server
   */
  async createOffer(): Promise<void> {
    try {
      const offer = await this.peerConnection!.createOffer();
      await this.peerConnection!.setLocalDescription(offer);

      this.sendSignalingMessage({
        type: 'offer',
        sdp: offer.sdp
      });

      console.log('Sent offer to signaling server');
    } catch (error) {
      console.error('Error creating offer:', error);
      throw error;
    }
  }

  /**
   * Handle signaling messages from server
   */
  async handleSignalingMessage(message: SignalingMessage): Promise<void> {
    const { type } = message;

    switch (type) {
      case 'answer':
        await this.peerConnection!.setRemoteDescription({
          type: 'answer',
          sdp: message.sdp!
        });
        console.log('Received answer from server');
        break;

      case 'ice-candidate':
        await this.peerConnection!.addIceCandidate(message.candidate!);
        console.log('Added ICE candidate');
        break;

      case 'error':
        console.error('Signaling error:', message.message);
        this.onError?.(new Error(message.message));
        break;

      default:
        console.warn('Unknown signaling message type:', type);
    }
  }

  /**
   * Send message to signaling server
   */
  sendSignalingMessage(message: SignalingMessage): void {
    if (this.signalingWs && this.signalingWs.readyState === WebSocket.OPEN) {
      this.signalingWs.send(JSON.stringify(message));
    } else {
      console.error('Signaling WebSocket not open');
    }
  }

  /**
   * Stop WebRTC session and cleanup
   */
  stop(): void {
    // Stop all local tracks
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
      this.localStream = null;
    }

    // Close peer connection
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    // Close signaling WebSocket
    if (this.signalingWs) {
      this.signalingWs.close();
      this.signalingWs = null;
    }

    console.log('WebRTC session stopped');
  }

  /**
   * Get local video stream for preview
   */
  getLocalStream(): MediaStream | null {
    return this.localStream;
  }
}

export default WebRTCClient;
