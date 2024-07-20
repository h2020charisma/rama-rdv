# + tags=["parameters"]
upstream = []
product = None
root_peakfitting_folder = None

# -

import json

import os.path
from pprint import pprint
import pandas as pd
import numpy as np
import glob
from pathlib import Path

def read_opticalpaths(file_name):
    front_sheet = pd.read_excel(file_name,sheet_name="Front sheet",header=None)
    front_sheet.fillna("",inplace=True)
    provider = front_sheet[1][0]
    investigation = front_sheet[5][0]
    operator = front_sheet[1][1]
    front_sheet[0][4]="ID"
    optical_paths = front_sheet.iloc[5:]
    optical_paths.columns = front_sheet.iloc[4]
    return (provider,investigation,operator,optical_paths)

def read_files(file_name):
    files_sheet = pd.read_excel(file_name,sheet_name="Files",header=0)
    return files_sheet

def files_lookup(folder_input):
    files = glob.glob(os.path.join(folder_input,"**","*.*"), recursive=True)
    lookup = {}
    for file_name in files:
        if file_name.endswith(".spc"):
            continue
        if not file_name.endswith(".xlsx"):
            p = Path(file_name)
            lookup[p.stem] = file_name
            lookup[p.name] = file_name
    return lookup

def read_template(folder_input,metadata={}):
    templates = glob.glob(os.path.join(folder_input,"**","*.xlsx"), recursive=True)
    for file_name in templates:
        if file_name.endswith(".xlsx"):
            lookup = files_lookup(os.path.dirname(file_name))
            try:
                provider,investigation,operator,optical_paths = read_opticalpaths(file_name)
                files = read_files(file_name)
                files['Date'] = files['Date'].astype(str)
                files['Time'] = files['Time'].astype(str)
                files.dropna(how="all").apply(lambda row : row2metadata(
                        lookup,
                        row["Filename"],row["Measurement #"],
                        provider,
                        row["Sample"],row["Instrument/OP ID"],row["Laser power, mW"],
                        row["Humidity"],row["Temperature , C"],row["Date"],row["Time"],
                        optical_paths,metadata),axis=1)
            except Exception as err:
                print(file_name,err)

def find_file(filename,lookup):
    file = Path(filename)
    if file.name in lookup:
        return lookup[file.name]
    elif file.stem in lookup:
        return lookup[file.stem]
    else:
        return None

def row2metadata(lookup,filename,
    measurement,provider,sample,op_id,laser_power,humidity,temperature,date,time,optical_paths,metadata):
    m = {}

    #m["investigation"] = investigation
    m["measurement"] = measurement
    m["provider"] = provider
    m["sample"] = sample
    m["optical_path"] = op_id
    try:
        if np.isnan(laser_power):
            m["laser_power"] = ""
        else:
            m["laser_power"] = laser_power
    except:
        m["laser_power"] = str(laser_power)
    try:
        if np.isnan(humidity):
            m["humidity"] = ""
        else:
            m["humidity"] = humidity
    except Exception as err:
        m["humidity"] = ""
    try:
        if np.isnan(humidity):
            m["temperature_c"] = ""
        else:
            m["temperature_c"] = temperature
    except Exception as err:
        m["temperature_c"] = ""
    m["date"] = date
    m["time"] = time
    op = optical_paths.loc[optical_paths["ID"]==op_id]
    if op.shape[0]>0:
        m["wavelength"] = op["Wavelength"].values[0]
        m["instrument"] =  op["Make"].values[0].upper().strip() + "_" + op["Model"].values[0].strip()
        m["collection_optics"] = op["Collection optics"].values[0].strip()
        m["collection_fibre_diameter"] = op["Collection Fibre Diameter"].values[0]
        m["slit_size"] = op["Slit Size"].values[0][0]
        m["gratings"] = op["Grating"].values[0]
        m["pin_hole_size"] = op["Pin hole size"].values[0]
        m["notes"] = op["Notes"].values[0]

    try:
        f = Path(filename)
        _f = find_file(f,lookup)
        if _f is None:
            for f in filename.split(" "):
                _f = find_file(f,lookup)
                if _f is None:
                    for m in lookup:
                        print("can't find {} in {}".format(f,os.path.dirname(lookup[m])))
                        break
                else:
                    metadata[_f.replace(root_peakfitting_folder,"")] = m
        else:
            metadata[_f.replace(root_peakfitting_folder,"")] = m
    except Exception as err:
        pass

metadata = {}
read_template(root_peakfitting_folder,metadata)



with open(product["data"], "w") as out_file:
   json.dump(metadata, out_file, indent = 4)
