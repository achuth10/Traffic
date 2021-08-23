# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.


# CODE TO RUN    py AWS_Traffic.py --root-ca Amazon-root-CA-1.pem --cert device.pem.crt --key private.pem.key

import argparse
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
from uuid import uuid4
import json
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import time

# This sample uses the Message Broker for AWS IoT to send and receive messages
# through an MQTT connection. On startup, the device connects to the server,
# subscribes to a topic, and begins publishing messages to that topic.
# The device should receive those same messages back from the message broker,
# since it is subscribed to that same topic.

parser = argparse.ArgumentParser(description="Send and receive messages through and MQTT connection.")
# parser.add_argument('--endpoint', required=True, help="Your AWS IoT custom endpoint, not including a port. " +
                                                    #   "Ex: \"abcd123456wxyz-ats.iot.us-east-1.amazonaws.com\"")
parser.add_argument('--port', type=int, help="Specify port. AWS IoT supports 443 and 8883.")
parser.add_argument('--cert', help="File path to your client certificate, in PEM format.")
parser.add_argument('--key', help="File path to your private key, in PEM format.")
parser.add_argument('--root-ca', help="File path to root certificate authority, in PEM format. " +
                                      "Necessary if MQTT server uses a certificate that's not already in " +
                                      "your trust store.")
parser.add_argument('--client-id', default="test-" + str(uuid4()), help="Client ID for MQTT connection.")
# parser.add_argument('--topic', default="test/topic", help="Topic to subscribe to, and publish messages to.")
# parser.add_argument('--message', default="Hello World!", help="Message to publish. " +
                                                            #   "Specify empty string to publish nothing.")
# parser.add_argument('--count', default=10, type=int, help="Number of messages to publish/receive before exiting. " +
                                                        #   "Specify 0 to run forever.")
parser.add_argument('--use-websocket', default=False, action='store_true',
    help="To use a websocket instead of raw mqtt. If you " +
    "specify this option you must specify a region for signing.")
parser.add_argument('--signing-region', default='us-east-1', help="If you specify --use-web-socket, this " +
    "is the region that will be used for computing the Sigv4 signature")
parser.add_argument('--proxy-host', help="Hostname of proxy to connect to.")
parser.add_argument('--proxy-port', type=int, default=8080, help="Port of proxy to connect to.")
parser.add_argument('--verbosity', choices=[x.name for x in io.LogLevel], default=io.LogLevel.NoLogs.name,
    help='Logging level')

# Using globals to simplify sample code
args = parser.parse_args()

io.init_logging(getattr(io.LogLevel, args.verbosity), 'stderr')

received_count = 0
received_all_event = threading.Event()

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == 10:
        received_all_event.set()
def turn_green():
        GPIO.output(23, GPIO.HIGH) # Turn on # Sleep for 1 second
        GPIO.output(20, GPIO.LOW) # Turn off # Sleep for 1 second
        GPIO.output(16, GPIO.LOW)
def turn_yellow():
    GPIO.output(23, GPIO.LOW) # Turn on # Sleep for 1 second
    GPIO.output(20, GPIO.HIGH) # Turn off # Sleep for 1 second
    GPIO.output(16, GPIO.LOW)
def turn_red():
    GPIO.output(23, GPIO.LOW) # Turn on # Sleep for 1 second
    GPIO.output(20, GPIO.LOW) # Turn off # Sleep for 1 second
    GPIO.output(16, GPIO.HIGH)

if __name__ == '__main__':
    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    proxy_options = None
    if (args.proxy_host):
        proxy_options = http.HttpProxyOptions(host_name=args.proxy_host, port=args.proxy_port)

    if args.use_websocket == True:
        credentials_provider = auth.AwsCredentialsProvider.new_default_chain(client_bootstrap)
        mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint="a32yt7qpdd8hkw-ats.iot.ap-south-1.amazonaws.com",
            client_bootstrap=client_bootstrap,
            region=args.signing_region,
            credentials_provider=credentials_provider,
            http_proxy_options=proxy_options,
            ca_filepath=args.root_ca,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=args.client_id,
            clean_session=False,
            keep_alive_secs=30)

    else:
        mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint="a32yt7qpdd8hkw-ats.iot.ap-south-1.amazonaws.com",
            port=args.port,
            cert_filepath=args.cert,
            pri_key_filepath=args.key,
            client_bootstrap=client_bootstrap,
            ca_filepath=args.root_ca,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=args.client_id,
            clean_session=False,
            keep_alive_secs=30,
            http_proxy_options=proxy_options)

    print("Connecting to {} with client ID '{}'...".format(
        "a32yt7qpdd8hkw-ats.iot.ap-south-1.amazonaws.com", args.client_id))

    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    # Subscribe
    print("Subscribing to topic '{}'...".format("topic"))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic="topic",
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    # Publish message to server desired number of times.
    # This step is skipped if message is blank.
    # This step loops forever if count was set to 0.
    # if args.count == 0:
    #     print ("Sending messages until program killed")
    # else:
    #     print ("Sending {} message(s)".format(args.count))



    # Code to PUBLISH
    # publish_count = 1
    # while True:
    #     message = "Message"
    #     print("Publishing message to topic '{}': {}".format("topic", message))
    #     message_json = json.dumps(message)
    #     mqtt_connection.publish(
    #         topic="topic",
    #         payload=message_json,
    #         qos=mqtt.QoS.AT_LEAST_ONCE)
    #     time.sleep(1)
    #     publish_count += 1
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BCM) # Use physical pin numbering
    GPIO.setup(23, GPIO.OUT, initial=GPIO.LOW) # Set pin 8 to be an output pin and set initial value to low (off)
    GPIO.setup(20, GPIO.OUT, initial=GPIO.LOW) #
    GPIO.setup(16, GPIO.OUT, initial=GPIO.LOW) #
    G=Y=R=0
    cur=""
        
    while(True):
      if(G==0 and Y==0 and R==0):
        G=5
        Y=2
        R=3
      if(G>0):
        if(cur!="green"):
          turn_green()
          print("green")
          cur="green"
        G-=1
      elif(Y>0):
        if(cur!="yellow"):
          turn_yellow()
          print("yellow")
          cur="yellow"
        Y-=1
      else:
        if(cur!="red"):
          turn_red()
          print("red")
          cur="red"
        R-=1
      time.sleep(1)

    # Wait for all messages to be received.
    # This waits forever if count was set to 0.
    if not received_all_event.is_set():
        # if args.count != 0 and not received_all_event.is_set():
        print("Waiting for all messages to be received...")

    received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
