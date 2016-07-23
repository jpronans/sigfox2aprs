import paho.mqtt.client as mqtt
import subprocess
import time
from ConfigParser import SafeConfigParser
import logging
import logging.handlers
import aprslib

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
    aprs = aprslib.IS(parser.get('aprs', 'callsign'),
                          parser.get('aprs', 'password'),
                          parser.get('aprs', 'host'),
                          parser.get('aprs', 'port'))
    aprs.connect()
    if topic == "sigfox/aprs":
        # Grab the bits we need from the mqtt payload
        id, lat, long, sats, hdop = payload.split(':')
        # http://www.aprs.org/aprs11/SSIDs.txt One way trackers should use -12

        # Currently only have two units.
        if id == "1511B":
            data = "EI0AC-9>APZWIT:!%s/%sa Sats:%s HDOP:%s Unit:%s" % (lat, long, sats, hdop, id)
        if id == "151DD":
            data = "EI0AC-8>APZWIT:!%s/%sa Sats:%s HDOP:%s Unit:%s" % (lat, long, sats, hdop, id)

        notify("Sending:", data)
        logger.info("Sending: %s" % data)
        aprs.sendall(data)

    elif topic == "sigfox/telem":
        id, seqNumber, snr, avgSnr, rssi, sats, hdop = payload.split(':')
        if id == "1511B":
            data = "EI0AC-9>APZWIT:T#%03d,%03d,%03d,%03d,%03d,%03d,00000000" % ((int(seqNumber) % 255), int(float(snr)),  int(float(avgSnr)), abs(float(rssi)), int(sats), int(hdop))
        if id == "151DD":
            data = "EI0AC-8>APZWIT:T#%03d,%03d,%03d,%03d,%03d,%03d,00000001" % ((int(seqNumber) % 255), int(float(snr)),  int(float(avgSnr)), abs(float(rssi)), int(sats), int(hdop))
        logger.info("Sending: %s" % data)
        aprs.sendall(data)
        time.sleep(1)


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

    client.subscribe(topic_list)
    logger.info("Subscribed")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global exit_me
    # logger.debug("Topic is: %s" % msg.topic)
    # Output from the cc128 perl scripts
    if msg.topic == "sigfox/aprs":
        process_sigfox_messages(msg.topic, msg.payload)
    if msg.topic == "sigfox/telem":
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
                         userdata=None, clean_session=True)
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
