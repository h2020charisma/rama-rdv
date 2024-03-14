# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
input_file = None
prominence_coeff = 10   # > 10 according to CWA, ideally >100
# -

import os.path
from ramanchada2.spectrum import from_chada
import ramanchada2.misc.constants  as rc2const
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from ramanchada2.protocols.calibration import CalibrationModel
import ramanchada2.misc.utils as rc2utils

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
calmodel.prominence_coeff = prominence_coeff

spe = {}

for _tag in ["neon","sil"]:
    filename = os.path.join(path_source,"{}_{}.cha".format(_tag,laser_wl))
    spe[_tag] = from_chada(filename, dataset=dataset_to_process)


spe_neon = spe["neon"]
#Gaussian


model_neon = calmodel.derive_model_curve(spe_neon,neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={},should_fit = False,name="Neon calibration")
#interp, model_units, df = calibration_model_x(laser_wl,spe_neon,ref=neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={"profile":"Gaussian"},should_fit = False)
print(model_neon)

model_neon.peaks.to_csv(os.path.join(product["data"],"matched_peaks_"+spe_neon.meta["Original file"]+".csv"),index=False)
model_neon.peaks.head()

#spe_neon_calib = apply_calibration(laser_wl,spe_neon,interp,0,spe_units="cm-1",model_units=model_units)
spe_neon_calib = model_neon.process(spe_neon,spe_units="cm-1",convert_back=False)
fig, ax = plt.subplots(2,1,figsize=(12,4))
spe_neon.plot(ax=ax[0],label='original')
spe_neon_calib.plot(ax=ax[1],color='r',label='calibrated',fmt=':')

#now lazer zeroing

spe_sil = spe["sil"]
spe_sil_ne_calib = model_neon.process(spe_sil,spe_units="cm-1",convert_back=False)
# x axis should be in nm
fig, ax = plt.subplots(2,1,figsize=(12,4))
spe_sil.plot(ax=ax[0],label='original')
spe_sil_ne_calib.plot(ax=ax[1],color='r',label='Ne calibrated',fmt=':')

#"profile":"Pearson4" by D3.3, default is gaussian!
#offset_sil, model_units_sil, df_sil = calibration_model_x(laser_wl,spe_sil_ne_calib,ref={520.45:1},spe_units="cm-1",ref_units="cm-1",find_kw={},fit_peaks_kw={},should_fit=True)
find_kw = {"prominence" :spe_sil_ne_calib.y_noise * calmodel.prominence_coeff , "wlen" : 200, "width" :  1 }
model_si = calmodel.derive_model_zero(spe_sil_ne_calib,ref={520.45:1},spe_units="nm",ref_units="cm-1",find_kw=find_kw,fit_peaks_kw={},should_fit=True,name="Si calibration")
print("model_si",model_si)

model_si.peaks.to_csv(os.path.join(product["data"],"peaks_"+spe_sil.meta["Original file"]+".csv"),index=False)
model_si.peaks.head()

spe_sil_calib = model_si.process(spe_sil_ne_calib,spe_units="nm",convert_back=False)


fig, ax =plt.subplots(3,1,figsize=(12,4))
spe_sil.plot(ax=ax[0],label="sil original")
spe_sil_ne_calib.plot(ax = ax[1],label="sil ne calibrated",fmt=":")
spe_sil_calib.plot(ax = ax[0],label="sil zeroed",fmt=":")
spe_sil.plot(label="sil original",ax=ax[2])
spe_sil_calib.plot(ax = ax[2],label="sil zeroed",fmt=":")
ax[2].set_xlim(520.45-50,520.45+50)

#check what we have done
find_kw = dict(sharpening=None)
for spe in [spe_sil,spe_sil_calib]:
    spe_pos_dict = spe.fit_peak_positions(center_err_threshold=10, 
                                find_peaks_kw=find_kw,  fit_peaks_kw={})  # type: ignore 
    x_spe,x_reference,x_distance,df = rc2utils.match_peaks(spe_pos_dict, model_si.ref)
    sum_of_differences = np.sum(np.abs(x_spe - x_reference)) / len(x_spe)
    print("sum_of_differences {} {}".format(sum_of_differences, model_si.ref_units))
    print(list(zip(x_spe,x_reference)))

# calmodel save

calmodel.save(product["model"])
