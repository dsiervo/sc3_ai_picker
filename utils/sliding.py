import numpy as np
import concurrent.futures
from functools import partial




def sliding_window(data, size, stepsize=1, padded=False, axis=-1, copy=True):
    """
    Calculate a sliding window over a signal
    Parameters
    ----------
    data : numpy array
        The array to be slided over.
    size : int
        The sliding window size
    stepsize : int
        The sliding window stepsize. Defaults to 1.
    axis : int
        The axis to slide over. Defaults to the last axis.
    copy : bool
        Return strided array as copy to avoid sideffects when manipulating the
        output array.
    Returns
    -------
    data : numpy array
        A matrix where row in last dimension consists of one instance
        of the sliding window.
    Notes
    -----
    - Be wary of setting `copy` to `False` as undesired sideffects with the
      output values may occurr.
    Examples
    --------
    >>> a = numpy.array([1, 2, 3, 4, 5])
    >>> sliding_window(a, size=3)
    array([[1, 2, 3],
           [2, 3, 4],
           [3, 4, 5]])
    >>> sliding_window(a, size=3, stepsize=2)
    array([[1, 2, 3],
           [3, 4, 5]])
    See Also
    --------
    pieces : Calculate number of pieces available by sliding
    """
    
    if axis >= data.ndim:
        raise ValueError(
            "Axis value out of range"
        )

    if stepsize < 1:
        raise ValueError(
            "Stepsize may not be zero or negative"
        )

    if size > data.shape[axis]:
        raise ValueError(
            "Sliding window size may not exceed size of selected axis"
        )

    shape = list(data.shape)
    shape[axis] = np.floor(data.shape[axis] / stepsize - size / stepsize + 1).astype(int)
    shape.append(size)

    strides = list(data.strides)
    strides[axis] *= stepsize
    strides.append(data.strides[axis])

    strided = np.lib.stride_tricks.as_strided(
        data, shape=shape, strides=strides
    )

    if copy:
        return strided.copy()
    else:
        return strided


def sliding_executor(array, size, stepsize):
    overlapping= (size-stepsize)*100/size
    t_array= array.transpose()
    t_array_list= list(t_array)
    scaling_list=[]
    with concurrent.futures.ProcessPoolExecutor() as executor:
        _result= partial(sliding_window, size=size, stepsize=stepsize)
        results=list(executor.map(_result,t_array_list))

    for j in range (len(results[0])):
        rearray= np.array([results[0][j]]).T
        for i in range(1,len(results)):
            rearray= np.append(rearray, np.array([results[i][j]]).T,axis=1)
        scaling_list.append(rearray)
    return scaling_list, overlapping
            
            
if __name__  == '__main__':
    ###-----------------------------------

    nrows, ncols = 300000, 3  ##el tama  o de fila y columna de la ""arreglo grande (sin escalar)" puede ser$
                          ##pero solo divide por columnas
    a= np.random.randint(nrows, size=(nrows,ncols)) ##Matriz de prueba
    size=3000  #tama  o de la columna del nuevo arreglo deseado
    stepsize=1500 #la longitud de paso para la divisi  n del arreglo  ej: para un nuevo arreglo deseado de 3$
               ##se haria un overlapping del 50%

    #~ Para mirar como trabaja recomiendo:
    #~ nrows, ncols = 10, 5
    #~ a= np.random.randint(nrows, size=(nrows,ncols)) ##Matriz de prueba
    #~ size=3
    #~ stepsize=2
    ###-----------------------------------

    print(f"Arreglo inicial= \n{a}")
    print(f"Tamaño de nuevo(s) arreglo(s)= {size}")
    print(f"Tamaño de paso= {stepsize}")
    print("----------------------------------------------------------------------")
    new_array_list,overlapping= sliding_executor(a,size, stepsize)
    print(f"Overlapping= {overlapping}")
    print(new_array_list)




