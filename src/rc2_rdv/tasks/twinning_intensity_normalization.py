# + tags=["parameters"]
upstream = ["twinning_normalize"]
product = None
root_data_folder: None
files_led_reference: None
files_led_twinned: None
files_spectra_reference: None
files_spectra_twinned: None
probe: None
wavelength: None
moving_minimum_window: 10

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

tags = { '785nm':"wavelength", 
        '532nm':"wavelength", 
        '785':"wavelength", 
        '532':"wavelength", 
          '150ms' : "acquisition_time",
          'Probe': "probe", 
          '1': "replicate",
          '2': "replicate",
          '3': "replicate",
          '4': "replicate",
         '5': "replicate",
         'txt' : "extension"}
from fuzzywuzzy import fuzz


def fuzzy_match(vals,tags):
    parsed = {}
    parsed_similarity= {}
    for val in vals:
        similarity_score = None
        match = None
        for tag in tags:
            _tmp = fuzz.ratio(val,tag)
            if (similarity_score is None) or (similarity_score < _tmp):
                similarity_score =_tmp
                match = tags[tag]
        if not match in parsed:
            parsed[match]  = val
            parsed_similarity[match] = similarity_score
        else:
            if parsed_similarity[match] < similarity_score:
                parsed[match]  = val
                parsed_similarity[match] = similarity_score        
    if "wavelength" in parsed:
         parsed["wavelength"] = re.findall(r'\d+', parsed["wavelength"])[0]
    if "extension" in parsed:
        del parsed["extension"]            
    return (parsed,parsed_similarity)

#fuzzy_match(['LED785nm', 'Probe', '250ms', '10x', '1', 'txt'],tags)


match_led={
    files_spectra_reference : files_led_reference,
    files_spectra_twinned: files_led_twinned
}
match_led

def spe_area(spe: rc2.spectrum.Spectrum):
    return np.sum(spe.y * np.diff(spe.x_bin_boundaries))

def load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],
             filter_filename=r'^(LED|NIR)',filter_probe="Probe"):
    led_spectra={ }
    for subset in folder_path_led:
        print(subset)
        for filename in os.listdir(os.path.join(root_led,subset)):
            if filename.endswith('.xlsx'): 
                continue
            if re.match(filter_filename, filename):
                #print(filename)
                if not filter_probe in filename:
                    continue
                result = re.split(r'[_().]+', filename)
                result = [s for s in result if s]            
                #print(fuzzy_match(result,tags))
                spe_led = rc2.spectrum.from_local_file(os.path.join(root_led,subset,filename))
                spe_led_y = spe_led.y
                spe_led_y[spe_led_y < 0] = 0
                spe_led.y = spe_led_y
                led_spectra[subset]= fuzzy_match(result,tags)[0]
                led_spectra[subset]["spectrum"] = spe_led;
                led_spectra[subset]["spe_dist"] = spe_led.spe_distribution()
                led_spectra[subset]["area"] =   spe_area(spe_led)
    return led_spectra




def intensity_normalization(row):
    try:

        ##    _x=  np.arange(0,300,0.1)
        #spe_sampled= rc2.spectrum.Spectrum(_x,spe_dist.pdf(_x)*area)
        spe = row["spectrum_normalized"]        
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
    #spe =  row["spectrum_normalized"]
    return spe - spe.moving_minimum(window)

devices_h5file= upstream["twinning_normalize"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices_h5file= product["data"]
devices.head()

led_spectra = load_led(root_led=root_data_folder,folder_path_led=[files_led_reference,files_led_twinned],filter_filename=r'^(LED|NIR)',filter_probe="Probe")
for key in led_spectra.keys():
    print(led_spectra[key])
assert bool(led_spectra), "No led spectra!"
led_frame = pd.DataFrame(led_spectra).T
led_frame.to_hdf(devices_h5file, key='led', mode='w')


twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition, "spectrum_corrected"] = devices.loc[twinned_condition].apply(intensity_normalization,axis=1)
devices.loc[twinned_condition, "spectrum_baseline"] = devices.loc[twinned_condition]["spectrum_corrected"].apply(baseline_spectra)
devices.to_hdf(devices_h5file, key='devices', mode='a')

reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition, "spectrum_corrected"] = devices.loc[reference_condition].apply(intensity_normalization,axis=1)
devices.loc[reference_condition, "spectrum_baseline"] = devices.loc[reference_condition]["spectrum_corrected"].apply(baseline_spectra)
devices.to_hdf(devices_h5file, key='devices', mode='a')

print(devices.columns)
# Assert that the DataFrame contains the expected columns
assert set(["spectrum_corrected"]).issubset(devices.columns), "a processed spectrum column is missing"



for led in led_spectra:
    fig, axes = plt.subplots(1, 3, figsize=(15, 2))   
    spe_led = led_spectra[led]["spectrum"]   
    spe_led.plot(label=led,ax=axes[0])
    area = led_spectra[led]["area"]
    spe_dist = led_spectra[led]["spe_dist"]
    axes[1].plot(spe_led.x,spe_dist.pdf(spe_led.x))
    axes[2].plot(spe_led.x,spe_dist.pdf(spe_led.x)*area)