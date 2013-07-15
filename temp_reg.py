import RPi.GPIO as GPIO
import pstorage
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(1, GPIO.OUT)

GPIO.output(1, 0)

storage = pstorage.Storage( "127.0.0.1" )

running = True;

while running:
  time.sleep(0.25)
  f = open('/sys/bus/w1/devices/28-000004611932/w1_slave')
  t = float(f.read().split('=')[-1])/1000
  storage.Server.WebSites.spi_devel.data['temperature'] = t
  print(t);
