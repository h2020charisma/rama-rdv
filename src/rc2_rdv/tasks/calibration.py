# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
# -

import ramanchada2 as rc2
import ramanchada2.misc.constants  as rc2const
import ramanchada2.misc.utils as rc2utils
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from pathlib import Path
import os.path
from ramanchada2.spectrum import from_chada, Spectrum
from ramanchada2.io.HSDS import read_cha


dataset_to_process = "/raw"
dataset_to_process = "/baseline"

def plot_peaks_stem(ref_keys,ref_values,spe_keys,spe_values,spe=None):
    fig, ax = plt.subplots(figsize=(8, 2))
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
        spe.plot(ax=ax.twinx())
    plt.show()

def iter_calib(in_spe, ref, prominence, wlen, n_iters, poly_order=3):
    tmp = in_spe
    for iter in range(n_iters):
        print("iter_calib",iter,len(tmp.x),min(x),max(x))
        tmp = tmp.xcal_fine(ref=ref,
                            poly_order=poly_order,
                            should_fit=False,
                            find_peaks_kw=dict(prominence=tmp.y_noise*prominence,
                                               wlen=wlen,
                                               width=1,
                                              )
                           )
        
    return tmp

def apply_calibration(spe,spe_calib ):
    try:
        assert len(spe.x) == len(spe_calib.x), ("x should have same resolution {} vs {}".format(len(spe.x),len(spe_calib.x)))
        assert min(spe.x) == min(spe_calib.x), ("x should have same start value {} vs {}".format(min(spe.x),min(spe_calib.x)))
        assert max(spe.x) == max(spe_calib.x), ("x should have same end value {} vs {}".format(max(spe.x),max(spe_calib.x)))
        spe = spe.__copy__()       
    except Exception as err:
        _left = min(spe_calib.x) 
        _right = max(spe_calib.x)
        spe =  spe.resample_NUDFT_filter(x_range=(_left if _left>0 else 0,_right), xnew_bins=len(spe_calib.x))
    spe.x = spe_calib.x
    return spe

def resample(spe_sil,spe_neon):
    xnew_bins = len(spe_neon.x)
    xmin = min(spe_neon.x)
    xmax = max(spe_neon.x)
    return spe_sil.resample_NUDFT_filter(x_range=(xmin,xmax), xnew_bins=xnew_bins)

def calibrate(spe_neon,spe_sil,laser_wl=785,neon_wl=rc2const.neon_wl_785_nist_dict,plot=True):
    print(laser_wl)
    peak_silica = 520.45
    spe_neon_wl = spe_neon.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)
    spe_neon_wl_calib = iter_calib(spe_neon_wl, ref=neon_wl, wlen=100, prominence=1, n_iters=10)

    print(min(spe_neon_wl.x),max(spe_neon_wl.x))
    fig, ax = plt.subplots(4,1,figsize=(12,6))
    spe_neon.plot(ax=ax[0], fmt=':', label='original')

    ax[1].stem(neon_wl.keys(), neon_wl.values(), label='reference (wl)',linefmt='r-', markerfmt='ro', basefmt=' ')
    ax[2].stem(neon_wl.keys(), neon_wl.values(), label='reference (wl)',linefmt='r-', markerfmt='ro', basefmt=' ')
    spe_neon_wl.plot(ax=ax[1].twinx(), fmt='-', label='initial (wl)')
    spe_neon_wl_calib.plot(ax=ax[2].twinx(), fmt='-', label='calibrated (wl)')    

    spe_neon_calib = spe_neon_wl_calib.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)
    print("spe_neon_calib",min(spe_neon_calib.x),max(spe_neon_calib.x))
    spe_neon_calib.plot(ax=ax[3], fmt='-', label='calibrated (rs)')    
    spe_sil.plot(ax=ax[3].twinx(), fmt=':', label='sil')    
    spe_sil_necal = apply_calibration(spe_sil,spe_neon_calib)
    spe_sil_necal.plot(ax=ax[3].twinx(), fmt='r-', label='sil calibrated with neon')    
    
    spe_sil_calib = iter_calib(spe_sil_necal, ref=[peak_silica], wlen=100, prominence=10, n_iters=1, poly_order=0)
    if plot:
        fig, ax = plt.subplots(3,1,figsize=(12,4))
        spe_sil.plot(ax=ax[0], label='Sil initial')
        spe_sil_necal.plot(ax=ax[1], label='Sil neon calibrated',fmt='-')
        spe_sil_calib.plot(ax=ax[2], label='Sil calibrated',fmt=':',c='r')
        for i in [0,1,2]:
            ax[i].set_xlim(peak_silica-100, peak_silica+100)

    #spe_sil._cachefile = product["data"]
    spe_sil.write_cha(product["data"],"/raw")

    #spe_sil.write_cache()   
    #spe_sil_necal._cachefile = product["data"]
    spe_sil_necal.write_cha(product["data"],"/calibrated_neon")    

    #spe_sil_calib._cachefile = product["data"]
    spe_sil_calib.write_cha(product["data"],"/calibrated_neon_sil")   

    #spe_sil_calib.write_cache()         
    return spe_sil_calib

#def plot_calibration():
#    fig, ax = plt.subplots()
#    spe_pst_silcal.plot(ax=ax, label='ne+sil calibrated')
#    spe_pst_calib.plot(ax=ax, label='self calibrated')



#Path(product["data"]).mkdir(parents=True, exist_ok=True)
path_source = upstream["calibration_load"]["data"]
if os.path.exists(product["data"]):
    os.remove(product["data"])

spe = {}

for _tag in ["neon","sil"]:
    filename = os.path.join(path_source,"{}_{}.cha".format(_tag,laser_wl))
    x, y, meta = read_cha(filename, dataset=dataset_to_process)
    assert min(x)>=0
    print(dataset_to_process,_tag,len(x),min(x),max(x))
    spe[_tag] = Spectrum(x=x, y=y, metadata=meta, cachefile = filename)  # type: ignore

#spe_neon = from_chada(os.path.join(path_source,"neon_{}.cha".format(laser_wl)))
#spe_sil  = from_chada(os.path.join(path_source,"sil_{}.cha".format(laser_wl)))
spe_neon = spe["neon"]
spe_sil  = spe["sil"]

neon_wl = {
    785: rc2const.neon_wl_785_nist_dict,
    633: rc2const.neon_wl_633_nist_dict,
    532: rc2const.neon_wl_532_nist_dict
}

if laser_wl in neon_wl:
    spe_sil_calib = calibrate(spe_neon,spe_sil,laser_wl,neon_wl[laser_wl])

    #spe_pst  = from_chada(os.path.join(path_source,"pst_{}.cha".format(laser_wl)))    
    
    try:
        #spe_pst_silcal = apply_calibration(spe_pst,spe_sil_calib)
        #self calibration    
        #spe_pst_calib = iter_calib(spe_pst_silcal, ref=rc2const.PST_RS_dict, prominence=1, wlen=100, n_iters=20)
        #fig, ax = plt.subplots()
        #spe_pst_silcal.plot(ax=ax, label='ne+sil calibrated')
        #spe_pst_calib.plot(ax=ax, label='self calibrated')
        #calibrated = spe_pst_calib
        calibrated = spe_sil_calib
        #calibrated._cachefile = product["data"]        
        calibrated.write_cha(product["data"],"/calibrated")
    
    except Exception as err:
        print(err)
else:
    print("laser wavelength {} not supported".format(laser_wl))    