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
    # move to working directory
    os.chdir(working_dir)
    
    # Run the prune and count script
    os.system("timeout -180 prune_and_count_events.py")

    # change the name of output file main_events_pruned.xml to main_events_pruned_starttime_endtime_n.xml
    os.rename("main_events_pruned.xml", f"main_events_pruned_{starttime}_{endtime}_{n}.xml")
    
    sys.exit(0)