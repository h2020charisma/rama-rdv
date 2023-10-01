# + tags=["parameters"]
upstream = ["twinning_normalize","load_spectra"]
product = None
root_data_folder: None
files_led_reference: None
files_led_twinned: None
files_spectra_reference: None
files_spectra_twinned: None
probe: None

# -
import os
import matplotlib.pyplot as plt
import re
import ramanchada2 as rc2
import numpy as np
import pandas as pd

def Y_532(x):
    A = 8.30752731e-01
    B = 2.54881472e-07
    x0 = 1.42483359e+3
    Y = A * np.exp(-B * (x - x0)**2)
    return Y

def Y_785(x):
    A0 = 5.90134423e-1
    A = 5.52032185e-1
    B = 5.72123096e-7
    x0 = 2.65628776e+3
    Y = A0 + A * np.exp(-B * (x - x0)**2)
    return Y

def load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],
             filter_filename=r'^(LED|NIR)',filter_probe="Probe"):
    led_spectra={}
    for subset in folder_path_led:
        print(subset)
        for filename in os.listdir(os.path.join(root_led,subset)):
            if filename.endswith('.xlsx'): 
                continue
            if re.match(filter_filename, filename):
                print(filename)
                if not filter_probe in filename:
                    continue
                result = re.split(r'[_().]+', filename)
                result = [s for s in result if s]            
         
                spe_led = rc2.spectrum.from_local_file(os.path.join(root_led,subset,filename))
                spe_led_y = spe_led.y
                spe_led_y[spe_led_y < 0] = 0
                spe_led.y = spe_led_y
                led_spectra[subset]=spe_led
    return led_spectra
led_spectra = load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],filter_filename=r'^(LED|NIR)',filter_probe="Probe")
led_spectra.keys()
assert bool(led_spectra), "No led spectra!"


match_led={
    files_spectra_reference : files_led_reference,
    files_spectra_twinned: files_led_twinned
}
match_led



def intensity_normalization(row):
    try:
        subset=row["device"]
        spe_led = led_spectra[match_led[subset]]
        Y = Y_785(spe_led.x)

        spe = row["spectrum_baseline"]        
        spe_y = spe.y
        spe_y[spe_y < 0] = 0
        print(subset,row["laser_power_percent"],len(spe.x),len(spe_led.x))
        spe_corrected = Y*spe_y/spe_led.y
        return rc2.spectrum.Spectrum(spe.x, spe_corrected)
    except Exception as err:
        print(err)
        return None


devices_h5file= upstream["load_spectra"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition, "spectrum_corrected"] = devices.loc[twinned_condition].apply(intensity_normalization,axis=1)
devices.to_hdf(devices_h5file, key='devices', mode='w')

reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition, "spectrum_corrected"] = devices.loc[reference_condition].apply(intensity_normalization,axis=1)
devices.to_hdf(devices_h5file, key='devices', mode='w')

print(devices.columns)
# Assert that the DataFrame contains the expected columns
assert set(["spectrum_corrected"]).issubset(devices.columns), "a processed spectrum column is missing"

