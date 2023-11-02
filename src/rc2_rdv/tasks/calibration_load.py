# + tags=["parameters"]
upstream = []
product = None
laser_wl = None
test_only = None
neon_file = None
silicon_file = None
# -

import ramanchada2 as rc2
import os.path
from pathlib import Path
from scipy import signal

Path(product["data"]).mkdir(parents=True, exist_ok=True)

if test_only:
    spe_neon = rc2.spectrum.from_test_spe(sample=['Neon'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
    spe_sil = rc2.spectrum.from_test_spe(sample=['S0B'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
else:
    spe_neon = rc2.spectrum.from_local_file(neon_file)
    if min(spe_neon.x)<0:
        spe_neon = spe_neon.trim_axes(method='x-axis',boundaries=(0,max(spe_neon.x)))
    spe_neon.plot()
    spe_sil = rc2.spectrum.from_local_file(silicon_file)    
    if min(spe_sil.x)<0:
        spe_sil = spe_sil.trim_axes(method='x-axis',boundaries=(0,max(spe_sil.x)))    
    spe_sil.plot()



print("Silicon len={} [{},{}]".format(len(spe_sil.x),min(spe_sil.x),max(spe_sil.x)))
print("Neon len={} [{},{}]".format(len(spe_neon.x),min(spe_neon.x),max(spe_neon.x)))

spe_neon_file = os.path.join(product["data"],"neon_{}.cha".format(laser_wl))
if os.path.exists(spe_neon_file):
    os.remove(spe_neon_file)
spe_neon._cachefile = spe_neon_file
spe_neon.write_cha(spe_neon_file,dataset = "/raw")
spe_neon = spe_neon - spe_neon.moving_minimum(120)
spe_neon = spe_neon.normalize()
spe_neon.plot()
spe_neon.write_cha(spe_neon_file,dataset = "/baseline")
assert min(spe_neon.x)>=0

spe_sil_file = os.path.join(product["data"],"sil_{}.cha".format(laser_wl))
if os.path.exists(spe_sil_file):
    os.remove(spe_sil_file)
spe_sil._cachefile = spe_sil_file
spe_sil.write_cha(spe_sil_file,"/raw")
spe_sil = spe_sil - spe_sil.moving_minimum(120)
spe_sil = spe_sil.normalize()
spe_sil.plot()
spe_sil.write_cha(spe_sil_file,dataset = "/baseline")
assert min(spe_sil.x)>=0

from ramanchada2.spectrum import from_chada
spe = from_chada(spe_sil_file,dataset="/baseline")
assert(min(spe.x)>=0)