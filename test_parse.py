#!/usr/bin/env python3

import subprocess
import re

def parse_wdutil_output(txt):
    rssi, noise = None, None
    in_wifi_section = False
    
    for line in txt.splitlines():
        line = line.strip()
        
        if line == 'WIFI':
            in_wifi_section = True
            print('Entering WIFI section')
            continue
        
        if line.startswith('————') and in_wifi_section:
            continue
        elif in_wifi_section and len(line) > 0 and not line.startswith('————') and line.isupper() and not ':' in line:
            print(f'Leaving WIFI section at: {line}')
            in_wifi_section = False
            continue
            
        if in_wifi_section:
            if 'RSSI' in line and ':' in line:
                print(f'Found WiFi RSSI line: {line}')
                try:
                    value_part = line.split(':')[1].strip()
                    rssi = float(re.findall(r'[-]?\d+', value_part)[0])
                    print(f'Extracted WiFi RSSI: {rssi}')
                except Exception as e: 
                    print(f'Error parsing RSSI: {e}')
            elif 'Noise' in line and ':' in line:
                print(f'Found Noise line: {line}')
                try:
                    value_part = line.split(':')[1].strip()
                    noise = float(re.findall(r'[-]?\d+', value_part)[0])
                    print(f'Extracted Noise: {noise}')
                except Exception as e: 
                    print(f'Error parsing Noise: {e}')
                
    return rssi, noise

if __name__ == "__main__":
    # code called when the program starts.
    # command to fetch wdutil
    cmd = ['sudo', 'wdutil', 'info']
    out = subprocess.check_output(cmd, text=True)
    rssi, noise = parse_wdutil_output(out)
    print(f'Final result: RSSI={rssi}, Noise={noise}')
