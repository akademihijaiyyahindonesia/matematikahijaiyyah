#!/bin/bash
set -e
cd "/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-security-integration"
chmod +x scripts/run_usss_sram_load.py
python3 scripts/run_usss_sram_load.py --run-id run2
