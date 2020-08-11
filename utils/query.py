class phpmyAdmin(object):
    def __init__(self,codex_in_txt):
        self.txt_file = open(codex_in_txt,"r", encoding="latin-1").readlines()
        self.text= self.txt_file[0]
        for line in self.txt_file [1:]:
            self.text= f'{self.text}\
                        {line}'

    def ID_query(self,ID):
        self.text= str(self.text)%(f'{ID}')
        return self.text

    def date_query(self,initial_date,final_date):
        fecha1,h1 =initial_date.split()
        fecha2,h2 =final_date.split()
        year1,mes1,dia1,hora1,min1,sec1 = fecha1[0:4],fecha1[4:6],fecha1[6:8],h1[0:2],h1[2:4],h1[4:6]
        year2,mes2,dia2,hora2,min2,sec2 = fecha2[0:4],fecha2[4:6],fecha2[6:8],h2[0:2],h2[2:4],h2[4:6]
        self.text=str(self.text)%(f'"{year1}/{mes1}/{dia1} {hora1}:{min1}:{sec1}"', f'"{year2}/{mes2}/{dia2} {hora2}:{min2}:{sec2}"')
        return self.text

    def picks_query(self,initial_date,final_date,stations):
        self.text=str(self.text)%(initial_date, final_date, stations)
        return self.text

    def radial_query(self,lat, lon, ratio, initial_date,final_date, min_mag,max_mag,min_prof,max_prof):
        fecha1,h1 =initial_date.split()
        fecha2,h2 =final_date.split()
        year1,mes1,dia1,hora1,min1,sec1 = fecha1[0:4],fecha1[4:6],fecha1[6:8],h1[0:2],h1[2:4],h1[4:6]
        year2,mes2,dia2,hora2,min2,sec2 = fecha2[0:4],fecha2[4:6],fecha2[6:8],h2[0:2],h2[2:4],h2[4:6]
        self.text=str(self.text)%(f'{lat}', f'{lon}', f'{lat}', f'{min_mag}',f'{max_mag}',f'{min_prof}',f'{max_prof}',
        f'"{year1}/{mes1}/{dia1} {hora1}:{min1}:{sec1}"',
        f'"{year2}/{mes2}/{dia2} {hora2}:{min2}:{sec2}"', f'{ratio}')
        return self.text