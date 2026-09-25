# Lepton Collider Geometery (lcgeo)
### 1. Prerequisits
#### Install DD4hep with GEANT4 and LCIO
To install the DD4hep, go to the DD4hep repository.

### 2. Initialize defendencies
```
source ~/dd4hep_ws/DD4hep-install/bin/thisdd4hep.sh
```
### 3. Cloning lcgeo
```
cd /path/to/directory/dd4hep_installed

git clone https://github.com/iLCSoft/lcgeo.git

cd lcdeo
mkdir build && cd build
```

### 4. build and install
```
cmake .. \
  -DCMAKE_INSTALL_PREFIX=~/dd4hep_ws/lcgeo-install \
  -DDD4hep_DIR=~/dd4hep_ws/DD4hep-install
```
```
make -j$(nproc)
```
```
make install
```
## Build on Recas
To build it on Recas fisrt we need to source the ROOT
```
source /cvmfs/sft.cern.ch/lcg/releases/ROOT/6.22.00-dd202/x86_64-centos7-gcc10-opt/bin/thisroot.sh
```
Then add the line to bashrc
