# + tags=["parameters"]
upstream = ["load_spectra","twinning_normalize","twinning_intensity_normalization"]
product = None
probe: None
# -

import pandas as pd
import matplotlib.pyplot as plt


devices_h5file= upstream["load_spectra"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()


def plot_spectra(row):
    try:
        row["spectrum"].plot(ax=axes[0],label="{}%".format(row["laser_power_percent"]))
    except:
        pass
    try:
        row["spectrum_normalized"].plot(ax=axes[1],label="{}%".format(row["laser_power_percent"]))
    except:
        pass
    try:
        row["spectrum_baseline"].plot(ax=axes[2],label="{}%".format(row["laser_power_percent"]))
    except:
        pass
    try:
        sc =row["spectrum_corrected"]
        sc = sc.trim_axes(method='x-axis', boundaries=(60, 300))
        sc.plot(ax=axes[3],label="{}%".format(row["laser_power_percent"]))
    except:
        pass    
    axes[0].set_title("{} {}".format(row["device"],row["probe"]))
    
fig, axes = plt.subplots(1, 4, figsize=(15, 2))      
axes[1].set_title("normalized")
axes[2].set_title("normalized + baseline")
axes[3].set_title("LED corrected")
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition].apply(plot_spectra, axis=1)

fig, axes = plt.subplots(1, 4, figsize=(15, 2))  
axes[1].set_title("normalized")
axes[2].set_title("baseline")
axes[3].set_title("LED corrected")
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition].apply(plot_spectra, axis=1)