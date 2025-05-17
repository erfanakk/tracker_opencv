import gdown

videos = [
    {
        "output": "0bfacc_0.mp4",
        "id": "12TqauVZ9tLAv8kWxTTBFWtgt2hNQ4_ZF"
    },
    {
        "output": "2e57b9_0.mp4",
        "id": "19PGw55V8aA6GZu5-Aac5_9mCy3fNxmEf"
    },
    {
        "output": "08fd33_0.mp4",
        "id": "1OG8K6wqUw9t7lp9ms1M48DxRhwTYciK-"
    },
    {
        "output": "573e61_0.mp4",
        "id": "1yYPKuXbHsCxqjA9G-S6aeR2Kcnos8RPU"
    },
    {
        "output": "121364_0.mp4",
        "id": "1vVwjW1dE1drIdd4ZSILfbCGPD4weoNiu"
    }
]

def download_videos():
    for video in videos:
        print(f"Downloading {video['output']}...")
        url = f"https://drive.google.com/uc?id={video['id']}"
        gdown.download(url, video['output'], quiet=False)
        print(f"Finished downloading {video['output']}")

if __name__ == "__main__":
    download_videos()
