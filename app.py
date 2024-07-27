import json
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from thingspeak import Thingspeak

app = Flask(__name__)

# Ensure environment variables are set
line_bot_api_key = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
line_bot_secret_key = os.environ.get('LINE_CHANNEL_SECRET_KEY')

# Check environment variables
if not line_bot_api_key or not line_bot_secret_key:
    raise EnvironmentError("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET_KEY not set")

# Channel Access Token and Secret
line_bot_api = LineBotApi(line_bot_api_key)
handler = WebhookHandler(line_bot_secret_key)

# Auth User list
auth_user_list = os.environ.get('AUTH_USER_LIST', '').split(',')
print('auth_user_list', auth_user_list)

# Listen to all POST requests from /callback
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

# Handle messages
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
            tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list = ts.get_data_from_thingspeak(channel_id, key)
            if tw_time_list == 'Not Found' or bpm_list == 'Not Found':
                message = TextSendMessage(text="User not found")
                line_bot_api.reply_message(event.reply_token, message)
            else:
                ts.gen_chart(tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list)
                ts.update_photo_size()
                chart_link, pre_chart_link = ts.upload_to_imgur()
                print("圖片網址", chart_link)
                print("縮圖網址", pre_chart_link)
                image_message = ImageSendMessage(
                    original_content_url=chart_link,
                    preview_image_url=pre_chart_link)
                line_bot_api.reply_message(event.reply_token, image_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=input_msg))
    else:
        message = TextSendMessage(text="你無權限使用該功能")
        line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)









