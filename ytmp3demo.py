import requests
import os
import time
from typing import Annotated

from fastapi import FastAPI, Request, Form, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pytubefix import YouTube
from pytubefix.cli import on_progress
from moviepy import AudioFileClip

from mutagen.id3 import ID3, APIC
from pathvalidate import sanitize_filename


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


downloads_folder = "downloads_new/"
if not os.path.exists(downloads_folder):
    os.makedirs(downloads_folder)


async def download_thumbnail(image_url, desired_filename):
    img_data = requests.get(image_url).content
    with open(downloads_folder+f"{desired_filename}.png", "wb") as handler:
        handler.write(img_data)
    return f"{desired_filename}.png"  # desired_filename == yt_video_filename


async def get_yt_video(url):
    print("GET YT VIDEO INITIATED")
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)
    ys = yt.streams.get_highest_resolution()
    yt_video_name = sanitize_filename(ys.title)

    yt_filename = yt_video_name
    ys.download(filename=yt_filename+".mp4", output_path=downloads_folder)
    # print("aight")
    return [yt_filename, yt_video_name]


async def get_yt_video_info(url):
    print("GET YT info INITIATED")
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)

    yt_video_name = sanitize_filename(yt.title)
    thumbnail = await download_thumbnail(yt.thumbnail_url, yt_video_name)

    yt_length = yt.length
    yt_length_divided = ""
    if yt_length >= 3600:
        yt_hours = yt_length // 3600
        yt_minutes = yt_length // 60 - yt_hours * 60
        yt_seconds = yt_length - yt_hours * 3600 - yt_minutes * 60
        yt_length_divided = f"{yt_hours} hours, {yt_minutes} minutes, {yt_seconds} seconds"
    else:
        yt_minutes = yt_length // 60
        yt_seconds = yt_length- yt_minutes * 60 - 1
        yt_length_divided = f"{yt_minutes} minutes, {yt_seconds} seconds"
    yt_video_info = {"yt_title": yt.title, "yt_desc": yt.description, "yt_author": yt.author,
                     "yt_publish_date": yt.publish_date, "yt_views": yt.views, "yt_length": yt_length_divided,
                     "yt_channel_url": yt.channel_url, "yt_video_url": url,
                     "yt_thumbnail_name": thumbnail}
    return yt_video_info


# remove the background_tasks line if you don't want for files to be deleted
@app.get("/grab_a_file")
async def grab_a_file(filename: str, background_tasks: BackgroundTasks):
    print("grab_a_file 1", filename)
    filepath = f"{downloads_folder}{os.path.basename(filename)}"
    if not os.path.exists(filepath):
        return "no file found"
    print("grab_a_file 2", filename)
    background_tasks.add_task(delete_file, filename)
    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)


def delete_file(filepath: str):
    print("delete file initiated")
    print(filepath)
    time.sleep(30)
    print("delete sleep over")

    file_to_delete_mp3 = f"{downloads_folder}{filepath[:-4]}.mp3"
    file_to_delete_mp4 = f"{downloads_folder}{filepath[:-4]}.mp4"
    file_to_delete_png = f"{downloads_folder}{filepath[:-4]}.png"
    if os.path.exists(file_to_delete_mp3):
        os.remove(file_to_delete_mp3)
        print(f"Removed {file_to_delete_mp3}")
    if os.path.exists(file_to_delete_mp4):
        os.remove(file_to_delete_mp4)
        print(f"Removed {file_to_delete_mp4}")
    if os.path.exists(file_to_delete_png):
        os.remove(file_to_delete_png)
        print(f"Removed {file_to_delete_png}")


def convert_video_to_mp3_return_file(mp4, mp3):
    try:
        file_to_convert = AudioFileClip(downloads_folder + mp4)
        file_to_convert.write_audiofile(downloads_folder + mp3)
        file_to_convert.close()
    except AttributeError:
        pass
    return file_to_convert


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/audio_htmx")
async def download_an_audio(request: Request, link: Annotated[str, Query()]):
    print("endpoint initiated")
    mp4 = await get_yt_video(link)
    yt_filename = mp4[0]
    yt_video_title = mp4[1]
    file = convert_video_to_mp3_return_file(mp4=yt_filename+".mp4", mp3=yt_video_title+".mp3")

    audio = ID3(downloads_folder + yt_video_title+".mp3")
    with open(f"{downloads_folder}{yt_filename}.png", "rb") as img:
        img_file = APIC(
            encoding=0,
            mime="image/png",
            type=3,
            desc="Cover",
            data=img.read()
        )
    audio.add(img_file)
    audio.save(downloads_folder + yt_video_title+".mp3")

    print("download_an_audio", file.filename)

    return templates.TemplateResponse(request=request, name="download_button.html", context={"file_filename": yt_video_title})


@app.post("/yt_video_fetch")
async def yt_video(request: Request, link: Annotated[str, Form()]):
    print("fetching a video, HTMX")
    yt_info = await get_yt_video_info(url=link)
    return templates.TemplateResponse(request=request, name="yt_video_data.html", context={"yt_info": yt_info})


@app.get("/get_vid_info")
async def get_yt_video_info_swagger(url: str):
    yt_info = await get_yt_video_info(url)
    return yt_info

