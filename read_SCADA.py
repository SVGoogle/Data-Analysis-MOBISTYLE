import os
from contextlib import contextmanager
import glob
import pandas as pd
import numpy as np
import time
from tqdm import tqdm

"""
This script is a part of the MOBISTYLE project (2018-2020), namely first step before data analysis for Deliverable D6.2 
at Slovenian demonstration. This script reads the csv files from 'SCADA_data' directory. These files are gathered from 
SFTP server at IRI-UL demo site, contact IRI-UL for further information. 
Resulting pandas DataFrame is converted to csv file. 
It is further used to analyse and plot figures, see file 'Data Analysis, Slovenia.ipynb'.
"""


@contextmanager
def change_dir(destination):
    """
    This f-n reads the subfolder path and then returns back to current working directory (cwd).
    Args: 
        destination (str): Subfolder name (that is located in cwd)
    Returns: 
        Location is returned back to cwd after desired computations are completed
    """
    try:
        cwd = os.getcwd()
        os.chdir(destination)
        yield
    finally:
        os.chdir(cwd)


start = time.perf_counter()

# Read file paths for files in 'SCADA_data' directory
file_paths = []
with change_dir('SCADA_data'):
    for file_name in glob.glob('**/*.csv', recursive=True):
        # read .csv file paths from sub folder
        file_path = os.path.join(os.getcwd(), file_name)
        file_paths.append(file_path)

print('File paths are gathered. Converting to DataFrame...')

# Convert data to DataFrame format and create a list
df_list = [pd.read_csv(file_path, na_values='Bad') for file_path in tqdm(file_paths, desc='File(s) completed')]

print('\nDataFrame list is created. Concatenating...')

# Concatenate DFs
frames = pd.concat(df_list, ignore_index=True, sort=False)

# Create datetime index
frames['Timestamp'] = pd.to_datetime(frames['Timestamp'])
frames.set_index('Timestamp', inplace=True)
frames.sort_index()

# Files folder (data for each room)
os.makedirs('./Files', exist_ok=True)
os.makedirs('./Files/SCADA_files', exist_ok=True)

# Save data as one .csv file
frames.to_csv('./Files/SCADA_files/SCADA_SI.csv')

print('\nSCADA dataFrame is created. Filtering and saving data by room...')

# Outdoor climate data
outdoor_data = frames.filter(
    items=['WEATHERS_TEMP', 'WEATHERS_HUM01', 'WEATHERS_ILL_SOUTH', 'WEATHERS_ILL_EAST', 'WEATHERS_ILL_WEST'])

# Correction for SCADA weather data Temp
outdoor_data['WEATHERS_TEMP'].replace({'Error': np.nan}, inplace=True)
outdoor_data['WEATHERS_TEMP'].astype('float64')

# Separate data for each room
room_ID = ['K1N0623', 'K1N0605', 'R3N0808', 'R3N0644', 'K1N0624', 'K3N0618', 'R2N0805', 'R3N0634']
room_dct = {room_name: frames.filter(regex=room_name) for room_name in room_ID}

# Save df for each room as csv file
for name, val in room_dct.items():
    val.to_csv(f'./Files/SCADA_files/SCADA_{name}.csv')

# Save outdoor climate data
# N.B. There is another outdoor climate source which is used in the analysis due to less missing data
outdoor_data.to_csv('./Files/SCADA_files/outdoor.csv')

finish = time.perf_counter()
print(f'\nFinished in {round(finish-start, 2)} second(s)')
