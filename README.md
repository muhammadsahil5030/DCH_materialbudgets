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
### 5. Material Budget Scan with g4PolarAngleScan
A general material-budget scan can be performed using:
```
g4PolarAngleScan \
  -c <compact_geometry.xml> \
  -o <output_file.root> \
  --angleDef <theta|eta|cosTheta> \
  --minValue <minimum_angle> \
  --maxValue <maximum_angle> \
  -b <bin_width> \
  --eventsPerBin <number_of_events_per_bin> \
  --ignoreMats Air Vacuum \
  --seed <seed>
```

#### Main Options
-c — DD4hep compact geometry file
-o — Output ROOT file
--angleDef — Angular variable used for the scan: theta, eta, or cosTheta
--minValue — Minimum value of the scan range
--maxValue — Maximum value of the scan range
-b — Angular bin width
--eventsPerBin — Number of random $\phi$ directions generated per angular bin
--ignoreMats — Materials excluded from the material-budget calculation
--seed — Random-number seed
