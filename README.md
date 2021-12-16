# sgc_ai_picker

![GitHub last commit](https://img.shields.io/github/last-commit/dsiervo/sgc_ai_picker)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

--------------
## Description 
[PhaseNet](https://github.com/wayneweiqiang/PhaseNet) and [EQTransformer](https://github.com/smousavi05/EQTransformer) implementation in the SeisComP3 system of the Colombian Geological Survey.
Allows events creation in seiscomp from Phasenet of EQTransformer picks.

The main script **ai_picker.py** reads the parameters from the ai_picker.inp in the working directory and according to your preferences allows you to download and pick waveforms, and to create SeisComP3 events from those picks.
