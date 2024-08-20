# + tags=["parameters"]
upstream = ["read_metadata"]
product = None
input4import = None
provider: None
instrument: None
wavelength: None
investigation: None

# -

import pandas as pd
import os.path
from ramanchada2 import spectrum
import matplotlib.pyplot as plt
from pyambit.nexus_spectra import configure_papp, spe2effect
import pyambit.datamodel as mx
import numpy as np
from typing import Dict, Optional, Union, List
import nexusformat.nexus.tree as nx
import os 
from pyambit.nexus_writer import to_nexus
import uuid
from pathlib import Path

prefix="CHRM"
def create_papp(folder,basename,tags):
    sample = tags[0]
    instrument = tags[1]
    sample_provider = folder


    papp =  mx.ProtocolApplication(protocol=mx.Protocol(topcategory="P-CHEM",
        category=mx.EndpointCategory(code="ANALYTICAL_METHODS_SECTION")),effects=[])
    papp.citation = mx.Citation(owner=provider,title=investigation,year=2022)
    papp.investigation_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID,investigation))
    papp.assay_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID,"{} {}".format(investigation,provider)))
    papp.parameters = {"E.method" : "Raman spectrometry" ,
                       "wavelength" : wavelength,
                       "T.instrument_model" : tags[1]
                }

    papp.uuid = "{}-{}".format(prefix,uuid.uuid5(uuid.NAMESPACE_OID,"RAMAN {} {} {} {} {} {}".format(
                "" if investigation is None else investigation,
                "" if sample_provider is None else sample_provider,
                "" if sample is None else sample,
                "" if provider is None else provider,
                "" if instrument is None else instrument,
                "" if wavelength is None else wavelength)))
    company=mx.Company(name = sample_provider)
    substance = mx.Sample(uuid = "{}-{}".format(prefix,uuid.uuid5(uuid.NAMESPACE_OID,sample)))
    papp.owner = mx.SampleLink(substance = substance,company=company)    
    return papp


df=pd.read_excel(upstream["read_metadata"]["data"])
supported_extensions =  { '.spc' : 1, '.sp' : 2, '.spa' :3, '.0' :4, '.1' :5, '.2' :6, 
                                      '.wdf' :7, '.ngs' :8, '.jdx' :9, '.dx' :10, '.rruf' :11,
                                      '.txt' :12, '.txtr' :13, '.csv' :14, '.prn' :15}
sorted_extensions = sorted(supported_extensions.items(), key=lambda x: x[1])  # Sort by priority
grouped = df.sort_values(by=['folder', 'basename', 'extension']).groupby(['folder'])

papps = {}

for folder, group_df in grouped:
    old_tag = None
    for basename, basename_group_df in group_df.groupby('basename'):
        tags = basename.split("_")
        try:
            tag = tags[0]
        except:
            tag = basename
        if old_tag != tag:
            papp = create_papp(folder[0],basename[0],tags)
            if tag in papps:
                papps[tag]["study"].append(papp)
            else:
                papps[tag] = {"study" : [papp]}
            fig, ax = plt.subplots(figsize=(10, 6))  # Create a new plot
            old_tag = tag

        for ext, priority in sorted_extensions:  # Iterate based on priority
            _tmp = basename_group_df.loc[basename_group_df["extension"]==ext]
            if not _tmp.empty:
                try:
                    file = os.path.join(_tmp.iloc[0]["folder"], f"{_tmp.iloc[0]['basename']}{_tmp.iloc[0]['extension']}")
                    spe = spectrum.from_local_file(file)
                    spe.plot(label=basename, ax=ax)

                    data_dict: Dict[str, mx.ValueArray] = {
                        'x': mx.ValueArray(values = spe.x, unit="cm-1")
                    }
                    e = mx.EffectArray(endpoint=_tmp.iloc[0]['basename'],endpointtype="RAW_DATA",
                                                    signal = mx.ValueArray(values = spe.y,unit="a.u."),
                                                    axes = data_dict)                    
                    papp.effects.append(e)
                    break
                except Exception as err:
                    print(err)
    ax.legend()  # Add legend
    ax.set_title(folder)  # Set title
    plt.tight_layout()
    #plt.savefig(folder.replace("\\", "_") + ".png")  # Save the plot as an image file
    plt.show()
    plt.close()  # Close the plot to release resources
    
Path(product["nexus"]).mkdir(parents=True, exist_ok=True)
for tag in papps:
    substance_records = []    
    substance = mx.SubstanceRecord(name=tag,publicname=tag,ownerName="CHARISMA")
    substance.i5uuid  = "{}-{}".format(prefix,uuid.uuid5(uuid.NAMESPACE_OID,tag))       
    substance.study = papps[tag]["study"]
    substance_records.append(substance)
    substances = mx.Substances(substance=substance_records)    
    nxroot = nx.NXroot()
    substances.to_nexus(nxroot)
    file = os.path.join(product["nexus"],"spectra_{}.nxs".format(tag))
    print(file)
    nxroot.save(file,mode="w")    
