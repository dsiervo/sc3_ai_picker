# sgc_ai_picker

![GitHub last commit](https://img.shields.io/github/last-commit/dsiervo/sgc_ai_picker)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

--------------
## Descripción 
Implementación en el sistema SeisComP3 del Servicio Geológico Colombiano de [PhaseNet](https://github.com/wayneweiqiang/PhaseNet) y [EQTransformer](https://github.com/smousavi05/EQTransformer).
Permite la creación de eventos en seiscomp a partir de los picks obtenidos con EQTransformer o PhaseNet.


El script principal **ai_picker.py** lee los parámetros desde el archivo ai_picker.inp en el directorio de trabajo y según sus preferencias permite descargar y seleccionar seismogramas, y crear eventos en seiscomp a partir de esos picks.

--------------
## Instalación

### Requisitos

- [Anaconda3](https://www.anaconda.com/products/individual)
- [SeisComP3](https://www.seiscomp.de/seiscomp3/)

### Crear el entorno virtual eqt
```bash
$ conda create -n eqt python=3.7
$ conda activate eqt
(eqt) $
```

### Clonar el repositorio
```bash
(eqt) $ git clone https://github.com/dsiervo/sgc_ai_picker.git
(eqt) $ cd sgc_ai_picker
```


### Instalar los requisitos
```bash
(eqt) $ pip install -r requirements.txt
```
### Configurar el entorno
#### Mejorando la descarga de señales
El siguiente paso es necesario para mejorar la performance al descargar señales usando EQTransformer.
Editar el archivo `<su ruta de anaconda3>/envs/eqt/lib/python3.7/site-packages/EQTransformer/utils/downloader.py` y agregar la siguiente línea antes de la línea `with ThreadPool(n_processors) as p:`

```python
n_processor = len(station_dic)
```

#### Configurando el entorno en ai_picker.py
Editar el archivo `ai_picker.py` y modificar la variable anaconda_path en la función **change_env**.

##### Agregar sgc_ai_picker a tu PATH
1. Editar el archivo `~/.bashrc` y agregar la siguiente línea:
```bash
export PATH="<su ruta a sgc_ai_picker>:$PATH"
```
2. En tu terminal ejecute `source ~/.bashrc` para recargar el entorno.
--------------
## Uso

### Modo antiguo de datos

### Modo Semi-realtime

### Modo Realtime
