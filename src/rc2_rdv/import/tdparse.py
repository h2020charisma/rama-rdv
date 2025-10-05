from pathlib import Path
import os
import pyambit.datamodel as mx
import pynanomapper.datamodel.templates.template_config as tc
import pynanomapper.datamodel.templates.tdparser as tp
import nexusformat.nexus.tree as nx
from pyambit import nexus_writer


# + tags=["parameters"]
upstream = None
product = None
config = None
dataset = None
# -


cfg = config[dataset]
cfg

substances = None
for file in cfg["FILES"]:
    xlsx_file = Path(os.path.join(cfg["INPUT_FOLDER"], file))
    tdconfig = tp.TemplateDesignerConfig(Path(xlsx_file))
    print(tdconfig.template_file_name)
    tdparser = tp.create_parser(tdconfig, "POLY")

    s = tdparser.parse_results()
    if substances is None:
        substances = s
    else:
        substances.substance.extend(s.substance)

nxroot = nx.NXroot()
substances.to_nexus(nxroot, hierarchy=False)
nxroot.save(product["nexus"], mode="w")