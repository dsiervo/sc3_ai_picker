import os

def read_params(par_file='phaseNet.inp'):
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


def PNet_pred_mseed(params):
    run_execute= os.path.join(params['PhaseNet_dir'],'run.py')
    command = f"python {run_execute} --mode={params['mode']} --model_dir={params['model_dir']} \
        --data_dir={params['data_dir']} --data_list={params['data_list']} \
        --output_dir={params['output_dir']} --plot_figure \
        --batch_size={params['batch_size']}  --input_mseed"
    print('\n', command, '\n')
    os.system(command)


if __name__ == "__main__":
    PNet_params= read_params(os.path.join(os.getcwd(),'to_run_PNet.inp'))
    PNet_pred_mseed(PNet_params)
    # print(PNet_params)
