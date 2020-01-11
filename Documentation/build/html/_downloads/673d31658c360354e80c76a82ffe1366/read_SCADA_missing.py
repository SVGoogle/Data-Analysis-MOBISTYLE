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
    cwd = os.getcwd()
    try:
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


# Change date format
def date_parser(date):
    try:
        if len(date) < 11:
            return datetime.strptime(date, '%d.%m.%Y')
        else:
            return datetime.strptime(date, '%d.%m.%Y %H:%M:%S')
    except TypeError:
        return pd.NaT


# Convert csv files to DataFrame format and create a list
df_list = []
for file_path in file_paths:
    df_list.append(
        (pd
         .read_csv(file_path,
                   sep=';',
                   decimal=',',
                   header=0,
                   skiprows=[1, 2, 3],
                   parse_dates=['SOURCE:'],
                   date_parser=date_parser)
         .rename(columns={'SOURCE:': 'Timestamp'})
         .drop_duplicates(subset=['Timestamp'])
         .dropna(subset=['Timestamp'])
         .set_index('Timestamp')
         .resample('15T')
         .nearest()
         )
    )

# Concatenate DFs
frame = pd.concat(df_list, sort=False)


# Filter data from frame by room name and store in a dictionary
room_lst = ['K1N0623', 'K3N0605', 'R3N0808', 'R3N0644', 'K1N0624', 'K3N0618', 'R2N0805', 'R2N0634']

missing_scada = {room_name: frame.filter(regex=room_name).dropna(how='all') for room_name in room_lst}

room_dct = dict()

for room_name in room_lst:
    df = missing_scada[room_name].copy()

    # Rename columns as in original SCADA data prepared by read_csv_SL.py and load_scada() function
    col_labels = [name.split('.')[2] for name in df.columns]
    df.columns = col_labels
    df = df.rename(columns={
        f'{room_name}_AV_Temp_prostora': f'{room_name}_CV_TEMP',
        f'{room_name}_AV_Sp_Tpr_Aktivna': f'{room_name}_SP_TEMPR_ACT',
        f'{room_name}_AO_DO4_Ventil_FC_HL': f'{room_name}_FC_HL',
        f'{room_name}_AO_DO5_Ventil_RAD_GR': f'{room_name}_RAD_HV',
        f'{room_name}_AV_Hitrost_ventilator': f'{room_name}_FC_SPEED',
        f'{room_name}_AV_Stikalo_ventilator': f'{room_name}_FC_SWITCH',
        f'{room_name}_AV_Dnevni_rezim': f'{room_name}_MODE',
        f'{room_name}_AV_Temp_Rezim': f'{room_name}_REG_TEMP',
                             }).sort_index()

    # Extract room occupied and window opening data from _MODE column
    # In _MODE column '0' means room is occupied, '4' - window open
    # N.B.: In room K1N0623 _OCC sensor is not working properly
    mask = df[f'{room_name}_MODE'].notna()
    s = df.loc[mask, f'{room_name}_MODE']
    df.loc[mask, f'{room_name}_OCC'] = np.where((s == 0) | (s == 4), 1, 0)
    df.loc[mask, f'{room_name}_WINDOW'] = np.where((s == 4), 1, 0)
    df.loc[mask, f'{room_name}_WINDOW_Openings'] = df.loc[mask, f'{room_name}_WINDOW'].diff()

    room_dct[room_name] = df

# Files folder (to store resulting files for each room)
os.makedirs('./Files', exist_ok=True)
os.makedirs('./Files/SCADA_missing_files', exist_ok=True)

# Save df for each room as csv file
for name, val in room_dct.items():
    val.to_csv(f'./Files/SCADA_missing_files/SCADA_missing_{name}.csv')
