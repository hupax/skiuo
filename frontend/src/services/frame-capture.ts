/**
 * Frame Capture Service
 * 使用 Canvas 从视频流中截取帧并发送到服务器
 */

const SIGNALING_URL = import.meta.env.VITE_SIGNALING_WS_URL || 'ws://localhost:3000';

class FrameCaptureService {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private ws: WebSocket | null = null;
  private intervalId: number | null = null;
  private sessionId: string | null = null;
  private isCapturing: boolean = false;
  private frameCount: number = 0;

  /**
   * 初始化服务
   */
  async initialize(stream: MediaStream, sessionId: string): Promise<void> {
    this.sessionId = sessionId;

    // 创建隐藏的 video 元素用于渲染流
    this.videoElement = document.createElement('video');
    this.videoElement.srcObject = stream;
    this.videoElement.muted = true;
    this.videoElement.playsInline = true;

    await this.videoElement.play();

    // 创建 canvas
    this.canvas = document.createElement('canvas');
    this.canvas.width = 1280;
    this.canvas.height = 720;
    this.ctx = this.canvas.getContext('2d');

    console.log('Frame capture service initialized');
  }

  /**
   * 连接到服务器WebSocket
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // 使用专门的帧传输WebSocket
      const wsUrl = `${SIGNALING_URL}/frames/${this.sessionId}`;
      console.log('Connecting to frames WebSocket:', wsUrl);

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Frames WebSocket connected');
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error('Frames WebSocket error:', error);
        reject(new Error('无法连接到帧传输服务器'));
      };

      this.ws.onclose = () => {
        console.log('Frames WebSocket closed');
      };

      setTimeout(() => {
        if (this.ws!.readyState !== WebSocket.OPEN) {
          reject(new Error('连接超时'));
        }
      }, 5000);
    });
  }

  /**
   * 开始捕获帧
   * @param fps - 每秒截取的帧数，默认1帧/秒
   */
  startCapture(fps: number = 1): void {
    if (this.isCapturing) {
      console.warn('Already capturing frames');
      return;
    }

    this.isCapturing = true;
    this.frameCount = 0;

    const interval = 1000 / fps;

    this.intervalId = window.setInterval(() => {
      this.captureAndSendFrame();
    }, interval);

    console.log(`Started capturing frames at ${fps} fps`);
  }

  /**
   * 截取一帧并发送
   */
  private captureAndSendFrame(): void {
    if (!this.ctx || !this.canvas || !this.videoElement || !this.ws) {
      return;
    }

    try {
      // 绘制当前视频帧到 canvas
      this.ctx.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);

      // 转换为 JPEG Base64
      this.canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Failed to create blob from canvas');
          return;
        }

        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1]; // 去掉 data:image/jpeg;base64, 前缀

          // 发送到服务器
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(base64);
            this.frameCount++;
            console.log(`Sent frame ${this.frameCount}`);
          }
        };
        reader.readAsDataURL(blob);
      }, 'image/jpeg', 0.8); // JPEG 质量 80%

    } catch (error) {
      console.error('Error capturing frame:', error);
    }
  }

  /**
   * 停止捕获
   */
  stopCapture(): void {
    if (!this.isCapturing) {
      return;
    }

    this.isCapturing = false;

    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    console.log(`Stopped capturing frames. Total: ${this.frameCount}`);
  }

  /**
   * 关闭服务
   */
  close(): void {
    this.stopCapture();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.videoElement) {
      this.videoElement.pause();
      this.videoElement.srcObject = null;
      this.videoElement = null;
    }

    this.canvas = null;
    this.ctx = null;

    console.log('Frame capture service closed');
  }
}

export default FrameCaptureService;
