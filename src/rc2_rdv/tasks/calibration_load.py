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
    spe_neon.plot()
    spe_sil = rc2.spectrum.from_local_file(silicon_file)    
    spe_sil.plot()



print("Silicon len={} [{},{}]".format(len(spe_sil.x),min(spe_sil.x),max(spe_sil.x)))
print("Neon len={} [{},{}]".format(len(spe_neon.x),min(spe_neon.x),max(spe_neon.x)))


spe_neon.write_cha(os.path.join(product["data"],"neon_{}.cha".format(laser_wl)),"/raw")
spe_sil.write_cha(os.path.join(product["data"],"sil_{}.cha".format(laser_wl)),"/raw")