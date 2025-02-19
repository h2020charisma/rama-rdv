from pathlib import Path
import pandas as pd
import ramanchada2 as rc2
import matplotlib.pyplot as plt
import pyambit.datamodel as mx
import uuid
from pyambit.nexus_spectra import configure_papp
from typing import Dict
import nexusformat.nexus.tree as nx
import os.path 
from ramanchada2.protocols.spectraframe import SpectraFrame


# + tags=["parameters"]
upstream = []
product = None
input_folder = None
metadata_file = None
dataset = None
prefix = None
# -


# Function to find the file based on Library ID
def find_file_by_library_id(library_id, base_directory):
    # Traverse all subdirectories to find the file
    for root, dirs, files in os.walk(base_directory):
        # Construct the filename expected for this library_id
        expected_filename = f"{library_id}.txt"
        if expected_filename in files:
            # Return the full path of the file
            return os.path.join(root, expected_filename)
    return None  # If no file found


def load_spectrum(row):
    return rc2.spectrum.Spectrum.from_local_file(row["file_name"])


def load(dataset, base_directory):
    df = pd.read_excel(os.path.join(input_folder, metadata_file), sheet_name=dataset)
    df["file_name"] = None
    df["device"] = None
    df["optical_path"] = None
    df["laser_power_mW"] = None
    df["laser_power_percent"] = None
    df["replicate"] = None
    df["provider"] = dataset
    file_paths = []

    # Iterate over each row in the dataframe and find the corresponding file
    for library_id in df['Library ID']:
        file_path = find_file_by_library_id(library_id.strip(), base_directory)
        file_paths.append(file_path)
    df['file_name'] = file_paths
#Library ID	Library ID Shortform	Polymer	Colour	Morphology	Source	Source Type	Laser (nm)	Grating 	Hole size (nm)	Slit (um)	Filter (%)	Acq. Time (s)	Accumulation	Delay (s)
    dynamic_column_mapping = {
        "Library ID": "sample",
        "Laser (nm)": "laser_wl",
        "Hole size (nm)": "pin_hole_size",
        "Acq. Time (s)": "acquisition_time",
        "Grating ": "grating",
        "Grating": "grating"
    }
    spe_frame = SpectraFrame.from_dataframe(df, dynamic_column_mapping)
    return spe_frame


def plot_spectra(df: SpectraFrame, title="spectra", source="spectrum", label="sample"):
    fig, ax = plt.subplots(1, 1, figsize=(12, 2))
    for index, row in df.iterrows():
        row[source].plot(ax=ax, label=row["sample"])
    ax.set_title(title)
    #plt.savefig("test_twinning_{}.png".format(title))


spe_frame = load(dataset, os.path.join(input_folder, dataset))
# spe_frame["file_name"]
spe_frame.to_excel(f"test_{dataset}.xlsx", index=False)
spe_frame.columns

# .head()
spe_frame["spectrum"] = spe_frame.apply(load_spectrum, axis=1)
grouped = spe_frame.groupby("Polymer")

for Polymer, group in grouped:
    plot_spectra(group, title=Polymer)
    substances = []
    for index, row in group.iterrows():
        sample_id = row["Library ID Shortform"]
        meta = {}
        for tag in ["pin_hole_size","acquisition_time","grating"]:
            meta[tag] = row[tag]
        substance = mx.SubstanceRecord(name=sample_id, publicname=row["sample"],
                                   ownerName=dataset, substanceType=row["Polymer"],
                                   ownerUUID="{}-{}".format(prefix, uuid.uuid5(uuid.NAMESPACE_OID, dataset)))
        substance.i5uuid = "{}-{}".format(prefix, uuid.uuid5(uuid.NAMESPACE_OID, sample_id))
        mol = mx.Compound(name=row["sample"])
        cmp = mx.Component(compound=mol, values={
            "Polymer": row["Polymer"],
            "Colour": row["Colour"],
            "Morphology": row["Morphology"],
            "Source": row["Source"]
        })
        substance.composition = [mx.CompositionEntry(component=cmp)]

        print(substance.model_dump_json())
        substance.study = []
        papp = mx.ProtocolApplication(
                protocol=mx.Protocol(
                    topcategory="P-CHEM",
                    category=mx.EndpointCategory(code="ANALYTICAL_METHODS_SECTION"),
                    guideline=["Raman spectroscopy"]
                ),
                effects=[]
                )
        _investigation = dataset
        citation = mx.Citation(
            owner="10.1021/acs.analchem.9b03626", title=dataset, year=2020)
        configure_papp(
                papp,  instrument=("HORIBA", "XploRA PLUS"),
                wavelength=str(row["laser_wl"]),
                provider=citation.owner,
                sample=sample_id,
                sample_provider=dataset,
                investigation=_investigation,
                citation=citation,
                prefix=prefix,
                meta=meta)
        papp.nx_name = sample_id
        spe = row["spectrum"]
        data_dict: Dict[str, mx.ValueArray] = {
            "Wavenumber": mx.ValueArray(values=spe.x, unit="cm¯¹")
        }    
        ea = mx.EffectArray(
                endpoint="Raman intensity",
                endpointtype="PROCESSED",
                signal=mx.ValueArray(values=spe.y, unit="Arbitr.units."),
                axes=data_dict
        )
        ea.nx_name = sample_id
        papp.effects.append(ea)
        substance.study.append(papp)
        substances.append(substance)

    ambit_substances = mx.Substances(substance=substances)
    nxroot = nx.NXroot()

    ambit_substances.to_nexus(nxroot)
    file = os.path.join(os.path.join(product["nexus"],"{}.nxs".format(Polymer)))
    Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)
    print(file)
    nxroot.attrs["pyambit"] = "0.0.1"
    nxroot.attrs["file_name"] = os.path.basename(file)
    nxroot.save(file, mode="w")

