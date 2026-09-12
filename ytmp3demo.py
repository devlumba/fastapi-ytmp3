from fastapi import FastAPI
from pytubefix import YouTube
from pytubefix.cli import on_progress
from moviepy import AudioFileClip, VideoFileClip


app = FastAPI()


async def get_yt_video(url):
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)
    ys = yt.streams.get_highest_resolution()
    yt_video_name = ys.title
    ys.download(filename=yt_video_name+".mp4")
    # print("aight")
    return yt_video_name



async def get_yt_audio(url):
    yt = YouTube(url, client="WEB", on_progress_callback=on_progress)
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_stream.download()
    print("aight")


def convert_video_to_mp3(mp4, mp3):
    FILETOCONVERT = AudioFileClip(mp4)
    FILETOCONVERT.write_audiofile(mp3)
    FILETOCONVERT.close()



@app.get("/video")
async def download_a_video(link: str):
    get_yt_video(link)
    return "123"


@app.get("/audio")
async def download_an_audio(link: str):
    mp4 = await get_yt_video(link)
    convert_video_to_mp3(mp4=mp4+".mp4", mp3=mp4+".mp3")
    return "321"


@app.get("/")
async def index():
    return "123"

