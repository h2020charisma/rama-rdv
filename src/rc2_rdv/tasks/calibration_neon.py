# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
input_file = None
# -

import os.path
from ramanchada2.spectrum import from_chada,from_local_file, Spectrum
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import euclidean_distances
from matplotlib.lines import Line2D


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

def apply_calibration(spe,spe_calib ):
    try:
        assert len(spe.x) == len(spe_calib.x), ("x should have same resolution {} vs {}".format(len(spe.x),len(spe_calib.x)))
        assert min(spe.x) == min(spe_calib.x), ("x should have same start value {} vs {}".format(min(spe.x),min(spe_calib.x)))
        assert max(spe.x) == max(spe_calib.x), ("x should have same end value {} vs {}".format(max(spe.x),max(spe_calib.x)))
        spe = spe.__copy__()       
    except Exception as err:
        _left = min(spe_calib.x) 
        _right = max(spe_calib.x)
        spe =  spe.resample_NUDFT_filter(x_range=(_left,_right), xnew_bins=len(spe_calib.x))
    spe.x = spe_calib.x
    return spe
    

def match_peaks(df):
    grouped = df.groupby('Cluster')
    x_spe = np.array([])
    x_reference = np.array([])
    x_distance = np.array([])
    clusters = np.array([])

    # Iterate through each group
    for cluster, group in grouped:
        # Get the unique sources within the group
        unique_sources = group['Source'].unique()
        #print(group)
        # Check if both 'dict1' and 'dict2' are present in the sources
        if 'reference' in unique_sources and 'spe' in unique_sources:
            #print(f"Cluster {cluster} (Contains items from both dictionaries):")
            # Pivot the DataFrame to create the desired structure
            for w_spe in group.loc[group["Source"]=="spe"]["Wavelength"].values:    
                x = None
                r = None
                e_min = None
                for w_ref in group.loc[group["Source"]=="reference"]["Wavelength"].values:               
                    e = euclidean_distances(w_spe.reshape(-1, 1), w_ref.reshape(-1, 1))[0][0]
                    if (e_min is None) or (e<e_min):
                        x = w_spe
                        r = w_ref
                        e_min = e
                x_spe = np.append(x_spe, x)
                x_reference = np.append(x_reference, r)
                x_distance = np.append(x_distance,e_min)
                clusters = np.append(clusters, cluster)
        #group by spe and get min distance o
    return (x_spe,x_reference,x_distance)


def calibrate(spe,ref,find_kw={}):
    print(ref)
    min_value = min(ref.values())
    max_value = max(ref.values())
    find_kw = dict(sharpening=None)
    # Normalize the values and store them in a new dictionary
    if len(ref.keys())>1:
        normalized_ref = {key: (value - min_value) / (max_value - min_value) for key, value in ref.items()}
    else:
        normalized_ref = ref
        
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

    n_ref = len(ref.keys())
    n_spe = len(spe_pos_dict.keys())
    kmeans = KMeans(n_clusters=n_ref if n_ref>n_spe else n_spe )
    kmeans.fit(feature_matrix)
    labels = kmeans.labels_
    # Extract cluster labels, x values, and y values
    df['Cluster'] = labels
    print(df)
    x_spe,x_reference,x_distance = match_peaks(df)
    print(x_spe,x_reference,x_distance)
    if len(x_reference)==1:
        _offset = ( x_reference[0] - x_spe[0])
        new_x = spe.x + _offset
        spe_calib = spe.__copy__() 
        spe_calib.x = new_x   
        return (spe_calib, _offset , df)
    else:
        plt.figure()
        plt.scatter(x_spe,x_reference,marker='o')
        try:
            kwargs = {"kernel" : "thin_plate_spline"}
            interp = interpolate.RBFInterpolator(x_spe.reshape(-1, 1),x_reference,**kwargs)
            new_x = interp(spe.x.reshape(-1, 1))
            spe_calib = spe.__copy__() 
            spe_calib.x = new_x    
            return (spe_calib, interp, df)
        except Exception as err:
            raise(err)







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
spe_neon_calib.plot(ax=ax,color='r',label='calibrated')

fig, ax =plt.subplots(1,1,figsize=(12,4))
spe_sil = spe["sil"]
spe_sil.plot(label="sil original",ax=ax)
spe_sil_ne_calib = spe_sil.__copy__() 
spe_sil_ne_calib.x = interp(spe_sil.x.reshape(-1, 1))
spe_sil_ne_calib.plot(ax = ax,label="sil ne calibrated")
spe_sil_calib, offset_sil, df_sil = calibrate(spe_sil_ne_calib,ref={520.45:1})
spe_sil_calib.plot(ax = ax,label="sil calibrated")

# apply

spe_to_calibrate = from_local_file(input_file)


if min(spe_to_calibrate.x)<0:
    spe_to_calibrate = spe_to_calibrate.trim_axes(method='x-axis',boundaries=(0,max(spe_to_calibrate.x)))      
spe_to_calibrate = spe_to_calibrate - spe_to_calibrate.moving_minimum(120)
spe_to_calibrate = spe_to_calibrate.normalize()       


spe_calibrated_ne = spe_to_calibrate.__copy__() 
spe_calibrated_ne.x = interp(spe_calibrated_ne.x.reshape(-1, 1))
spe_calibrated_sil = spe_calibrated_ne.__copy__() 
spe_calibrated_sil.x = spe_calibrated_sil.x + offset_sil

fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_to_calibrate.plot(ax=ax,label = "original")
spe_calibrated_ne.plot(ax=ax,label="Si calibrated")
spe_calibrated_sil.plot(ax=ax,label="Ne+Si calibrated")



def peaks(spe_nCal_calib, prominence, profile='Moffat'):
    cand = spe_nCal_calib.find_peak_multipeak(prominence=prominence, wlen=300, width=1)
    init_guess = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand, no_fit=True)
    fit_res = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand)
    return cand, init_guess, fit_res

def plot_peaks_stem(ref_keys,ref_values,spe_keys,spe_values,spe=None, label="calibrated"):
    fig, ax = plt.subplots(figsize=(12, 2))
    pst = rc2const.PST_RS_dict
    ref_stem = ax.stem(pst.keys(), pst.values(), linefmt='b-', label='reference')
    stem_plot = ax.twinx()
    calibrated_stem = stem_plot.stem(spe_keys, spe_values, linefmt='r-', markerfmt='ro', basefmt=' ')
    # Create custom legend elements
    legend_elements = [
        Line2D([0], [0], color='b', linestyle='-', label='reference'),
        Line2D([0], [0], color='r', linestyle='-', marker='o', label='calibrated')
    ]
    ax.legend(handles=legend_elements)
    ax.grid(True)
    if spe != None:
        spe.plot(ax=stem_plot,label=label)
    plt.show()

cand, init_guess, fit_res = peaks(spe_calibrated_sil,prominence = spe_sil_calib.y_noise*10)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand, init_guess, fit_res]
for data, subplot in zip(data_list, ax):
    spe_calibrated_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

df = fit_res.to_dataframe_peaks()
df["Original file"] = spe_to_calibrate.meta["Original file"]
df[['group', 'peak']] = df.index.to_series().str.split('_', expand=True)
#df["profile"] = profile
#df["prominence"] = prominence
#df.to_csv(os.path.join(product["data"],"peaks.csv"))
df

sample = "PST"
if sample=="PST":
    pst = rc2const.PST_RS_dict
    plot_peaks_stem(pst.keys(), pst.values(),df["center"], df["height"] , spe_calibrated_sil ,label="calibrated")      
    plot_peaks_stem(pst.keys(), pst.values(),df["center"], df["height"] , spe_to_calibrate , label="original")        