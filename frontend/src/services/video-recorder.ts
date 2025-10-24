/**
 * Video Recorder Service
 * 使用 MediaRecorder API 录制视频片段并上传到服务器
 */

import api from './api';  // 使用配置好的 axios 实例（包含 JWT token）

interface VideoRecorderConfig {
  sessionId: string;
  segmentDuration: number;  // 视频片段时长（毫秒）
  onUploadSuccess?: (response: any) => void;
  onUploadError?: (error: Error) => void;
  onSegmentRecorded?: (segmentIndex: number) => void;
}

class VideoRecorderService {
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private config: VideoRecorderConfig | null = null;
  private isRecording: boolean = false;
  private segmentIndex: number = 0;
  private recordedChunks: Blob[] = [];
  private segmentTimer: number | null = null;

  /**
   * 初始化录制服务
   */
  async initialize(stream: MediaStream, config: VideoRecorderConfig): Promise<void> {
    this.mediaStream = stream;
    this.config = config;
    this.segmentIndex = 0;

    console.log('Video recorder service initialized');
  }

  /**
   * 开始录制
   */
  startRecording(): void {
    if (!this.mediaStream || !this.config) {
      throw new Error('Video recorder not initialized');
    }

    if (this.isRecording) {
      console.warn('Already recording');
      return;
    }

    this.isRecording = true;
    this.segmentIndex = 0;

    // 开始录制第一个片段
    this.startSegment();

    console.log('Video recording started');
  }

  /**
   * 开始录制一个片段
   */
  private startSegment(): void {
    if (!this.mediaStream || !this.config) {
      return;
    }

    // 清空之前的数据
    this.recordedChunks = [];

    try {
      // 创建 MediaRecorder
      // 使用 WebM 格式（浏览器原生支持）
      const options = {
        mimeType: 'video/webm;codecs=vp8,opus',
        videoBitsPerSecond: 2500000  // 2.5 Mbps
      };

      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);

      // 数据可用时收集
      this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      // 录制停止时处理
      this.mediaRecorder.onstop = () => {
        this.handleSegmentComplete();
      };

      // 开始录制
      this.mediaRecorder.start();

      console.log(`Started recording segment ${this.segmentIndex + 1}`);

      // 设置定时器：N 秒后停止当前片段
      this.segmentTimer = window.setTimeout(() => {
        this.stopSegment();
      }, this.config.segmentDuration);

    } catch (error) {
      console.error('Failed to start MediaRecorder:', error);
      throw error;
    }
  }

  /**
   * 停止当前片段的录制
   */
  private stopSegment(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.segmentTimer !== null) {
      clearTimeout(this.segmentTimer);
      this.segmentTimer = null;
    }
  }

  /**
   * 处理片段录制完成
   */
  private async handleSegmentComplete(): Promise<void> {
    if (this.recordedChunks.length === 0) {
      console.warn('No data recorded in this segment');
      return;
    }

    const segmentBlob = new Blob(this.recordedChunks, { type: 'video/webm' });
    const currentSegmentIndex = this.segmentIndex;

    console.log(`Segment ${currentSegmentIndex + 1} complete, size: ${segmentBlob.size} bytes`);

    if (this.config?.onSegmentRecorded) {
      this.config.onSegmentRecorded(currentSegmentIndex);
    }

    // 上传片段
    try {
      await this.uploadSegment(segmentBlob, currentSegmentIndex);
    } catch (error) {
      console.error(`Failed to upload segment ${currentSegmentIndex + 1}:`, error);
      if (this.config?.onUploadError) {
        this.config.onUploadError(error as Error);
      }
    }

    // 如果还在录制，继续录制下一个片段
    if (this.isRecording) {
      this.segmentIndex++;
      this.startSegment();
    }
  }

  /**
   * 上传视频片段到服务器
   */
  private async uploadSegment(blob: Blob, segmentIndex: number): Promise<void> {
    if (!this.config) {
      return;
    }

    const formData = new FormData();
    formData.append('video', blob, `segment_${segmentIndex}.webm`);

    try {
      const response = await api.post(
        `/api/videos/${this.config.sessionId}/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 30000  // 30 秒超时
        }
      );

      console.log(`Segment ${segmentIndex + 1} uploaded successfully:`, response.data);

      if (this.config.onUploadSuccess) {
        this.config.onUploadSuccess(response.data);
      }

    } catch (error) {
      console.error(`Upload failed for segment ${segmentIndex + 1}:`, error);
      throw error;
    }
  }

  /**
   * 停止录制
   */
  stopRecording(): void {
    if (!this.isRecording) {
      return;
    }

    this.isRecording = false;

    // 停止当前片段
    this.stopSegment();

    console.log(`Video recording stopped, total segments: ${this.segmentIndex + 1}`);
  }

  /**
   * 关闭服务
   */
  close(): void {
    this.stopRecording();

    if (this.mediaRecorder) {
      this.mediaRecorder = null;
    }

    // Note: 不要停止 mediaStream，因为它可能还在被 video 元素使用
    // 由调用者负责停止 stream

    console.log('Video recorder service closed');
  }

  /**
   * 获取录制状态
   */
  getRecordingState(): boolean {
    return this.isRecording;
  }

  /**
   * 获取当前片段索引
   */
  getCurrentSegmentIndex(): number {
    return this.segmentIndex;
  }
}

export default VideoRecorderService;
