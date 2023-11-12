# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
input_file = None
prominence_coeff = 10   # > 10 according to CWA, ideally >100
# -

import os.path
from ramanchada2.spectrum import from_chada,from_local_file
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from ramanchada2.protocols.calibration import CalibrationModel


Path(product["data"]).mkdir(parents=True, exist_ok=True)

noise_factor = 1.5
neon_wl = {
    785: rc2const.neon_wl_785_nist_dict,
    633: rc2const.neon_wl_633_nist_dict,
    532: rc2const.neon_wl_532_nist_dict
}
dataset_to_process = "/baseline"

path_source = upstream["calibration_load"]["data"]



import numpy as np


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

def peaks(spe_nCal_calib, prominence, profile='Gaussian',wlen=300, width=1):
    cand = spe_nCal_calib.find_peak_multipeak(prominence=prominence, wlen=wlen, width=width)
    init_guess = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand, no_fit=True)
    fit_res = spe_nCal_calib.fit_peak_multimodel(profile=profile, candidates=cand)
    return cand, init_guess, fit_res

#start


calmodel = CalibrationModel(laser_wl)

spe = {}

for _tag in ["neon","sil"]:
    filename = os.path.join(path_source,"{}_{}.cha".format(_tag,laser_wl))
    spe[_tag] = from_chada(filename, dataset=dataset_to_process)


spe_neon = spe["neon"]
#Gaussian


model_neon = calmodel.derive_model_x(spe_neon,neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={},should_fit = False,name="Neon calibration")
#interp, model_units, df = calibration_model_x(laser_wl,spe_neon,ref=neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={"profile":"Gaussian"},should_fit = False)

model_neon.peaks.to_csv(os.path.join(product["data"],"matched_peaks_"+spe_neon.meta["Original file"]+".csv"),index=False)
model_neon.peaks 

#spe_neon_calib = apply_calibration(laser_wl,spe_neon,interp,0,spe_units="cm-1",model_units=model_units)
spe_neon_calib = model_neon.process(spe_neon,spe_units="cm-1",convert_back=False)
fig, ax = plt.subplots(2,1,figsize=(12,4))
spe_neon.plot(ax=ax[0],label='original')
spe_neon_calib.plot(ax=ax[1],color='r',label='calibrated',fmt=':')


spe_sil = spe["sil"]
spe_sil_ne_calib = model_neon.process(spe_sil,spe_units="cm-1",convert_back=False)
fig, ax = plt.subplots(2,1,figsize=(12,4))
spe_sil.plot(ax=ax[0],label='original')
spe_sil_ne_calib.plot(ax=ax[1],color='r',label='calibrated ',fmt=':')

#"profile":"Pearson4" by D3.3, default is gaussian!
#offset_sil, model_units_sil, df_sil = calibration_model_x(laser_wl,spe_sil_ne_calib,ref={520.45:1},spe_units="cm-1",ref_units="cm-1",find_kw={},fit_peaks_kw={},should_fit=True)
find_kw = {"prominence" :spe_sil_ne_calib.y_noise * prominence_coeff , "wlen" : 200, "width" :  1 }
model_si = calmodel.derive_model_shift(spe_sil_ne_calib,ref={520.45:1},spe_units="nm",ref_units="cm-1",find_kw=find_kw,fit_peaks_kw={},should_fit=True,name="Si calibration")

model_si.peaks.to_csv(os.path.join(product["data"],"matched_peaks_"+spe_sil.meta["Original file"]+".csv"),index=False)
model_si.peaks

spe_sil_calib = model_si.process(spe_sil_ne_calib,spe_units="nm",convert_back=False)

fig, ax =plt.subplots(3,1,figsize=(12,4))
spe_sil.plot(ax=ax[0],label="sil original")
spe_sil_ne_calib.plot(ax = ax[1],label="sil ne calibrated",fmt=":")
spe_sil_calib.plot(ax = ax[0],label="sil calibrated",fmt=":")
spe_sil.plot(label="sil original",ax=ax[2])
spe_sil_calib.plot(ax = ax[2],label="sil calibrated",fmt=":")
ax[2].set_xlim(520.45-100,520.45+100)

# apply

spe_to_calibrate = from_local_file(input_file)
spe_to_calibrate.plot()
if min(spe_to_calibrate.x)<0:
    spe_to_calibrate = spe_to_calibrate.trim_axes(method='x-axis',boundaries=(0,max(spe_to_calibrate.x)))     
kwargs = {"niter" : 40 }
spe_to_calibrate = spe_to_calibrate.subtract_baseline_rc1_snip(**kwargs)
#spe_to_calibrate = spe_to_calibrate - spe_to_calibrate.moving_minimum(120)
#spe_to_calibrate = spe_to_calibrate.normalize()    
spe_to_calibrate.plot(label="moving min")  


spe_calibrated_ne_sil = calmodel.apply_calibration_x(spe_to_calibrate,spe_units="cm-1")

fig, ax = plt.subplots(1,1,figsize=(12,2))
spe_to_calibrate.plot(ax=ax,label = "original")
#spe_calibrated_ne.plot(ax=ax,label="Si calibrated",fmt=":")
spe_calibrated_ne_sil.plot(ax=ax,label="Ne+Si calibrated",fmt=":")


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

cand, init_guess, fit_res = peaks(spe_calibrated_ne_sil,prominence = spe_calibrated_ne_sil.y_noise*prominence_coeff,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand, init_guess, fit_res]
for data, subplot in zip(data_list, ax):
    spe_calibrated_ne_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

#original spectrum to be calibrated
cand_0, init_guess_0, fit_res_0 = peaks(spe_to_calibrate,prominence = spe_to_calibrate.y_noise*prominence_coeff,profile=profile,wlen=wlen,width=width)
fig, ax = plt.subplots(3,1,figsize=(12, 4))
data_list = [cand_0, init_guess_0, fit_res_0 ]
for data, subplot in zip(data_list, ax):
    spe_calibrated_ne_sil.plot(ax=subplot, fmt=':')
    data.plot(ax=subplot)

df_peaks = fit_res.to_dataframe_peaks()
df_peaks["Original file"] = spe_to_calibrate.meta["Original file"]
df_peaks[['group', 'peak']] = df_peaks.index.to_series().str.split('_', expand=True)
df_peaks["param_profile"] = profile
df_peaks["param_wlen"] = wlen
df_peaks["param_width"] = width
df_peaks["param_prominence"] = spe_calibrated_ne_sil.y_noise*prominence_coeff
df_peaks.to_csv(os.path.join(product["data"],spe_to_calibrate.meta["Original file"]+".csv"))

from ramanchada2.misc import utils as rc2utils

sample = "PST"
if sample=="PST":
    pst = rc2const.PST_RS_dict
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_calibrated_ne_sil ,label="calibrated")      
    plot_peaks_stem(pst.keys(), pst.values(),df_peaks["center"], df_peaks["height"] , spe_to_calibrate , label="original")        

    x_sample,x_reference,x_distance,df = rc2utils.match_peaks(cand_0.get_pos_ampl_dict(),pst)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    print("original sum of diff",sum_of_differences,"original sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))    
    x_sample,x_reference,x_distance,df = rc2utils.match_peaks(cand.get_pos_ampl_dict(),pst)
    sum_of_differences = np.sum(np.abs(x_sample - x_reference)) / len(x_sample)
    sum_of_distances = np.sum(x_distance) / len(x_sample)
    print("calibrated sum of diff",sum_of_differences,"calibrated sum of distances",sum_of_distances,len(x_sample),list(zip(x_sample,x_reference)))

