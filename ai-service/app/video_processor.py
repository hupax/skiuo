"""
Video Processor - 使用 FFmpeg 滑动窗口切片视频
"""
import subprocess
import os
import logging
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VideoWindow:
    """视频窗口信息"""
    window_index: int
    start_time: float
    end_time: float
    file_path: str
    duration: float


class VideoProcessor:
    """
    视频处理器
    使用滑动窗口策略切片视频
    """

    def __init__(
        self,
        window_size: float = 15.0,  # 窗口大小（秒）
        step_size: float = 10.0,    # 步长（秒）
        output_dir: str = "./temp_windows"
    ):
        """
        初始化视频处理器

        Args:
            window_size: 窗口大小（秒），默认 15 秒
            step_size: 步长（秒），默认 10 秒（与前一窗口重叠 5 秒）
            output_dir: 窗口视频输出目录
        """
        self.window_size = window_size
        self.step_size = step_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            视频时长（秒）
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            logger.info(f"Video duration: {duration:.2f} seconds")
            return duration
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get video duration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            raise

    def slice_video_with_sliding_window(
        self,
        video_path: str,
        session_id: str
    ) -> List[VideoWindow]:
        """
        使用滑动窗口切片视频

        策略：
        - 窗口大小：15 秒
        - 步长：10 秒
        - 重叠：5 秒

        例如，30 秒视频：
        - window_1: 0-15秒
        - window_2: 10-25秒
        - window_3: 20-30秒

        Args:
            video_path: 原始视频文件路径
            session_id: 会话 ID

        Returns:
            窗口列表
        """
        # 获取视频时长
        duration = self.get_video_duration(video_path)

        # 创建会话专用目录
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        windows: List[VideoWindow] = []
        window_index = 0
        current_time = 0.0

        while current_time < duration:
            # 计算窗口结束时间
            end_time = min(current_time + self.window_size, duration)
            window_duration = end_time - current_time

            # 如果剩余时间太短（<5秒），合并到上一个窗口
            if window_duration < 5.0 and window_index > 0:
                logger.info(f"Remaining duration {window_duration:.2f}s too short, skipping")
                break

            # 生成窗口文件路径（使用 MP4 格式，Qwen API 推荐）
            window_filename = f"window_{window_index:03d}_{int(current_time)}_{int(end_time)}.mp4"
            window_path = session_dir / window_filename

            # 使用 FFmpeg 切片
            try:
                self._extract_window(
                    video_path=video_path,
                    start_time=current_time,
                    duration=window_duration,
                    output_path=str(window_path)
                )

                windows.append(VideoWindow(
                    window_index=window_index,
                    start_time=current_time,
                    end_time=end_time,
                    file_path=str(window_path),
                    duration=window_duration
                ))

                logger.info(
                    f"Created window {window_index}: "
                    f"{current_time:.2f}s - {end_time:.2f}s "
                    f"({window_duration:.2f}s)"
                )

            except Exception as e:
                logger.error(f"Failed to create window {window_index}: {e}")
                raise

            # 移动到下一个窗口
            window_index += 1
            current_time += self.step_size

        logger.info(f"Created {len(windows)} windows for video (duration: {duration:.2f}s)")
        return windows

    def _extract_window(
        self,
        video_path: str,
        start_time: float,
        duration: float,
        output_path: str
    ):
        """
        使用 FFmpeg 提取视频窗口

        Args:
            video_path: 原始视频路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
            output_path: 输出文件路径
        """
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264',      # 视频：使用 H.264 编码器
            '-preset', 'fast',      # 编码速度：fast（平衡速度和质量）
            '-crf', '23',           # 质量：23（默认值，0=无损，51=最差）
            '-an',                  # 跳过音频（前端录制时禁用了音频）
            '-movflags', '+faststart',  # 优化 MP4 用于流式播放
            '-y',                   # 覆盖已存在的文件
            output_path
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=60  # 超时保护
            )
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout for window extraction")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode('utf-8')}")
            raise

    def cleanup_windows(self, session_id: str):
        """
        清理会话的所有窗口文件

        Args:
            session_id: 会话 ID
        """
        session_dir = self.output_dir / session_id
        if session_dir.exists():
            try:
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up windows for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup windows for session {session_id}: {e}")

    def get_window_info(self, video_path: str, session_id: str) -> List[Tuple[int, float, float]]:
        """
        获取视频的窗口信息（不实际切片）

        返回格式：[(window_index, start_time, end_time), ...]
        """
        duration = self.get_video_duration(video_path)

        windows_info = []
        window_index = 0
        current_time = 0.0

        while current_time < duration:
            end_time = min(current_time + self.window_size, duration)
            window_duration = end_time - current_time

            if window_duration < 5.0 and window_index > 0:
                break

            windows_info.append((window_index, current_time, end_time))
            window_index += 1
            current_time += self.step_size

        return windows_info
