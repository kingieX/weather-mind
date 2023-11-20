from flask import Flask, jsonify,render_template,Response
import serial
from serial.tools import list_ports
import sqlite3
import json
import datetime
import threading
import re
import csv
from io import StringIO


app = Flask(__name__)


class WeatherData:
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp

    @classmethod
    def read_serial(cls, comport, baudrate):
        ser = serial.Serial(comport, baudrate, timeout=0.1)
        while True:
            data = ser.readline().decode().strip()
            if data:
                print(f"Received data: {data}")
                json_data = cls.convert_weather_data_to_json(data)  # Convert data to JSON
                json_dict = json.loads(json_data)  # Convert JSON string to dictionary
                conn =  cls.get_db_connection()
                weather_stream = conn.execute("INSERT INTO weather_data (Humidity, DHTTemperature,Pressure,Altitude,BMPTemperature,heatIndex) VALUES (?,?,?,?,?,?)",
                                 (json_dict.get("Humidity", 0), json_dict.get("DHTTemperature", 0), json_dict.get("Pressure", 0),
                                  json_dict.get("Altitude", 0), json_dict.get("BMPTemperature", 0), json_dict.get("heatIndex", 0))
                                 )
                conn.commit()
                conn.close()

    @classmethod
    def export_to_csv(cls):
        conn = cls.get_db_connection()
        cursor = conn.cursor()

        # Fetch all data from the weather_data table
        cursor.execute('SELECT * FROM weather_data ORDER BY created DESC')
        data = cursor.fetchall()

        # Create a StringIO buffer to write CSV data
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # Write header
        csv_writer.writerow(['Timestamp', 'Humidity', 'DHTTemperature', 'Pressure', 'Altitude', 'BMPTemperature', 'heatIndex'])

        # Write data rows
        for row in data:
            csv_writer.writerow(row)

        # Close the database connection
        conn.close()

        # Set up response headers for CSV file
        headers = {
            'Content-Disposition': 'attachment; filename=weather_data.csv',
            'Content-Type': 'text/csv'
        }

        return Response(csv_buffer.getvalue(), mimetype='text/csv', headers=headers)

    @staticmethod
    def convert_weather_data_to_json(data):
        """Converts weather data to JSON."""
        pattern = r'(\w+): ([\d.°%]+)'
        matches = re.findall(pattern, data)
        weather_data = {}
        for key, value in matches:
            value = value.strip('°%')  # Remove '°' and '%' characters
            try:
                value = float(value)
            except ValueError:
                pass
            weather_data[key] = value
        return json.dumps(weather_data, indent=4)
    
    @classmethod
    def get_db_connection(cls):
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def retrieve_last_inserted_data(cls):
        # Connect to the SQLite database
        conn = cls.get_db_connection()
        cursor = conn.cursor()

        # Fetch the last inserted row
        cursor.execute('SELECT * FROM weather_data ORDER BY created DESC LIMIT 1')
        weatherData = cursor.fetchone()

        if weatherData is not None:
            json_data = {
                "Humidity": weatherData[2],
                "DHTTemperature": weatherData[3],
                "Pressure": weatherData[4],
                "Altitude": weatherData[5],
                "BMPTemperature": weatherData[6],
                "heatIndex": weatherData[7]
            }

            data_dict = {
                "json_data": json_data,
                "timestamp": weatherData[1]
            }
        else:
            data_dict = {}

        # Close the database connection
        conn.close()
        return data_dict

# section for getting port

def discover_serial_port():
    # Get a list of available serial ports
    ports = list_ports.comports()
    
    # Filter for ports with a certain keyword, e.g., 'USB'
    usb_ports = [port.device for port in ports if 'USB' in port.description]

    if usb_ports:
        return usb_ports[0]  # Return the first USB port found
    else:
        return None

def start_serial_thread():
    comport = discover_serial_port()
    if comport:
        print(f"Using serial port: {comport}")
        baudrate = 9600  # Baud rate
        WeatherData.read_serial(comport, baudrate)
    else:
        print("No suitable serial port found. Please check your connections.")


# def start_serial_thread():
#     comport = '/dev/ttyACM0'  # Serial port
#     baudrate = 9600  # Baud rate
#     WeatherData.read_serial(comport, baudrate)


# Start the serial reading thread
serial_thread = threading.Thread(target=start_serial_thread)
serial_thread.daemon = True
serial_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather', methods=['GET'])
def get_weather():
    data_dict = WeatherData.retrieve_last_inserted_data()
    return jsonify(data_dict)

@app.route('/export_csv', methods=['GET'])
def export_csv():
    return WeatherData.export_to_csv()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)
