#!/home/siervod/anaconda3/bin/python
# -*- coding: utf-8 -*-
"""
Created on Jan 2021

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py discontinously in a large amount
of time
"""

from email.policy import default
import os
import datetime
import random
import click


@click.command()
@click.option('-s', "--start", required=True, prompt='Start date [yyyy-MM-dd hh:mm:ss]',
              help='Starting date in format like "2020-01-22 00:00:00"')
@click.option('-e', "--end", required=True, prompt='End date [yyyy-MM-dd hh:mm:ss]',
              help='Ending date in format like "2020-01-22 00:00:00"')
@click.option('-n', "--n_days", prompt=True, default=7, type=float,
              help='Run ai_picker every n_days\n')
@click.option('-d', "--db", required=False, prompt=False, default='None',
              help='Seiscomp database to migrate events every n_days. Could be 10.100.100.13')
def discontinuous_picker(start, end, n_days, db):

    start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
    end = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
    dt = datetime.timedelta(days=n_days)
    overlap_rate = 0.05

    assert start < end, f'Start date must be before end date:\n Start {start},\n end: {end}'
    
    temp_inp = 'temp_ai_picker.inp'
    params = read_params(temp_inp)
    wav_dir = params['general_data_dir']
    main_path = params['general_output_dir']

    while start <= end:
        # taking current time in UTC
        t = datetime.datetime.utcnow()

        final_time = start + dt
        if final_time > end:
            final_time = end

        print(f'\n\n\trunning from {start} to {final_time}\n\n')

        os.system('rm -fr %s' % wav_dir)

        # output_dir name ddmmyyyy-hhmmss_ddmmyy-hhmmss
        output_dir = start.strftime('%d%m%Y-%H%M%S') + '_' + final_time.strftime('%d%m%Y-%H%M%S')

        general_output_dir = os.path.join(params['general_output_dir'],
                                          output_dir)

        chunk_size_inp = int((final_time - start).total_seconds()*0.5)
        
        # change the init, end time and output dir in ai_picker.inp
        change_times_dir(temp_inp,
                         start.strftime("%Y-%m-%d %H:%M:%S"),
                         final_time.strftime("%Y-%m-%d %H:%M:%S"),
                         general_output_dir,
                         str(chunk_size_inp))

        # excecuting ai_picker.py
        os.system('time ai_picker.py')
        
        # copy ai_picker.inp to general_output_dir
        os.system(f'cp ai_picker.inp {general_output_dir}/')

        # getting the origins path
        output_path = get_origins_path(main_path, 'origenes_preferidos.xml')
        # getting the picks path
        picks_path = get_origins_path(main_path, 'picks.xml')

        # migrating picks to seiscomp db
        #cmd_picks = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scdispatch -i %s -H %s -u ai_sgc' % (picks_path, db)
        #print(cmd_picks)
        #os.system(cmd_picks)

        # migrating events to seiscomp db as long as the file exist and
        # is not empty
        if output_path is not None:
            # if the file is not empty
            if os.path.getsize(output_path):
                print('xml a modificar:', output_path)
                print('\n\n\tUploading to db\n\n')

                # random number to avoid repetead users
                num = random.randint(1, 10)
                #cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scdispatch -i %s -H %s -u ai_sgc_%d' % (output_path,
                #                                               db, num)
                #print(cmd)
                #os.system(cmd)
            else:
                print('\n\n\tArchivo vacio!\n\n')
        else:
            print('\n\n\tNo se encontró origenes_preferidos.xml!\n\n')

        start += dt*(1-overlap_rate)
        tf = datetime.datetime.utcnow()

        logger(t, tf)


def read_params(par_file='phaseNet.inp'):
    """Read params from .inp file

    Parameters
    ----------
    par_file : str, optional
        File name of parameter file, by default 'phaseNet.inp'

    Returns
    -------
    dic
        Dictionary with parameters and values from params file
    """
    lines = open(par_file).readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic


def change_times_dir(inp_file: str, ti: str, tf: str, general_output_dir: str, dt: str):
    """Change starttime and endtime in ai_picker.inp file

    Parameters
    ----------
    inp_file: str
        ai_picker.inp template file
    ti : str
        Initial UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    tf : str
        Final UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    general_output_dir : str
        Output dir path
    """

    f_lines = open(inp_file).readlines()

    for idx, line in enumerate(f_lines):
        if line.startswith('starttime'):
            start_idx = idx
        elif line.startswith('endtime'):
            end_idx = idx
        elif line.startswith('general_output_dir'):
            out_dir_idx = idx
        elif line.startswith('dt'):
            dt_idx = idx

    # replacing start, end and dt time lines
    f_lines[start_idx] = f'starttime = {ti}\n'
    f_lines[end_idx] = f'endtime = {tf}\n'
    f_lines[out_dir_idx] = f'general_output_dir = {general_output_dir}\n'
    f_lines[dt_idx] = f'dt = {dt}\n'

    # writing new file
    with open('ai_picker.inp', 'w') as f:
        text = ''.join(f_lines)
        f.write(text)


def get_origins_path(path, xmlfile):
    orig_path = None
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if filename == xmlfile:
                orig_path = os.path.join(dirpath, filename)
                break

    print(xmlfile, orig_path)
    return orig_path


def logger(ti, tf):
    logfile = 'discontinuous.log'
    if not os.path.isfile(logfile):
        f = open(logfile, 'w')
    else:
        f = open(logfile, 'a')
    print(f'Inició ejecución a las: {ti} UTC, terminó la ejecución a las: {tf} UTC', file=f)
    f.close()


if __name__ == '__main__':
    
    """start = '2020-01-22 00:00:00'
    end = '2020-11-01 23:59:59'
    n_days = 7
    db = '10.100.100.13:4803'
    
    discontinuous_picker(start, end, n_days, db)"""
    
    discontinuous_picker()
