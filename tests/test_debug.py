
# Add the project root to the Python path first
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import the modules
import asyncio
from src.cli import _generate

# Hardcoded test parameters
url = "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/Nezha_Inventor_s_kit_for_microbit_case_75"
output_dir = "D:/Coderdojo/Projects"  # Renamed to avoid conflict with function parameter
verbose = True
no_enhance = False
no_translate = False
no_qrcode = False
no_makecode = False
no_download = False


print(f"Generating guide from: {url}")
print(f"Output directory: {output_dir}")
print(f"Options: verbose={verbose}, no_enhance={no_enhance}, no_translate={no_translate}")
print(f"Options: no_qrcode={no_qrcode}, no_makecode={no_makecode}, no_download={no_download}")

# Run the generation
asyncio.run(_generate(url, output_dir, verbose, no_enhance, no_translate, no_qrcode, no_makecode, no_download))
