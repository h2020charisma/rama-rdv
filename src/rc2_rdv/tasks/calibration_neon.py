# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
input_file = None
prominence_coeff = 5
# -

import os.path
from ramanchada2.spectrum import from_chada,from_local_file, Spectrum
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import euclidean_distances
from matplotlib.lines import Line2D
from pathlib import Path
from ramanchada2.spectrum.calibration.calibration_model import apply_calibration as apply_calibration_x


Path(product["data"]).mkdir(parents=True, exist_ok=True)

noise_factor = 1.5
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

def set_x_axis(spe,spe_calib ):
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
    

def match_peaks(spe_pos_dict,ref):
    # Min-Max normalize the reference values
    min_value = min(ref.values())
    max_value = max(ref.values())    
    if len(ref.keys())>1:
        normalized_ref = {key: (value - min_value) / (max_value - min_value) for key, value in ref.items()}
    else:
        normalized_ref = ref

    min_value_spe = min(spe_pos_dict.values())
    max_value_spe = max(spe_pos_dict.values())  
    # Min-Max normalize the spe_pos_dict
    if len(spe_pos_dict.keys()) > 1:
        normalized_spe = {key: (value - min_value_spe) / (max_value_spe - min_value_spe) for key, value in spe_pos_dict.items()}
    else:
        normalized_spe = spe_pos_dict          
    data_list = [
        {'Wavelength': key, 'Intensity': value, 'Source': 'spe'} for key, value in normalized_spe.items()
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
    grouped = df.groupby('Cluster')
    x_spe = np.array([])
    x_reference = np.array([])
    x_distance = np.array([])
    clusters = np.array([])
    # Iterate through each group
    for cluster, group in grouped:
        # Get the unique sources within the group
        unique_sources = group['Source'].unique()
        if 'reference' in unique_sources and 'spe' in unique_sources:
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
    sort_indices = np.argsort(x_spe)        
    return (x_spe[sort_indices],x_reference[sort_indices],x_distance[sort_indices],df)

def apply_calibration(laser_wl,spe, interp=None, offset=0,spe_units="cm-1",model_units="nm"):
    print("apply_calibration laser_wl {} spe ({}) model ({}) interp {} offset {}".format(laser_wl,spe_units,model_units,interp,offset))
    if spe_units==model_units:
        spe_to_calibrate = spe.__copy__()
    else:
        if model_units == "nm":
            spe_to_calibrate = spe.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)     
        else:
            spe_to_calibrate =  spe.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)
    if interp != None:
        spe_to_calibrate.x = interp(spe_to_calibrate.x.reshape(-1, 1)) 
    spe_to_calibrate.x = spe_to_calibrate.x + offset
    #convert back
    if spe_units==model_units:
        return spe_to_calibrate
    else:
        if model_units == "nm":
            return spe_to_calibrate.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)
        else:
            return spe.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)      


def peaks(spe_nCal_calib, prominence, profile='Gaussian',wlen=300, width=1):
    cand = spe_nCal_calib.find_peak_multipeak(prominence=prominence, wlen=wlen, width=width)
    init_guess = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand, no_fit=True)
    fit_res = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand)
    return cand, init_guess, fit_res

def calibration_model_x(laser_wl,spe,ref,spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={},should_fit = False):
    print("calibration_model laser_wl {} spe ({}) reference ({})".format(laser_wl,spe_units,ref_units))
    #convert to ref_units
    spe_to_process = None #spe_to_process.__copy__()
    if ref_units == "nm":
        if spe_units != "nm":
            spe_to_process = spe.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)
    else: #assume cm-1
        if spe_units != "cm-1":
            spe_to_process = spe.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)
    if spe_to_process is None:
       spe_to_process = spe.__copy__() 
    fig, ax = plt.subplots(3,1,figsize=(12,4))
    spe.plot(ax=ax[0].twinx(),label=spe_units)    
    spe_to_process.plot(ax=ax[1],label=ref_units)
    
    #if should_fit:
    #    spe_pos_dict = spe_to_process.fit_peak_positions(center_err_threshold=1, 
    #                        find_peaks_kw=find_kw,  fit_peaks_kw=fit_peaks_kw)  # type: ignore   
    #else:
    #    find_kw = dict(sharpening=None)
    #    spe_pos_dict = spe_to_process.find_peak_multipeak(**find_kw).get_pos_ampl_dict()  # type: ignore
    #prominence=prominence, wlen=wlen, width=width
    find_kw = dict(sharpening=None)
    if should_fit:
        spe_pos_dict = spe_to_process.fit_peak_positions(center_err_threshold=10, 
                            find_peaks_kw=find_kw,  fit_peaks_kw=fit_peaks_kw)  # type: ignore           
        #fit_res = spe_to_process.fit_peak_multimodel(candidates=cand,**fit_peaks_kw)
        #pos, amp = fit_res.center_amplitude(threshold=1)
        #spe_pos_dict = dict(zip(pos, amp))        
    else:
        #prominence=prominence, wlen=wlen, width=width
        cand = spe_to_process.find_peak_multipeak(**find_kw)
        spe_pos_dict = cand.get_pos_ampl_dict()        

    ax[2].stem(spe_pos_dict.keys(),spe_pos_dict.values(),linefmt='b-', basefmt=' ')
    ax[2].twinx().stem(ref.keys(),ref.values(),linefmt='r-', basefmt=' ')
   
    x_spe,x_reference,x_distance,df = match_peaks(spe_pos_dict,ref)
    sum_of_differences = np.sum(np.abs(x_spe - x_reference)) / len(x_spe)
    print("sum_of_differences original {} {}".format(sum_of_differences, ref_units))
    if len(x_reference)==1:
        _offset = ( x_reference[0] - x_spe[0])
        print("ref",x_reference[0],"sample", x_spe[0],"offset", _offset, ref_units)
        return ( _offset ,ref_units, df)
    else:
        fig, ax = plt.subplots(1,1,figsize=(3,3))
        ax.scatter(x_spe,x_reference,marker='o')
        ax.set_xlabel("spectrum x ".format(ref_units))
        ax.set_ylabel("reference x ".format(ref_units))
        try:
            kwargs = {"kernel" : "thin_plate_spline"}
            return (interpolate.RBFInterpolator(x_spe.reshape(-1, 1),x_reference,**kwargs) ,ref_units,  df)
        except Exception as err:
            raise(err)



#start




spe = {}

for _tag in ["neon","sil"]:
    filename = os.path.join(path_source,"{}_{}.cha".format(_tag,laser_wl))
    spe[_tag] = from_chada(filename, dataset=dataset_to_process)


spe_neon = spe["neon"]
#Gaussian
interp, model_units, df = calibration_model_x(laser_wl,spe_neon,ref=neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={"profile":"Gaussian"},should_fit = False)
df.to_csv(os.path.join(product["data"],"matched_peaks_"+spe_neon.meta["Original file"]+".csv"),index=False)
df 

#spe_neon_calib = apply_calibration(laser_wl,spe_neon,interp,0,spe_units="cm-1",model_units=model_units)
spe_neon_calib = apply_calibration_x(spe_neon,laser_wl,interp,0,spe_units="cm-1",model_units=model_units)
fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_neon.plot(ax=ax,label='original')
spe_neon_calib.plot(ax=ax,color='r',label='calibrated',fmt=':')


spe_sil = spe["sil"]
#spe_sil_ne_calib = apply_calibration(laser_wl,spe_sil,interp,0,spe_units="cm-1",model_units=model_units)
spe_sil_ne_calib = apply_calibration_x(spe_sil,laser_wl,interp,0,spe_units="cm-1",model_units=model_units)

#"profile":"Pearson4" by D3.3, default is gaussian!
offset_sil, model_units_sil, df_sil = calibration_model_x(laser_wl,spe_sil_ne_calib,ref={520.45:1},spe_units="cm-1",ref_units="cm-1",find_kw={},fit_peaks_kw={},should_fit=True)
df_sil.to_csv(os.path.join(product["data"],"matched_peaks_"+spe_sil.meta["Original file"]+".csv"),index=False)
df_sil


#spe_sil_calib = apply_calibration(laser_wl,spe_sil_ne_calib,None,offset_sil,spe_units="cm-1",model_units=model_units_sil)
spe_sil_calib = apply_calibration_x(spe_sil_ne_calib,laser_wl,None,offset_sil,spe_units="cm-1",model_units=model_units_sil)

fig, ax =plt.subplots(2,1,figsize=(12,4))
spe_sil.plot(ax=ax[0],label="sil original")
spe_sil_ne_calib.plot(ax = ax[0],label="sil ne calibrated",fmt=":")
spe_sil_calib.plot(ax = ax[0],label="sil calibrated",fmt=":")
spe_sil.plot(label="sil original",ax=ax[1])
spe_sil_ne_calib.plot(ax = ax[1],label="sil ne calibrated",fmt=":")
spe_sil_calib.plot(ax = ax[1],label="sil calibrated",fmt=":")
ax[1].set_xlim(520.45-100,520.45+100)

# apply

spe_to_calibrate = from_local_file(input_file)
if min(spe_to_calibrate.x)<0:
    spe_to_calibrate = spe_to_calibrate.trim_axes(method='x-axis',boundaries=(0,max(spe_to_calibrate.x)))     
kwargs = {"niter" : 40 }
spe_to_calibrate = spe_to_calibrate.subtract_baseline_rc1_snip(**kwargs)
#spe_to_calibrate = spe_to_calibrate - spe_to_calibrate.moving_minimum(120)
#spe_to_calibrate = spe_to_calibrate.normalize()       


#spe_calibrated_ne = apply_calibration(laser_wl,spe_to_calibrate,interp,0,spe_units="cm-1",model_units=model_units)
spe_calibrated_ne = apply_calibration_x(spe_to_calibrate,laser_wl,interp,0,spe_units="cm-1",model_units=model_units)

#spe_calibrated_sil = apply_calibration(laser_wl,spe_calibrated_ne,None,offset_sil,spe_units="cm-1",model_units=model_units_sil)
spe_calibrated_sil = apply_calibration_x(spe_calibrated_ne,laser_wl,None,offset_sil,spe_units="cm-1",model_units=model_units_sil)

fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_to_calibrate.plot(ax=ax,label = "original")
spe_calibrated_ne.plot(ax=ax,label="Si calibrated",fmt=":")
spe_calibrated_sil.plot(ax=ax,label="Ne+Si calibrated",fmt=":")


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

profile = "Voigt"
wlen = 50
width = 3

cand, init_guess, fit_res = peaks(spe_calibrated_sil,prominence = spe_calibrated_sil.y_noise*prominence_coeff,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand, init_guess, fit_res]
for data, subplot in zip(data_list, ax):
    spe_calibrated_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

#original spectrum to be calibrated
cand_0, init_guess_0, fit_res_0 = peaks(spe_to_calibrate,prominence = spe_to_calibrate.y_noise*prominence_coeff,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand_0, init_guess_0, fit_res_0 ]
for data, subplot in zip(data_list, ax):
    spe_calibrated_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

df_peaks = fit_res.to_dataframe_peaks()
df_peaks["Original file"] = spe_to_calibrate.meta["Original file"]
df_peaks[['group', 'peak']] = df_peaks.index.to_series().str.split('_', expand=True)
df_peaks["param_profile"] = profile
df_peaks["param_wlen"] = wlen
df_peaks["param_width"] = width
df_peaks["param_prominence"] = spe_calibrated_sil.y_noise*prominence_coeff
df_peaks.to_csv(os.path.join(product["data"],spe_to_calibrate.meta["Original file"]+".csv"))



sample = "PST"
if sample=="PST":
    pst = rc2const.PST_RS_dict
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_calibrated_sil ,label="calibrated")      
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_to_calibrate , label="original")        

    x_sample,x_reference,x_distance,df = match_peaks(cand_0.get_pos_ampl_dict(),pst)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    print("original sum of diff",sum_of_differences,"original sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))    
    x_sample,x_reference,x_distance,df = match_peaks(cand.get_pos_ampl_dict(),pst)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    print("calibrated sum of diff",sum_of_differences,"calibrated sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))

