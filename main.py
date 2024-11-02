import requests
from matplotlib import pyplot as plt
import json
import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from datetime import datetime
from api_key import API_KEY


# CITY_ID = "293725"
# CITY = "Rehovot,IL"
# CITY, CITY_ID = "Kursk,RU", "538560"
CITY, CITY_ID = "Jerusalem,IL", "293198"
DEFAULT_FILENAME = 'test1'


class Design(GridLayout):
    def __init__(self, **kwargs):
        super(Design, self).__init__(**kwargs)
        self.cols = 1
        self.refresh_data()
        self.label = Label(on_touch_down=self.on_touch_down, halign='center', text=str(self.cur_temp) + u' C\N{DEGREE SIGN},\n' + self.cur_description + '\n\n' + self.date_time)
        self.add_widget(self.label)
        self.graph = Image(source=self.file, allow_stretch=True, keep_ratio=False)
        self.add_widget(self.graph)

    def on_touch_down(self, touch):
        """refreshes the data and widgets upon touch of the label"""
        print("[REFRESHED]")
        self.refresh_widgets()

    def refresh_data(self):
        """refreshes the data and the graph file"""
        self.data = City(CITY, CITY_ID)
        self.cur_temp = self.data.get_cur_temp()
        self.cur_description = self.data.get_cur_status_description()
        self.date_time = datetime.now().strftime("%H:%M\n%d/%m/%Y ")
        self.file = self.data.save()

    def refresh_widgets(self):
        """refreshes the image and the label text in the app"""
        self.refresh_data()
        self.graph.reload()
        self.label.text = str(self.cur_temp) + u' C\N{DEGREE SIGN},\n' + self.cur_description + '\n\n' + self.date_time


class WeatherApp(App):
    def build(self):
        return Design()


def write_cities_dict():
    """create a dict of {name,country : id}, from the API of open-weather json file"""
    with open('files/city.list.json', encoding='utf-8') as data_file:
        data = json.loads(data_file.read())
    cities = {}
    for ci in data:
        cities[f"{ci['name']},{ci['country']}"] = str(ci['id'])
    j = json.dumps(cities)
    with open('files/cities_dict.json', 'w') as f:
        f.write(j)


class City:
    """gets the weather data of a given city, using OpenWeather API"""
    def __init__(self, city_name, city_id, api_key=API_KEY):
        self.plot = None
        url = f"http://api.openweathermap.org/data/2.5/forecast?id={city_id}&appid={api_key}&units=metric"
        url2 = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
        self.city = city_name[:-3]
        self.raw_forecast = requests.get(url).json()
        self.weather = requests.get(url2).json()
        self.temperature, self.time, self.statuses, self.hours, self.dates = [], [], [], [], []
        self.forecast = self.create_forecast()  # [('2021-09-16 00:00:00', 25.2, 'Clear')...]
        print("[DATA CREATED]")
        self.plot_forecast()
        self.find_rain()

    def create_forecast(self):
        """splits the data from OpenWeather into different lists"""
        forecast_details = []
        for time_point in self.raw_forecast['list']:
            forecast_details.append((time_point['dt_txt'],  # time, format: YYYY-MM-DD HH:MM:SS
                                     round(time_point['main']['temp'], 1),  # float
                                     time_point['weather'][0]['main']))  # can change the main to id/description...
        for time, temp, status in forecast_details:
            self.time.append(time)
            self.hours.append(time_format_cleaner(time, 'h'))
            date = time_format_cleaner(time, 'd')
            self.dates.append(self.__add_date(date))
            self.temperature.append(temp)
            self.statuses.append(status)
        self.dates[0] = '     '
        return forecast_details

    def __add_date(self, date):
        """deletes duplicates from self.dates list, replaces the duplicates with empty strings"""
        if not self.dates:  # first iteration
            return date
        return self.__helper(date, -1)

    def __helper(self, date, index):
        """helper function for __add_date()"""
        if self.dates[index] != '     ':  # the element is a date
            if self.dates[index] != date:
                return date
            return '     '
        return self.__helper(date, index - 1)

    def get_cur_temp(self):
        """current temperature"""
        return round(self.weather['main']['temp'], 1)

    def get_cur_status(self):
        """current status of weather"""
        return self.weather['weather'][0]['main']  # 'clear', maybe use 'id' for images?

    def get_cur_status_description(self):
        """current status of weather"""
        return self.weather['weather'][0]['description']  # 'clear sky'

    def plot_forecast(self):
        """creates a plot from the data"""
        plt.close('all')  # closes previous plots
        self.plot = Graph(self.hours, self.temperature, title=f'{self.city} forecast', xlabel='date',
                          ylabel='temp.', x_labels=self.dates, color='red', highlights='self.rain')
        return self.plot

    def save(self):
        """saves an image of the plot"""
        if self.plot:
            file_name = self.plot.save()
            return file_name

    def __str__(self):
        s = ''
        for i in range(len(self.temperature)):
            s += self.dates[i] + '     ' + self.hours[i] + ' - ' + str(self.temperature[i]) + ' C\n'
        return s

    def find_rain(self):
        """highlights the times when it will rain (x axis highlight)"""
        new_highlight_range, min_value, max_value = True, 0, 0
        for i in range(len(self.statuses) - 1):
            if 'Rain' in self.statuses[i]:
                if new_highlight_range:
                    min_value = i
                    max_value = i + 1
                    new_highlight_range = False
                else:
                    max_value = i + 1
            else:
                if not max_value:
                    continue
                plt.axvspan(min_value, max_value, alpha=0.5, color='blue')
                new_highlight_range, min_value, max_value = True, 0, 0  # reset

    def show(self):
        """shows the plot"""
        self.plot.show()


class Graph:
    """pyplot graph"""
    def __init__(self, x_values, y_values, **kwargs):
        """
        :param x_values: x_axis values
        :param y_values: y_axis values
        :param kwargs: title, xlabel, ylabel, x_labels (what will be displayed at x axis)
        """
        self.create_plot(x_values, y_values, **kwargs)

    @staticmethod
    def create_plot(x_values, y_values, **kwargs):
        print("[CREATING PLOT]")
        if 'x_labels' not in kwargs:
            x_labels = x_values[:]
        else:
            x_labels = kwargs.pop('x_labels')
        x_values = [i for i in range(len(x_values))]
        plt.plot(x_values, y_values, color='red')
        if 'title' in kwargs:
            plt.title(kwargs.pop('title'))
        if 'xlabel' in kwargs:
            plt.xlabel(kwargs.pop('xlabel'))
        if 'ylabel' in kwargs:
            plt.ylabel(kwargs.pop('ylabel'))
        plt.xticks(x_values, x_labels)

    @staticmethod
    def save(file_name=DEFAULT_FILENAME):
        """saves the plot"""
        plt.savefig(file_name)
        print(f'[SAVED] as: {file_name}')
        return file_name + '.png'

    @staticmethod
    def show():
        """shows the plot"""
        plt.tight_layout()
        plt.grid(axis='x')
        plt.show()

    @staticmethod
    def quit():
        plt.close('all')


def time_format_cleaner(time: str, mode: str):
    """
    :param time: example: '2021-09-16 00:00:00'
    :param mode: "d" for date, "h" for hour
    :return: shortened string
    """
    if mode == "h":
        return time[10:13] + ":00"
    if mode == "d":
        return f'{time[8:10]}/{time[5:7]}'


if __name__ == "__main__":
    WeatherApp().run()
