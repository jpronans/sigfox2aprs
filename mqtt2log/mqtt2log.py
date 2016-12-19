import paho.mqtt.client as mqtt
import subprocess
import time
from ConfigParser import SafeConfigParser
import logging
import logging.handlers
import os

# Constant
exit_me = False

parser = SafeConfigParser()
parser.read('config.ini')

my_name = parser.get('mqtt', 'clientname')
output_format = my_name+' %(message)s'

# Set up Logger object
logger = logging.getLogger(my_name)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s '+output_format)

# Set up a handler for pushing to syslog
# This line should be used for a properly listening syslogd
#handler = logging.handlers.SysLogHandler(facility=logging.handlers.SysLogHandler.LOG_DAEMON, address=('localhost', 514))
handler = logging.handlers.SysLogHandler(facility=logging.handlers.SysLogHandler.LOG_DAEMON, address='/dev/log')
# Change to our format
formatter = logging.Formatter(output_format)
handler.setFormatter(formatter)
logger.addHandler(handler)


def process_sigfox_messages(topic, payload):
    logger.debug("Payload %s" % payload)

    if topic == "sigfox/survey":
        time, data, id, station, duplicate, rssi, snr, avgSnr, seqNumber, lat, long = payload.split(':')

        # Grab the bits we need from the mqtt payload
        f = open(parser.get('logging', 'prefix')+"-"+station+".js", "a+")

        # Move the pointer (similar to a cursor in a text editor) to the end of the file. 
        f.seek(0, os.SEEK_END)

        # This code means the following code skips the very last character in the file -
        # i.e. in the case the last line is null we delete the last line
        # and the penultimate one
        pos = f.tell() - 1

        # Read each character in the file one at a time from the penultimate 
        # character going backwards, searching for a newline character
        # If we find a new line, exit the search
        while pos > 0 and f.read(1) != "\n":
                pos -= 1
                f.seek(pos, os.SEEK_SET)

        #So long as we're not at the start of the file, delete all the characters ahead of this position
        if pos > 0:
                f.seek(pos, os.SEEK_SET)
                f.truncate()

        outStr = "\n[%.4f, %.4f, %3d],  <!-- %s -->\n];\n" % (float(lat), float(long), int(float(rssi)+200), payload)
        try:
            f.write(outStr)
        except:
            outStr = "Caught Exception: could not write to log file.\n"
            logging.debug(outStr)

        f.close()
        logger.info("Logged: %s" % payload)


# Send desktop notification.
def notify(title, message):
    sendmessage(title, message)


# Send Desktop notification
def sendmessage(title, message):
    subprocess.Popen(['notify-send', str(title), str(message), '-t', '10000'])


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.debug("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    topic_list = []
    for item in parser.get('mqtt', 'topics').split(','):
        topic_list.append((item.lstrip(), 0))
    logger.info("Topic list is: %s" % topic_list)
    logger.info("Prefix is: %s" % parser.get('logging', 'prefix'))

    client.subscribe(topic_list)
    logger.info("Subscribed")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global exit_me

    if msg.topic == "sigfox/survey":
        process_sigfox_messages(msg.topic, msg.payload)
    # Control Messages
    elif msg.topic == "sigfox/debug":
        if msg.payload.upper() == "DEBUG":
            logger.info("Logging level now {}".format(msg.payload.upper()))
            logger.setLevel(logging.DEBUG)
        if msg.payload.upper() == "INFO":
            logger.info("Logging level now {}".format(msg.payload.upper()))
            logger.setLevel(logging.INFO)
        #
        if msg.payload.upper() == "EXIT":
            logger.info("Received exit so exiting...")
            exit_me = True
            client.disconnect()


def main():
    client = mqtt.Client(parser.get('mqtt', 'clientname'),
                         userdata=file, clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(parser.get('mqtt', 'server'),
                   parser.get('mqtt', 'port'), 60)

    # Loop forever
    try:
        client.loop_forever()
    # Catches SigINT
    except KeyboardInterrupt:
        global exit_me
        exit_me = True
        client.disconnect()
        logger.info("Exiting main thread")
        time.sleep(2.0)

if __name__ == '__main__':
    main()
