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
import numpy as np

devices_h5file= upstream["twinning_peaks"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

processing = pd.read_hdf(devices_h5file, "processing")
processing.head()

regression = pd.read_hdf(devices_h5file, "regression")
factor_correction = pd.read_hdf(devices_h5file, "factor_correction")
regression,factor_correction

print(factor_correction.iloc[0,0])

leds_h5file= upstream["load_leds"]["data"]
leds = pd.read_hdf(leds_h5file, "led")
leds.head()

match_led = pd.read_hdf(leds_h5file, "match")
match_led.head()

    
print(processing.index,processing["field"])
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

fig, axes = plt.subplots(1,2, figsize=(10,4)) 
axes[0].plot(A["laser_power"],A["amplitude"],'o',label=A["device"].unique())
axes[0].plot(B["laser_power"],B["amplitude"],'+',label=B["device"].unique())
axes[0].legend()
bar_width = 0.2  # Adjust this value to control the width of the groups
bar_positions = np.arange(len(A["laser_power_percent"].values))
axes[1].bar(bar_positions -bar_width,A["area"], width=bar_width,label=str(A["device"].unique()))
bar_positions = np.arange(len(B["laser_power_percent"].values))
axes[1].bar(bar_positions  ,B["area"],width=bar_width,label=str(B["device"].unique()))
axes[1].bar(bar_positions + bar_width,B["area_harmonized"],width=bar_width,label="{} harmonized".format(B["device"].unique()))
# Set the x-axis positions and labels
plt.xticks(bar_positions, bar_positions)
axes[1].legend()
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