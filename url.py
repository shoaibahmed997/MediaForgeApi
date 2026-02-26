import tldextract
from urllib.parse import urlparse
from service_config import services
import re
def get_host_if_valid(url:str):
    result = tldextract.extract(url=url)
    service = services[result.domain]
    print('service is',service)
    if not service:
        raise ValueError("Service not supported")
    return result.domain


def extract(url):
    if isinstance(url,str):
        parsed_url = urlparse(url=url)
    else:
        parsed_url = url
    host = get_host_if_valid(url)
    if not host:
        return {"error":"Link.invalid"}
    
    query_path = parsed_url.path.lstrip("/") + ( "?" + parsed_url.query if parsed_url.query else "")
    print('query path',query_path)
    pattern_match = None
    for pattern in services[host]["patterns"]:
        match = re.match(pattern,query_path)
        print('match is ...',match)
        if match:
            pattern_match = match
            break
    print('pattern match',pattern_match)
    if not pattern_match:
        return {
            "error":"link.unsupported",
            "context":{
                "service": host
            }
        }
    
    return {
        "host":host,
        "pattern_Match":pattern_match.groupdict() if pattern_match else None
    }


    




