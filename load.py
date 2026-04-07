import requests
import os
import sys
import json
import copy
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVE_PATH = os.path.join(DATA_DIR, "balanced_config.json")

SOURCE_URL = "https://raw.githubusercontent.com/zieng2/wl/main/vless_lite.txt"
KEYWORDS = ["VK", "Yandex", "Selectel", "Timeweb", "CDNvideo"]

# Define Routing Lists
BLOCK_DOMAINS = [
    "domain:extmaps-api.yandex.net",
    "domain:appmetrica.yandex.ru",
    "domain:adfstat.yandex.ru",
    "domain:metrika.yandex.ru",
    "domain:offerwall.yandex.net",
    "domain:adfox.yandex.ru",
    "domain:mc.yandex.ru",
    "domain:analytics.google.com",
    "domain:api.bugsnag.com",
    "domain:app.bugsnag.com",
    "domain:browser.sentry-cdn.com",
    "domain:app.getsentry.com",
    "domain:ads.vk.com",
    "domain:ad.mail.ru",
    "domain:top-fwz1.mail.ru",
    "domain:ads.huawei.com",
    "domain:adsdk.yandex.ru",
    "domain:analytics.mobile.yandex.net"
]

DIRECT_DOMAINS = [
    "domain:yandex.ru",
    "domain:yandex.net",
    "domain:yandex.com",
    "domain:ya.ru",
    "domain:vk.com",
    "domain:vk.me",
    "domain:vk-cdn.net",
    "domain:mail.ru",
    "domain:ok.ru",
    "domain:gosuslugi.ru",
    "domain:mos.ru",
    "domain:nalog.gov.ru",
    "domain:ozon.ru",
    "domain:wildberries.ru",
    "domain:avito.ru",
    "domain:sberbank.ru",
    "domain:sber.ru",
    "domain:tinkoff.ru",
    "domain:tbank.ru",
    "domain:alfabank.ru",
    "domain:vtb.ru",
    "domain:gazprombank.ru",
    "domain:rutube.ru",
    "domain:kinopoisk.ru"
]

# The new base configuration utilizing burstObservatory, leastping balancing, and custom routing
BASE_CONFIG = {
    "burstObservatory": {
        "pingConfig": {
            "timeout": "3s",
            "interval": "1m",
            "sampling": 1,
            "destination": "http://www.gstatic.com/generate_204",
            "connectivity": ""
        },
        "subjectSelector": ["proxy"]
    },
    "dns": {
        "servers": ["1.1.1.1", "1.0.0.1"],
        "queryStrategy": "UseIP"
    },
    "routing": {
        "balancers": [
            {
                "tag": "Super_Balancer",
                "selector": ["proxy"],
                "strategy": {
                    "type": "leastLoad",
                    "settings": {
                        "maxRTT": "1s",
                        "expected": 2,
                        "baselines": ["1s"],
                        "tolerance": 0.01
                    }
                },
                "fallbackTag": "direct"
            }
        ],
        "rules": [
            {
                "type": "field",
                "domain": BLOCK_DOMAINS,
                "outboundTag": "block"
            },
            {
                "type": "field",
                "domain": DIRECT_DOMAINS,
                "outboundTag": "direct"
            },
            {
                "type": "field",
                "protocol": ["bittorrent"],
                "outboundTag": "direct"
            },
            {
                "type": "field",
                "network": "tcp,udp",
                "balancerTag": "Super_Balancer"
            }
        ],
        "domainMatcher": "hybrid",
        "domainStrategy": "IPIfNonMatch"
    },
    "inbounds": [
        {
            "tag": "socks",
            "port": 10808,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {
                "udp": True,
                "auth": "noauth"
            },
            "sniffing": {
                "enabled": True,
                "routeOnly": False,
                "destOverride": ["http", "tls", "quic"]
            }
        },
        {
            "tag": "http",
            "port": 10809,
            "listen": "127.0.0.1",
            "protocol": "http",
            "settings": {
                "allowTransparent": False
            },
            "sniffing": {
                "enabled": True,
                "routeOnly": False,
                "destOverride": ["http", "tls", "quic"]
            }
        }
    ],
    "outbounds": [
        {
            "tag": "direct",
            "protocol": "freedom"
        },
        {
            "tag": "block",
            "protocol": "blackhole"
        }
    ]
}

def parse_vless_to_outbound(url_str, index):
    """Parses a vless:// URI and returns a single outbound dictionary object."""
    parsed = urlparse(url_str)
    
    if parsed.scheme != "vless":
        raise ValueError("Not a valid vless:// URL")

    # Extract ID, Address, and Port
    user_info, host_port = parsed.netloc.split('@')
    uuid = user_info
    address, port = host_port.split(':')
    port = int(port)

    # Extract Query Parameters
    query = parse_qs(parsed.query)
    
    # We can extract remarks just for terminal logging
    remarks = unquote(parsed.fragment)

    def get_q(key, default=""):
        return query.get(key, [default])[0]

    network = get_q("type", "tcp")
    security = get_q("security", "none")

    # Build outbound proxy dictionary
    # Important: The tag starts with "proxy-" to match the selector ["proxy"]
    proxy_outbound = {
        "tag": f"proxy-{index}",
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": address,
                "port": port,
                "users": [{
                    "encryption": get_q("encryption", "none"),
                    "id": uuid,
                    "level": 8,
                    "security": "auto"
                }]
            }]
        },
        "streamSettings": {
            "network": network,
            "security": security
        }
    }

    # Optional MUX config (if you want it enabled/disabled explicitly)
    proxy_outbound["mux"] = {
        "concurrency": -1,
        "enabled": False,
        "xudpConcurrency": 8,
        "xudpProxyUDP443": ""
    }

    # Assign flow if provided (usually for xtls-rprx-vision)
    flow = get_q("flow", "")
    if flow:
        proxy_outbound["settings"]["vnext"][0]["users"][0]["flow"] = flow

    # Configure Transport Protocol (Network) Settings
    if network == "tcp":
        proxy_outbound["streamSettings"]["tcpSettings"] = {
            "header": {"type": get_q("headerType", "none")}
        }
    elif network == "grpc":
        proxy_outbound["streamSettings"]["grpcSettings"] = {
            "serviceName": get_q("serviceName", ""),
            "multiMode": get_q("mode", "gun") == "multi"
        }
    elif network == "ws":
        proxy_outbound["streamSettings"]["wsSettings"] = {
            "path": get_q("path", "/"),
            "headers": {"Host": get_q("host", "")}
        }

    # Configure Security Settings (TLS or Reality)
    if security == "tls":
        proxy_outbound["streamSettings"]["tlsSettings"] = {
            "allowInsecure": False,
            "serverName": get_q("sni", ""),
            "fingerprint": get_q("fp", "chrome"),
            "show": False
        }
        alpn = get_q("alpn", "")
        if alpn:
            proxy_outbound["streamSettings"]["tlsSettings"]["alpn"] = alpn.split(",")
            
    elif security == "reality":
        proxy_outbound["streamSettings"]["realitySettings"] = {
            "publicKey": get_q("pbk", ""),
            "shortId": get_q("sid", ""),
            "serverName": get_q("sni", ""),
            "fingerprint": get_q("fp", "chrome"),
            "show": False,
            "spiderX": get_q("spx", "")
        }

    return proxy_outbound, remarks

def update_and_generate_balanced_config():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        print("Fetching latest servers...")
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        # Load the base config into memory
        final_config = copy.deepcopy(BASE_CONFIG)
        proxy_outbounds = []
        processed_count = 0

        for line in lines:
            line = line.strip()
            if not line or "#" not in line:
                continue

            parts = line.split("#", 1)
            tag = parts[1]
            
            # Check if keyword exists in tag
            if any(k.lower() in tag.lower() for k in KEYWORDS):
                try:
                    # Pass processed_count to uniquely tag each proxy (proxy-0, proxy-1, etc.)
                    outbound_json, remarks = parse_vless_to_outbound(line, processed_count)
                    
                    # We inject a pseudo-comment for readability in the final JSON (Xray safely ignores unknown fields beginning with _)
                    outbound_json["_comment"] = remarks 
                    
                    proxy_outbounds.append(outbound_json)
                    processed_count += 1
                except Exception as e:
                    print(f"Failed to parse link for '{tag}': {e}")
        
        # Insert all dynamically generated proxies at the beginning of the outbounds list
        final_config["outbounds"] = proxy_outbounds + final_config["outbounds"]

        # Write to single file
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(final_config, f, indent=4, ensure_ascii=False)
                        
        print(f"Success! Processed {len(lines)} total links.")
        print(f"Generated a unified load-balanced config with {processed_count} proxies.")
        print(f"Saved to: {SAVE_PATH}")
        
    except Exception as e:
        print(f"Error during process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_and_generate_balanced_config()