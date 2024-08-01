from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import openai
import traceback
from thingspeak import Thingspeak  # 確保 thingspeak.py 和 app.py 在同一目錄下

app = Flask(__name__)

# 配置路徑
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Line API 初始化
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# OpenAI API Key 初始化
openai.api_key = os.getenv('OPENAI_API_KEY')

# 授權用戶列表
auth_user_list = ["U39b3f15d09b42fbd028e5689156a49e1"]
auth_user_ai_list = ["U39b3f15d09b42fbd028e5689156a49e1"]

def GPT_response(user_msg):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "回答問題時盡可能簡潔"},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
            max_tokens=500
        )
        reply_msg = response.choices[0].message['content'].strip()
        return reply_msg
    except Exception as e:
        print(f"OpenAI API 錯誤: {e}")
        return '對不起，我遇到了問題，無法處理請求。'

# 處理來自 /callback 的 POST 請求
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("請求主體: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理用戶訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    input_msg = event.message.text
    check = input_msg[:3].lower()
    user_msg = input_msg[3:].strip()

    if user_id in auth_user_list:
        if check == "圖表:":
            try:
                channel_id, key = user_msg.split(',')
                ts = Thingspeak()
                results = ts.process_and_upload_all_fields(channel_id, key)
                if results == 'Not Found':
                    message = TextSendMessage(text="數據未找到或無法處理請求。")
                else:
                    image_messages = [
                        ImageSendMessage(
                            original_content_url=urls['image_url'],
                            preview_image_url=urls['pre_image_url']
                        )
                        for field, urls in results.items()
                    ]
                    message = image_messages
                line_bot_api.reply_message(event.reply_token, message)
            except Exception as e:
                print(f"處理圖表請求時錯誤: {e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage('處理圖表時出現問題。請檢查輸入是否正確。'))
        
        elif check == 'ai:' and user_id in auth_user_ai_list:
            try:
                GPT_answer = GPT_response(user_msg)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            except Exception as e:
                print(f"GPT 回應錯誤: {e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage('對不起，我無法處理你的請求。'))

@handler.add(PostbackEvent)
def handle_postback(event):
    print(f"Postback 事件資料: {event.postback.data}")

@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入!')
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)



