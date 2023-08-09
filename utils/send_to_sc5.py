#!/home/siervod/anaconda3/envs/eqt/bin/python
import os
import sys


def send_to_sc5(xml_path, usr='aitexnet', test=True):
    """Sends picks or origins xml files to sc5.
    """
    sc5_dir = '/home/seiscomp/daniel/eqcct_xml/'
    sc5_path = os.path.join(sc5_dir, os.path.basename(xml_path))
    scdispatch_cmd = f'/opt/seiscomp/bin/seiscomp exec scdispatch -i {sc5_path} -H localhost/production -u {usr}'
    test_cmd = f'echo {scdispatch_cmd} > {os.path.join(sc5_dir, "command_test.txt")}'
    send_cmd = test_cmd if test else scdispatch_cmd
    
    cmd = f'scp {xml_path} seiscomp@scdb.beg.utexas.edu:{sc5_dir};'
    # "echo" and " > os.path.join(sc5_dir, command_test.txt)" are for testing
    cmd += f'ssh -l seiscomp scdb.beg.utexas.edu "{send_cmd}"'
    print('\n'+cmd+'\n')
    os.system(cmd)


if __name__ == "__main__":
    xml_path = sys.argv[1]
    usr = sys.argv[2]
    send_to_sc5(xml_path, usr)

