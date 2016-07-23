# sigfox2aprs

Two small programs to take data from the sigfox backend and publish as APRS Objects. It uses mqtt to pass the requesite data to a second (python) process for publishing on the APRS-IS.   

## callback.php
This is run on a suitable cgi-enabled webserver. Depends on https://github.com/bluerhinos/phpMQTT for MQTT connectivity. The Sigfox backend needs to be configured to call this callback.

## mqtt2aprs
A small program for connecting to the APRS-IS backbone using https://github.com/rossengeorgiev/aprs-python and http://www.eclipse.org/paho/

It listens for mqtt messages from callback.php and pushes matching messages into the APRS-IS backone. Currently only have two units, so matching is hardcoded.

### mqtt2aprs Config file
    [mqtt]
    server = 127.0.0.1
    port = 1883
    clientname = Sigfox Sub
    topics = sigfox/#

    [aprs] 
    callsign = mqtt2aprs
    password = -1
    host = rotate.aprs2.net
    port = 14580

    [logging]
    level = logging.INFO

