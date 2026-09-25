# Lepton Collider Geometery (lcgeo)
### 1. Prerequisits
#### Install DD4hep with GEANT4 and LCIO
To install the DD4hep, go to the DD4hep repository.

### 2. Initialize defendencies
```
source source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh
```
### 3. Cloning lcgeo
```
cd /path/to/directory

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
