# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
# -

import os.path
from ramanchada2.spectrum import from_chada, Spectrum
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt


neon_wl = {
    785: rc2const.neon_wl_785_nist_dict,
    633: rc2const.neon_wl_633_nist_dict,
    532: rc2const.neon_wl_532_nist_dict
}
dataset_to_process = "/baseline"

path_source = upstream["calibration_load"]["data"]


from sklearn.cluster import KMeans
import numpy as np
import pandas as pd
from scipy import interpolate

def match_peaks(df):
    grouped = df.groupby('Cluster')
    x_spe = np.array([])
    x_reference = np.array([])
    clusters = np.array([])

    # Iterate through each group
    for cluster, group in grouped:
        # Get the unique sources within the group
        unique_sources = group['Source'].unique()
        
        # Check if both 'dict1' and 'dict2' are present in the sources
        if 'reference' in unique_sources and 'spe' in unique_sources:
            #print(f"Cluster {cluster} (Contains items from both dictionaries):")
            # Pivot the DataFrame to create the desired structure
            #print(group)
            for w_spe in group.loc[group["Source"]=="spe"]["Wavelength"].values:
                for w_ref in group.loc[group["Source"]=="reference"]["Wavelength"].values:
                    x_spe = np.append(x_spe, w_spe)
                    x_reference = np.append(x_reference, w_ref)
                    clusters = np.append(clusters, cluster)
                    break
    return (x_spe,x_reference)


def calibrate(spe,ref,find_kw={}):
    min_value = min(ref.values())
    max_value = max(ref.values())
    
    # Normalize the values and store them in a new dictionary
    normalized_ref = {key: (value - min_value) / (max_value - min_value) for key, value in ref.items()}
        
    fig, ax = plt.subplots(1,1,figsize=(12,2))
    spe_pos_dict = spe.find_peak_multipeak(**find_kw).get_pos_ampl_dict()  # type: ignore
    ax.stem(spe_pos_dict.keys(),spe_pos_dict.values(),linefmt='b-', basefmt=' ')
    ax.twinx().stem(ref.keys(),ref.values(),linefmt='r-', basefmt=' ')
    
    data_list = [
        {'Wavelength': key, 'Intensity': value, 'Source': 'spe'} for key, value in spe_pos_dict.items()
    ] + [
        {'Wavelength': key, 'Intensity': value, 'Source': 'reference'} for key, value in normalized_ref.items()
    ]

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(data_list)
    feature_matrix = df[['Wavelength', 'Intensity']].to_numpy()
    kmeans = KMeans(n_clusters=len(ref.keys()))
    kmeans.fit(feature_matrix)
    labels = kmeans.labels_
    # Extract cluster labels, x values, and y values
    df['Cluster'] = labels
    x_spe,x_reference = match_peaks(df)
    interp = interpolate.RBFInterpolator(x_spe.reshape(-1, 1),x_reference)
    plt.figure()
    plt.scatter(x_spe,x_reference,marker='o')
    new_x = interp(spe.x.reshape(-1, 1))
    spe_calib = spe.__copy__() 
    spe_calib.x = new_x    
    return (spe_calib, interp, df)


spe = {}

for _tag in ["neon","sil"]:
    filename = os.path.join(path_source,"{}_{}.cha".format(_tag,laser_wl))
    spe[_tag] = from_chada(filename, dataset=dataset_to_process)


spe_neon = spe["neon"]
spe_neon_wl = spe_neon.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)


spe_neon_wl_calib, interp, df = calibrate(spe_neon_wl,ref=neon_wl[laser_wl])

spe_neon_calib = spe_neon_wl_calib.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)


fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_neon.plot(ax=ax,label='original')
spe_neon_calib.plot(ax=ax.twinx(),color='r',label='calibrated')
