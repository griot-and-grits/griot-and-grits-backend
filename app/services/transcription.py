import httpx
import io


class Transcription:
    """Transcription Service"""

    def __init__(self, api: str):
        """The API to the Whisper/ASR model

        Args:
            api: the link to the API service
        """
        self.api = api

    async def transcribe(
        self,
        audio_bytes: bytes,
        encode: bool = True,
        task: str = "transcribe",
        language: str = "en",
    ):
        # with open(file, "rb") as f:
        async with httpx.AsyncClient() as client:
            # audio_stream = io.BytesIO(audio_bytes)
            # audio_stream.seek(0)
            file = {
                "audio_file": (
                    "audio.wav",
                    audio_bytes,
                    "audio/wav",
                )
            }
            res = await client.post(
                url=self.api + "/asr",
                params={
                    "encode": str(encode).lower(),
                    "task": task,
                    "language": language,
                    "output": "txt",
                    "initial_prompt": "Transcribe the audio.",
                },
                # headers={"Content-Type": "multipart/form-data"},
                files=file,
                timeout=60,
            )
        res.raise_for_status()
        return res.json()
