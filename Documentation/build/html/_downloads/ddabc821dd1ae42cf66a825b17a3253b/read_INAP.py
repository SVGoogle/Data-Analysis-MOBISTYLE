import requests
import pandas as pd
import json
import os
from tqdm import tqdm


def read_inap(room_name='K1N0624', start='2018-02-01', end='2018-03-01'):
    """
    Function to download Indoor Environmental Quality (IEQ) data monitored by INAP sensors in SL demo-case
    using IRI-UL web api. You may need to update the token if the current one is expired (contact IRI-UL).

    Args:
        room_name (str): Room identification.
        start (str): Start date as a date string object.
        end (str): End date as a date string object.

    Returns:
        df (pandas DataFrame object): IEQ data (CO2, temperature, relative humidity, VOC).

    Example:
        df_R3N0808 = read_inap('R3N0808', '2018-02-01', '2018-03-01')

    """

    # Room INAP sensor id dictionary
    sensor_id = {'R3N0808': '00681B5B', 'R3N0644': '00682753', 'K1N0623': '0068224F', 'K3N0605': '0068272C',
                 'R2N0805': '0029DC18', 'R2N0634': '00681B21', 'K1N0624': '000CC736', 'K3N0618': '00681A09'}
    # Selected room sensor id
    ids = sensor_id[room_name]

    # Create URL with correct parameters (contact IRI-UL to get token)
    start_date = f'{start}T00:00:00Z'
    end_date = f'{end}T23:59:59Z'
    token = ''
    url = f'http://52.211.97.129:8080/api/sensors/data?token={token}&id={ids}&startDate={start_date}&endDate={end_date}'

    # Connect to IRI-UL INAP sensor api
    r = requests.get(url, stream=True)

    # Check connection status
    print(f'\nRoom {room_name}: Connection is good!') if r else print('\nAn error has occurred.')

    with open('INAP_chunks.txt', 'wb') as txt:
        for chunk in r.iter_content(chunk_size=1024):

            # writing one chunk at a time to txt file
            if chunk:
                txt.write(chunk)

    with open('INAP_chunks.txt', 'r') as f:
        f_contents = f.readlines()

    # Convert api response to DataFrame object
    lst = json.loads(f_contents[0])
    data = lst[0]['measurements']

    if lst[0]['id'] != ids:
        print('Sensor id in response do not match')

    df = pd.DataFrame(data)
    df.drop(labels=['interupt', 'rgbw', 'score', 'sound', 'type'], axis=1, inplace=True)
    df['timeStamp'] = pd.to_datetime(df['timeStamp'], format='%Y-%m-%d %H:%M:%S')
    df.set_index('timeStamp', inplace=True)
    df.columns = [f'{room_name}_INAP_{col}' for col in df.columns]
    df.index.rename('Timestamp', inplace=True)

    if 'df' in locals():
        os.remove('INAP_chunks.txt')
    else:
        print('DataFrame is not created')

    print(f'Room {room_name}: Data from {start} to {end} is downloaded.')

    return df


# Divide the length of the period and download data one month at a time (to avoid web api closing the connection)
dates1 = pd.date_range(start='2018-04-1', end='2019-03-1', freq='MS').strftime('%Y-%m-%d')
dates2 = pd.date_range(start='2018-04-1', end='2019-03-1', freq='M').strftime('%Y-%m-%d')
date_lst = list(zip(dates1, dates2))

# Files folder (data for each room)
os.makedirs('./Files', exist_ok=True)
os.makedirs('./Files/INAP_files', exist_ok=True)

# Room list to perform data analysis on. Room R2N0805 INAP sensor id is not working
# room_lst = ['K3N0605', 'K1N0623', 'R3N0808', 'R3N0644', 'K1N0624', 'K3N0618', 'R2N0634']
room_lst = ['R2N0805']

# Collect the data and save it for all rooms in room_lst
for name in tqdm(room_lst, desc='Room(s)', position=0, leave=True):
    
    # Append only new data to existing files
    # INAP_data = pd.read_csv(f'./INAP_data/INAP_{name}.csv', parse_dates=True, index_col='Timestamp')
    # df_stack = read_inap(name, '2019-11-01', '2019-12-2').resample('15Min').mean()
    # INAP_data = INAP_data.append(df_stack, sort=False)
    
    # load data from beginning
    INAP_data = pd.concat([read_inap(name, date[0], date[1]) for date in tqdm(date_lst, desc='Data download', position=1, leave=True)])
    INAP_data = INAP_data.resample('15Min').mean()
    INAP_data = INAP_data.interpolate(limit=8, limit_direction='both', limit_area='inside')
    
    INAP_data.to_csv(f'./Files/INAP_files/INAP_{name}.csv')
    print(f'Room {name}: Data is saved.')
