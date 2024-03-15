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

    for folder in glob.glob(os.path.join(main_folder, "*")):
        if os.path.isdir(folder):
            print("\033[1;35m" + f"\n\n\n\n\tProcessing folder: {folder}\n\n\n\n" + "\033[0m")
            os.chdir(folder)

            # Copy the original file
            shutil.copyfile("ai_picker_scdl.inp", "temp_ai_picker.inp")

            # Run the discontinuous picker
            #os.system(f"time discontinuous_picker.py -s  -e  -n 0.027777777777777776")
            os.system(f"time discontinuous_picker.py -s \"{starttime}\" -e \"{endtime}\" -n {n}")

            # Remove the temp file
            os.remove("temp_ai_picker.inp")

            # Go back to the main folder
            os.chdir("..")

    # Run the prune and count script
    os.system("timeout -180 prune_and_count_events.py")
    
    # change the name of output file main_events_pruned.xml to main_events_pruned_starttime_endtime_n.xml
    os.rename("main_events_pruned.xml", f"main_events_pruned_{starttime}_{endtime}_{n}.xml")
    sys.exit(0)
