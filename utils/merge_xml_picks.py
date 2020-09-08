
# coding: utf-8

# In[90]:

import fnmatch
import os


def merge_xml_picks(picks_dir, out_path):
	picks = ""
	indices = []

	for pick_file in os.listdir(picks_dir):
		if fnmatch.fnmatch(pick_file, '*.xml'):
			print (pick_file)
			# se salta un xml de pick si no tiene ninguna picada
			try:
				parte, ind, file_name = pick_extractor(pick_file, picks_dir)
			except IndexError:
				os.system('rm -fr %s'%pick_file)
				continue
			texto = "".join(parte)
			picks += texto 
			
			indices.append([ind, file_name])

	try:
		ind = indices[0][0]
	except IndexError:
		print ('No se encontró ningún archivo .xml en la carpeta %s'%picks_dir)
	file_name = indices[0][1]

	top, bottom = complete_xml_file(file_name, ind, picks_dir)
	picks_file_complete = top+picks+bottom

	print (len(picks_file_complete.split("\n")))

	picks_final = open(out_path, "w")
	picks_final.write(picks_file_complete)
	picks_final.close()


def pick_extractor(file_name, folder_name = "picks/"):
    
    f = open(folder_name+file_name).readlines()

    ind = []

    for idx, line in enumerate(f):
        if line.strip().strip("\n") == "<EventParameters>" or \
        line.strip().strip("\n") == "</EventParameters>":
            #print line, idx
            ind.append(idx)

    part = f[ind[0]+1:ind[-1]]
    return part, ind, file_name


def complete_xml_file(file_name, ind, folder_name = "picks/"):
    
    f = open(folder_name+file_name).readlines()
    
    top = "".join(f[:ind[0]+1])
    bottom = "".join(f[ind[1]:])
    
    return top, bottom


if __name__ == '__main__':
	merge_xml_picks('picks/', 'picks')
