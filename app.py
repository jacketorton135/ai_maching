from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import traceback
import openai
from thingspeak import Thingspeak  # 引入 thingspeak 模塊

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
openai.api_key = os.getenv('OPENAI_API_KEY')

def GPT_response(text):
    response = openai.Completion.create(model="gpt-3.5-turbo-instruct", prompt=text, temperature=0.5, max_tokens=500)
    answer = response['choices'][0]['text'].replace('。', '')
    return answer

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
    msg = event.message.text
    if msg.startswith("圖表:"):
        channel_id = msg.split(':')[1].split(',')[0]
        api_read_key = msg.split(':')[1].split(',')[1]
        print("User channel_id:", channel_id, "Read_key:", api_read_key)
        
        ts = Thingspeak()
        results = ts.process_and_upload_all_fields(channel_id, api_read_key)
        
        if results == 'Not Found':
            line_bot_api.reply_message(event.reply_token, TextSendMessage("無法找到指定的 Thingspeak 資料"))
        else:
            messages = []
            for key, value in results.items():
                messages.append(ImageSendMessage(original_content_url=value['image_url'], preview_image_url=value['pre_image_url']))
            line_bot_api.reply_message(event.reply_token, messages)
    else:
        try:
            GPT_answer = GPT_response(msg)
            print(GPT_answer)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
        except:
            print(traceback.format_exc())
            line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的 OPENAI API key 額度可能已經超過，請於後台 Log 內確認錯誤訊息'))

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
