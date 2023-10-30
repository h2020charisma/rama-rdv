# + tags=["parameters"]
upstream = ["calibration"]
product = None
laser_wl = None
test_only = None
input_file = None
# -

from ramanchada2.spectrum import Spectrum, from_chada, from_local_file, from_test_spe
from pathlib import Path
import matplotlib.pyplot as plt

Path(product["data"]).mkdir(parents=True, exist_ok=True)

def peaks(spe_nCal_calib, prominence):
    cand = spe_nCal_calib.find_peak_multipeak(prominence=prominence, wlen=300, width=1)
    init_guess = spe_nCal_calib.fit_peak_multimodel(profile='Moffat', candidates=cand, no_fit=True)
    fit_res = spe_nCal_calib.fit_peak_multimodel(profile='Moffat', candidates=cand)
    return cand, init_guess, fit_res

def load_calibration(path_source):
    spe_calibration = {}
    peak_silica = 520.45
    ax = None
    fig, ax = plt.subplots(1,4,figsize=(16,4))
    ix = 0
    for _tag in ["/raw","/calibrated_neon","/calibrated_neon_sil","/calibrated"]:
        try:
            spe_calibration[_tag] = from_chada(path_source,_tag)
            print("{} len={} [{},{}]".format(_tag,len(spe_calibration[_tag].x),min(spe_calibration[_tag].x),max(spe_calibration[_tag].x)))          
            spe_calibration[_tag].plot(ax=ax[ix],label=_tag)
            ax[ix].set_xlim(peak_silica-50, peak_silica+50)
            ix=ix+1
        except Exception as err:
            print(err)
    return spe_calibration


def apply_calibration(spe,spe_calib ):
    try:
        assert len(spe.x) == len(spe_calib.x), ("x should have same resolution {} vs {}".format(len(spe.x),len(spe_calib.x)))
        assert min(spe.x) == min(spe_calib.x), ("x should have same start value {} vs {}".format(min(spe.x),min(spe_calib.x)))
        assert max(spe.x) == max(spe_calib.x), ("x should have same end value {} vs {}".format(max(spe.x),max(spe_calib.x)))
        spe = spe.__copy__()
    except Exception as err:
        spe =  spe.resample_NUDFT_filter(x_range=(min(spe_calib.x),max(spe_calib.x)), xnew_bins=len(spe_calib.x))
    spe.x = spe_calib.x
    return spe


if test_only:
    spe_pst = from_test_spe(sample=['PST'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])    
    spe_nCal = from_test_spe(sample=['nCAL'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
else:
    spe_nCal = from_local_file(input_file)

print("{} len={} [{},{}]".format(input_file,len(spe_nCal.x),min(spe_nCal.x),max(spe_nCal.x)))
spe_nCal.plot()

spe_calibration = load_calibration(path_source=upstream["calibration"]["data"])
calibrated = spe_calibration["/calibrated"]
spe_nCal_movmin = spe_nCal - spe_nCal.moving_minimum(120)
spe_nCal_calib = apply_calibration(spe_nCal_movmin,calibrated)
spe_nCal_calib.plot()

cand, init_guess, fit_res = peaks(spe_nCal_calib,prominence = calibrated.y_noise*10)
for _ in [cand, init_guess,fit_res]:
    fig, ax = plt.subplots()
    spe_nCal_calib.plot(ax=ax, fmt=':')
    _.plot(ax=ax)
    #ax.set_xlim(300, 1000)