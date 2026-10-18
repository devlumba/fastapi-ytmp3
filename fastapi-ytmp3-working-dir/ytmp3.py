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
from pathvalidate import sanitize_filename
from celery import Celery
from celery.result import AsyncResult
import yt_dlp


app = FastAPI()
celery_app = Celery(name="fastapi-ytmp3", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")
app.mount("/static", StaticFiles(directory="fastapi-ytmp3-working-dir/static"), name="static")

templates = Jinja2Templates(directory="fastapi-ytmp3-working-dir/templates")


downloads_folder = "fastapi-ytmp3-working-dir/downloads_new/"
if not os.path.exists(downloads_folder):
    os.makedirs(downloads_folder)


def download_thumbnail(image_url, desired_filename):
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


@celery_app.task
def get_yt_video_ytdlp(url: str):
    print("GET YT VIDEO INITIATED")
    output_dir = downloads_folder
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # or 'bestvideo+bestaudio'
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info = ydl.extract_info(url, download=False)
        filename_old = ydl.prepare_filename(info)[:-4]
        filename = os.path.basename(filename_old)

        print("filename", filename_old)
        print("filename exists", os.path.exists(filename_old))
        filepath = f"{downloads_folder}{os.path.basename(filename)}"
        os.chmod(filepath+".mp4", stat.S_IREAD)  # making the mp4 read only so moviepy doesn't remove the thumbnail
    return filename


@celery_app.task
def get_yt_video_info(url):
    print("GET YT info INITIATED")
    yt = YouTube(url, client="MWEB", on_progress_callback=on_progress)

    yt_video_name = sanitize_filename(yt.title)
    thumbnail = download_thumbnail(yt.thumbnail_url, yt_video_name)

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


async def delete_file(filepath: str):
    print("delete file initiated")
    print(filepath)
    await asyncio.sleep(600)
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


@celery_app.task
def convert_video_to_mp3_return_file(mp4, mp3):
    print('conversion started')
    with AudioFileClip(downloads_folder+mp4) as clip:
        clip.write_audiofile(downloads_folder + mp3)
        clip.close()

        yt_video_title = mp3[:-4]

        audio = ID3(downloads_folder + yt_video_title + ".mp3")
        png_file = f"{downloads_folder}{yt_video_title}.png"
        print("png file is ", png_file)
        print(os.path.exists(png_file))
        with open(png_file, "rb") as img:
            img_file = APIC(
                encoding=0,
                mime="image/png",
                type=3,
                desc="Cover",
                data=img.read()
            )
        audio.add(img_file)
        audio.save(downloads_folder + yt_video_title + ".mp3")
    # return file_to_convert
    return "finished converting"


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/initiate_download")
async def initiate_download(request: Request, link: Annotated[str, Query()]):
    print("`initiate download` initiated")
    mp4_file_task = get_yt_video_ytdlp.delay(url=link)
    return templates.TemplateResponse(request=request, name="htmx_pending.html",
                                      context={"task_id": mp4_file_task.id, "task_type": "yt_download"})


@app.get("/task_id_yt_download/{task_id}")
def task_id_yt_download(request:Request, task_id: str):
    task = AsyncResult(task_id, app=celery_app)

    if task.status == "SUCCESS":
        yt_title = task.get()
        if os.path.exists(downloads_folder + yt_title + ".mp3"):
            return templates.TemplateResponse(request=request, name="download_button.html", context={"file_filename": yt_title})
        else:
            conversion_task = convert_video_to_mp3_return_file.delay(mp4=yt_title+".mp4", mp3=yt_title+".mp3")

    return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": task.id, "task_type": "yt_download"})


@app.post("/audio_htmx")
async def download_an_audio(request: Request, link: Annotated[str, Query()]):
    print("endpoint initiated")
    # mp4 = await get_yt_video(link)
    mp4 = get_yt_video_ytdlp(url=link)
    yt_filename = mp4
    yt_video_title = mp4
    print("video title is ", yt_video_title)
    print("video title is ", yt_video_title)
    print("video title is ", yt_video_title)
    file = convert_video_to_mp3_return_file(mp4=yt_filename+".mp4", mp3=yt_video_title+".mp3")
    print("file is ", file)
    print("file is ", file)
    print("file is ", file)
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
    yt_info = get_yt_video_info.delay(url=link)
    print("task delayed")
    # return templates.TemplateResponse(request=request, name="yt_video_data.html", context={"yt_info": yt_info})
    return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": yt_info.id, "task_type": "yt_info"})


@app.get("/task_id_yt_info/{task_id}")
def task_id_yt_info(request:Request, task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    if task.status == "SUCCESS":
        yt_info = task.get()
        print(type(yt_info))
        return templates.TemplateResponse(request=request, name="yt_video_data.html", context={"yt_info": yt_info})

    else:
        return templates.TemplateResponse(request=request, name="htmx_pending.html", context={"task_id": task.id, "task_type": "yt_info"})


@app.get("/get_vid_info")
async def get_yt_video_info_swagger(url: str):
    yt_info = await get_yt_video_info(url)
    return yt_info


# get_yt_video_info.delay(url="https://www.youtube.com/watch?v=_oyCroWsQkg")
