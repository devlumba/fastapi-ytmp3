from unittest import mock
from unittest.mock import patch

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

