## Shotwell-EventVsFolderGUI

# :exclamation: This is in alpha state, do not expect it to work correctly yet!

A small PyGObject-(GTK)-based decision tool to move photos into folders matching their events name or rename events
based on their photo's folder name.

# Installation

```bash
git clone git@github.com:pokulo/Shotwell-EventVsFolderGUI.git
cd Shotwell-EventVsFolderGUI
virtualenv venv
source venv/bin/activate
pip install requirements.txt
python3 shotwell_sync.py <path-to-photo.db> <path-to-photo-directory>
```