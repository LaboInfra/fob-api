import dns.resolver
from typing import List, Optional

from datetime import datetime, timedelta

from sqlmodel import Session, select
from fob_api import engine, Config

from fob_api.models.database import User, Token
from fob_api.worker import celery
from fob_api.tasks import headscale, openstack
from fob_api.models.api import SyncInfo
from fob_api.managers import ProxyManager

@celery.task(name="fob_api.tasks.validate_proxy_domain_host")
def validate_proxy_domain_host():

    CORRECT_IP = Config().traefik_host_ip

    with Session(engine) as session:
        pm = ProxyManager(session)
        for proxy in pm.get_all_proxies():
            # if proxy enabled recheck domain only one week after last check
            # if not enabled recheck domain only if last check was 15minutes ago
            if proxy.latest_dns_check_result:
                if not proxy.latest_dns_check or proxy.latest_dns_check < datetime.now() - timedelta(weeks=1):
                    print(f"Checking domain {proxy.rule} for proxy {proxy.id}")
                    result = check_domain_ip(proxy.rule, CORRECT_IP)
                    proxy.latest_dns_check = datetime.now()
                    proxy.latest_dns_check_result = result
                    print(f"Proxy {proxy.id} domain {proxy.rule} check result: {result}")
                    session.add(proxy)
            else:
                if not proxy.latest_dns_check or proxy.latest_dns_check < datetime.now() - timedelta(minutes=15):
                    print(f"Checking domain {proxy.rule} for proxy {proxy.id}")
                    result = check_domain_ip(proxy.rule, CORRECT_IP)
                    proxy.latest_dns_check = datetime.now()
                    proxy.latest_dns_check_result = result
                    print(f"Proxy {proxy.id} domain {proxy.rule} check result: {result}")
                    session.add(proxy)

            session.commit()

def check_domain_ip(domain: str, target_ip: str, dns_server: Optional[str] = None) -> bool:
    """
    Check if a domain has an A record pointing to a specific IP address.
    
    Args:
        domain: Domain name to check (e.g., "docs.laboinfra.net")
        target_ip: Expected IP address (e.g., "8.8.8.8")
        dns_server: Optional DNS server to use (e.g., "8.8.8.8", "1.1.1.1")
    
    Returns:
        bool: True if domain points to the target IP
    """
    try:
        # Create resolver
        resolver = dns.resolver.Resolver()
        if dns_server:
            resolver.nameservers = [dns_server]
        
        # Get A records
        answers = resolver.resolve(domain, 'A')
        
        # Check if target IP is in the results
        ips = [str(rdata) for rdata in answers]
        print(f"Domain {domain} resolves to: {ips}")
        
        return target_ip in ips
    
    except dns.resolver.NXDOMAIN:
        print(f"Error: Domain {domain} does not exist")
        return False
    except dns.resolver.NoAnswer:
        print(f"Error: No A records found for {domain}")
        return False
    except Exception as e:
        print(f"Error querying DNS: {e}")
        return False