# SimRigLights
Code for the badass sim rig lights

## Installation
### As an executable
```bash
pip install pyinstaller
pyinstaller simriglights
```
Run the executable generated in dist/simriglights
#### Windows
Run simriglights.exe

#### Unix
```bash
cd dist/simriglights
./simriglights
```

### To run with python
```bash
python setup.py install
python simriglights.py
```
Dependencies are installed manually on your system, and the application is run with python in a console window

## Testing
```bash
python setup.py test
```
All unit tests are run using [nose](https://nose.readthedocs.io/en/latest/testing.html)
