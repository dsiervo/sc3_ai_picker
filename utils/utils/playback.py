"""#!/home/sgc/anaconda3/envs/phaseNet/bin/python"""
# -*- coding: utf-8 -*-
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import os, multiprocessing
from datetime import timedelta
try:
    from utils.merge_xml_picks import merge_xml_picks
except ModuleNotFoundError:
    from merge_xml_picks import merge_xml_picks


def get_xml_Origins(xml_picks,output_file,locator_type="LOCSAT",
                    locator_profile="iasp91",
                    db="sysop:sysopp@10.100.100.13/seiscomp3"):
    """
    Write origins in an origins xml file.

    Parameters:
    -----------
    xml_picks: str
        path where is lcoated the picks xml file
    output_file: str
        path where will be lcoated the origins xml file
    locator_type: str
        "LOCSAT" or "Hypo71"
    locator_profile: str
        "iaspei91" for LOCSAT and "RSNC" for Hypo71
    db: str
        "sysop:sysopp@10.100.100.13/seiscomp3" 

    Returns:
    --------
    origin xml file
    """

    if os.path.isdir(os.path.dirname(output_file)) == False:
        os.makedirs(os.path.dirname(output_file))

    scanloc_cmd = f'scanloc -u playback --locator-type {locator_type} --locator-profile {locator_profile} '
    scanloc_cmd += '--ep %s -d %s  > %s'%(xml_picks, db, output_file)

    
    if  locator_type == "Hypo71":

        tmp_file = os.path.join(os.path.dirname(output_file),
                                os.path.basename(output_file).split('.')[0]+'_tmp.xml')
        mv_msg = f"mv {output_file} {tmp_file} "
        # print(mv_msg)
        # os.system(mv_msg)

        key_word = '<?xml version="1.0" encoding="UTF-8"?>'
        clean_msg = f"sed -n '/{key_word}/,$p' {tmp_file} > {output_file}"
        # print(clean_msg)
        # os.system(clean_msg)

        rm_msg = f"rm {tmp_file}"
        # print(rm_msg)

        scanloc_cmd = ';'.join([scanloc_cmd,mv_msg,clean_msg,rm_msg])
        # os.system(scanloc_cmd)
    return scanloc_cmd

def merge_xml(xmls,output_file):
    """
    merge xml files

    Parameters:
    -----------
    xmls: list
        List of paths of the xml files
    output_file: str
        Path of the merged xml
    """
    if len(xmls) <2 :
        raise Exception("Need two or more xml files to merge")

    xmls = " ".join(xmls)

    msg = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scxmlmerge {xmls} > {output_file}'

    # os.system(msg)
    return msg

def get_scanloc_msg(picks_file,origins_file,origins_loc={"LOCSAT":"iasp91"},
                    db="sysop:sysopp@10.100.100.13/seiscomp3"):
    """
    Parameters:
    picks_file: str
        Path of the xml picks file
    origins_file: str
        Path of the xml origins file
    origins_loc: dict (default:{"LOCSAT":"iasp91"})
        key-> locator_type , value -> locator_profile
    db: str
        database
    """

    location_types = list(origins_loc.keys())
    location_profiles = list(origins_loc.values())

    filenames = []
    for i in range(0,len(location_types)):
        name = os.path.basename(origins_file).split('.')[0]
        extra_name = f"_{location_types[i]}_{location_profiles[i]}.xml"
        filename = os.path.join(os.path.dirname(origins_file),name + extra_name)
        merge_filename = os.path.join(os.path.dirname(origins_file), f"merge_{i}.xml")

        msg_orig = get_xml_Origins(picks_file,filename,location_types[i],
                                    location_profiles[i], db)

        if i>0:
            msg_orig += ";" + merge_xml([filenames[i-1],filename],merge_filename)
            filename = merge_filename
        else:
            first_orig = msg_orig

        filenames.append(filename)

    msg_orig = first_orig +";"+ msg_orig

    if len(location_types) == 1:
        msg_orig += ";" + f"mv {filenames[0]} {origins_file}"
    else:
        msg_orig += ";" + f"mv {filenames[i]} {origins_file}"

    print(msg_orig)
    return msg_orig

class playback:
    
    def __init__(self, sc_scanloc,locator_dict, picks, wf_dir,
              out_dir,
              station="YPLC", loc_cod='00', net='CM', ch='HHN',
              init_time="2019-02-01 00:00:00",
              end_time="2019-02-28 23:59:59",
              ip_fdsn="http://10.100.100.232:8091",
              db="mysql://sysop:sysop@localhost/seiscomp3",
              xml_picks_file = 'picks_final.xml',
              ai_type='pnet'
              ):
        """Class to create playback process.
        :param station: Station or string with list of station comma
                        separated.
        :type station: string
        
        :param init_time: Initial time to excecute playback
        :type init_time: string in format YYYY-MM-DD hh:mm:ss
        
        :param ip_fdsn: IP direction with port to FDSN service
        :type ip_fdsn: string
        
        :param db: mysql direction to database
        :type db: string
        
        :param picks: Name or list of names of scaoutopick profiles. 
                      Like pickZbayes, pickNbayes
        :type picks: String
        """
        
        self.sc_scanloc = sc_scanloc
        self.locator_dict = locator_dict
        self.station = station
        self.loc_cod = loc_cod
        self.net = net
        self.ch = ch
        self.init_time = init_time
        self.end_time = end_time
        self.ip_fdsn = ip_fdsn
        self.db = db
        self.picks = picks.replace(' ', '').split(',')
        self.picks_dir = 'picks/'
        self.wf_dir = wf_dir
        self.xml_picks_file = xml_picks_file
        self.out_dir = out_dir
        
        if ai_type == 'pnet':
            dir_split = os.path.split(self.out_dir)
            self.general_dir = dir_split[0] # Taking the general output dir
            self.event_name = dir_split[-1]+'.xml'
            self.ev_f_path = os.path.join(self.general_dir, "events_final.xml")
        else:
            self.general_dir = out_dir
            self.event_name = 'events.xml'
            self.ev_f_path = os.path.join(self.general_dir, "events_final.xml")
    
        # por defecto hace extracciones separadas cada 2 horas
        self.delta = 3600*2

        self.events_dir = os.path.join(self.general_dir, 'xml_events')
        
        if not os.path.exists(self.events_dir):
            os.makedirs(self.events_dir, exist_ok=True)    

    def wf_extraction(self):
    
        wf_list = []
        
        client = Client(self.ip_fdsn)
        
        start = UTCDateTime(self.init_time)
        end = UTCDateTime(self.end_time)
        
        assert start < end, "init_time must be less than end_time"
        # si las diferencias entre las fechas inicial y final son menores de
        # 2 horas entonces se hace extracciones cada 15 minutos
        print(int(end-start))
        if int(end-start)< self.delta:
            self.delta = 60*15
        tmp = start
        
        dt = timedelta(seconds=self.delta)
        
        #print(self.delta, type(self.delta))
        #print(dt, type(dt))


        if not os.path.exists(self.wf_dir):
            os.makedirs(self.wf_dir)

        while tmp < end:
            
            s_tmp = tmp.strftime('%Y-%m-%d %H:%M:%S')
            print (s_tmp)
            name = s_tmp.split()[0]+'-'+s_tmp.split()[1]+'.mseed'
            try:
                if not os.path.isfile(self.wf_dir+name):
                    st = client.get_waveforms(self.net, self.station,
                        self.loc_cod, self.ch, tmp, tmp+dt)
        
                    st.write(self.wf_dir+name, 'mseed')
                tmp = tmp + dt
            except:
                print("\n #######################################################")
                print(self.net, self.station, self.loc_cod, self.ch, 
                      tmp, tmp+dt)
                print('No se encontraron datos!\n')
                tmp = tmp + dt
                continue

            wf_list.append(self.wf_dir+name)

        with open('%swf_list.txt'%self.wf_dir, 'w') as f:
            f.write('\n'.join(wf_list))

    def multi_picks(self, wf):
        '''Run autopicks in parallel threads.
        
        :param wf: name of the waveform or path to waveform on which the autopick will run
        :type wf: string
        
        create xml files in picks folder'''
        os.system('rm -f picks/*')
        if not os.path.exists('picks'):
            os.makedirs(self.picks_dir)

        command = "%s -u playback -I %s -d \
            mysql://sysop:sysop@localhost/seiscomp3 --playback --ep\
             --debug>%spicks%s.xml"
        
        #self.wf_path = self.wf_dir+wf
        process = [" ".join(command.split())%(pick, wf, self.picks_dir, i)\
         for i, pick in enumerate(self.picks)]

        jobs = []
        for p in process:
            print (p)
            q = multiprocessing.Process(target=os.system, args=(p,))
            jobs.append(q)

        for j in jobs:
            j.start()
        for j in jobs:
            j.join()    

    def merge_picks(self):
        merge_xml_picks(self.picks_dir)
        
    def playback_commands(self, picks2events=False):
        """Excecute seiscomp playback comands to group picks, compute amplitudes,
        compute magnitudes and create seiscomp events.

        Parameters
        ----------
        wf : str
            Path to wavefrom to compute amplitudes
        locator_dict : dict
            Dictionary with locator and velocity models
        """
        print('self.out_dir', self.out_dir)
        print('self.events_dir', self.events_dir)
        origins_name = 'origins.xml'
        amplitudes_name = 'amp.xml'
        magnitudes_name = 'mag.xml'
        # keep only the file name of the self.xml_picks_file path
        picks_file_name = os.path.split(self.xml_picks_file)[-1]
        # if we are events from picks outside of the ai_picker
        if picks2events:
            self.event_name = 'ev_'+picks_file_name
            origins_name = 'origins_'+picks_file_name
            amplitudes_name = 'amp_'+picks_file_name
            magnitudes_name = 'mag_'+picks_file_name
            self.event_path = os.path.join(self.events_dir, self.event_name)
        else:
            self.event_path = os.path.join(self.events_dir, self.event_name)
        
        origin_path = os.path.join(self.out_dir, origins_name)
        amp_path = os.path.join(self.out_dir, amplitudes_name)
        mag_path = os.path.join(self.out_dir, magnitudes_name)

        if self.sc_scanloc == 'scanloc':
            """scanloc_cmd = get_scanloc_msg(picks_file=self.xml_picks_file,
                                            origins_file=origin_path,
                                            origins_loc=self.locator_dict, # { "LOCSAT": "iasp91", "Hypo71":"RSNC" }
                                            db = self.db)"""
            locator_type = list(self.locator_dict.keys())[0]
            locator_profile = self.locator_dict[locator_type]
            scanloc_cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scanloc -u playback --locator-type {locator_type} --locator-profile {locator_profile} '
            scanloc_cmd += '--ep %s -d %s  > %s'%(self.xml_picks_file, self.db, origin_path)
        else:
            scanloc_cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec %s -u playback --ep %s -d %s  > %s'%(self.sc_scanloc,
                                                            self.xml_picks_file,
                                                            self.db, origin_path)
        
        scamp_cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scamp -u playback --ep %s -d %s > %s'%(origin_path,
                                                            self.db, amp_path)

        scmag_cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scmag -u playback --ep %s -d %s  > %s'%(amp_path, self.db, mag_path)

        scevent_cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scevent -u playback --ep %s -d %s  > %s'%(mag_path, self.db,
                                                                self.event_path)
        
        all_cmd = ';'.join([scamp_cmd, scmag_cmd, scevent_cmd])
        
        print(scanloc_cmd)
        print(all_cmd)
        
        os.system(scanloc_cmd)

        clean_nll_origin(origin_path)

        os.system(all_cmd)
        
    def scdb(self):
        os.system('scdb -i %s -d %s'%(self.ev_f_path, self.db))

    def merge_events(self):
        merge_xml_picks(self.events_dir+'/', self.ev_f_path)


def read_params(par_file):
    lines = open(par_file).readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            #print(line)
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic

def clean_nll_origin(xml_path):
    """
    Remove the NLL lines at the beginning of the xml file
    """
    with open(xml_path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith('<'):
                break
    with open(xml_path, 'w') as f:
        f.writelines(lines[i:])

if __name__ == '__main__':

    import sys

    # script directory for playback.inp searching
    main_dir = os.path.dirname(os.path.abspath(__file__))
    par_fn = 'playback.inp'
    rel_par_path = os.path.join('../', par_fn)
    main_par_path = os.path.join(main_dir, par_fn)

    # verifying if playback.inp exist in any of the following 3 paths. 
    check_inp_dirs = [par_fn, rel_par_path, main_par_path]
    for path in check_inp_dirs:
        if os.path.isfile(path):
            print('Reading params for: {0} \n'.format(path))
            par = read_params(path)
            break
    
    xml_picks_file='picks_final.xml'
    if len(sys.argv) == 2:
        xml_picks_file = sys.argv[1]
    print('creando objeto playback')
    my_playback = playback(
            sc_scanloc=par['sc_scanloc'],
            station=par['station'],
            loc_cod=par['loc_cod'],
            net=par['net'],
            ch=par['ch'],
            init_time=par['init_time'],
            end_time=par['end_time'],
            ip_fdsn=par['ip_fdsn'],
            db=par['db'],
            picks =par['picks'],
			xml_picks_file=xml_picks_file,
            wf_dir = 'waveforms/',
            out_dir='out_play/'
            )

    print('extrayendo la formas de onda...')
    # extrayendo formas de onda
    
    if par['wf_extraction'] in ['yes', 'YES', 'Yes', 'y', 'Y', 'True',
                         'TRUE', 'true']:
        my_playback.wf_extraction()
    
    wfs = open(my_playback.wf_dir+'wf_list.txt').readlines()
    
    os.system('rm -fr xml_events/* events_final.xml')
    
    print(wfs)
    for wf in wfs:
        wf_path = wf.strip('\n').strip() 
        print (wf_path)

        # si no existe xml de phaseNet entonces ejecuta los picks
        # de seiscomp y los une un solo xml
        if par['phaseNet'] not in ['yes', 'YES', 'Yes', 'y',
                                    'Y', 'True', 'TRUE', 'true']:    
            my_playback.multi_picks(wf_path)    
            my_playback.merge_picks()
        else:
            # Verifing if the xml file with picks from phasenet exist
            assert os.path.isfile(xml_picks_file), '\n\n\tNo existe el archivo %s en el directorio\n'%xml_picks_file
            #   print()
            #   sys.exit()

        my_playback.playback_commands()
    
    my_playback.merge_events()
    
    if par['upload'] in ['yes', 'YES', 'Yes', 'y', 'Y', 'True',
                         'TRUE', 'true']:
        my_playback.scdb()
        
        
        
