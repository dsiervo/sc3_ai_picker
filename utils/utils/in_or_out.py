#Script en Python3

#sirve para buscar los eventos dentro del poligono vmm y ll
#tambien genera los ids para el periodo de tiempo revisado
#para revisar sismos ver linea 182.
#Basado en el programa adentro.py

#Juan Carlos Bermudez jcbermudezb@sgc.gov.co



from obspy import read_events, UTCDateTime
from obspy.clients.fdsn import Client


INT_MAX = 10000

# Dados tres puntos colineales p, q,r,  
# la funcion revisa si el punto q esta  
# sobre el segmento de linea 'pr' 
def onSegment(p:tuple, q:tuple, r:tuple) -> bool:

    if ((q[0] <= max(p[0], r[0])) &
        (q[0] >= min(p[0], r[0])) &
        (q[1] <= max(p[1], r[1])) &
        (q[1] >= min(p[1], r[1]))):
        return True

    return False

# Encuentra la orientacion de la tripleta (p, q, r). 
# La funcion devuelve los sigientes valores 
# 0 --> p, q y r son colineales 
# 1 --> Sentido horario 
# 2 --> Sentido antihorario 
def orientation(p:tuple, q:tuple, r:tuple) -> int:

    val = (((q[1] - p[1]) *
            (r[0] - q[0])) -
           ((q[0] - p[0]) *
            (r[1] - q[1])))

    if val == 0:
        return 0
    if val > 0:
        return 1 # Colineal
    else:
        return 2 # Horario o antihorario

def doIntersect(p1, q1, p2, q2):

    # Encuentra las cuatro orientaciones necesarias   
    # para los casos general y especificos. 
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    # Caso general
    if (o1 != o2) and (o3 != o4):
        return True

    # Casos especiales 
    # p1, q1 y p2 son colineales y 
    # p2 esta sobre el segmento p1q1 
    if (o1 == 0) and (onSegment(p1, p2, q1)):
        return True

    # p1, q1 y p2 son colineales y 
    # q2 esta sobre el segmento p1q1 
    if (o2 == 0) and (onSegment(p1, q2, q1)):
        return True

    # p2, q2 y p1 son colineales y 
    # p1 esta sobre el segmento p2q2 
    if (o3 == 0) and (onSegment(p2, p1, q2)):
        return True

    # p2, q2 y q1 son colineales y 
    # q1 esta sobre el segmento p2q2 
    if (o4 == 0) and (onSegment(p2, q1, q2)):
        return True

    return False


# Devuelve verdadero si el punto p esta   
# dentro del poligono[] con n vertices 
def is_inside_polygon(points:list, p:tuple) -> bool:

    n = len(points)

    # El poligono debe tener al menos tres vertices
    # 
    if n < 3:
        return False

    # Crea un punto para el segmento de linea
    # desde p al infinito
    extreme = (INT_MAX, p[1])
    count = i = 0

    while True:
        next = (i + 1) % n

        # Revisa si el segmento de linea de 'p' al 'extremo'  
        # intersecta con el segmento de linea 
        # del 'poligono[i]' al 'poligono[i+1]' 
        if (doIntersect(points[i],
                        points[next],
                        p, extreme)):

            # Si el punto 'p' es colineal con el segmento de linea   
            # segment 'i,i+1', entonces revisa si esta queda sobre  
            # el segmento de linea. Si esta, devuelve verdadero, si no, falso 
            if orientation(points[i], p,
                           points[next]) == 0:
                return onSegment(points[i], p,
                                 points[next])

            count += 1

        i = next

        if (i == 0):
            break

    # Devuelve verdadero si el contador es impar, si no, falso 
    return (count % 2 == 1)


if __name__ == '__main__':


    vmm = open('zonavmm_border.bna','r').readlines()
    #vmm = open('bloque_ll.bna','r').readlines()
    polygon1 = []
    for i in vmm:
        try:
            j = i.split(',')
            x = float(j[0])
            y = float(j[1])
            pvmm = (x,y)
            polygon1.append(pvmm)
        except:
            pass


"""
client = Client("http://10.100.100.232:8091")


laMin = 5.5 # lat minima
laMax = 10.5 # lat maxima

loMin = -75.0 #lon minima
loMax = -72.8 #lon maxima
#6.5 7.0 -73.5 -73.0
ti_cat = UTCDateTime("2021-04-28T00:00:00")
tf_cat = UTCDateTime("2021-04-28T23:59:59")

cat=client.get_events(starttime = ti_cat,endtime = tf_cat,  minlatitude=laMin, maxlatitude=laMax, minlongitude=loMin, maxlongitude=loMax, minmagnitude=0.0, maxmagnitude=10.0)
##IMPORTANTE: la profundidad debe estar en metros 


#cat.plot()

cat1 = read_events()
cat1.clear()


ff1 = open('ids.csv','w')
for b in cat:
    iidd = b.resource_id.id.split('/')[2]
    print(iidd)

    #latEvS = str(b.origins[0].latitude)[0:5]
    latEv = b.origins[0].latitude
    #lonEv = str(b.origins[0].longitude)[0:7]
    lonEv = b.origins[0].longitude
    p=(lonEv, latEv)
    if (is_inside_polygon(points = polygon1, p = p)):
        print('Dentro',iidd)
        if b.event_type == 'earthquake':
            cat1.append(b) 
        else:
            pass
    else:
        print('Fuera')

    #print(polygon1, len(polygon1))	

cat1.write('myCatalog.xml', format='QUAKEML')
"""
