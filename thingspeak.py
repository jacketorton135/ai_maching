import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import pytz
import pyimgur
from PIL import Image

class Thingspeak:
    def get_data_from_thingspeak(self, channel_id, api_read_key):
        url = f'https://thingspeak.com/channels/{channel_id}/feed.json?api_key={api_read_key}'
        data = requests.get(url).json()
        if data.get('error') == 'Not Found':
            return 'Not Found', 'Not Found'
        
        time_list = []
        bpm_list = []
        temperature_list = []
        humidity_list = []
        body_temperature_list = []
        ECG_list = []
        for data_point in data.get('feeds', []):
            time_list.append(data_point.get('created_at'))
            bpm_list.append(data_point.get('field1'))
            temperature_list.append(data_point.get('field2'))
            humidity_list.append(data_point.get('field3'))
            body_temperature_list.append(data_point.get('field4'))
            ECG_list.append(data_point.get('field5'))

        # Convert to Taiwan time
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

    def gen_chart(self, time_list, *field_lists):
        labels = ['BPM', 'temperature', 'humidity', 'body temperature', 'ECG']
        colors = ['r', 'g', 'b', 'y', 'm']
        fig, axes = plt.subplots(nrows=len(labels), ncols=1, figsize=(8, 12))  # Use a single figure with subplots

        for i, (field_list, label) in enumerate(zip(field_lists, labels)):
            field_list = [float(value) if value and value != '' else 0 for value in field_list]
            ax = axes[i]
            ax.plot(time_list, field_list, f'{colors[i]}-o', label=label)
            ax.set_xlabel('Time')
            ax.set_ylabel('Value')
            ax.set_title(f'Thingspeak Data - {label}')
            ax.legend()
            ax.tick_params(axis='x', rotation=45)  # Rotate x-axis labels

        plt.tight_layout()  # Adjust layout to prevent overlap
        plt.savefig('combined_charts.jpg', format='jpg', quality=85)  # Save a single combined chart
        plt.close()

    def update_photo_size(self):
        img = Image.open('combined_charts.jpg')
        img_resized = img.resize((800, 800))  # Resize to 800x800
        img_resized.save('pre_combined_charts.jpg')

    def upload_to_imgur(self):
        CLIENT_ID = os.environ.get('IMGUR_CLIENT_ID')
        urls = []
        pre_urls = []

        PATH = 'combined_charts.jpg'
        title = "Uploaded with PyImgur - Combined Charts"
        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=title)
        urls.append(uploaded_image.link)

        pre_PATH = 'pre_combined_charts.jpg'
        pre_title = "Uploaded with pre_PyImgur - Combined Charts"
        pre_im = pyimgur.Imgur(CLIENT_ID)
        uploaded_pre_image = pre_im.upload_image(pre_PATH, title=pre_title)
        pre_urls.append(uploaded_pre_image.link)

        return urls, pre_urls

    def process_and_upload_all_fields(self, channel_id, api_read_key):
        tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list = self.get_data_from_thingspeak(channel_id, api_read_key)
        if tw_time_list == 'Not Found' or bpm_list == 'Not Found':
            return 'Not Found'

        self.gen_chart(tw_time_list, bpm_list, temperature_list, humidity_list, body_temperature_list, ECG_list)
        self.update_photo_size()
        chart_links, pre_chart_links = self.upload_to_imgur()

        results = {
            'combined': {'image_url': chart_links[0], 'pre_image_url': pre_chart_links[0]},
        }
        return results

if __name__ == "__main__":
    ts = Thingspeak()
    results = ts.process_and_upload_all_fields("2466473", "GROLYCVTU08JWN8Q")
    print(results)

