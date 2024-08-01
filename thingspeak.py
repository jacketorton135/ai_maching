import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import pytz
import pyimgur
from PIL import Image

class Thingspeak():
    def get_data_from_thingspeak(self, channel_id, api_read_key):
        url = f'https://thingspeak.com/channels/{channel_id}/feed.json?api_key={api_read_key}'
        data = requests.get(url).json()
        if data.get('error') == 'Not Found':
            return 'Not Found', 'Not Found'
        time_list = list()
        bpm_list = list()
        temperature_list = list()
        humidity_list = list()
        body_temperature_list = list()
        ECG_list = list()
        for data_point in data['feeds']:
            time_list.append(data_point.get('created_at'))
            bpm_list.append(data_point.get('field1'))
            temperature_list.append(data_point.get('field2'))
            humidity_list.append(data_point.get('field3'))
            body_temperature_list.append(data_point.get('field4'))
            ECG_list.append(data_point.get('field5'))

        # 換成台灣時間
        tw_time_list = self.format_time(time_list)
        return tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list

    def format_time(self, time_list):
        taiwan_tz = pytz.timezone('Asia/Taipei')
        tw_time_list = []
        for timestamp in time_list:
            dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
            dt_utc = pytz.utc.localize(dt)
            dt_taiwan = dt_utc.astimezone(taiwan_tz)
            tw_time_list.append(dt_taiwan.strftime('%Y-%m-%d %H:%M:%S'))
        return tw_time_list

    def gen_chart(self, time_list, field_list, label):
        plt.figure(figsize=(12, 6))
        field_list = [float(value) if value and value != '' else 0 for value in field_list]
        plt.plot(time_list, field_list, 'b-o', label=label)
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.title(f'Thingspeak Data - {label}')
        plt.xticks(rotation=45)
        plt.legend()
        plt.savefig(f'{label}_chart.jpg', format='jpg')
        plt.close()

    def update_photo_size(self):
        for label in ['BPM', 'temperature', 'humidity', 'body_temperature', 'ECG']:
            try:
                img = Image.open(f'{label}_chart.jpg')
                img_resized = img.resize((240, 240))
                img_resized.save(f'{label}_chart_resized.jpg')
            except FileNotFoundError:
                print(f"文件 {label}_chart.jpg 不存在")
                
    def process_and_upload_field(self, channel_id, api_read_key, field):
        tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list = self.get_data_from_thingspeak(channel_id, api_read_key)
        if tw_time_list == 'Not Found':
            return 'Not Found'
        if field == 'field1':
            self.gen_chart(tw_time_list, bpm_list, 'BPM')
        elif field == 'field2':
            self.gen_chart(tw_time_list, temperature_list, 'temperature')
        elif field == 'field3':
            self.gen_chart(tw_time_list, humidity_list, 'humidity')
        elif field == 'field4':
            self.gen_chart(tw_time_list, body_temperature_list, 'body_temperature')
        elif field == 'field5':
            self.gen_chart(tw_time_list, ECG_list, 'ECG')
        else:
            return 'Invalid Field'
        
        self.update_photo_size()

        try:
            image_url = self.upload_image(f'{field}_chart_resized.jpg')
            pre_image_url = self.upload_image(f'{field}_chart_resized.jpg')
            return {'image_url': image_url, 'pre_image_url': pre_image_url}
        except Exception as e:
            print(f"處理圖表請求時錯誤: {e}")
            return {'image_url': None, 'pre_image_url': None}

    def upload_image(self, file_path):
        CLIENT_ID = 'YOUR_IMGUR_CLIENT_ID'
        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(file_path, title="Uploaded with PyImgur")
        return uploaded_image.link


