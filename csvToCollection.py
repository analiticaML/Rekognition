import csv
lista = []
with open("/home/analitica2/Documentos/personas.csv") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
            lista.append(row)
print(lista)
