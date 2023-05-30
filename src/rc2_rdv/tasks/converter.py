import h5py
import numpy as np


def write_attributes(h5file, h5path, ambitobj, props=['ownerName', "substanceType", "name", "publicname"]):
    for a in props:
        try:
            h5file.require_group(h5path)
            try:
                h5file[h5path].attrs[a] = ambitobj[a]
            except Exception as err:
                # print(a,err)
                h5file[h5path].attrs[a] = str(ambitobj[a])
        except Exception as err:
            print(err, h5path, ambitobj, props)


def ambit2hdf5(datamodel, h5file):
    for substance in datamodel['substance']:

        # print(substance['ownerName'], substance["substanceType"], substance["name"], substance["publicname"])
        write_attributes(h5file, "/substance/{}".format(
                    substance['i5uuid']), substance,
                    props=["ownerName", "substanceType", "name", "publicname"])
        results = {}
        for study in substance['study']:
            write_attributes(h5file, "/study/{}".format(study['uuid']), study, props=['investigation_uuid', "assay_uuid"])
            write_attributes(h5file, "/study/{}/owner/substance".format(study['uuid']), study['owner']['substance'], props=['uuid'])
            write_attributes(h5file, "/study/{}/owner/company".format(study['uuid']), study['owner']['company'], props=['uuid', 'name'])
            write_attributes(h5file, "/study/{}/citation".format(study['uuid']), study['citation'], props=['title', 'year', 'owner'])
            write_attributes(h5file, "/study/{}/protocol".format(study['uuid']), study['protocol'], props=['topcategory', 'endpoint','guideline'])
            write_attributes(h5file, "/study/{}/protocol".format(study['uuid']), study['protocol']['category'], props=['code', 'title', 'term'])
            for param in study['parameters']:
                write_attributes(h5file, "/study/{}/parameters".format(study['uuid']), study['parameters'], props= [ param])

            # print(study['reliability'])
            dt_effects = np.dtype([("endpoint", float), ("concentration", float), ("time", int)])
            for effect in study['effects']:
                if "unit" in effect:
                    _unit = effect["unit"]
                else:
                    _unit = "None"
                try:
                    if "concentration" in effect["conditions"]:
                        if "unit" in effect["conditions"]["concentration"]:
                            concentration_unit = str(effect["conditions"]["concentration"]["unit"])
                            control = None
                        else:
                            control = effect["conditions"]["concentration"]
                            concentration_unit = "None"
                except Exception as err:
                    # no concentration
                    concentration_unit = "None"
                    control = None
                    pass

                _tag = "/study/{}/results/{}".format(study['uuid'],effect["endpointtype"])
                _tag_endpoint = "{}/{}({})".format(_tag, effect["endpoint"],_unit)
                if not (_tag_endpoint in results):
                    results[_tag_endpoint] = {"dataset": np.array([], dtype=dt_effects), "properties": {}}
                # print(_tag_endpoint,_tmp)
                try:
                    _tmp = results[_tag_endpoint]["dataset"]
                    results[_tag_endpoint]["properties"] = {
                                "endpoint": effect["endpoint"],
                                "endpoint.unit": _unit, "concentration.unit": concentration_unit}
                    # results[_tag_endpoint]["properties"]["unit"] = _unit

                    try:
                        results[_tag_endpoint]["properties"]["E.exposure_time.unit"] = str(effect["conditions"]["E.exposure_time"]["unit"])
                    except Exception as err:
                        pass
                        # print("!!!",err,effect["conditions"]["E.exposure_time"])
                    results[_tag_endpoint]["dataset"]=  np.append(_tmp,
                        np.array([(effect["result"]["loValue"],
                                   effect["conditions"]["concentration"]["loValue"],
                                int(effect["conditions"]["E.exposure_time"]["loValue"])
                                   )], dtype=dt_effects))

                    # print(effect["endpoint"]["loValue"],effect["conditions"]["concentration"]["loValue"])
                except Exception as err:
                    # print(err)
                    pass
                #
                # print(effect["endpoint"])
                # print(effect["endpointtype"])
                # for condition in effect["conditions"]:
                #    print(condition,effect["conditions"][condition])
                #  print(">>result")
                # for result in effect["result"]:
                    #print(result,effect["result"][result])
        #print(results)
        for _tag in results:
            result_dataset = h5file.require_dataset(_tag, data=results[_tag]["dataset"], shape=(len(results[_tag]["dataset"]), ), dtype=dt_effects)
            for prop in results[_tag]["properties"]:
                result_dataset.attrs[prop] = results[_tag]["properties"][prop]
