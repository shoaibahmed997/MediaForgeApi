import tldextract
from urllib.parse import urlparse, urlunparse,quote,parse_qs
from core.service_config import services
from core.utils import get_service_from_url,pattern_to_regex
import re
def get_host_if_valid(url:str):
    result = tldextract.extract(url=url)
    service = services[result.domain]
    if not service:
        raise ValueError("Service not supported")
    return result.domain


def extract(url:str):
    service = get_service_from_url(url)
    print(f"  Service detected: {service}")
    
    if not service:
        return("Result: {'error': 'link.invalid'}")
    
    parsed = urlparse(url)
    path_part = parsed.path.lstrip("/")
    query_part = f"?{parsed.query}" if parsed.query else ""
    match_input = path_part + query_part
    
    service_config = services[service]
    patterns = service_config.get("patterns",[])

    for pattern in patterns:
        regax_str = pattern_to_regex(pattern)
        match = re.match(regax_str,match_input)
        if match:
            return {
                "host":service,
                "patternMatch":match.groupdict()
            }
    
    return {
        "error": "link.unsupported",
        "context": {
            "service": service  # Could add friendly name here if desired
        }
    }

    

def parse_domain(hostname:str) -> dict:
    extracted = tldextract.extract(hostname)

    return {
       "subdomain": extracted.subdomain or None,
        "domain": extracted.domain,      
        "suffix": extracted.suffix,      
        "sld": extracted.domain,         
        "tld": extracted.suffix.split(".")[-1] if extracted.suffix else None,  
        "registered_domain": extracted.registered_domain  

    }

def _get_query_param(url:str,param:str):
    parsed = urlparse(url)
    params = parse_qs(parsed.query,keep_blank_values=True)
    values = params.get(param,[])
    return values[0] if values else None

def alias_url(url:str) -> str:
    """
    Convert alternative/short URLs to canonical format.
    
    Takes URL string, returns transformed URL string.
    """
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    if not hostname:
        print('error: no hostname found')
        return url

    domain_info = parse_domain(hostname)
    host = domain_info["sld"]
    
    parts = [p for p in parsed_url.path.split("/") if p] 

    match host:
        case "youtube":
            if parsed_url.path.startswith("/live/") or parsed_url.path.startswith("/shorts/"):
                # parts = ["shorts","vgksle"] or ["live","jsdlkf"] no empty segment since we remove it above.
                if len(parts) >=2:
                    video_id = quote(parts[1],safe="")
                    return f"https://youtube.com/watch?v={video_id}"
        
        case "youtu":
            if parsed_url.hostname == "youtu.be" and len(parts) >=1:
                video_id = quote(parts[0],safe="")
                return f"https://youtube.com/watch?v{video_id}"
        # ─────────────────────────────────────
        # Pinterest: pin.it/ID → pinterest.com/url_shortener/ID
        # ─────────────────────────────────────
        case "pin":
            if domain_info["registered_domain"] == "pin.it" and len(parts) == 1:
                short_id = quote(parts[0], safe="")
                return f"https://pinterest.com/url_shortener/{short_id}"
        
        # ─────────────────────────────────────
        # Twitter: alt domains (vxtwitter, fixvx, x.com) → twitter.com
        # ─────────────────────────────────────
        case "vxtwitter" | "fixvx" | "x":
            alt_domains = services.get("twitter", {}).get("altDomains", [])
            if hostname in alt_domains:
                # Rebuild URL with twitter.com hostname, keep path/query
                return urlunparse((
                    parsed_url.scheme,
                    "twitter.com",
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    ""  # Strip fragment
                ))
        
        # ─────────────────────────────────────
        # Twitch: clips.twitch.tv/ID → twitch.tv/_/clip/ID
        # ─────────────────────────────────────
        case "twitch":
            if hostname == "clips.twitch.tv" and len(parts) >= 1:
                clip_id = quote(parts[0], safe="")
                return f"https://twitch.tv/_/clip/{clip_id}"
        
        # ─────────────────────────────────────
        # Bilibili: bilibili.tv/PATH → bilibili.com/_tv/PATH
        # ─────────────────────────────────────
        case "bilibili":
            if domain_info["suffix"] == "tv":
                return f"https://bilibili.com/_tv{parsed_url.path}"
        
        # ─────────────────────────────────────
        # B23: b23.tv/ID → bilibili.com/_shortLink/ID
        # ─────────────────────────────────────
        case "b23":
            if hostname == "b23.tv" and len(parts) == 1:
                short_id = quote(parts[0], safe="")
                return f"https://bilibili.com/_shortLink/{short_id}"
        
        # ─────────────────────────────────────
        # Dailymotion: dai.ly/ID → dailymotion.com/video/ID
        # ─────────────────────────────────────
        case "dai":
            if hostname == "dai.ly" and len(parts) == 1:
                video_id = quote(parts[0], safe="")
                return f"https://dailymotion.com/video/{video_id}"
        
        # ─────────────────────────────────────
        # Facebook: handle ?v= param and fb.watch short links
        # ─────────────────────────────────────
        case "facebook" | "fb":
            # Case 1: URL has ?v=VIDEO_ID param → convert to canonical format
            v_param = _get_query_param(url, "v")
            if v_param:
                video_id = quote(v_param, safe="")
                return f"https://web.facebook.com/user/videos/{video_id}"
            
            # Case 2: fb.watch/ID short link
            if hostname == "fb.watch" and len(parts) >= 1:
                short_id = quote(parts[0], safe="")
                return f"https://web.facebook.com/_shortLink/{short_id}"
        
        # ─────────────────────────────────────
        # Instagram: ddinstagram.com alt domains → instagram.com
        # ─────────────────────────────────────
        case "ddinstagram":
            alt_domains = services.get("instagram", {}).get("altDomains", [])
            # Only transform if subdomain is None, "d", or "g"
            if hostname in alt_domains and domain_info["subdomain"] in (None, "d", "g"):
                return urlunparse((
                    parsed_url.scheme,
                    "instagram.com",
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    ""
                ))
        
        # ─────────────────────────────────────
        # VK: alt domains → vk.com, handle ?z= param redirect style
        # ─────────────────────────────────────
        case "vk" | "vkvideo":
            # Transform alt domains to vk.com
            alt_domains = services.get("vk", {}).get("altDomains", [])
            if hostname in alt_domains:
                url = urlunparse((
                    parsed_url.scheme,
                    "vk.com",
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    ""
                ))
                parsed_url = urlparse(url)  # Re-parse after hostname change
            
            # Handle ?z= param: vk.com/some/path?z=video12345_67890 → vk.com/video12345_67890
            z_param = _get_query_param(url, "z")
            if z_param:
                return f"https://vk.com/{z_param}"
        
        # ─────────────────────────────────────
        # Xiaohongshu: xhslink.com/TYPE/ID → xiaohongshu.com/TYPE/ID
        # ─────────────────────────────────────
        case "xhslink":
            if hostname == "xhslink.com" and len(parts) == 2:
                share_type, share_id = parts[0], parts[1]
                return f"https://www.xiaohongshu.com/{share_type}/{share_id}"
        
        # ─────────────────────────────────────
        # Loom: extract last 32 chars of last path segment for share links
        # ─────────────────────────────────────
        case "loom":
            if parts:
                id_part = parts[-1]
                if len(id_part) > 32:
                    short_id = id_part[-32:]  # Take last 32 characters
                    return urlunparse((
                        parsed_url.scheme,
                        parsed_url.netloc,
                        f"/share/{short_id}",
                        parsed_url.params,
                        parsed_url.query,
                        ""
                    ))
        
        # ─────────────────────────────────────
        # Reddit: v.redd.it/ID → reddit.com/video/ID
        # ─────────────────────────────────────
        case "redd":
            if hostname == "v.redd.it" and len(parts) == 1:
                video_id = quote(parts[0], safe="")
                return f"https://www.reddit.com/video/{video_id}"
    
    # ─────────────────────────────────────────────────────────────
    # No transformation matched → return original URL
    # ─────────────────────────────────────────────────────────────
    return url
            
def clean_url(url: str) -> str:
    """
    Strip tracking params, fragments, credentials, ports.
    Keep only essential query params for specific services.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    
    if not hostname:
        return url  
    
    domain_info = parse_domain(hostname)
    host = domain_info["sld"] 
    
    final_query = ""
    
    # ─────────────────────────────────────
    # Service-specific query param handling
    # ─────────────────────────────────────
    
    if host == "pinterest":
        parsed = parsed._replace(netloc="pinterest.com")
        
    elif host == "vk":
        if "/clip" in parsed.path:
            z_val = _get_query_param(url, "z")
            if z_val:
                final_query = f"z={quote(z_val, safe='')}"
                
    elif host == "youtube":
        v_val = _get_query_param(url, "v")
        if v_val:
            final_query = f"v={quote(v_val, safe='')}"
            
    elif host in ("bilibili", "rutube"):
        p_val = _get_query_param(url, "p")
        if p_val:
            final_query = f"p={quote(p_val, safe='')}"
            
    elif host == "twitter":
        post_id = _get_query_param(url, "post_id")
        if post_id:
            final_query = f"post_id={quote(post_id, safe='')}"
            
    
    # ─────────────────────────────────────
    # Rebuild URL with cleaned components
    # ─────────────────────────────────────
    
    clean_netloc = hostname 
    
    clean_path = parsed.path
    if clean_path.endswith("/") and clean_path != "/":
        clean_path = clean_path.rstrip("/")
    
    cleaned = urlunparse((
        parsed.scheme,
        clean_netloc,
        clean_path,
        "",          
        final_query, 
        ""           
    ))
    
    return cleaned

def normalise_url(url:str)->str:
    aliased_url = alias_url(url)
    cleaned_url = clean_url(aliased_url)
    return cleaned_url
