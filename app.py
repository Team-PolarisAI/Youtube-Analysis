from apiclient.discovery import build
import json
import os
import pandas as pd
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

DEVELOPER_KEY = os.environ['KEY']
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, 
                YOUTUBE_API_VERSION, 
                developerKey = DEVELOPER_KEY)

def video_search(youtube, q = 'アンパンマン', max_results = 50):
  response = youtube.search().list(
    q = q,
    part = "id, snippet",
    order = 'viewCount',
    type = 'video',
    maxResults =  max_results
  ).execute()

  items = response['items']
  items_id = []
  for item in items:
    item_id = {}
    item_id['video_id'] = item['id']['videoId']
    item_id['channel_id'] = item['snippet']['channelId']
    items_id.append(item_id)

  df_videos = pd.DataFrame(items_id)

  return df_videos

def get_results(df_video, threshold=5000):
    channel_ids = df_video['channel_id'].unique().tolist()

    subscriber_list = youtube.channels().list(
    id = ','.join(channel_ids),
    part = "statistics",
    fields = 'items(id, statistics(subscriberCount))'
    ).execute()

    subscribers = []

    for item in subscriber_list['items']:
      subscriber = {}
      if len(item['statistics']) > 0:
        subscriber['channel_id'] = item['id']
        subscriber['subscriber_count'] = int(item['statistics']['subscriberCount'])
      else:
        subscriber['channel_id'] = item['id']
      subscribers.append(subscriber)

    df_subscribers = pd.DataFrame(subscribers)

    df = pd.merge(left=df_video, right=df_subscribers, on = 'channel_id')
    df_extracted = df[df['subscriber_count'] < 1000000]

    video_ids = df_extracted['video_id'].tolist()
    videos_list = youtube.videos().list(
    id = ','.join(video_ids),
    part = "snippet, statistics",
    fields = 'items(id, snippet(title), statistics(viewCount))'
    ).execute()

    items = videos_list['items']
    videos_info = []
    for item in items:
      video_info = {}
      video_info['video_id'] = item['id']
      video_info['title'] = item['snippet']['title']
      video_info['view_count'] = item['statistics']['viewCount']
      videos_info.append(video_info)

    df_videos_info = pd.DataFrame(videos_info)

    if 'video_id' in df_videos_info and 'video_id' in df_extracted:
        res = pd.merge(left=df_extracted, right = df_videos_info, on = 'video_id')
        res = res.loc[:,['video_id', 'title', 'view_count', 'subscriber_count', 'channel_id']]
    else:
        res = 0
    return res

st.title('Youtubeの分析アプリ')

st.sidebar.write('## クエリと閾値の設定')
st.sidebar.write('## クエリの入力')
query = st.sidebar.text_input('検索クエリを入力してください', 'ヒカキン')

st.sidebar.write('### 閾値の設定')
threshold = st.sidebar.slider('登録者数の閾値', 100, 1000000, 500000)

st.sidebar.write('### 取得する動画数')
maxresults = st.sidebar.slider('取得する動画の数', 1, 50, 10)

st.write('### 選択中のパラメータ')
st.markdown(
f"""
- 検索クエリ: {query}
- 登録者数の閾値: {threshold}
- 取得する動画: {maxresults} 
""")

df_video = video_search(youtube, q = query, max_results = maxresults)
res = get_results(df_video, threshold = threshold)

st.write('### 分析結果')
if type(res) == int:
   st.write('該当する結果は有りません。クエリまたは閾値を変えてください')
else:
   st.write(res)

st.write('### 動画再生')
video_id = st.text_input('動画IDを入力してください')
url = f'https://youtu.be/{video_id}'

video_field = st.empty()
video_field.write('こちらに動画が表示されます')

if st.button('ビデオ表示'):
   if len(video_id) > 0:
    try:
        video_field.video(url)
    except:
       st.error('エラーが起きました')