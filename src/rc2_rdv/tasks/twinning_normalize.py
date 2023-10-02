# + tags=["parameters"]
upstream = ["load_spectra"]
product = None
root_data_folder: None
probe: None
# -

import pandas as pd
import matplotlib.pyplot as plt

def score_laserpower(reference,twinned):
    # Merge the two DataFrames on "laser_power_percent"
    merged_df = twinned.merge(reference, on="laser_power_percent", suffixes=('', '_ref'))
    # Calculate the score and assign it to the "score" column
    merged_df['score'] = merged_df['laser_power_ref'] / merged_df['laser_power']
    # Update the original "twinned" DataFrame with the calculated scores
    #display(merged_df)
    return merged_df['score'].values

def baseline_spectra(spe,window=32):
    #spe =  row["spectrum_normalized"]
    return spe - spe.moving_minimum(window)

def normalize_spectra(row):
    return row["spectrum"] / row["score"]

devices_h5file= upstream["load_spectra"]["data"]
devices = pd.read_hdf(devices_h5file, "devices")
devices.head()

def calculate_twinned_score(devices,twinned_condition):
    for group, group_df in devices.loc[devices["reference"]].groupby(['device', 'instrument', 'probe']):
        probe = group[2]
        #print("-{}-".format(probe))
        twinned = devices.loc[twinned_condition]
        score = score_laserpower(group_df,twinned)
        devices.loc[twinned_condition,"score"] = score
        #get_slope(group_df,twinned)

#score for the referencespectra
devices.loc[devices["reference"],"score"]  =1.0
#score for twinned spectra
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
calculate_twinned_score(devices,twinned_condition)

print(devices.columns)
# Assert that the DataFrame contains the expected columns
assert set(["score"]).issubset(devices.columns), "score column is missing"

#normalisation
devices["spectrum_baseline"] = devices["spectrum"].apply(baseline_spectra)
twinned_condition = (~devices["reference"]) & pd.notna(devices["score"])
devices.loc[twinned_condition, "spectrum_normalized"] = devices.loc[twinned_condition].apply(normalize_spectra, axis=1)
devices.loc[twinned_condition, "spectrum_baseline"] = devices.loc[twinned_condition]["spectrum_normalized"].apply(baseline_spectra)

print(devices.columns)
# Assert that the DataFrame contains the expected columns
assert set(["spectrum_baseline","spectrum_normalized"]).issubset(devices.columns), "a processed spectrum column is missing"

devices.to_hdf(product["data"], key='devices', mode='w')


def plot_spectra(row):
    try:
        row["spectrum"].plot(ax=axes[0],label=row["laser_power_percent"])
    except:
        pass
    try:
        row["spectrum_normalized"].plot(ax=axes[1],label=row["laser_power_percent"])
    except:
        pass
    try:
        row["spectrum_baseline"].plot(ax=axes[2],label=row["laser_power_percent"])
    except:
        pass
    try:
        row["spectrum_corrected"].plot(ax=axes[2],label=row["laser_power_percent"])
    except:
        pass    
    axes[0].set_title("{} {}".format(row["device"],row["probe"]))
    
fig, axes = plt.subplots(1, 3, figsize=(15, 2))      
axes[1].set_title("normalized")
axes[2].set_title("normalized + baseline")
twinned_condition = (~devices["reference"]) & (devices["probe"] == probe)
devices.loc[twinned_condition].apply(plot_spectra, axis=1)

fig, axes = plt.subplots(1, 3, figsize=(15, 2))  
axes[1].set_title("normalized")
axes[2].set_title("baseline")
reference_condition = (devices["reference"]) & (devices["probe"] == probe)
devices.loc[reference_condition].apply(plot_spectra, axis=1)