# op1z-sample-manager

**NEW: OP-1 Support Added! New Features!** Sample manager supports OP-1, plus tape track exporter and backup/restore feature

This is a Flask app built with PyQt5 to handle everything with samples on the OP-Z. As time goes on, I'm adding more features around project management, export, and other various utilities.


### Run app using:
1) Install requirements in ```requirements.txt``` 
2) ```python main.py``` **or** build app by running ```./build.sh```, and run the created executable under ```dist/```

To build the app on linux, also install requirements in ```requirements-linux-gui.txt``` and any dependencies of that library.

### Using the App:
- Double check that all paths are set correctly in Utility Settings
- Connect your device in disk mode and begin managing your samples, tapes, projects, and more!

## Screenshots
### Home Page:
![home page](/screenshots/homepage.png)

### Sample Manager:
![sample manager OP-Z](/screenshots/samplemanageropz.png)
![sample manager OP-Z](/screenshots/samplemanagerop1.png)

### Sample Converter:
![sample converter](/screenshots/sampleconverter.png)

### Config File Editor:
![config file editor](/screenshots/configeditoropz.png)

### Tape Exporter:
![tape exporter op1](/screenshots/tapeexport.png)

### Backup and Restore:
![Backup and Restore OP-Z](/screenshots/backupandrestoreopz.png)
![Backup and Restore OP-1](/screenshots/backupandrestoreop1.png)

### Utility Settings:
![utility settings](/screenshots/utilitysettings.png)

## Third-Party Licenses

This application includes the following third-party software:

### FFmpeg
This software uses libraries from the [FFmpeg project](https://ffmpeg.org/) under the LGPLv2.1.
FFmpeg source code is available at https://ffmpeg.org/download.html
