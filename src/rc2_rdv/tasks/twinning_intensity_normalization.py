# + tags=["parameters"]
upstream = ["twinning_normalize","load_leds"]
product = None
files_led_reference: None
files_led_twinned: None
files_spectra_reference: None
files_spectra_twinned: None
probe: None
wavelength: None
moving_minimum_window: 10
spectrum_to_correct: None
spectrum_corrected_column: None

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

def Y(x,wavelength=785):
    if wavelength==785:
        return Y_785(x)
    elif wavelength==532:
        return Y_532(x)
    else:
        raise Exception("not supported wavelength {}".format(wavelength))


match_led={
    files_spectra_reference : files_led_reference,
    files_spectra_twinned: files_led_twinned
}
match_led


def intensity_normalization(row):
    try:

        ##    _x=  np.arange(0,300,0.1)
        #spe_sampled= rc2.spectrum.Spectrum(_x,spe_dist.pdf(_x)*area)
        spe = row[spectrum_to_correct]        
        spe_y = spe.y
        spe_y[spe_y < 0] = 0
        _Y = Y(spe.x,wavelength)

        subset=row["device"]
        #spe_led = led_spectra[match_led[subset]]["spectrum"]
        #spe_dist = led_spectra[match_led[subset]]["spe_dist"]
        #area = led_spectra[match_led[subset]]["area"]
        led_row = led_frame.loc[match_led[subset]]
        spe_led = led_row["spectrum"]
        spe_dist = led_row["spe_dist"]
        area = led_row["area"]

        spe_led_sampled= spe_dist.pdf(spe.x)*area
        #print(subset,row["laser_power_percent"],len(spe.x),len(spe_led.x),spe.x==spe_led.x)
        #spe_corrected = Y*spe_y/spe_led.y
        spe_corrected = _Y*spe_y/spe_led_sampled
        # Assuming _Y, spe_y, and spe_led_sampled are NumPy arrays
        mask = (spe_led_sampled == 0)
        spe_corrected[mask] = 0
        return rc2.spectrum.Spectrum(spe.x, spe_corrected)
    except Exception as err:
        print(err)
        return None

def baseline_spectra(spe,window=moving_minimum_window):
    return spe - spe.moving_minimum(window)

devices_h5file= upstream["twinning_normalize"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices_h5file= product["data"]
devices.head()

led_frame = pd.read_hdf(upstream["load_leds"]["data"], "led")

baseline_column = "{}_baseline".format(spectrum_corrected_column)
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition, spectrum_corrected_column] = devices.loc[twinned_condition].apply(intensity_normalization,axis=1)
devices.loc[twinned_condition, baseline_column] = devices.loc[twinned_condition]["spectrum_corrected"].apply(baseline_spectra)
devices.to_hdf(devices_h5file, key='devices', mode='w')

reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition, spectrum_corrected_column] = devices.loc[reference_condition].apply(intensity_normalization,axis=1)
devices.loc[reference_condition, baseline_column] = devices.loc[reference_condition][spectrum_corrected_column].apply(baseline_spectra)
devices.to_hdf(devices_h5file, key='devices', mode='w')

led_frame.to_hdf(devices_h5file, key='led', mode='a')

print(devices.columns)
# Assert that the DataFrame contains the expected columns
assert set([spectrum_corrected_column]).issubset(devices.columns), "a processed spectrum column is missing"

