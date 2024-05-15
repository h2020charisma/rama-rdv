# + tags=["parameters"]
upstream = ["templates_load","templates_read"]
product = None
config_root = None
neon_tag = None
si_tag = None
pst_tag = None
test_tags = None
# -

import os.path
import glob
import pandas as pd
from ramanchada2.protocols.calibration import CalibrationModel
import ramanchada2.misc.constants  as rc2const
from ramanchada2.spectrum import from_chada
import matplotlib.pyplot as plt
import ramanchada2.misc.utils as rc2utils
import numpy as np
from pathlib import Path

noise_factor = 1.5
neon_wl = {
    785: rc2const.neon_wl_785_nist_dict,
    633: rc2const.neon_wl_633_nist_dict,
    532: rc2const.neon_wl_532_nist_dict
}

def calibrate(op,laser_wl,spe_neon,spe_sil):
    calmodel = CalibrationModel(laser_wl)
    calmodel.prominence_coeff = 3
    model_neon = calmodel.derive_model_curve(spe_neon,neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw={},fit_peaks_kw={},should_fit = False,name="Neon calibration")
    spe_neon_calib = model_neon.process(spe_neon,spe_units="cm-1",convert_back=False)
    spe_sil_ne_calib = model_neon.process(spe_sil,spe_units="cm-1",convert_back=False)
    find_kw = {"prominence" :spe_sil_ne_calib.y_noise * calmodel.prominence_coeff , "wlen" : 200, "width" :  1 }
    model_si = calmodel.derive_model_zero(spe_sil_ne_calib,ref={520.45:1},spe_units="nm",ref_units="cm-1",find_kw=find_kw,fit_peaks_kw={},should_fit=True,name="Si calibration")
    
    Path(os.path.join(product["data"],op)).mkdir(parents=True, exist_ok=True)
    model_si.peaks.to_csv(os.path.join(product["data"],op,"peaks.csv"),index=False)
    #print("model_si",model_si)    
    spe_sil_calib = model_si.process(spe_sil_ne_calib,spe_units="nm",convert_back=False)

    fig, ax =plt.subplots(3,1,figsize=(12,4))
    spe_sil.plot(ax=ax[0],label="sil original")
    spe_sil_ne_calib.plot(ax = ax[1],label="sil ne calibrated",fmt=":")
    spe_sil_calib.plot(ax = ax[0],label="sil zeroed",fmt=":")
    spe_sil.plot(label="sil original",ax=ax[2])
    spe_sil_calib.plot(ax = ax[2],label="sil zeroed",fmt=":")
    ax[2].set_xlim(520.45-50,520.45+50)    
    ax[0].set_title(op)

    find_kw = dict(sharpening=None)
    diff = []
    sname = []
    for spe in [spe_sil,spe_sil_calib]:
        spe_pos_dict = spe.fit_peak_positions(center_err_threshold=10, 
                                    find_peaks_kw=find_kw,  fit_peaks_kw={})  # type: ignore 
        x_spe,x_reference,x_distance,df = rc2utils.match_peaks(spe_pos_dict, model_si.ref)
        sum_of_differences = np.sum(np.abs(x_spe - x_reference)) / len(x_spe)
        print("{}\tsum_of_differences {} {}".format(op,sum_of_differences, model_si.ref_units))
        diff.append(sum_of_differences)

    pd.DataFrame(diff).to_csv(os.path.join(product["data"],op,"differences.csv"),index=False)

    return calmodel,spe_sil_calib

Path(product["data"]).mkdir(parents=True, exist_ok=True)
metadata = pd.read_hdf(upstream["templates_read"]["h5"], key="templates_read")
unique_optical_paths = metadata['optical_path'].unique()
output = upstream["templates_load"]["data"]

for op in unique_optical_paths:
    print(op)
    op_meta = metadata.loc[metadata["optical_path"] == op]
    if not op_meta['enabled'].unique()[0]:
        continue
    wavelength = op_meta['wavelength'].unique()[0]
    _path = os.path.join(output,str(int(wavelength)),op)
    try:
        spe_neon = from_chada(os.path.join(_path,"{}.cha".format(neon_tag)),dataset="/normalized")
        spe_sil = from_chada(os.path.join(_path,"{}.cha".format(si_tag)),dataset="/normalized")
        calmodel, spe_sil_calib = calibrate(op,wavelength,spe_neon,spe_sil)
        calmodel.save(os.path.join(_path,"calibration.pkl"))   
        spe_sil_calib.write_cha(os.path.join(_path,"{}.cha".format(si_tag)),dataset="/calibrated")

        spe_pst = from_chada(os.path.join(_path,"{}.cha".format(pst_tag)),dataset="/normalized")
        spe_pst_calib = calmodel.process(spe_pst,spe_units="nm",convert_back=False)
        spe_pst_calib.write_cha(os.path.join(_path,"{}.cha".format(pst_tag)),dataset="/calibrated")
    except Exception as err:
        print(err)
   

    
