import sqlite3

connection = sqlite3.connect('database.db')


with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute("INSERT INTO weather_data (Humidity, DHTTemperature,Pressure,Altitude,BMPTemperature,heatIndex) VALUES (?,?,?,?,?,?)",
            ('83.0', '30.2','1003.54','79.1','29.91','39.2')
            )
connection.commit()
connection.close()

