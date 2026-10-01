import uuid
import requests
from typing import Annotated

from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pytubefix import YouTube
from pytubefix.cli import on_progress
from moviepy import AudioFileClip, VideoFileClip

from mutagen.id3 import ID3, APIC, PictureType
from mutagen.mp3 import MP3


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


async def download_thumbnail(image_url, desired_filename):
    img_data = requests.get(image_url).content
    with open(f"{desired_filename}.png", "wb") as handler:
        handler.write(img_data)
    return f"{desired_filename}.png"  # desired_filename == yt_video_filename


async def get_yt_video(url):
    print("GET YT VIDEO INITIATED")
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)
    ys = yt.streams.get_highest_resolution()
    yt_video_name = ys.title
    yt_filename = str(uuid.uuid4())
    ys.download(filename=str(yt_filename)+".mp4")
    # print("aight")
    thumbnail = await download_thumbnail(yt.thumbnail_url, yt_filename)
    print(f"Thumbnail URL: {thumbnail}")  # desired_filename == yt_video_filename
    yt_video_name = yt_video_name.replace("/", "", -1)
    yt_video_name = yt_video_name.replace("(", "", -1)
    yt_video_name = yt_video_name.replace(")", "", -1)
    yt_video_name = yt_video_name.replace("\"", "", -1)
    return [yt_filename, yt_video_name]



async def get_yt_video_info(url):
    print("GET YT info INITIATED")
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)
    yt_video_info = {"yt_title": yt.title, "yt_desc": yt.description, "yt_author": yt.author,
                     "yt_publish_date": yt.publish_date}
    return yt_video_info


async def get_yt_audio(url):
    yt = YouTube(url, client="WEB", on_progress_callback=on_progress)
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_stream.download()
    print("aight")


def convert_video_to_mp3(mp4, mp3):
    FILETOCONVERT = AudioFileClip(mp4)
    FILETOCONVERT.write_audiofile(mp3)
    FILETOCONVERT.close()


def convert_video_to_mp3_return_file(mp4, mp3):
    try:
        FILETOCONVERT = AudioFileClip(mp4)
        FILETOCONVERT.write_audiofile(mp3)
        FILETOCONVERT.close()
    except AttributeError:
        pass
    return FILETOCONVERT

# gotta update
# @app.get("/video")
# async def download_a_video(link: str):
#     get_yt_video(link)
#     return "123"

# to update
# @app.get("/audio")
# async def download_an_audio(link: str):
#     mp4 = await get_yt_video(link)
#     convert_video_to_mp3(mp4=yt_filename+".mp4", mp3=yt_video_title+".mp3")
#     return "321"


@app.post("/audio_htmx")
async def download_an_audio(request: Request, link: Annotated[str, Form()]):
    print("endpoint initiated")
    mp4 = await get_yt_video(link)
    yt_filename = mp4[0]
    yt_video_title = mp4[1]
    file = convert_video_to_mp3_return_file(mp4=yt_filename+".mp4", mp3=yt_video_title+".mp3")

    audio = ID3(yt_video_title+".mp3")
    with open(f"{yt_filename}.png", "rb") as img:
        img_file = APIC(
            encoding=0,
            mime="image/png",
            type=3,
            desc="Cover",
            data=img.read()
        )
    audio.add(img_file)
    audio.save(yt_video_title+".mp3")

    print(file.filename)
    print(file.filename)
    print(file.filename)
    print(file.filename)
    print(file.filename)
    print(file.filename)

    # return templates.TemplateResponse(request=request, name="download_button.html", context={"file_filename": yt_video_title+".mp3"})
    return templates.TemplateResponse(request=request, name="download_button.html")



@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")





