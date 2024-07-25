#!/home/siervod/anaconda3/bin/python

import os
from test_dispatch_sc5 import test_sc5_env

#os.system("source /home/siervod/sc5env")
# add the following environment variables before running the script
'''
export SEISCOMP_ROOT="/home/siervod/seiscomp"
export PATH="/home/siervod/seiscomp/bin:$PATH"
export LD_LIBRARY_PATH="/home/siervod/seiscomp/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="/home/siervod/seiscomp/lib/python:$PYTHONPATH"
export MANPATH="/home/siervod/seiscomp/share/man:$MANPATH"
export LC_ALL=C
source "/home/siervod/seiscomp/share/shell-completion/seiscomp.bash"
export PATH="/home/siervod/sc3_ai_picker:$PATH"
export PATH="/home/siervod/sc3_ai_picker/utils:$PATH"
'''

os.environ["SEISCOMP_ROOT"] = "/home/siervod/seiscomp"
os.environ["PATH"] = "/home/siervod/seiscomp/bin:$PATH"
os.environ["LD_LIBRARY_PATH"] = "/home/siervod/seiscomp/lib:$LD_LIBRARY_PATH"
os.environ["PYTHONPATH"] = "/home/siervod/seiscomp/lib/python:$PYTHONPATH"
os.environ["MANPATH"] = "/home/siervod/seiscomp/share/man:$MANPATH"
os.environ["LC_ALL"] = "C"
os.system("source /home/siervod/seiscomp/share/shell-completion/seiscomp.bash")
os.environ["PATH"] = "/home/siervod/sc3_ai_picker:$PATH"
os.environ["PATH"] = "/home/siervod/sc3_ai_picker/utils:$PATH"

#os.system("scdispatch -V")
test_sc5_env()
