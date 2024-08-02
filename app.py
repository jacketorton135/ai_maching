import os
import openai
import requests
import csv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import traceback

app = Flask(__name__, static_folder="./static", static_url_path="/static")
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# 授權用戶列表
auth_user_list = ["U39b3f15d09b42fbd028e5689156a49e1"]
auth_user_ai_list = ["U39b3f15d09b42fbd028e5689156a49e1"]

# 爬取 CSV 數據
def fetch_csv_data(csv_url):
    response = requests.get(csv_url)
    decoded_content = response.content.decode('utf-8')
    cr = csv.DictReader(decoded_content.splitlines(), delimiter=',')
    return list(cr)

# 爬取特定的 CSV
def get_bmi_data():
    csv_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTbj3f0rhEu2aCljm1AgkPiaqU7XLGfLUfmL_3NVClYABWXmarViEg1RSE4Q9St0YG_rR74VZyNh7MF/pub?output=csv'
    return fetch_csv_data(csv_url)

def get_environment_data():
    csv_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS5C_o47POhPXTZEgq40budOJB1ygTTZx9D_086I-ZbHfApFPZB_Ra5Xi09Qu6hxzk9_QXJ-7-QFoKD/pub?output=csv'
    return fetch_csv_data(csv_url)

def get_heartbeat_data():
    csv_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSULVwFdSh9_HuIJe1dWPae-jzcQYsyYb5DuRfXHtDenUlr1oSYTRr-AQ-aMthcCsNRTcVIbvmt_7qJ/pub?output=csv'
    return fetch_csv_data(csv_url)

# 判斷數值是否正常
def check_normal_or_abnormal(value, normal_range):
    if normal_range[0] <= value <= normal_range[1]:
        return "正常"
    else:
        return "異常"

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
    input_msg = event.message.text.lower().strip()
    
    if user_id in auth_user_list:
        if input_msg.startswith('ai:'):
            try:
                user_msg = input_msg[3:].strip()
                if user_msg == "心跳":
                    data = get_heartbeat_data()
                    latest_row = data[-1]
                    heartbeat = float(latest_row.get("Heartbeat"))
                    time = latest_row.get("Time")
                    status = check_normal_or_abnormal(heartbeat, (60, 100))
                    message_text = f"心跳: {heartbeat}, 時間: {time}, 狀態: {status}"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
                elif user_msg == "溫度":
                    data = get_environment_data()
                    latest_row = data[-1]
                    temperature = float(latest_row.get("Temperature"))
                    time = latest_row.get("Time")
                    status = check_normal_or_abnormal(temperature, (20, 25))
                    message_text = f"溫度: {temperature}, 時間: {time}, 狀態: {status}"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
                elif user_msg == "濕度":
                    data = get_environment_data()
                    latest_row = data[-1]
                    humidity = float(latest_row.get("Humidity"))
                    time = latest_row.get("Time")
                    status = check_normal_or_abnormal(humidity, (30, 50))
                    message_text = f"濕度: {humidity}, 時間: {time}, 狀態: {status}"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
                elif user_msg == "體溫":
                    data = get_environment_data()
                    latest_row = data[-1]
                    body_temperature = float(latest_row.get("Body Temperature"))
                    time = latest_row.get("Time")
                    status = check_normal_or_abnormal(body_temperature, (36.5, 37.5))
                    message_text = f"體溫: {body_temperature}, 時間: {time}, 狀態: {status}"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
                elif user_msg == "bmi":
                    data = get_bmi_data()
                    latest_row = data[-1]
                    bmi = float(latest_row.get("BMI"))
                    time = latest_row.get("Time")
                    status = check_normal_or_abnormal(bmi, (18.5, 24.9))
                    message_text = f"BMI: {bmi}, 時間: {time}, 狀態: {status}"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
                else:
                    GPT_answer = GPT_response(user_msg)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            except Exception as e:
                print(f"GPT 回應錯誤: {e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage('對不起，我無法處理你的請求。'))
                
        elif input_msg.startswith("圖表:"):
            if user_id in auth_user_list:
                try:
                    parts = input_msg[3:].strip().split(',')
                    if len(parts) != 3:
                        raise ValueError("輸入格式錯誤。請使用正確格式，例如: '圖表:2466473,GROLYCVTU08JWN8Q,field1'")
                    
                    channel_id, key, field = parts
                    print("用戶 channel_id: ", channel_id, "Read_key: ", key, "Field: ", field)
                    
                    if field not in ['field1', 'field2', 'field3', 'field4', 'field5']:
                        raise ValueError("無效的 field 識別符。請使用 'field1', 'field2', 'field3', 'field4', 或 'field5'。")
                    
                    ts = Thingspeak()
                    result = ts.process_and_upload_field(channel_id, key, field)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(result))
                except Exception as e:
                    print(f"圖表處理錯誤: {e}")
                    line_bot_api.reply_message(event.reply_token, TextSendMessage('對不起，無法生成圖表。'))

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
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)








