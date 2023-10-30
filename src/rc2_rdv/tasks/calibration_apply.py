# + tags=["parameters"]
upstream = ["calibration"]
product = None
laser_wl = None
# -

from ramanchada2.spectrum import from_chada
from pathlib import Path
import matplotlib.pyplot as plt

Path(product["data"]).mkdir(parents=True, exist_ok=True)

path_source = upstream["calibration"]["data"]
print(path_source)

spe_calibration = {}

peak_silica = 520.45
ax = None
fig, ax = plt.subplots(4,1,figsize=(16,4))
ix = 0
for _tag in ["/raw","/calibrated_neon","/calibrated_neon_sil","/calibrated"]:
    try:
        spe_calibration[_tag] = from_chada(path_source,_tag)
        spe_calibration[_tag].plot(ax=ax[ix],label=_tag)
        ax[ix].set_xlim(peak_silica-50, peak_silica+50)
        ix=ix+1
    except Exception as err:
        print(err)
