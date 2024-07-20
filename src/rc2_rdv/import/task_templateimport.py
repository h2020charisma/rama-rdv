# + tags=["parameters"]
upstream = ["createinvestigation","task_template2metadata"]
product = None
ramandb_api = None
hsds_investigation = None
dry_run = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None
root_peakfitting_folder = None
metadatapath = None
# -

import json

import os.path
from pprint import pprint

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from services.serviceclasses import TokenService
from services.service_import import ImportService
import traceback
from services.metadata4import import Metadata
import glob


class Container(containers.DeclarativeContainer):
    kcclient = providers.Singleton(
        KeycloakOpenID,
        server_url=keycloak_server_url,
        client_id=keycloak_client_id,
        realm_name=keycloak_realm_name,
        client_secret_key="secret"
    )

    tokenservice = providers.Factory(
        TokenService,
        kcclient = kcclient
    )

    importservice = providers.Factory(
        ImportService,
        tokenservice = tokenservice,
        ramandb_api = ramandb_api,
        hsds_investigation = hsds_investigation,
        dry_run = dry_run
    )

def import_plain(path , metadatapath, importservice=None):
    _metadata = {}
    with open(metadatapath, "r",encoding="utf-8") as read_file:
        _metadata = json.load(read_file)
    #print(_metadata)
    files = glob.glob(os.path.join(path,"**","*.*"), recursive=True)
    for filename in files:
        try:
            if filename in _metadata:
                print(filename)
                _m = _metadata[filename]
                print(_m)
                instrument = _m["instrument"].split("/")[0].strip()

                m = Metadata(instrument=instrument,provider=_m["provider"],wavelength=_m["wavelength"])
                fe = m.create_fileentry(files=[filename],laser_power=_m["laser_power"],sample=_m["sample"])

                try:
                    if not dry_run:
                        with open(filename) as _f:
                            response = importservice.submit2hsds(_f,
                                m.get_provider(),m.get_instrument(),m.get_wavelength(),
                                    _m["optical_path"],_m["sample"],laser_power=_m["laser_power"])
                            print(filename,response)
                    else:
                        print(filename,m)
                except Exception as err:
                    print(err)
        except Exception as err:
            print(err)



@inject
def main(importservice = Provide[Container.importservice] ):
    importservice.login(hs_username,hs_password)
    try:
        print(importservice.hsds_investigation)
        import_plain(root_peakfitting_folder , metadatapath, importservice)

    except Exception as err:
        print(err)
    finally:
        importservice.logout()


print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
