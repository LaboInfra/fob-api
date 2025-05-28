from sqlmodel import Session, select
import base64
from fob_api.models.database import ProxyServiceMap, Project

class ProxyManager:

    session = None
    default_traefik_config = {
        "http": {
            "routers": {},
            "services": {},
            "middlewares": {
                "https-redirect": {
                    "redirectScheme": {
                        "scheme": "https",
                        "permanent": True
                    }
                }
            },
            "serversTransports": {
                "ignore-self-signed": {
                    "insecureSkipVerify": True
                }
            },
        },
        "tls": {
            "options": {
                "tlsOptions": {
                    "sniStrict": True,
                    "minVersion": "VersionTLS12",
                    "cipherSuites": [
                        "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                        "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                        "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                        "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                        "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
                        "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
                    ]
                }
            }
        }
    }

    def __init__(self, session: Session):
        """
        Initialize the ProxyManager with a database session.
        """
        if session:
            self.session = session
    
    def build_treafik_config(self):
        # loop over all ProxyServiceMap entries and build the Traefik config
        
        proxy_service_maps = self.session.exec(select(ProxyServiceMap)).all()
        if not proxy_service_maps:
            return self.default_traefik_config
        new_maps = self.default_traefik_config.copy()
        for service in proxy_service_maps:
            project = self.session.exec(select(Project).where(Project.id == service.project_id)).first()
            if not project:
                continue
            uniq_name = f"{base64.b64encode(service.rule.encode()).decode()}".replace("=", "")[5:25]
            uniq_name = f"{project.name}-{uniq_name}"
            new_maps["http"]["routers"][uniq_name+"-http"] = {
                "entrypoints": "web",
                "rule": "Host(`{}`)".format(service.rule),
                "middlewares": ["https-redirect"],
                "service": "{}-service".format(uniq_name),
            }
            new_maps["http"]["routers"][uniq_name+"-https"] = {
                "entrypoints": "websecure",
                "rule": "Host(`{}`)".format(service.rule),
                "service": "{}-service".format(uniq_name),
                "tls": { "certResolver": "certificateResolver" }
            }
            new_maps["http"]["services"]["{}-service".format(uniq_name)] = {
                "loadBalancer": {
                    "servers": [
                        {"url": "".format(service.target)}
                    ],
                    "passHostHeader": True,
                }
            }
        return new_maps