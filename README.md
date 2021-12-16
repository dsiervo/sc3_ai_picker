# sgc_ai_picker

![GitHub last commit](https://img.shields.io/github/last-commit/dsiervo/sgc_ai_picker)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

--------------
## Description 
[PhaseNet](https://github.com/wayneweiqiang/PhaseNet) and [EQTransformer](https://github.com/smousavi05/EQTransformer) implementation in the SeisComP3 system of the Colombian Geological Survey.
Allows events creation in seiscomp from Phasenet of EQTransformer picks.

The main script **ai_picker.py** reads the parameters from the ai_picker.inp in the working directory and according to your preferences allows you to download and pick waveforms, and to create SeisComP3 events from those picks.

--------------
## Installation

### Requirements

- [Anaconda3](https://www.anaconda.com/products/individual)
- [SeisComP3](https://www.seiscomp.de/seiscomp3/)

### Create eqt virtual environment
```bash
$ conda create -n eqt python=3.7
$ conda activate eqt
(eqt) $
```

### Clone the repository
```bash
(eqt) $ git clone https://github.com/dsiervo/sgc_ai_picker.git
(eqt) $ cd sgc_ai_picker
```

### Install the requirements
```bash
(eqt) $ pip install -r requirements.txt
```
### Configure the environment
#### Improving the waveform download
The following steps are required to improve the performance when downloading waveforms using EQTransformer.
Edit the file `<your anaconda3 path>/envs/eqt/lib/python3.7/site-packages/EQTransformer/utils/downloader.py` and add the following line in the **downloadMseed** function before the line `with ThreadPool(n_processors) as p:`

```python
n_processor = len(station_dic)
```

#### Setting up the environment in ai_picker.py
Edit the file `ai_picker.py` and modify the anaconda_path variable to your anaconda3 path in the **change_env** function.

##### Add sgc_ai_picker to your PATH
1. Edit the file `~/.bashrc` and add the following line:
```bash
export PATH="<your sgc_ai_picker path>:$PATH"
```
2. In your terminal run `source ~/.bashrc` to reload the environment.
--------------
## Usage

### Old data mode

### Semi-realtime mode

### Realtime mode
