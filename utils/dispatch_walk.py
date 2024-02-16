#!/home/siervod/anaconda3/envs/eqt/bin/python
import os
import time
from typing import List
#import sys


def get_xml_path(path: str, xmlfile: str) -> List[str]:
    """
    Returns the list of paths of xml files with a given name in a directory and its subdirectories.
    
    Parameters
    ----------
    path : str
        The path of the directory containing the XML files.
    xmlfile : str
        The name of the XML files to be searched for.
        
    Returns
    -------
    List[str]
        List of string of xml path files
    """
    xml_paths = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if filename == xmlfile:
                xml_paths.append(os.path.join(dirpath, filename))
                break
    return xml_paths


def dispatch(xml_path: str, host: str) -> None:
    """
    Dispatch the xml file specified by xml_path to the host using scdispatch command.
    
    Parameters
    ----------
    xml_path : str
        The path of the xml file to be dispatched
    host : str
        The host to which the xml file should be dispatched
        
    Returns
    -------
    None
    """
    print(xml_path)
    cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scdispatch -H {host} -i {xml_path}'
    print(cmd)
    os.system(cmd)


def check_file_size(file_path:str, threshold:float)->bool:
    file_size = os.path.getsize(file_path)
    if file_size > threshold:
        return True
    else:
        return False


def update_author(file_path:str, new_author:str)->None:
    """
    Open the file and replace the old string with the new string
    
    Parameters
    ----------
    file_path : str
        The path of the file to be updated.
        
    Returns
    -------
    None
    
    Example
    -------
    update_file("path/to/file.txt")
    """
    new_str = f"        <author>{new_author}</author>"
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    with open(file_path, 'w') as f:
        for line in lines:
            if "        <author>EQCCT</author>" in line:
                line = line.replace("        <author>EQCCT</author>", new_str)
            f.write(line)


def dispatch_walk(path: str, xmlfile: str, host: str, new_author=None, sleep_time: float=60) -> None:
    """
    Walks through a directory and dispatches XML files to a specified host.
    
    Parameters
    ----------
    path : str
        The path of the directory containing the XML files.
    xmlfile : str
        The name of the XML files to be dispatched.
    host : str
        The host to which the XML files should be dispatched.
    sleep_time : float, optional
        The time to wait between dispatching each XML file, in seconds. Default is 60.
        
    Returns
    -------
    None
    """
    xml_paths = get_xml_path(path, xmlfile)
    print(f"Dispatching {len(xml_paths)} files:")
    for xml_path in xml_paths:
        if check_file_size(xml_path, 300):
            if new_author:
                print(f"Updating author to {new_author} in {xml_path}...")
                update_author(xml_path, new_author)
            dispatch(xml_path, host)
            print(f"\nSleeping for {sleep_time} seconds...\n\n")
            time.sleep(sleep_time)
        else:
            print(f'File size of {xml_path} is too small. Skipping.')


if __name__ == '__main__':
    path = '.'
    xmlfile = 'origenes_preferidos.xml'
    #host = 'sc3primary.beg.utexas.edu'
    host = 'scdb.beg.utexas.edu'
    dispatch_walk(path, xmlfile, host, new_author='EQCCT', sleep_time=30)
