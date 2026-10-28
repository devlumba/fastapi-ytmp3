from unittest import mock
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from pytest import raises
from celery.exceptions import Retry

from ytmp3 import celery_app, app, get_yt_video_info

# def test_yt_info_fetch():
#     from ytmp3 import get_yt_video_info
#     result = get_yt_video_info.delay(url="https://www.youtube.com/watch?v=mTbxOkv-z7w&list=RDMM&index=2")
#     assert type(result.get(timeout=10)) == dict


def test_endpoint_queues_the_video_fetch_task(client):
    with patch("ytmp3.get_yt_video_info.delay") as mock_delay:
        mock_delay.return_value.id = "fake-task-id-233"

        response = client.post("/yt_video_fetch", data={"link": "https://www.youtube.com/watch?v=kS0hpMVQn0k&list=RDMMmTbxOkv-z7w&index=28"})

        mock_delay.assert_called_once_with(url="https://www.youtube.com/watch?v=kS0hpMVQn0k&list=RDMMmTbxOkv-z7w&index=28")

        print(response.text)

        assert "fake-task-id-233" in response.text


def test_endpoint_queues_the_video_download_task(client):
    with patch("ytmp3.get_yt_video_audio_ytdlp.delay") as mock_delay:
        mock_delay.return_value.id = "fake-task-id-122"

        response = client.post("/initiate_download", params={"link": "https://www.youtube.com/watch?v=kS0hpMVQn0k&list=RDMMmTbxOkv-z7w&index=28"})

        print(response.text)

        mock_delay.assert_called_once_with(url="https://www.youtube.com/watch?v=kS0hpMVQn0k&list=RDMMmTbxOkv-z7w&index=28")

        assert "fake-task-id-122" in response.text



def test_celery_fetch_video_task(celery_eager):
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


