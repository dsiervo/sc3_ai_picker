
# coding: utf-8

# In[90]:

import fnmatch
import os


def merge_xml_picks(picks_dir, out_path):
    picks = ""
    # lista que contiene una lista por cada archivo en la
    # carpeta picks_dir donde el primer elemento es una tupla de 2 elementos
    # que contiene los índices donde empieza y termina la etiqueta EventParameters
    # y el segundo elemento es el nombre del archivo
    indices = []
    
    # variable para controlar si no existe un archivo con información en la 
    # carpeta picks_dir.
    not_usefull_file = True

    for pick_file in os.listdir(picks_dir):
        if fnmatch.fnmatch(pick_file, '*.xml'):
            print (pick_file)
            # se salta un xml de pick si no tiene ninguna picada
            try:
                parte, ind, file_name = pick_extractor(pick_file, picks_dir)
                not_usefull_file = False
            except IndexError:
                print(f'No encontró datos en el archivo {pick_file}')
                #os.system('rm -fr %s'%pick_file)
                continue
            texto = "".join(parte)
            picks += texto 

            indices.append([ind, file_name])

    try:
        ind = indices[0][0]
    except IndexError:
        #print ('No se encontró ningún archivo .xml en la carpeta %s'%picks_dir)
        pass
    
    if not_usefull_file:
        print(f'\n\tNo se creo el archivo {out_path}\n')
    else:
        file_name = indices[0][1]

        top, bottom = complete_xml_file(file_name, ind, picks_dir)
        picks_file_complete = top+picks+bottom

        picks_final = open(out_path, "w", encoding='utf-8')
        picks_final.write(picks_file_complete)
        picks_final.close()
        print(f'\n\tArchivo final con los eventos generados:\n\t  {out_path}')


def pick_extractor(file_name, folder_name = "picks/"):
    path = os.path.join(folder_name, file_name)
    f = open(path, encoding='utf-8').readlines()

    ind = []

    for idx, line in enumerate(f):
        clean_line = line.strip().strip("\n")

        if clean_line == "<EventParameters>" or \
        clean_line == "</EventParameters>":
            #print line, idx
            ind.append(idx)

    part = f[ind[0]+1:ind[-1]]
    return part, ind, file_name


def complete_xml_file(file_name, ind, folder_name = "picks/"):
    
    path = os.path.join(folder_name, file_name)
    f = open(path, encoding='utf-8').readlines()
    
    top = "".join(f[:ind[0]+1])
    bottom = "".join(f[ind[1]:])
    
    return top, bottom


if __name__ == '__main__':
    merge_xml_picks('picks/', 'picks')
