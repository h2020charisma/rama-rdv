# + tags=["parameters"]
upstream = ["twinning_peaks","load_leds"]
product = None
probe: None
spectrum_corrected_column: None

# -

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from tasks.utils import plot_spectra

devices_h5file= upstream["twinning_peaks"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

regression = pd.read_hdf(devices_h5file, "regression")
factor_correction = pd.read_hdf(devices_h5file, "factor_correction")
regression,factor_correction

print(factor_correction.iloc[0,0])

leds_h5file= upstream["load_leds"]["data"]
leds = pd.read_hdf(leds_h5file, "led")
leds.head()

match_led = pd.read_hdf(leds_h5file, "match")
match_led.head()

    
fig, axes = plt.subplots(8,2, figsize=(14,14))  
cmap = plt.get_cmap('plasma')
norm = mcolors.Normalize(vmin=0, vmax=100)
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
A=devices.loc[reference_condition].sort_values(by='laser_power_percent')
A.apply(lambda row: plot_spectra(row,axes, 0, True,match_led,leds,cmap,norm), axis=1)
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
B =devices.loc[twinned_condition].sort_values(by='laser_power_percent')
B.apply(lambda row: plot_spectra(row,axes, 1,False,match_led,leds,cmap,norm,fc=factor_correction.iloc[0,0]), axis=1)
plt.tight_layout()

A

B

for index, led_spectra in leds.iterrows():
    fig, axes = plt.subplots(1, 3, figsize=(15, 2))   
    spe_led = led_spectra["spectrum"]   
    spe_led.plot(label=index,ax=axes[0])
    area = led_spectra["area"]
    spe_dist = led_spectra["spe_dist"]
    axes[1].plot(spe_led.x,spe_dist.pdf(spe_led.x))
    axes[2].plot(spe_led.x,spe_dist.pdf(spe_led.x)*area)