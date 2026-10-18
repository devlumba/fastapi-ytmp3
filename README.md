as this project uses ~~[pytubefix]([pytubefix](https://github.com/JuanBindez/pytubefix))~~ [yt_dlp]([yt_dlp](https://github.com/yt-dlp/yt-dlp)), 
i'm pretty sure it needs node.js for that automatic PoToken generation, so you'll have to install it on your PC. 
Or use the Docker version, since it does install it automatically. 



to stop files from being deleted, you gotta manually change `grab_a_file` function(line 76):

![img.png](img.png)
