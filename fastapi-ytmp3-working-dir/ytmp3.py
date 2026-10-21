import requests
import os
import stat
import time
import shutil
import asyncio
from typing import Annotated

from fastapi import FastAPI, Request, Form, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pytubefix import YouTube
from pytubefix.cli import on_progress
from moviepy import AudioFileClip

from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from pathvalidate import sanitize_filename
from celery import Celery
from celery.result import AsyncResult
import yt_dlp


app = FastAPI()
celery_app = Celery(name="fastapi-ytmp3", broker="redis://redis:6379/0", backend="redis://redis:6379/1")
app.mount("/static", StaticFiles(directory="fastapi-ytmp3-working-dir/static"), name="static")

templates = Jinja2Templates(directory="fastapi-ytmp3-working-dir/templates")


downloads_folder = "fastapi-ytmp3-working-dir/downloads_new/"
if not os.path.exists(downloads_folder):
    os.makedirs(downloads_folder)


def download_thumbnail(image_url, desired_filename):
    img_data = requests.get(image_url).content
    with open(downloads_folder+f"{desired_filename}.png", "wb") as handler:
        handler.write(img_data)
    return f"{desired_filename}.png"


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@celery_app.task
def get_yt_video_audio_ytdlp(url: str):
    print("GET YT VIDEO INITIATED")
    output_dir = downloads_folder

    ydl_options = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # or 'bestvideo+bestaudio'
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        "embed-thumbnail": True,
    }
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=True)
        for key in info:
            print(key)
        mp4_filepath = info["requested_downloads"][0]["filepath"]
        actual_filename = ydl.prepare_filename(info)
        video = MP4(mp4_filepath)
        png_file = f"{mp4_filepath[:-4]}.png"
        with open(png_file, "rb") as img:
            video["covr"] = [
                MP4Cover(img.read(), imageformat=MP4Cover.FORMAT_PNG)
            ]
        video.save(mp4_filepath)

    ydl_options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        "embed-thumbnail": True,
    }
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=True)  # doing it like this so conversion isn't hardcoded
        mp3_filepath = info["requested_downloads"][0]["filepath"]
        # print("mp3 exists", os.path.exists(mp3_filepath))
        audio = ID3(mp3_filepath)
        png_file = f"{mp3_filepath[:-4]}.png"
        with open(png_file, "rb") as img:
            img_file = APIC(encoding=0, mime="image/png", type=3, desc="Cover", data=img.read())
        audio.add(img_file)
        audio.save(mp3_filepath)

    return actual_filename


@celery_app.task
def get_yt_video_info(url):
    ydl_options = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                           'outtmpl': f'{downloads_folder}/%(title)s.%(ext)s',
                           "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=False)
        yt_video_name = os.path.basename(ydl.prepare_filename(info))[:-4]
    thumbnail = download_thumbnail(info["thumbnail"], yt_video_name)
    yt_length = info["duration"]
    yt_description = info["description"]
    yt_channel = info["channel"]
    yt_channel_url = info["channel_url"]
    yt_publish_date = info["upload_date"]
    yt_views = info["view_count"]
    yt_channel_follower_count = info["channel_follower_count"]

    print("'get_yt_video_info' function initiated")

    if yt_length >= 3600:
        yt_hours = yt_length // 3600
        yt_minutes = yt_length // 60 - yt_hours * 60
        yt_seconds = yt_length - yt_hours * 3600 - yt_minutes * 60
        yt_length_divided = f"{yt_hours} hours, {yt_minutes} minutes, {yt_seconds} seconds"
    else:
        yt_minutes = yt_length // 60
        yt_seconds = yt_length- yt_minutes * 60 - 1
        yt_length_divided = f"{yt_minutes} minutes, {yt_seconds} seconds"
    yt_video_info = {"yt_title": yt_video_name, "yt_desc": yt_description, "yt_author": yt_channel,
                     "yt_publish_date": yt_publish_date, "yt_views": yt_views, "yt_length": yt_length_divided,
                     "yt_channel_url": yt_channel_url, "yt_video_url": url,
                     "yt_thumbnail_name": thumbnail, "yt_channel_follower_count": yt_channel_follower_count}
    return yt_video_info


# remove the background_tasks line if you don't want for files to be deleted
@app.get("/grab_a_file")
async def grab_a_file(filename: str, background_tasks: BackgroundTasks, request: Request):
    filepath = f"{downloads_folder}{os.path.basename(filename)}"
    if not os.path.exists(filepath):
        print("'grab_a_file' - file not found")
        return templates.TemplateResponse(request, "message.html", context={"message": "File not found"})
    background_tasks.add_task(delete_file, filename)
    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)


async def delete_file(filepath: str):  # a background task
    print("'delete_file' function initiated")
    await asyncio.sleep(600)

    file_to_delete_mp3 = f"{downloads_folder}{filepath[:-4]}.mp3"
    file_to_delete_mp4 = f"{downloads_folder}{filepath[:-4]}.mp4"
    file_to_delete_png = f"{downloads_folder}{filepath[:-4]}.png"
    if os.path.exists(file_to_delete_mp3):
        os.remove(file_to_delete_mp3)
        print(f"Removed {file_to_delete_mp3}")
    if os.path.exists(file_to_delete_mp4):
        os.chmod(file_to_delete_mp4, stat.S_IWRITE)  # remove the read-only attribute
        os.remove(file_to_delete_mp4)
        print(f"Removed {file_to_delete_mp4}")
    if os.path.exists(file_to_delete_png):
        os.remove(file_to_delete_png)
        print(f"Removed {file_to_delete_png}")


@app.post("/initiate_download")
async def initiate_download(request: Request, link: Annotated[str, Query()]):
    print("'initiate_download' function initiated")
    mp4_file_task = get_yt_video_audio_ytdlp.delay(url=link)
    return templates.TemplateResponse(request=request, name="htmx_pending.html",
                                      context={"task_id": mp4_file_task.id, "task_type": "yt_download"})


@app.get("/task_id_yt_download/{task_id}")
def task_id_yt_download(request:Request, task_id: str):
    mp4_file_task = AsyncResult(task_id, app=celery_app)
    if mp4_file_task.status == "SUCCESS":
        actual_filename = mp4_file_task.get()
        yt_title = os.path.basename(actual_filename)[:-4]
        yt_title = sanitize_filename(yt_title)
        return templates.TemplateResponse(request=request, name="download_button.html", context={"file_filename": yt_title})
    return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": mp4_file_task.id, "task_type": "yt_download"})


@app.post("/yt_video_fetch")
async def yt_video_fetch(request: Request, link: Annotated[str, Form()]):
    # print("fetching a video, HTMX")
    print("'yt_video' function initiated(/yt_video_fetch)")
    yt_info = get_yt_video_info.delay(url=link)
    return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": yt_info.id, "task_type": "yt_info"})


@app.get("/task_id_yt_info/{task_id}")
def task_id_yt_info(request:Request, task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    if task.status == "SUCCESS":
        yt_info = task.get()
        return templates.TemplateResponse(request=request, name="yt_video_data.html", context={"yt_info": yt_info})

    else:
        return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": task.id, "task_type": "yt_info"})


@app.get("/get_vid_info")
async def get_yt_video_info_swagger(url: str):
    yt_info = get_yt_video_info.delay(url)
    time.sleep(5)
    return yt_info.get()


# get_yt_video_info.delay(url="https://www.youtube.com/watch?v=_oyCroWsQkg")
