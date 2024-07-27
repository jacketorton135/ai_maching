import json
from openai import OpenAI
from flask import Flask, request, abort
import os
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *
from thingspeak import Thingspeak

app = Flask(__name__)
line_bot_api_key = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
line_bot_secret_key = os.environ.get('LINE_CHANNEL_SECRET_KEY')

# Channel Access Token
line_bot_api = LineBotApi(line_bot_api_key)
# Channel Secret
handler = WebhookHandler(line_bot_secret_key)

# Open AI key
openai_api_key = os.environ.get('OPEN_AI_KEY')

# U5583a266be8eb6b47ad9fa7d96846c80
# Auth User list
auth_user_list = os.environ.get('AUTH_USER_LIST')  # string
auth_user_list = auth_user_list.split(',')  #list
print('auth_user_list', auth_user_list)

# U5583a266be8eb6b47ad9fa7d96846c80
# Auth AI User list
auth_user_ai_list = os.environ.get('AUTH_AI_USER_LIST')  # string
auth_user_ai_list = auth_user_ai_list.split(',')  #list
print('auth_user_ai_list', auth_user_ai_list)

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# input:  "圖表:2466473,field1,GROLYCVTU08JWN8Q"
# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_request_user_id = event.source.user_id
    print('get_request_user_id', get_request_user_id)
    input_msg = event.message.text
    check = input_msg[:3].lower()
    user_msg = input_msg[3:]  # 2466473,field1,GROLYCVTU08JWN8Q
    print('check', check)
    print('user_msg', user_msg)
    if get_request_user_id in auth_user_list:

        if check in "圖表:":
            channel_id = user_msg.split(',')[0]
            field = user_msg.split(',')[1]
            key = user_msg.split(',')[2]
            print("User channel_id: ", channel_id, "Field: ", field, "Read_key: ", key)
            ts = Thingspeak()
            tw_time_list, bpm_list = ts.get_data_from_thingspeak(
                channel_id, field, key)
            if tw_time_list == 'Not Found' or bpm_list == 'Not Found':
                message = TextSendMessage(text="User not found")
                line_bot_api.reply_message(event.reply_token, message)
            else:
                ts.gen_chart(tw_time_list, bpm_list)
                ts.update_photo_size()
                chart_link, pre_chart_link = ts.upload_to_imgur()
                print("圖片網址", chart_link)
                print("縮圖網址", pre_chart_link)
                image_message = ImageSendMessage(
                    original_content_url=chart_link,
                    preview_image_url=pre_chart_link)
                line_bot_api.reply_message(event.reply_token, image_message)
        elif check == 'ai:' and get_request_user_id in auth_user_ai_list:
            try:
                client = OpenAI(api_key=openai_api_key)

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {
                            "role": "system",
                            "content": "如果回答問題盡可能用簡潔的話回復"
                        },
                        {
                            "role": "user",
                            "content": user_msg,
                        },
                    ],
                )
                reply_msg = response.choices[0].message.content
                print('reply_msg', reply_msg)
                message = TextSendMessage(text=reply_msg)
                line_bot_api.reply_message(event.reply_token, message)
            except Exception as e:
                print(e)
        else:  # 學使用者說話
            message = TextSendMessage(text=event.message.text)
            line_bot_api.reply_message(event.reply_token, message)
    else:
        message = TextSendMessage(text='使用者沒有權限')
        line_bot_api.reply_message(event.reply_token, message)


if __name__ == "__main__":
    # port = int(os.environ.get('PORT', 5001))
    # local
    # app.run(host='0.0.0.0', port=5001)
    # Render
    app.run()











