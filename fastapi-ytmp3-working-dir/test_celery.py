from unittest import mock
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from pytest import raises
from celery.exceptions import Retry

from ytmp3 import celery_app, app, get_yt_video_info


def test_celery_fetch_video_task(celery_eager):  # eager test. checks whether celery actually runs the tasks
    fake_info_raw = {
                  "description": "123",
                  "upload_date": "20220401",
                  "view_count": 1530137,
                  "duration": 2641,
                  "channel": "moon",
                  "channel_url": "https://www.youtube.com/channel/UC",
                  "thumbnail": "123.png",
                  "channel_follower_count": 2780
                }
    fake_info_processed = {"yt_title": "smoville",
                  "yt_desc": "123",
                  "yt_publish_date": "20220401",
                  "yt_views": 1530137,
                  "yt_length": "44 minutes, 0 seconds",
                  "yt_author": "moon",
                  "yt_channel_url": "https://www.youtube.com/channel/UC",
                  "yt_video_url": "https://www.youtube.com/watch?v=L",
                  "yt_thumbnail_name": "123.png",
                  "yt_channel_follower_count": 2780
                }
    with patch("ytmp3.yt_dlp.YoutubeDL") as mock_ydl_class, patch("ytmp3.download_thumbnail") as mock_download_thumbnail:
        mock_instance = mock_ydl_class.return_value.__enter__.return_value  # mocking with yt_dlp.YoutubeDL as ydl
        mock_instance.extract_info.return_value = fake_info_raw
        mock_instance.prepare_filename.return_value = "smoville.mp4"
        mock_download_thumbnail.return_value = fake_info_raw["thumbnail"]

        from ytmp3 import get_yt_video_info
        result = get_yt_video_info("https://www.youtube.com/watch?v=L")
        print(result)
        print(fake_info_processed)


        assert result == fake_info_processed


