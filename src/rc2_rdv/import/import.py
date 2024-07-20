# + tags=["parameters"]
upstream = ["read_metadata"]
product = None
config_input = None
metadata_root = None
ramandb_api = None
hsds_investigation = None
dry_run = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
hs_username = None
hs_password = None

# -

import json

import os,path
from pprint import pprint
import glob
import pandas as pd

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from services.serviceclasses import TokenService
from services.service_import import ImportService
import traceback




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


@inject
def main(importservice = Provide[Container.importservice], ):
    importservice.login(hs_username,hs_password)
    try:
        print(importservice.hsds_investigation)
        importservice.import2hsds(config_input,metadata_root,product["data"])
    except Exception as err:
        print(err)
    finally:
        importservice.logout()


print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
