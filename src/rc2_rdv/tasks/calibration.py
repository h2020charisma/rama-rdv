# + tags=["parameters"]
upstream = ["calibration_load"]
product = None
laser_wl = None
# -

import ramanchada2 as rc2
import ramanchada2.misc.constants  as rc2const
import ramanchada2.misc.utils as rc2utils
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import os.path
from ramanchada2.spectrum import from_chada


def iter_calib(in_spe, ref, prominence, wlen, n_iters, poly_order=3):
    tmp = in_spe
    for iter in range(n_iters):
        tmp = tmp.xcal_fine(ref=ref,
                            poly_order=poly_order,
                            should_fit=False,
                            find_peaks_kw=dict(prominence=tmp.y_noise*prominence,
                                               wlen=wlen,
                                               width=1,
                                              )
                           )
    return tmp


def calibrate(spe_neon,spe_sil,laser_wl=785,neon_wl=rc2const.neon_wl_785_nist_dict,plot=True):
    peak_silica = 520.45
    spe_neon_wl = spe_neon.shift_cm_1_to_abs_nm_filter(laser_wave_length_nm=laser_wl)
    spe_neon_wl_calib = iter_calib(spe_neon_wl, ref=neon_wl, wlen=100, prominence=.5, n_iters=20)
    fig, ax = plt.subplots()
    spe_neon_wl.plot(ax=ax, fmt=':', label='initial')
    spe_neon_wl_calib.plot(ax=ax, fmt=':', label='calibrated')
    ax.twinx().stem(neon_wl.keys(), neon_wl.values(), label='reference')

    spe_neon_calib = spe_neon_wl_calib.abs_nm_to_shift_cm_1_filter(laser_wave_length_nm=laser_wl)

    spe_sil_necal = spe_sil.__copy__()
    spe_sil_necal.x = spe_neon_calib.x
    spe_sil_calib = iter_calib(spe_sil_necal, ref=[peak_silica], wlen=100, prominence=10, n_iters=1, poly_order=0)
    if plot:
        fig, ax = plt.subplots(3,1,figsize=(12,4))
        spe_sil.plot(ax=ax[0], label='Sil initial')
        spe_sil_necal.plot(ax=ax[1], label='Sil neon calibrated',fmt='-')
        spe_sil_calib.plot(ax=ax[2], label='Sil calibrated',fmt=':',c='r')
        for i in [0,1,2]:
            ax[i].set_xlim(peak_silica-100, peak_silica+100)
    return spe_sil_calib

def plot_calibration():
    fig, ax = plt.subplots()
    spe_pst_silcal.plot(ax=ax, label='ne+sil calibrated')
    spe_pst_calib.plot(ax=ax, label='self calibrated')

def apply_calibration(spe_pst,spe_sil_calib ):
    spe_pst_silcal = spe_pst.__copy__()
    spe_pst_silcal.x = spe_sil_calib.x
    return spe_pst_silcal


def peaks(spe_nCal_calib, prominence):
    cand = spe_nCal_calib.find_peak_multipeak(prominence=prominence, wlen=300, width=1)
    init_guess = spe_nCal_calib.fit_peak_multimodel(profile='Moffat', candidates=cand, no_fit=True)
    fit_res = spe_nCal_calib.fit_peak_multimodel(profile='Moffat', candidates=cand)
    return cand, init_guess, fit_res


Path(product["data"]).mkdir(parents=True, exist_ok=True)
path_source = upstream["calibration_load"]["data"]
spe_neon = from_chada(os.path.join(path_source,"neon_{}.cha".format(laser_wl)))
spe_sil  = from_chada(os.path.join(path_source,"sil_{}.cha".format(laser_wl)))


neon_wl = {
    785: rc2const.neon_wl_785_nist_dict,
    633: rc2const.neon_wl_633_nist_dict,
    532: rc2const.neon_wl_532_nist_dict
}

if laser_wl in neon_wl:
    spe_sil_calib = calibrate(spe_neon,spe_sil,laser_wl,neon_wl[laser_wl])

    spe_pst  = from_chada(os.path.join(path_source,"pst_{}.cha".format(laser_wl)))    
    spe_pst_silcal = apply_calibration(spe_pst,spe_sil_calib)
    #self calibration    
    spe_pst_calib = iter_calib(spe_pst_silcal, ref=rc2const.PST_RS_dict, prominence=1, wlen=100, n_iters=20)
    fig, ax = plt.subplots()
    spe_pst_silcal.plot(ax=ax, label='ne+sil calibrated')
    spe_pst_calib.plot(ax=ax, label='self calibrated')
    #ncal
    spe_nCal = from_chada(os.path.join(path_source,"ncal{}.cha".format(laser_wl)))
    spe_nCal_movmin = spe_nCal - spe_nCal.moving_minimum(120)
    spe_nCal_calib = apply_calibration(spe_nCal_movmin,spe_pst_calib) 
    cand, init_guess, fit_res = peaks(spe_nCal_calib,prominence = spe_pst_calib.y_noise*10)
    for _ in [cand, init_guess,fit_res]:
        fig, ax = plt.subplots()
        spe_nCal_calib.plot(ax=ax, fmt=':')
        _.plot(ax=ax)
        ax.set_xlim(300, 1000)
else:
    print("laser wavelength {} not supported".format(laser_wl))    