# + tags=["parameters"]
upstream = []
product = None
root_folder = None
template_metadata = None
multidimensional = None
# -

import ramanchada2 as rc2
import os.path
import pandas as pd
import pyambit.datamodel as mx
import numpy as np 
from typing import Dict
from pyambit.nexus_spectra import configure_papp
import uuid
import nexusformat.nexus.tree as nx
import traceback
from numpy.typing import NDArray


def read_template(template_path):
    df = pd.read_excel(template_path, sheet_name='Files')
    df['Path'] = df['Filename'].apply(lambda x: os.path.dirname(x))
    df['Basename'] = df['Filename'].apply(lambda x: os.path.basename(x))
    df['Folder'] = df['Filename'].apply(lambda x: x.strip('/').split('/')[0])
    # zero values for laser power are error / empty values
    df['Laser power, mW'] = df['Laser power, mW'].replace(0, np.nan)
    df.dropna(axis=1, how='all', inplace=True)

    df_meta = pd.read_excel(template_path, sheet_name='Front sheet', skiprows=4)
    df_meta.dropna(axis=1, how='all', inplace=True)
    return df, df_meta


def get_unique_values(df):
    # Initialize dictionaries
    single_value_dict = {}
    multi_value_dict = {}
    for col in df.columns:
        unique_values = df[col].unique()
        if len(unique_values) == 1:
            single_value_dict[col] = str(unique_values[0]).strip()
        else:
            multi_value_dict[col] = ', '.join(map(str, unique_values.tolist()))
    return single_value_dict, multi_value_dict


def process_files(root_folder, df, meta_columns, multidimensional=False):
    not_meta_columns = df.columns.difference(meta_columns)
    substances = []
    
    for sample in df["Sample"].unique():
        substance = mx.SubstanceRecord(name=sample, publicname=sample, ownerName=provider)
        substance.i5uuid = "{}-{}".format(prefix, uuid.uuid5(uuid.NAMESPACE_OID, sample))
        substance.study = []
        df_sample = df.loc[df["Sample"] == sample]
        grouped_path_instrument = df_sample.groupby(['Path', 'Instrument/OP ID', 'Wavelength, nm', 'Make', 'Model', 'Notes'])
        for instrument_keys, df_subfolder in grouped_path_instrument:
            subfolder = instrument_keys[0].split("/")[0]
            instrument_id = instrument_keys[1]
            instrument_wl = instrument_keys[2]
            instrument_make = instrument_keys[3]
            instrument_model = instrument_keys[4]
            data_provider = instrument_keys[5]
            papp = mx.ProtocolApplication(
                protocol=mx.Protocol(
                    topcategory="P-CHEM",
                    category=mx.EndpointCategory(code="ANALYTICAL_METHODS_SECTION"),
                    guideline=["Raman spectroscopy"]
                ),
                effects=[],
                )

            _investigation = "{}.{}".format(subfolder, investigation)
            citation = mx.Citation(
                    owner=data_provider, title="10.5281/zenodo.13387413", year=2024)
            
            configure_papp(
                papp,  instrument=(instrument_make, instrument_model),
                wavelength=str(instrument_wl),
                provider=citation.owner,
                sample=sample,
                sample_provider=provider,
                investigation=_investigation,
                citation=citation,
                prefix=prefix,
                meta=None)   
            papp.nx_name = "{} {} {}".format(subfolder, instrument_id, sample)          
            replicate = "Measurement #"
            spectra = []
            for index, row in df_subfolder.iterrows():
                try:
                    spe = rc2.spectrum.from_local_file(os.path.join(root_folder, instrument_keys[0], row["Basename"]).strip())
                    _sperow = {"spe" : spe, "minx" : min(spe.x), "maxx" : max(spe.x), "bins" : len(spe.x),
                                    "replicate" : row[replicate],  "basename" : row["Basename"], 
                                    "@signal" : "Raman intensity", "@axes" : "Raman shift"}
                    for key in spe.meta.get_all_keys():
                        if key == "@signal":
                            _sperow[key] = "Raman intensity" if spe.meta[key] == "" else spe.meta[key]
                        elif key == "@axes":
                            _sperow[key] = "Raman shift" if spe.meta[key][0] == "" else spe.meta[key][0]     
                        else:
                            _sperow["META_{}".format(key)] = spe.meta[key]
                    spectra.append(_sperow)
                except Exception as err:
                    traceback.print_exc()
                    print(row["Filename"],err)

            df_spectra = pd.DataFrame(spectra) 
            df_spectra_META = df_spectra[[col for col in df_spectra.columns if col.startswith('META_')]]
            _conditions_single, _conditions_multi = get_unique_values(df_spectra_META)
            grouped = df_spectra.groupby(['minx', 'maxx', 'bins', '@signal', '@axes'])
            for group_keys, group_df in grouped:
                try:
                    unique_replicates = sorted(group_df['replicate'].unique())
                    num_replicates = len(unique_replicates)
                    if multidimensional:
                        array_2d: NDArray[np.float64] = np.empty((num_replicates, group_keys[2]))
                        for i, (index, row) in enumerate(group_df.iterrows()):
                            spe_y = row['spe'].y
                            spe_x = row['spe'].x
                            replicate_number = row['replicate']
                            # Fill the ith column with the spe.x values of the current replicate
                            column_index = unique_replicates.index(replicate_number)
                            array_2d[column_index, :] = spe_y

                        # print(type(array_2d),array_2d)
                        data_dict: Dict[str, mx.ValueArray] = {
                            "Replicate": mx.ValueArray(values=np.array(unique_replicates), unit=None),
                            group_keys[4]: mx.ValueArray(values=spe_x, unit="cm-1")
                        }

                        _conditions_single["grouped_by"] = ', '.join(map(str, group_keys)) 
                        ea = mx.EffectArray(
                                endpoint="Raman intensity",
                                endpointtype=group_keys[3],
                                signal=mx.ValueArray(values=array_2d, unit="a.u.",
                                                    conditions=None if _conditions_multi == {} else _conditions_multi),
                                axes=data_dict,
                                conditions=_conditions_single
                        )
                        ea.nx_name = f'{sample} {subfolder}'
                        papp.effects.append(ea)
                    else:
                        signal = None
                        signal_name = None
                        auxiliary = {}
                        data_dict: Dict[str, mx.ValueArray] = {}
                        
                        for i, (index, row) in enumerate(group_df.iterrows()):
                            spe_y = row['spe'].y
                            spe_x = row['spe'].x

                            _name = "Raman intensity"
                            _axes = ["Raman shift"]
                            _signal_meta = None
                            _spemeta = None
                            for key in row['spe'].meta.get_all_keys():
                                if key == "@signal":
                                    _name = row['spe'].meta[key]
                                elif key == "@axes":
                                    _axes = row['spe'].meta[key]
                                else:
                                    if _spemeta is None:
                                        _spemeta = {}
                                    _spemeta[f'META_{key}'] = str(row['spe'].meta[key])
                            #_name = row['spe'].meta["@signal"] if "@signal" in row['spe'].meta.get_all_keys() else "Raman intensity"
                            #_axes = row['spe'].meta["@axes"] if "@axes" in row['spe'].meta.get_all_keys() else ["Raman shift"]

                            replicate_number = row['replicate']
                            if signal is None:
                                
                                signal_endpointtype = "RAW_DATA" if _name == "" else _name
                                signal = spe_y
                                if _spemeta is None:
                                    _spemeta = {}
                                _signal_meta = _spemeta
                                _signal_meta["REPLICATE"] = str(replicate_number)
                                data_dict : Dict[str, mx.ValueArray] = { "Raman shift": mx.ValueArray(values=spe_x, unit="1/cm")}
                            else:
                                _spemeta["REPLICATE"] = str(replicate_number)
                                # auxiliary["{}".format(row["basename"])] = mx.MetaValueArray(values=spe_y,unit="a.u",conditions=_spemeta)
                                auxiliary["Raman intensity ({})".format(row["replicate"])] = mx.MetaValueArray(values=spe_y, unit="a.u", conditions=_spemeta)
                        #print(papp.uuid,auxiliary)                           
                        ea = mx.EffectArray(
                                endpoint="Raman intensity",
                                endpointtype=signal_endpointtype,
                                signal=mx.ValueArray(values=signal, unit="a.u.",auxiliary=auxiliary, conditions=_signal_meta),
                                axes=data_dict,
                                #conditions={replicate : row[replicate]} # , "Original file" : meta["Original file"]}
                                conditions={"grouped_by" : ', '.join(map(str, group_keys))}
                        )
                        ea.nx_name = f'{sample} {subfolder}'
                        papp.effects.append(ea)
                except Exception as e:
                    traceback.print_exc()
                    print(e, group_keys)

            substance.study.append(papp)
        substances.append(substance)       
    return mx.Substances(substance=substances)

df, df_meta = read_template(os.path.join(root_folder, template_metadata))
# join file list and meta
result = pd.merge(df, df_meta, how='outer', left_on='Instrument/OP ID', right_on='Identifier (ID)')
#drop column with nans
result.dropna(axis=1, how='all', inplace=True)
result.columns

# tbd read these from the template instead
investigation = "CHARISMA_STUDY_PEAK_FITTING"
provider = "CHARISMA"
prefix = "CRMA"

try:
    _meta = df_meta

    for folder in result["Path"].unique():
        _tmp = result.loc[result["Path"] == folder]
        head, tail = os.path.split(folder)
        if head:
            os.makedirs(os.path.join(product["nexus"], head), exist_ok=True) 

        substances = process_files(root_folder, _tmp, _meta.columns, multidimensional=multidimensional)

        nxroot = nx.NXroot()
        substances.to_nexus(nxroot)
        file = os.path.join(os.path.join(product["nexus"], "{}.nxs".format(folder)))
        nxroot.attrs["pyambit"] = "0.0.1"
        nxroot.attrs["file_name"] = os.path.basename(file)
        nxroot.save(file, mode="w")
except Exception as err:
    traceback.print_exc()
    print(err)