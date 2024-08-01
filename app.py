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

# 授權用戶列表
auth_user_list = ["U39b3f15d09b42fbd028e5689156a49e1"]  # 允許使用圖表功能的用戶ID列表
auth_user_ai_list = ["U39b3f15d09b42fbd028e5689156a49e1"]  # 允許使用AI功能的用戶ID列表

def GPT_response(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": text}
            ],
            temperature=0.5,
            max_tokens=500
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print(f"GPT 回應錯誤: {e}")
        return "對不起，我無法處理你的請求。"

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
    user_id = event.source.user_id
    input_msg = event.message.text
    check = input_msg[:3].lower()
    user_msg = input_msg[3:].strip()  # 例如 "2466473,GROLYCVTU08JWN8Q,field1"
    
    if user_id in auth_user_list:
        if check == "圖表:":
            try:
                parts = user_msg.split(',')
                if len(parts) != 3:
                    raise ValueError("輸入格式錯誤。請使用正確格式，例如: '圖表:2466473,GROLYCVTU08JWN8Q,field1'")
                channel_id, key, field = parts
                print("用戶 channel_id: ", channel_id, "Read_key: ", key, "Field: ", field)
                ts = Thingspeak()
                result = ts.process_and_upload_field(channel_id, key, field)
                if result == 'Not Found':
                    message = TextSendMessage(text="數據未找到或無法處理請求。")
                elif result == 'Invalid Field':
                    message = TextSendMessage(text="無效的 field 識別符。請使用 'field1', 'field2', 'field3', 'field4', 或 'field5'。")
                else:
                    image_message = ImageSendMessage(
                        original_content_url=result['image_url'],
                        preview_image_url=result['pre_image_url']
                    )
                    message = image_message
                line_bot_api.reply_message(event.reply_token, message)
            except Exception as e:
                print(f"處理圖表請求時錯誤: {e}")
                message = TextSendMessage(text=f"處理圖表請求時出現問題: {str(e)}")
                line_bot_api.reply_message(event.reply_token, message)
        
        elif check == 'ai:' and user_id in auth_user_ai_list:
            try:
                GPT_answer = GPT_response(user_msg)
                print(GPT_answer)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            except Exception as e:
                print(f"GPT 回應錯誤: {e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage('對不起，我無法處理你的請求。'))

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




