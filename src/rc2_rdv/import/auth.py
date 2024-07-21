# + tags=["parameters"]
from datetime import date
upstream = []
product = None
hs_endpoint = None
ramandb_api = None
hs_username = None
hs_password = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None

# -

import json
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from pynanomapper.clients.authservice import TokenService, QueryService

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

    queryservice = providers.Factory(
        QueryService,
        tokenservice = tokenservice
    )


@inject
def main(qs = Provide[Container.queryservice]):
    try:
        qs.login(hs_username,hs_password)
        try:
            api_metadata = "{}metadata".format(ramandb_api)
            print(api_metadata)
        except Exception as err:
            print(err)
        try:
            response = qs.get(hs_endpoint+"/domains", params={"domain" : "/"})
            
            with open(product["domains"], 'w') as json_file:
                json.dump(response.json(), json_file, indent=4)

        except Exception as err:
            print(err)

    except Exception as err:
        print(err)
    finally:
        qs.logout()


print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()
