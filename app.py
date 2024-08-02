import os
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# Google Sheets API初始化
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv('GOOGLE_SHEETS_CREDENTIALS'), scope)
    client = gspread.authorize(creds)
    return client

# 爬取 Google Sheets 數據
def fetch_sheet_data(sheet_url, sheet_name):
    client = init_gspread()
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet.get_all_records()

# 爬取特定的 Google Sheets
def get_bmi_data():
    sheet_url = 'https://docs.google.com/spreadsheets/d/1ji-9bYlxt3KDxJvFIdat-3NwIkL7ejUa6wMFXgFe2a0/edit?resourcekey=&gid=1661867759'
    sheet_name = 'Sheet1'
    return fetch_sheet_data(sheet_url, sheet_name)

def get_environment_data():
    sheet_url = 'https://docs.google.com/spreadsheets/d/12rkfKKxrm3NcnrZNgZPzml9oNZm4alc2l-8UFsA2iCY/edit?resourcekey#gid=1685037583'
    sheet_name = 'Sheet1'
    return fetch_sheet_data(sheet_url, sheet_name)

def get_heartbeat_data():
    sheet_url = 'https://docs.google.com/spreadsheets/d/1DUD0yMOqnjaZB5fhIytxBM0Ajmg6mP72oAmwC-grT4g/edit?resourcekey=&gid=1895836984'
    sheet_name = 'Sheet1'
    return fetch_sheet_data(sheet_url, sheet_name)

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
        if input_msg == "bmi":
            data = get_bmi_data()
            message_text = ""
            for row in data:
                bmi = row.get("BMI")
                time = row.get("Time")
                status = check_normal_or_abnormal(bmi, (18.5, 24.9))
                message_text += f"BMI: {bmi}, 時間: {time}, 狀態: {status}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
        
        elif input_msg == "溫度":
            data = get_environment_data()
            message_text = ""
            for row in data:
                temperature = row.get("Temperature")
                time = row.get("Time")
                status = check_normal_or_abnormal(temperature, (20, 25))
                message_text += f"溫度: {temperature}, 時間: {time}, 狀態: {status}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
        
        elif input_msg == "濕度":
            data = get_environment_data()
            message_text = ""
            for row in data:
                humidity = row.get("Humidity")
                time = row.get("Time")
                status = check_normal_or_abnormal(humidity, (30, 50))
                message_text += f"濕度: {humidity}, 時間: {time}, 狀態: {status}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
        
        elif input_msg == "體溫":
            data = get_environment_data()
            message_text = ""
            for row in data:
                body_temperature = row.get("Body Temperature")
                time = row.get("Time")
                status = check_normal_or_abnormal(body_temperature, (36.5, 37.5))
                message_text += f"體溫: {body_temperature}, 時間: {time}, 狀態: {status}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
        
        elif input_msg == "心跳":
            data = get_heartbeat_data()
            message_text = ""
            for row in data:
                heartbeat = row.get("Heartbeat")
                time = row.get("Time")
                status = check_normal_or_abnormal(heartbeat, (60, 100))
                message_text += f"心跳: {heartbeat}, 時間: {time}, 狀態: {status}\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(message_text))
        
        elif input_msg.startswith('ai:') and user_id in auth_user_ai_list:
            try:
                user_msg = input_msg[3:].strip()
                GPT_answer = GPT_response(user_msg)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
            except Exception as e:
                print(f"GPT 回應錯誤: {e}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage('對不起，我無法處理你的請求。'))

    # 圖表處理邏輯
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







