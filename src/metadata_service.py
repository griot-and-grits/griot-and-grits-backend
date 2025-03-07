from .models.metadata import (
    Artifact,
    VideoMetadata,
    AudioMetadata,
    TypeMetadata,
    Duration,
)
import ffmpeg
import os


class MetadataService:
    VIDEO_TYPES = ["mp4"]
    AUDIO_TYPES = ["mp3"]
    TXT_TYPES = ["pdf", "txt", "rtf"]

    def __init__(self):
        pass

    def __validate_file(self, file: str):
        """Validates a file

        Args:
            file: file or path to the file.
        """
        if not os.path.exists(file):
            raise MetadataServiceError(
                "Could not find file. Please ensure path is correct."
            )

    def extract(self, file: str) -> Artifact:
        """Extracts a file to its corresponding Metadata object.

        Args: a file or path to a file.
        """
        file_type = file.split(".")[-1].lower()
        self.__validate_file(file)

        if file_type in self.VIDEO_TYPES:
            vm = self._video_to_metadata(file, file_type)
            return vm

    def _video_to_metadata(self, file: str, file_type: str) -> VideoMetadata:
        """
        Convert video probe to proper metadata

        Args:
            file: the video file
        """
        data = ffmpeg.probe(file)
        video_meta: dict = next(
            (stream for stream in data["streams"] if stream["codec_type"] == "video"),
            None,
        )
        if not video_meta:
            raise MetadataServiceError("Could not evaluate the file as a video.")
        fps = round(float(eval(video_meta.get("r_frame_rate", "0/1"))), 2)
        secs = round(float(video_meta.get("duration")), 0)
        width = video_meta.get("width")
        height = video_meta.get("height")
        codec = video_meta.get("codec_name")
        # get size in mb
        size_in_mb = round((os.path.getsize(file) / (1024 * 1024)), 2)
        duration = Duration(seconds=secs)

        return VideoMetadata(
            duration=duration,
            resolution_width=width,
            resolution_height=height,
            codec=codec,
            format=file_type,
            frame_rate=fps,
            file_size_mb=size_in_mb,
        )


class MetadataServiceError(Exception):
    """Exception related to MetadataService"""
