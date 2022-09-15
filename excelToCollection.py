import pandas as pd
lista = []
df = pd.read_excel (r'C:\Users\user\Desktop\Despliegue rekognition\personas.xlsx')
for row in df.itertuples():
    tulple = (row.Cedula,row.Nombre,row.Apellido,row.Cargo)
    lista.append(tulple)
print(lista)