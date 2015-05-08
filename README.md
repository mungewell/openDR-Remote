OpenDR-Remote
=============

This project was started in response to the lack of Linux support
for the DR-22WL audio record, and lack of a public API. The project
aims to reverse engineer the network protocol that is used to control
the recorder and demostrate how the protocol can be used.

The reverse engineering is being done at the network layer, using 
wireshark on a rooted Android device.

The Hardware
============

The audio recorder is a high quality wav/mp3 recorder, with WiFi capabilities
provided by a GainSpan micro. The device acts as a WiFi AP and issues the
connecting PC with 192.168.1.22 (using 192.168.1.1 for itself).

All control is done through a TCP/IP connection to port 8010.

I own a DR-22WL, there is also a DR-44WL (4 channel) recorder which is
known to use the same/similar protocol. If anyone wants to provide logs
from one of those we could analyse the differences.

Packets
=======

Construction:
* All packets start with 0x44, 0x52 ("DR") and are nominally 14 bytes long.
* Packets are padded with 0x00 upto complete size.
* The 3rd byte can signal it is an extended packet and the additional number
  of bytes is in the 13th+14th byte. (...:05:68 = 0x0568 = 1384, add 14 to
  give 1398 byte packet). Long packets seen with 0xF0, 0x40.
* Some TCP/IP packets contain multiple Tascam packets, this may just be an
  articfact of wireshark. None the less they seem to be treated same as
  seperate packets.

Packets are either 'status' which are automatically issued (for display 
updates/streaming audio/etc), or 'command/response' pairs. There are some 
pcap files in the 'pcap' directory and annotated text files explaining 
them.

$ tshark -r shark_dump_1430448755.pcap -Tfields -e frame.number  -e ip.src \
 -e ip.dst -e tcp.len -e data.data > shark_dump_1430448755.pcap.txt


Start of Play - Demo App
========================

The project includes a sample add ('openDR-remote.py') which can do basic
communication with the recorded. The app can decode some of the updates 
from the device and issue some commands (play, record and stop).

This is a good enough start, but I'd like to take if further.
