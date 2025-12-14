# op1z-sample-manager

**NEW: OP-1 Support Added! New Features!** Sample manager supports OP-1, plus tape track exporter and backup/restore feature

This is a Flask app built with PyQt5 to handle everything with samples on the OP-Z. As time goes on, I'm adding more features around project management, export, and other various utilities.


### Run app using:
1) Install requirements in ```requirements.txt```
2) ```python main.py``` **or** build app by running ```./build.sh```, and run the created executable under ```dist/```

### Using the App:
- Set your directories in utility settings:
    - Set your working directory (This is where backups, converted samples, and more are stored)
    - Set your OP-Z mount path (if connected)
    - Set your OP-1 mount path (if connected)

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
