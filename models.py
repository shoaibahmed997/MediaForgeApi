from pydantic import BaseModel,Field, field_validator, ConfigDict,HttpUrl
from typing import Literal,Optional
from core.url import normalise_url

class RequestModel(BaseModel):
    """
    """
    model_config = ConfigDict(extra="forbid")

    url:str
    audioBitrate: Literal["320", "256", "128", "96", "64", "8"] = "128"
    audioFormat: Literal["best", "mp3", "ogg", "wav", "opus"] = "mp3"
    downloadMode: Literal["auto", "audio", "mute"] = "auto"
    filenameStyle: Literal["classic", "pretty", "basic", "nerdy"] = "basic"
    youtubeVideoCodec: Literal["h264", "av1", "vp9"] = "h264"
    youtubeVideoContainer: Literal["auto", "mp4", "webm", "mkv"] = "auto"
    videoQuality: Literal["max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"] = "1080"
    localProcessing: Literal["disabled", "preferred", "forced"] = "disabled"

    youtubeDubLang:Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=8,
        pattern=r"^[0-9a-zA-Z\-]+$",
        description="Language code for YouTube dubbing (e.g., 'en', 'pt-BR')"
    )

    subtitleLang: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=8,
        pattern=r"^[0-9a-zA-Z\-]+$",
        description="Language code for subtitles"
    )
    disableMetadata: bool = False
    allowH265: bool = False
    convertGif: bool = True
    tiktokFullAudio: bool = False
    alwaysProxy: bool = False
    youtubeHLS: bool = False
    youtubeBetterAudio: bool = False

    
    @field_validator("url",mode="before")
    @classmethod
    def normalise_url_field(cls,value:str) -> str:
        """
        Runs before type validation
        Purpose: 
        1. strips the url of whitespaces
        2. checks for aliases and transform the url 
        3. strips away tracking and non essential query params
        """
        try:
            return normalise_url(value.strip())
        except Exception as e:
            print('error:',e)
            raise ValueError(f"invalid url: {e}")


