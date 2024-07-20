# + tags=["parameters"]
upstream = []
product = None
hsds_investigation = None
config_input = None
hs_username = None
hs_password = None
keycloak_server_url = None
keycloak_client_id = None
keycloak_realm_name = None
# -


from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from keycloak import KeycloakOpenID
from services.serviceclasses import TokenService
from services.service_export import ExportService


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

    exportservice = providers.Factory(
        ExportService,
        tokenservice = tokenservice
    )


@inject
def main(es = Provide[Container.exportservice]):
    es.login(hs_username,hs_password)
    try:
        #es.export(hsds_investigation,config_input,product["data"])
        #es.export(hsds_investigation,product["data"])
        results = {}
        for investigation in ["SANDBOX","Round_Robin_1","TEST","SILICON_STUDY"]:
            es.visit_domain("/{}/".format(investigation),
                    process_dataset=es.index_chada,kwargs= {"results" : results})
        print(len(results))
        ExportService.substances2solrindex(results,product["data"])
    except Exception as err:
        print(err)
    finally:
        es.logout()



print(__name__)
container = Container()
container.init_resources()
container.wire(modules=[__name__])
main()


