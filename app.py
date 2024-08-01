from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import os
import openai
import time
import traceback

from thingspeak import Thingspeak  # 確認 thingspeak.py 和 app.py 在同一目錄下

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

auth_user_list = ["USER_ID1", "USER_ID2"]  # 允許使用圖表功能的用戶ID列表
auth_user_ai_list = ["USER_ID1", "USER_ID2"]  # 允許使用AI功能的用戶ID列表

def GPT_response(text):
    response = openai.Completion.create(model="gpt-3.5-turbo-instruct", prompt=text, temperature=0.5, max_tokens=500)
    print(response)
    answer = response['choices'][0]['text'].replace('。 ', '')
    return answer

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_request_user_id = event.source.user_id
    print('get_request_user_id', get_request_user_id)
    input_msg = event.message.text
    check = input_msg[:3].lower()
    user_msg = input_msg[3:]  # 2374700,2KNDBSF9FN4M5EY1
    print('check', check)
    print('user_msg', user_msg)
    if get_request_user_id in auth_user_list:
        if check == "圖表:":
            channel_id, key = user_msg.split(',')
            print("User channel_id: ", channel_id, "Read_key: ", key)
            ts = Thingspeak()
            results = ts.process_and_upload_all_fields(channel_id, key)
            if results == 'Not Found':
                message = TextSendMessage(text="User not found")
                line_bot_api.reply_message(event.reply_token, message)
            else:
                image_messages = []
                for field, urls in results.items():
                    image_message = ImageSendMessage(
                        original_content_url=urls['image_url'],
                        preview_image_url=urls['pre_image_url']
                    )
                    image_messages.append(image_message)
                line_bot_api.reply_message(event.reply_token, image_messages)
        elif check == 'ai:' and get_request_user_id in auth_user_ai_list:
            try:
                GPT_answer = GPT_response(user_msg)
                print(GPT_answer)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            except:
                print(traceback.format_exc())
                line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息'))

@handler.add(PostbackEvent)
def handle_postback(event):
    print(event.postback.data)

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


