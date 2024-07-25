#!/home/siervod/anaconda3/bin/python

"""A python script that will enter to each first level subfolder and then will run:

cp ai_picker_scdl.inp temp_ai_picker.inp
time discontinuous_picker.py -s "2023-10-01 00:00:00" -e "2023-10-02 23:59:59" -n 0.027777777777777776

And then in the main directory will run:

timeout -180 prune_and_count_events.py
"""
import os
import sys
import glob
import shutil
import multiprocessing
import time


def process_folder(folder, starttime, endtime, n):
    if os.path.isdir(folder):
        os.chdir(folder)

        # Copy the original file
        shutil.copyfile("ai_picker_scdl.inp", "temp_ai_picker.inp")

        # Run the discontinuous picker
        os.system(f"time discontinuous_picker.py -s \"{starttime}\" -e \"{endtime}\" -n {n}")

        # Remove the temp file
        os.remove("temp_ai_picker.inp")

        # Go back to the main folder
        os.chdir('..')

def print_and_run(command):
    print(command)
    os.system(command)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 test_regions_as_discontinuos.py <main_folder> '2023-10-01 00:00:00' '2023-10-01 23:59:59'")
        sys.exit(1)

    main_folder = sys.argv[1]
    #starttime = "2023-10-01 00:00:00"
    #endtime = "2023-10-01 23:59:59"
    starttime = sys.argv[2]
    endtime = sys.argv[3]
    # 0.027777777777777776 is 40 minutes in days
    n = 0.027777777777777776

    # remove main_events_pruned.xml files and test folders: find delaware -type d -name "test" -exec rm -fr {} \; -o -type f -name "main_events_pruned.xml" -exec rm -f {} \;
    print_and_run(f"find {main_folder} -type d -name 'test' -exec rm -fr {{}} \; -o -type f -name 'main_events_pruned.xml' -exec rm -f {{}} \;")

    # Iniciate seiscomp environment
    os.environ["SEISCOMP_ROOT"] = "/home/siervod/seiscomp"
    # os.environ["PATH"] = "/home/siervod/seiscomp/bin:$PATH"
    # os.environ["LD_LIBRARY_PATH"] = "/home/siervod/seiscomp/lib:$LD_LIBRARY_PATH"
    # os.environ["PYTHONPATH"] = "/home/siervod/seiscomp/lib/python:$PYTHONPATH"
    # os.environ["MANPATH"] = "/home/siervod/seiscomp/share/man:$MANPATH"
    # os.environ["LC_ALL"] = "C"
    # os.system("source /home/siervod/seiscomp/share/shell-completion/seiscomp.bash")
    # os.environ["PATH"] = "/home/siervod/sc3_ai_picker:$PATH"
    # os.environ["PATH"] = "/home/siervod/sc3_ai_picker/utils:$PATH"
    
    processes = []
    for i, folder in enumerate(glob.glob(os.path.join(main_folder, "*"))):
        p = multiprocessing.Process(target=process_folder, args=(folder, starttime, endtime, n))
        p.start()
        processes.append(p)
        time.sleep(0.5)  # Add a delay of 0.5 seconds before starting the next process

    for p in processes:
        p.join()

    # working directory
    working_dir = os.getcwd()
    
    #events_dir = os.path.join(working_dir, main_folder)
    # move to working directory
    #print(f"Moving to {main_folder}")
    #os.chdir(main_folder)
    
    # run dispatch_walk.py path xmlfile_name host new_author(change author in origenes_preferidos.xml to EQCCT and send to seiscomp throuhg scdispatch)
    print_and_run(f"dispatch_walk.py {main_folder} origenes_preferidos.xml scdb.beg.utexas.edu EQCCT")
    
    # Run the prune and count script
   # os.system("timeout -180 prune_and_count_events.py")

    # change the name of output file main_events_pruned.xml to main_events_pruned_starttime_endtime_n.xml
    #os.rename("main_events_pruned.xml", f"main_events_pruned_{starttime}_{endtime}_{n}.xml")
    
    sys.exit(0)