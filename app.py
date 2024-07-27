from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from thingspeak import Thingspeak

app = Flask(__name__)
line_bot_api_key = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_bot_secret_key = os.getenv('LINE_CHANNEL_SECRET_KEY')

# Channel Access Token
line_bot_api = LineBotApi(line_bot_api_key)
# Channel Secret
handler = WebhookHandler(line_bot_secret_key)

# Auth User list
auth_user_list = os.getenv('AUTH_USER_LIST').split(',')

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_request_user_id = event.source.user_id
    input_msg = event.message.text
    check = input_msg[:3].lower()
    user_msg = input_msg[3:]
    
    if get_request_user_id in auth_user_list:
        if check in "圖表:":
            channel_id, key = user_msg.split(',')
            ts = Thingspeak()
            results = ts.process_and_upload_all_fields(channel_id, key)
            if results == 'Not Found':
                message = TextSendMessage(text="User not found")
                line_bot_api.reply_message(event.reply_token, message)
            else:
                for field, urls in results.items():
                    image_message = ImageSendMessage(
                        original_content_url=urls['image_url'],
                        preview_image_url=urls['pre_image_url']
                    )
                    line_bot_api.reply_message(event.reply_token, image_message)
    else:
        message = TextSendMessage(text='使用者沒有權限')
        line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    app.run()








