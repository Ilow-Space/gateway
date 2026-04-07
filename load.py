import requests
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVE_PATH = os.path.join(DATA_DIR, "filtered_vless.txt")

SOURCE_URL = "https://raw.githubusercontent.com/zieng2/wl/main/vless_lite.txt"
# These keywords will now ONLY be looked for in the tag after the '#'
KEYWORDS = ["VK", "Yandex", "Selectel", "Timeweb", "CDNvideo"]

def update_file():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        filtered = []

        for line in lines:
            if "#" in line:
                # Split the link and take everything after the first '#'
                parts = line.split("#", 1)
                tag = parts[1]
                
                # Check if any keyword exists specifically in the tag
                if any(k.lower() in tag.lower() for k in KEYWORDS):
                    filtered.append(line)
        
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(filtered))
            
        print(f"Success! Processed {len(lines)} total links.")
        print(f"Filtered down to {len(filtered)} links matching tags: {KEYWORDS}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_file()