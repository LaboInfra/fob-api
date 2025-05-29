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
            project = self.session.get(Project, service.project_id)
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
    
    def create_proxy(self, project: Project, rule: str, target: str):
        """
        Create a new proxy service map.
        """
        # check if not already exists
        existing_proxy = self.session.exec(
            select(ProxyServiceMap).where(
                (ProxyServiceMap.project_id == project.id) &
                (ProxyServiceMap.rule == rule) &
                (ProxyServiceMap.target == target)
            )
        ).first()
        if existing_proxy:
            return existing_proxy
        new_proxy = ProxyServiceMap(project_id=project.id, rule=rule, target=target)
        self.session.add(new_proxy)
        self.session.commit()
        return new_proxy
    
    def get_proxy_by_project(self, project: Project):
        """
        Get all proxy service maps for a given project.
        """
    
        return self.session.exec(select(ProxyServiceMap).where(ProxyServiceMap.project_id == project.id)).all()
    
    def delete_proxy(self, proxy: ProxyServiceMap):
        """
        Delete a proxy service map.
        """    
        self.session.delete(proxy)
        self.session.commit()
        return True
    
    def validate_targets(self, targets: list[str]) -> bool:
        """
        Validate the target URL format. Only allow student networks.
        """
        for target in targets:
            if not target.startswith("http://172.16"):
                return False
        return True