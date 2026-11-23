# Python FastAPI YTMP(YTMP3) 
## A fully working dockerized app for downloading .mp3 and .mp4 files in the highest quality from YouTube.

as this project uses ~~[pytubefix]([pytubefix](https://github.com/JuanBindez/pytubefix/))~~ [yt_dlp]([yt_dlp](https://github.com/yt-dlp/yt-dlp/)), 
if you're running it without Docker you'll have to insall node.js or deno for automatic PoToken generation
You don't need to manually install those if you are using Docker.

also you'd need to install ffmpeg for the app to work correctly.


to stop files from being deleted, you should remove the line 152 from the `grab_a_file` 
function(`background_tasks.add_task(delete_file, filename)`), line 76 in the picture below:

![img.png](img.png)

and remove the line 27(`shutil.rmtree(downloads_folder)`) of the `ytmp3.py` file.

The folder all the files are temporarily downloaded into can be modified at the beginning of the
`fastapi-ytmp3-working-dir/ytmp3.py` file (`downloads_folder` variable).

You can change the amount of time after which files are deleted in the `delete_file` function, the `await asyncio.sleep(600)` line. 
They will however still be deleted after the app shuts down unless you remove the line 27 of the `ytmp3.py` file. 

