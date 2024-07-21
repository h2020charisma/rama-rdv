
from pynanomapper.clients.service_charisma import H5Service
import json
from pynanomapper.clients.datamodel_simple import StudyRaman, Substance
import h5py,h5pyd
import numpy as np

class ExportService(H5Service):

    def __init__(self,tokenservice):
        super().__init__(tokenservice)

    #hnsw embeddings are better with 2^n dimension

    def ramanchada2ambit(self,file_name,  substances={}, owner="CHARISMA",dim=1024):
        self.tokenservice.refresh_token()
        with h5pyd.File(file_name,api_key=self.tokenservice.api_key()) as h5:
            
            (cdf,pdf) = StudyRaman.h52embedding(h5,dataset="raw",xlinspace = StudyRaman.x4search())

            _sample = h5["annotation_sample"].attrs["sample"]
            _tags = ["investigation", "provider"]
            _annotation_study = "annotation_study"
            _params = {}
            for attr in h5[_annotation_study].attrs:
                _attr = attr
                if attr in _tags:
                    pass
                else:
                    if _attr == "native_filename":
                        _attr = "__input_file_s"
                    else:
                        _attr = attr + "_s"
                    _params[_attr] = h5[_annotation_study].attrs[attr]

            if _sample not in substances:
                substances[_sample] = Substance(
                    _sample, _sample, owner_name=owner, substance_type=self.lookup_substancetype(_sample))
            substances[_sample].add_study(StudyRaman(
                h5[_annotation_study].attrs["investigation"],
                h5[_annotation_study].attrs["provider"],
                _params, file_name,(np.round(cdf[0:dim],decimals=4).tolist(),np.round(pdf[0:dim],decimals=4).tolist())))
            return substances


    def lookup_substancetype(self,name):
        _dict = {
            "S0B": "CHEBI_26677",
            "S0N": "CHEBI_26677",
            "S1N": "CHEBI_26677",
            "S0P": "CHEBI_26677",
            "SIL": "CHEBI_26677",
            "NCAL": "CHEBI_46719",
            "SCAL": "CHEBI_46719",
            "PST": "CHEBI_61642"

        }
        try:
            return _dict[name.upper()]
        except Exception as err:
            return "CHEBI_59999"

    def index_chada(self,parentdomain,domain,results={}):
        #with h5pyd.File(domain) as f:
        #    wavelength = f["annotation_study"].attrs["wavelength"]
        #    sample = f["annotation_sample"].attrs["sample"]
        if domain.endswith(".cha"):
            try:
                results = self.ramanchada2ambit(domain, results)
            except Exception as err:
                print(err)




    @staticmethod
    def substances2solrindex(substances,solr_json_index):
        with open(solr_json_index, 'w') as outfile:
            outfile.write("[")
            _sep = ""
            for key in substances:
                outfile.write(_sep)
                outfile.write(json.dumps(substances[key].to_solr_json()))
                _sep = ","
                outfile.flush()
            outfile.write("]")


    def export_config(self,hsds_investigation,config_input,solr_json_index):
        substances = {}
        # for _file in _files:
        #    substances = ramanchada2ambit(_file, substances)
        with open(config_input, 'r') as infile:
            config = json.load(infile)
        for entry in config:
            print(entry)
            # if not entry["enabled"]:
            #    continue
            self.tokenservice.refresh_token()
            try:
                h5domain = "/{}/".format(hsds_investigation)
                                                #entry["hsds_provider"], entry["hsds_instrument"], entry["hsds_wavelength"])
                domain = h5pyd.Folder(h5domain, api_key=self.tokenservice.api_key())
                _ndatasets = -1
                _r = 0
                n = domain._getSubdomains()
                if n > 0:
                    for s in domain._subdomains:
                        file_name = s["name"]
                        if file_name.endswith(".cha"):
                            try:
                                substances = self.ramanchada2ambit(file_name, substances)
                            except Exception as xerr:
                                print(xerr,file_name)
            except Exception as err:
                print(err)

        with open(solr_json_index, 'w') as outfile:
            outfile.write("[")
            _sep = ""
            for key in substances:
                outfile.write(_sep)
                outfile.write(json.dumps(substances[key].to_solr_json(hsds_investigation)))
                _sep = ","
                outfile.flush()
            outfile.write("]")
