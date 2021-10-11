import requests
import json
import os
from datetime import datetime

WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')


def formatted_time(time_unix, time_offset):
    """Make readable time format (HH:MM).

    Args:
            time_unix (datetime): Timestamp of needed time.
            time_offset (int): Timestamp offset.

    Returns:
            str: Time string (HH:MM).
    """

    time_unix = int(time_unix)
    time_offset = int(time_offset)

    time = time_unix + time_offset
    time_formatted = datetime.utcfromtimestamp(time).strftime('%H:%M')

    return str(time_formatted)


def get_emoji(weather_cond, time_unix, sunrise_unix, sunset_unix):
    """Check weather conditions and return apropriate emoji.

    Args:
            weather_cond (str): Weather condition.
            time_unix (datetime): Current time.
            sunrise_unix (datetime): Sunrise time.
            sunset_unix (datetime): Sunset time.

    Returns:
            str: Single emoji.
    """

    if weather_cond == 'Thunderstorm':
        emoji = '⛈️'
    elif weather_cond == 'Drizzle':
        emoji = '🌧️'
    elif weather_cond == 'Rain':
        emoji = '🌧️'
    elif weather_cond == 'Snow':
        emoji = '❄️'
    elif weather_cond == 'Atmosphere':
        emoji = '🌫️'
    elif weather_cond == 'Clouds':
        emoji = '☁️'
    elif weather_cond == 'Clear':
        if sunrise_unix < time_unix < sunset_unix:
            emoji = '☀️'
        else:
            emoji = '🌒'

    return emoji


def time_to_intervals(time_list, offset):
    """Converts list of timestamps into ready to output time ranges and separete hours if those are.

    Args:
            time_list (list): List of timestamps.
            offset (datetime): Timezone offset.

    Returns:
            str: Complete output, ready for use.
    """

    intervals = []
    intervals_all = []
    intervals_temp = []
    counter = 0
    flag = False
    output = ''

    if len(time_list) == 0:
        output += '     {}\n'.format('No data provided')
        return output

    elif len(time_list) == 1:
        output += '     {}\n'.format(formatted_time(time_list[0], offset))
        return output

    for i in range(len(time_list) - 1):
        if time_list[counter + 1] - time_list[counter] == 3600:
            if flag:
                if intervals_temp != []:
                    intervals.append(intervals_temp)
                intervals_temp = []
                flag = False

            intervals_temp.append(time_list[counter])
            intervals_temp.append(time_list[counter + 1])

            intervals_all.append(time_list[counter])
            intervals_all.append(time_list[counter + 1])
        else:
            flag = True
            intervals_temp = sorted(set(intervals_temp))

        counter += 1

    hours = set(time_list) - set(intervals_all)
    intervals_temp = sorted(set(intervals_temp))
    intervals.append(intervals_temp)
    hours = sorted(hours)

    for i in hours:
        output += '     {}\n'.format(formatted_time(i, offset))

    if len(intervals[0]) == 0:
        return output
    elif len(intervals) == 1:
        output += '     {}-{}\n'.format(formatted_time(
            intervals[0][0], offset), formatted_time(intervals[0][-1], offset))
    else:
        for i in range(len(intervals)):
            output += '     {}-{}\n'.format(formatted_time(
                intervals[i][0], offset), formatted_time(intervals[i][-1], offset))

    return output


def get_weather():

    url = f'https://api.openweathermap.org/data/2.5/onecall?lat=49.5559&lon=25.6056&exclude=minutely,alerts&units=metric&appid={WEATHER_API_KEY}'

    data = requests.get(url).json()

    time_offset_unix = data['timezone_offset']
    time_sunrise_unix = data['current']['sunrise']
    time_sunset_unix = data['current']['sunset']

    time_sunrise = formatted_time(time_sunrise_unix, time_offset_unix)
    time_sunset = formatted_time(time_sunset_unix, time_offset_unix)

    temp_min = str(data['daily'][0]['temp']['min'])
    temp_max = str(data['daily'][0]['temp']['max'])
    temp_now = str(data['current']['temp'])
    temp_now_feels = str(data['current']['feels_like'])
    temp_morn_feels = str(data['daily'][0]['feels_like']['morn'])
    temp_day_feels = str(data['daily'][0]['feels_like']['day'])
    temp_eve_feels = str(data['daily'][0]['feels_like']['eve'])

    wind_speed_now = str(data['current']['wind_speed'])

    pop_now = str(int(float(data['daily'][0]['pop'])*100))

    output = 'Weather for today:\n\n'

    counter = 0
    midnight_flag = False

    weather_time = data['hourly'][counter]['dt']

    temp_intervals = []
    res_intervals = []

    if formatted_time(weather_time, time_offset_unix) == '00:00':
        counter = 1
        midnight_flag = True

    weather_time = data['hourly'][counter]['dt']

    while formatted_time(weather_time, time_offset_unix) != '00:00':
        weather_time = data['hourly'][counter]['dt']

        weather = data['hourly'][counter]['weather'][0]['main']

        if counter == 0 or midnight_flag == True:
            midnight_flag = False
            temp_intervals.append(weather)
            temp_intervals.append(weather_time)
        else:
            weather_previous = data['hourly'][counter-1]['weather'][0]['main']
            if weather_previous == weather:
                temp_intervals.append(weather_time)
            else:
                res_intervals.append(temp_intervals)
                temp_intervals = []
                temp_intervals.append(weather)
                temp_intervals.append(weather_time)

        counter += 1

        if formatted_time(weather_time, time_offset_unix) == '00:00':
            res_intervals.append(temp_intervals)

    for interval in res_intervals:
        if len(interval) >= 3:
            output += '{} {}: {}-{}\n'.format(
                get_emoji(
                    interval[0],
                    interval[1],
                    time_sunrise_unix,
                    time_sunset_unix
                ),
                interval[0],
                formatted_time(interval[1], time_offset_unix),
                formatted_time(interval[-1], time_offset_unix)
            )
        else:
            output += '{} {} {}\n'.format(
                get_emoji(
                    interval[0],
                    interval[-1],
                    time_sunrise_unix,
                    time_sunset_unix
                ),
                interval[0],
                formatted_time(interval[-1], time_offset_unix)
            )

    output += '\n\n'

    output += '🌡️ Temp:'
    output += ' (now {}℃)\n'.format(temp_now)
    output += '     min: {}℃\n     max: {}℃\n\n'.format(temp_min, temp_max)
    output += '😶 Feels:'
    output += ' (now {}℃)\n'.format(temp_now_feels)

    time = int(datetime.now().hour) + 3

    if 5 < time < 10:
        output += '     morn: {}℃\n'.format(temp_morn_feels)
        output += '     eve: {}℃\n'.format(temp_eve_feels)
        output += '     day: {}℃\n\n'.format(temp_day_feels)
    elif 10 < time < 16:
        output += '     day: {}℃\n'.format(temp_day_feels)
        output += '     eve: {}℃\n\n'.format(temp_eve_feels)
    elif 16 < time < 22:
        output += '     eve: {}℃\n\n'.format(temp_eve_feels)

    output += '🌀 Wind speed: {}m/s\n'.format(wind_speed_now)
    output += '💧 Probability of precipitation: {}%\n\n'.format(pop_now)

    output += '🌅 Sunrise: {},  🌆 Sunset: {}'.format(time_sunrise, time_sunset)

    return output

