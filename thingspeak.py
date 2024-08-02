import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import pytz
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
        plt.figure(figsize=(12, 8), dpi=100)  # 修改此行以調整圖形的大小和解析度
        field_list = [float(value) if value and value != '' else 0 for value in field_list]
        plt.plot(time_list, field_list, 'b-o', label=label)
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.title(f'Thingspeak Data - {label}')
        plt.xticks(rotation=45)
        plt.legend()
        file_path = f'./static/{label}_chart.jpg'
        plt.savefig(file_path, format='jpg')
        plt.close()
        return file_path

    def update_photo_size(self, file_path):
        try:
            img = Image.open(file_path)
            img_resized = img.resize((240, 240))
            resized_file_path = file_path.replace('.jpg', '_resized.jpg')
            img_resized.save(resized_file_path)
            return resized_file_path
        except FileNotFoundError:
            print(f"文件 {file_path} 不存在")
            return None

    def process_and_upload_field(self, channel_id, api_read_key, field):
        tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list = self.get_data_from_thingspeak(channel_id, api_read_key)
        if tw_time_list == 'Not Found':
            return 'Not Found'
        if field == 'field1':
            file_path = self.gen_chart(tw_time_list, bpm_list, 'BPM')
        elif field == 'field2':
            file_path = self.gen_chart(tw_time_list, temperature_list, 'temperature')
        elif field == 'field3':
            file_path = self.gen_chart(tw_time_list, humidity_list, 'humidity')
        elif field == 'field4':
            file_path = self.gen_chart(tw_time_list, body_temperature_list, 'body_temperature')
        elif field == 'field5':
            file_path = self.gen_chart(tw_time_list, ECG_list, 'ECG')
        else:
            return 'Invalid Field'

        resized_file_path = self.update_photo_size(file_path)
        if resized_file_path:
            return {'image_path': resized_file_path}
        else:
            return 'Error Resizing Image'


