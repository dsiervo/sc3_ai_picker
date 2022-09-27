# sgc_ai_picker

![GitHub last commit](https://img.shields.io/github/last-commit/dsiervo/sgc_ai_picker)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

--------------
## Descripción 
Implementación en el sistema SeisComP3 del Servicio Geológico Colombiano de [PhaseNet](https://github.com/wayneweiqiang/PhaseNet) y [EQTransformer](https://github.com/smousavi05/EQTransformer).
Permite la creación de eventos en seiscomp a partir de los picks obtenidos con EQTransformer o PhaseNet.


El script principal **ai_picker.py** lee los parámetros desde el archivo ai_picker.inp en el directorio de trabajo y según sus preferencias permite descargar y seleccionar seismogramas, y crear eventos en seiscomp a partir de esos picks.

No se recomienda usar este script directamente, en su lugar se recomienda usar los scripts **discontinuous_picker.py** para picar periodos largos de tiempo de formas de onda ya descargadas y **ai_scheduler.py** para picar y enviar a Seiscomp los picks y eventos generados en semi tiempo real. Estos 2 scripts hace uso interno del ai_picker.py, esto significa que ambos scripts tomarán los parámetros que se especifiquen en un archivo similar al **ai_picker.inp**, `ai_picker_scdl.inp` en el caso de **ai_scheduler.py** y `temp_ai_picker.inp` en el caso de **discontinuous_picker.py**.

--------------
## Instalación

### Requisitos

- [Anaconda3](https://www.anaconda.com/products/individual)
- [SeisComP3](https://www.seiscomp.de/seiscomp3/)

### Descargue el ai_picker
```bash
(eqt) $ git clone https://github.com/dsiervo/sgc_ai_picker.git
(eqt) $ cd sgc_ai_picker
```

### Instale EQTransformer

#### Cree el ambiente virtual para EQTransformer con los siguientes comandos:
```bash
$ conda create -n eqt python=3.7
$ conda activate eqt
(eqt) $
```

#### Instale EQTransformer y las dependencias de los scripts para la generación de dashboards interactivos.
```bash
(eqt) $ pip install -r requirements.txt
(eqt) $ conda deactivate
$
```

### Instale Phasenet
#### Descargue el repositorio
```bash
$ git clone https://github.com/wayneweiqiang/PhaseNet.git
```

#### Cree ambiente virtual para Phasenet e instalelo con el siguiente comando:
```bash
$ cd PhaseNet
$ git checkout a9383be2138c01ca4f1d514f6a5b9b95fb9a7cba
$ conda env create -f env.yml -n pnet
$ conda activate pnet
(pnet) $ python -m pip install mysql-connector-python obsplus
```



#### Configure la optimización de descaga de formas de onda
El siguiente paso es necesario para mejorar el desempeño al descargar señales usando EQTransformer.
Edite el archivo `<su ruta a anaconda3>/envs/eqt/lib/python3.7/site-packages/EQTransformer/utils/downloader.py` y agregue la siguiente línea dentro de la función **downloadMseeds** justo antes de la línea `with ThreadPool(n_processor) as p:`

```python
n_processor = len(station_dic)
```

#### Configure los entornos virtuales en el ai_picker.py
1. Abra el archivo `<su ruta a sgc_ai_picker>/anaconda_path.txt`
2. Modifique el valor de la variable `anaconda_path` por la ruta hacia su anaconda3.
```
anaconda_path = '<su ruta a anaconda3>'
```
3. Modifique la ruta hacia el directorio anaconda3 en los archivos prune_and_count_evnets.py y run_dashboard.sh
4. Modifique la ruta hacia el sc3_ai_picker en run_dashboard.sh

#### Agregue sgc_ai_picker y sgc_ai_picker/utils a su PATH
1. Edite el archivo `~/.bashrc` y agregue la siguientes 2 líneas:
```bash
export PATH="<su ruta a sgc_ai_picker>:$PATH"
export PATH="<su ruta a sgc_ai_picker>/utils:$PATH"
```

2. En tu terminal ejecute `source ~/.bashrc` para recargar el entorno.

--------------
## Uso ai_picker.py (no recomendado)
Para usar el **ai_picker.py** copie en su directorio de trabajo el archivo de configuración `ai_picker.inp` y ejecute el comando:
```bash
$ ai_picker.py
```
## Salida ai_picker.py
Una vez ejecutado éste generará en el directorio especificado en el parámetro **general_output_dir** del archivo `ai_picker.inp` unos archivos xml con los picks (picks_final.xml), los orígenes con amplitudes (amp.xml), orígenes con amplitudes y magnitudes (mag.xml), los eventos generados con todo lo anterior (events_final.xml) y un xml que contiene solo los orígenes preferidos de los eventos generados (origenes_preferidos.xml). En el caso de PhaseNet se creará una carpeta por cada intervalo de tiempo **dt** dentro de las cuales encontrará el archivo picks.csv, los archivos xml de seiscomp de picks, amplitudes y orígenes para ese intervalo de tiempo, junto con la carpeta xml_events/ con los archivos .xml de eventos en formato seiscomp de cada subintervalo dt.

Tanto para PhaseNet como para EQTransformer se generará en **general_output_dir** el archivo **events_final.xml** con todos los eventos localizados en todo el rango de tiempo entre **starttime** y **endtime**.


### Inspeccionar eventos generados
Puede inspeccionar los eventos generados utilizando el scolv en modo offline y cargando en este el archivo events_final.xml. Para abrir el scolv en modo offline:

    scolv --offline

Una vez abierto el scolv cargue el archivo **events_final.xml** dando click en: File -> Open.

### Archivos de control (ai_picker.inp, ai_picker_scdl.inp y temp_ai_picker.inp)
Los scripts `ai_picker.py`, `ai_scheduler.py` y `discontinuous_picker.py` toman los parámetros desde sus respectivos archivos de configuración (`ai_picker.inp`, `ai_picker_scdl.inp` y `temp_ai_picker.inp` respectivamente) que encuentresn en el directorio de trabajo (el directorio desde donde se ejecuta el programa). Tales como las estaciones a picar, el rango de tiempo y el servidor desde donde traerá la configuración de las estaciones.

Puede introducir comentarios al ai_picker.inp usando el caracter `#` al inicio de la línea.

A continuación se explicarán los parámetros más relevantes. (No se recomienda modificar los parámetros no mencionados acá a menos de que sepa lo que está haciendo):

<!---
Explicación de parámetros generales: picker, starttime, endtime, dt, download_data, general_data_dir, general_output_dir, db_sc (opcional).
Los parámetros de solo PhaseNet: filter_data, pnet_plot_figure.
Los parámetros de solo EQTransformer: eqt_detection_threshold, eqt_P_threshold, eqt_S_threshold, eqt_number_of_plots.
-->
#### Parámetros generales
**-** `picker`: Picker a utilizar. Puede escoger entre **pnet** para PhaseNet o **eqt** para EQTransformer, se recomienda EQTransformer.

**-** `starttime`: Fecha y hora de inicio del rango de tiempo a picar en formato yyyy-mm-dd hh:mm:ss.

**-** `endtime`: Fecha y hora de fin del rango de tiempo a picar en formato yyyy-mm-dd hh:mm:ss.

**-** `dt`: Su definición depende del `picker` escogido.
* **pnet**: Tiempo máximo en segundos para hacer una descarga de formas de onda, corrida de PhaseNet y corrida de playback de SeisComP a la vez. Es decir, si los segundos entre starttime y endtime son mayores a dt, el programa dividirá su ejecución (descarga de formas de onda, corrida de PhaseNet y playback de SeisComP) en intervalos de tamaño dt. Para cada intervalo de tamaño dt creará una carpeta con los correspondientes archivos de salida. Se recomienda dejarlo en 6 horas (21600 segundos).
* **eqt**: Tiempo en el que dividirá los mseed descargados en segundos. Entre más grande es, más memoria RAM se consumirá. Se recomienda dejarlo en 6 horas (21600 segundos).

**-** `download_data`: Controla la descarga de las formas de onda y las estaciones que se usarán. Puede escoger entre “no” (sin comillas) para no descargar formas de onda (si las descargó previamente) o entre un listado separado por coma de las estaciones a descargar siguiendo la nomenclatura “net.station.loc.ch”. En el siguiente ejemplo se descargarán todas las componentes de la banda ancha de la estación BAR2, la componente Z de la estación sismológica de PAM y todas las componentes del acelerómetro de RUS:

    download_data = CM.BAR2.00.HH*, CM.PAM.20.EHZ, CM.RUS.10.*

**-** `general_data_dir`: Directorio donde se guardarán los archivos de formas de onda descargadas.

**-** `general_output_dir`: Directorio donde se guardarán los archivos de salida del ai_picker.py.

**-** `db_sc` (opcional): Base de datos desde donde SeisComP tomará la configuración de las estaciones para el picado de las amplitudes y para la localización de los eventos. Por defecto apunta al servidor 13, si se quisiera tomar esos datos desde el 232 deberá agregar la siguiente línea en cualquier lugar del archivo ai_picker.inp:

    db_sc = mysql://sysop:sysop@10.100.100.232/seiscomp3


#### Parámetros de PhaseNet
**-** `filter_data`: Controla los datos que se filtraran. Para estaciones lejanas a la fuente PhaseNet funciona mejor si los datos están filtrados. Puede escoger entre “no” (sin comillas) para no filtrar ninguna estación o escribir el listado de las estaciones que se filtraran. En el siguiente ejemplo se filtrarán todas los datos de PAM y RUS:

    filter_data = CM.PAM, CM.RUS

**-** `pnet_plot_figure`: Controla la generación de las figuras de los gráficos de los resultados de PhaseNet.  Puede ser True o False. El programa se ejecuta más lento cuando esta opción está activa.


#### Parámetros de EQTransformer
**-** `eqt_detection_threshold`: Umbral de probabilidad para la detección de sismos. Número flotante entre 0 y 1. Entre más pequeño este valor más sismos detectará con el riesgo de que aumenten los falsos positivos. Se recomienda usar 0.003.

**-** `eqt_P_threshold`: Umbral de probabilidad para el picado de la P. Número flotante entre 0 y 1. Entre más pequeño este valor más arribos P picará con el riesgo de que aumenten los falsos positivos. Se recomienda usar 0.01.

**-** `eqt_S_threshold`: Umbral de probabilidad para el picado de la S. Número flotante entre 0 y 1. Entre más pequeño este valor más arribos S picará con el riesgo de que aumenten los falsos positivos. Se recomienda usar 0.01.

**-** `eqt_number_of_plots`: Número de figuras a guardar de las formas de onda con los picks generados por EQTransformer.

## Ejecución offline (discontinuous_picker.py)
 Dependiendo de la cantidad de datos que se desee picar, puede usar el ai_picker.py directamente o usar el script de ayuda **discontinuous_picker.py**.
 En caso de que desee picar más de 2 días de datos con más de 10 estaciones se recomienda usar el script **discontinuous_picker.py**.
 Ambos pueden usarse para picar sismicidad en archivos de formas de onda de estaciones portátiles o para reprocesar formas de onda asociadas a ejambres sísmicos o réplicas.

### Uso discontinuous_picker.py
Para ejecutar el programa debe tener configurado previamente en el directorio de ejecución el archivo de configuración `temp_ai_picker.inp` (toma todos los parámetros excepto las fechas inicial y final, por lo que puede dejar las que estén por defecto). Para esto copie en su directorio de trabajo el archivo `ai_picker.inp` que se encuentra en la ruta `<su ruta a sgc_ai_picker>/ai_picker.inp`, luego cámbiele el nombre por `temp_ai_picker.inp` y finalmente edite los parámetros dentro de éste según sus preferencias  (estaciones a picar, ruta de los directorios donde se guardarán las formas de onda y donde se generarán los archivos de salida, etc). Una vez ubicado en su directorio de trabajo ejecute el programa de a acuerdo al rego de fechas que desee. Si por ejemplo desea picar entre el 1/1/2020 al 31/7/2020 puede ejecutar en consola el siguiente comando: 

    $ discontinuous_picker.py -s "2020-01-01 00:00:00" -e "2020-07-31 23:59:59"

El programa empezará a picar y guardará los resultados en carpetas de 7 días. Si desea en cambio que guarde en un rango de tiempo distinto, puede modificarlo con la opción -n seguido del número de días en el que desea que se vayan guardando los datos.

Puede acceder a las opciones del programa ejecutando:
    
        $ discontinuous_picker.py --help


### Salida discontinuous_picker.py
Una vez ejecutado este generará en el directorio especificado en el parámetro general_output_dir del archivo temp_ai_picker.inp una carpeta por cada 7 días que contendrá los archivos xml de salida correspondientes a los picks, orígenes y eventos (para más detalles de los xml generados por favor remítase a la sección [Salida ai_picker.py](#salida-ai_picker.py) de este documento), por lo tanto habrán un xml de eventos por cada carpeta de 7 días.

#### Inspección de eventos generados
##### Uniendo xmls y revisión en dashboard
Debido a que los eventos localizados se generan en diferentes xml resulta conveniente unir todos archivos xml de eventos en un solo archivo xml. Para esto puede ejecutar en el directorio que contiene las carpetas con los xml el siguiente comando:

    $ prune_and_count_events.py

El programa prune_and_count_events.py unirá en el archivo **main_events_pruned.xml** todos los xml de eventos que se encuentren en las carpetas subyacentes, creará un archivo separado por comas con la información resumida (all_events.csv) y creará un dashboard que puede ser accedido desde el navegador web del computador local cambiando en la dirección en el navegado local, *localhost* por la *ip del computador desde el cual se está ejecutando el script*, siempre y cuando el computador local se encuentre conectado a la misma red LAN ya sea físicamente o a través de una VPN.

En el panel izquierdo del dashboard podrá filtrar los eventos por magnitud, coordenadas, profundidad, RMS e intervalo temporal. En el lado derecho de la página se mostrará una tabla con información resumida de los eventos localizados que puede ser ordenada por la columna de preferencia. Adicionalmente se generarán histogramas sobre el número de eventos por valor de magnitud, rms y profundidad. Cómo también la evolución temporal de la sismicidad, perfiles de profundidad y un mapa con la sismicidad.

## Ejecución en tiempo semi-real (ai_scheduler.py y ai_scheduler_sc4.py)
Los scripts **ai_scheduler.py** y **ai_scheduler_sc4.py** permiten picar en tiempo semi-real las formas de onda de la red con el ai_picker y enviar los eventos generados a un servidor de seiscomp de forma automática (SeisComP3 en el caso del ai_scheduler.py y SeisComP4 en el caso del ai_scheduler_sc4.py).

### Configuración ai_scheduler.py (seiscomp3)

#### Copie los archivos necesarios
Primero debe hacer una copia de los archivos **ai_scheduler.py** y **ai_picker_scdl.inp** a su directorio de trabajo, para ello úbiquese en su directorio de trabajo desde la terminal y ejecute:
    
        $ cp <ruta hacia sgc_ai_picker>/utils/ai_scheduler.py .
        $ cp <ruta hacia sgc_ai_picker>/utils/ai_picker_scdl.inp .

#### Modifique ai_picker_scdl.inp y ai_scheduler.py
Edite el los parámetros de ai_picker_scdl.inp según sus preferencias (se recomienda usar como picker a EQTransformer, para mas información puede mirar [guía parámetros de configuración](#parámetros-generales)) y luego abra el archivo **ai_scheduler.py** y en el bloque `if __name__ == "__main__"` edite el valor de las variables `every_minutes`, `minutes` y `db` según sus preferencias. A continuación se explicará en que consiste cada una de éstas (no se explica la variable `buffer` pues se recomienda siempre dejarla en 0):

* `every_minutes`: Especifica el intervalo de tiempo en minutos entre cada ejecución del programa.
* `minutes`: Especifica el tamaño de las formas de onda a picar en minutos.
* `db`: Especifica la dirección de host de la base de datos de seiscomp a la cual se enviarán los eventos generados por el programa usando scdispatch (usando el parámetro -H).

**Se recomienda configurar el programa para que se ejecute cada 15 minutos picando trazas de la última media hora (implicitamente un overlaping de 5 minutos) configurando el valor de `minutes` como 30, el de `every_minutes` como 15 y el de `buffer` como 0.**

### Configuración ai_scheduler_sc4.py (seiscomp4)
Debido a que no fue posible arreglar el problema de conexión en SeisComP4 para enviar eventos desde un cliente a un servidor usando *scdispatch* de forma remota, se decidió copiar tanto el xml de picks como el de eventos al servidor de destino y desde allí ejecutar *scdispatch*. Esto se maneja desde el script ai_scheduler_sc4.py de forma automática.

#### Copie los archivos necesarios
Primero debe hacer una copia de los archivos **ai_scheduler_sc4.py** y **ai_picker_scdl.inp** a su directorio de trabajo, para ello úbiquese en su directorio de trabajo desde la terminal y ejecute:
    
        $ cp <ruta hacia sgc_ai_picker>/utils/ai_scheduler_sc4.py .
        $ cp <ruta hacia sgc_ai_picker>/utils/ai_picker_scdl.inp .

#### Modifique ai_picker_scdl.inp y ai_scheduler_sc4.py
Edite el los parámetros de ai_picker_scdl.inp según sus preferencias (se recomienda usar como picker a EQTransformer, para mas información puede mirar [guía parámetros de configuración](#parámetros-generales)) y luego abra el archivo **ai_scheduler_sc4.py** y en el bloque `if __name__ == "__main__"` edite el valor de las variables `every_minutes`, `minutes`, `ip_db`, `usr_db` y `psw_db` según sus preferencias. A continuación se explicará en que consisten las últimas 3 (para las primeras 2 puede mirar la sección [Modifique ai_picker_scdl.inp y ai_scheduler.py](#modifique_ai_picker_scdl.inp_y_ai_scheduler.py)):

* `ip_db`: Dirección IP del servidor SeisComP4.
* `usr_db`: Nombre de usuario del servidor SeisComP4.
* `psw_db`: Contraseña del servidor SeisComP4.

**Se recomienda configurar el programa para que se ejecute cada 15 minutos picando trazas de la última media hora (implicitamente un overlaping de 5 minutos) configurando el valor de `minutes` como 30, el de `every_minutes` como 15 y el de `buffer` como 0.**

### Uso ai_scheduler.py y ai_scheduler_sc4.py
Para ambos scripts la ejecución es igual, una ves configurado el .py y .inp, se debe primero activar el entorno de anaconda correspodiente al picker seleccionado en el archivo ai_picker_scdl.inp y luego ejecutar con python el script.

Si se seleccionó `eqt` (EQTransformer), el cual es el picker recomendado, se debe ejecutar:
    
        $ conda activate eqt

En caso de haber seleccionado `pnet` (PhaseNet), se debe ejecutar:
    
        $ conda activate pnet

Por ultimo ejecutar el script con python (ejemplo con ai_scheduler.py) usando `nohup` al inicio del comando y `&` al final para evitar que el programa se detenga en caso de que la terminal se cierre:
    
        (eqt) $ nohup python ai_scheduler.py&

Se puede monitorear la salida del programa revisando las 500 últimas líneas del archivo nohup.out con el comando

    (eqt) $ tail -500 nohup.out



