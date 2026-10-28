from fastapi.testclient import TestClient

from ytmp3 import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200


# def test_send_url():
#     response = client.post("/yt_video_fetch", data={"link": "https://www.youtube.com/watch?v=kS0hpMVQn0k&list=RDMMmTbxOkv-z7w&index=27"})
#     print(response.json())
#     assert response.status_code == 200

