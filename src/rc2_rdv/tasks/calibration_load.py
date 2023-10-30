# + tags=["parameters"]
upstream = []
product = None
laser_wl = None
# -

import ramanchada2 as rc2
import os.path
from pathlib import Path

Path(product["data"]).mkdir(parents=True, exist_ok=True)

spe_neon = rc2.spectrum.from_test_spe(sample=['Neon'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
spe_pst = rc2.spectrum.from_test_spe(sample=['PST'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
spe_sil = rc2.spectrum.from_test_spe(sample=['S0B'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])
spe_nCal = rc2.spectrum.from_test_spe(sample=['nCAL'], provider=['FNMT'], OP=['03'], laser_wl=[str(laser_wl)])

spe_neon.write_cha(os.path.join(product["data"],"neon_{}.cha".format(laser_wl)),"/raw")
spe_sil.write_cha(os.path.join(product["data"],"sil_{}.cha".format(laser_wl)),"/raw")
spe_pst.write_cha(os.path.join(product["data"],"pst_{}.cha".format(laser_wl)),"/raw")
spe_nCal.write_cha(os.path.join(product["data"],"ncal{}.cha".format(laser_wl)),"/raw")
