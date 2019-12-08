import os
from contextlib import contextmanager
import glob
from datetime import datetime
import numpy as np
import pandas as pd

"""
This script is a part of the MOBISTYLE project (2018-2020), data analysis for Deliverable D6.2 at Slovenian demo-case. 
This script reads the csv files from 'SCADA_data' directory. These files are gathered from SFTP server at IRI-UL,
contact IRI-UL for further information. 
This folder contains .csv files with different columns, thus different way of reading is necessary. 
Resulting pandas DataFrame is stored as csv file.
It is further used to update the SCADA csv data, see file 'Data Analysis, Slovenia.ipynb'.
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


# Read file paths from 'SCADA_missing' directory
file_paths = []

with change_dir('SCADA_missing'):
    for file_name in glob.glob('**/*.csv', recursive=True):
        
        # read .csv file paths from sub folder
        file_path = os.path.join(os.getcwd(), file_name)
        file_paths.append(file_path)


# Convert csv files to DataFrame format and create a list
df_list = [pd.read_csv(file_path,
                       sep=';', decimal=',', header=0, skiprows=[1, 2, 3],
                       parse_dates=True) for file_path in file_paths]

# Concatenate DFs
frame = pd.concat(df_list, ignore_index=True, sort=False)

# Remove NaT dates
frame = frame[~frame['SOURCE:'].isna()]

# Set DatetimeIndex
frame['Timestamp'] = frame['SOURCE:'].apply(lambda x:
                                            datetime.strptime(x, '%d.%m.%Y') if len(x) < 11 else datetime.strptime(x,'%d.%m.%Y %H:%M:%S'))
frame.set_index('Timestamp', inplace=True)
frame.drop(['SOURCE:'], axis=1, inplace=True)

# Filter data from frame by room name and store in a dictionary
room_lst = ['K1N0623', 'K3N0605', 'R3N0808', 'R3N0644', 'K1N0624', 'K3N0618', 'R2N0805', 'R3N0634', 'R2N0634']

missing_scada = {room_name: frame.filter(regex=room_name).dropna(how='all') for room_name in room_lst}

room_dct = dict()

for room_name in room_lst:
    df = missing_scada[room_name].copy()

    # Rename columns as in original SCADA data prepared by read_csv_SL.py and load_scada() function
    col_labels = [name.split('.')[2] for name in df.columns.tolist()]
    df.columns = col_labels
    df1 = df.rename(columns={f'{room_name}_AV_Temp_prostora': f'{room_name}_CV_TEMP',
                             f'{room_name}_AV_Sp_Tpr_Aktivna': f'{room_name}_SP_TEMPR_ACT',
                             f'{room_name}_AO_DO4_Ventil_FC_HL': f'{room_name}_FC_HL',
                             f'{room_name}_AO_DO5_Ventil_RAD_GR': f'{room_name}_RAD_HV',
                             f'{room_name}_AV_Hitrost_ventilator': f'{room_name}_FC_SPEED',
                             f'{room_name}_AV_Stikalo_ventilator': f'{room_name}_FC_SWITCH',
                             f'{room_name}_AV_Dnevni_rezim': f'{room_name}_MODE',
                             f'{room_name}_AV_Temp_Rezim': f'{room_name}_REG_TEMP',
                             })

    # Remove duplicate timestamps
    df1 = df1[~df1.index.duplicated()]

    # Sort DF
    df1.sort_index(inplace=True)

    # Extract room occupied and window opening data from _MODE column
    # In _MODE column('0','4' means room is occupied, '4' - window open)
    # Note: In room K1N0623 _OCC sensor is not working properly
    mask = df1[f'{room_name}_MODE'].notna()
    s = df1.loc[mask, f'{room_name}_MODE']
    df1.loc[mask, f'{room_name}_OCC'] = np.where((s == 0) | (s == 4), 1, 0)
    df1.loc[mask, f'{room_name}_WINDOW'] = np.where((s == 4), 1, 0)
    df1.loc[mask, f'{room_name}_WINDOW_Openings'] = df1.loc[mask, f'{room_name}_WINDOW'].diff()

    room_dct[room_name] = df1

# Files folder (to store resulting files for each room)
os.makedirs('./Files', exist_ok=True)
os.makedirs('./Files/SCADA_missing_files', exist_ok=True)

# Save df for each room as csv file
for name, val in room_dct.items():
    val.to_csv(f'./Files/SCADA_missing_files/SCADA_missing_{name}.csv')
