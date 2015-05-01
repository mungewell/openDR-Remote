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
* If the 3rd byte is 0xF0 it is an extended packet and the additional number
  of bytes is in the 13th+14th byte. (...:05:68 = 0x0568 = 1384, add 14 to
  give 1398 byte packet)
* Some TCP/IP packets contain multiple Tascam packets, this may just be an
  articfact of wireshark. None the less they seem to be treated same as
  seperate packets.

Packets are either 'status' which are automatically issued (for display 
updates/streaming audio/etc), or 'command/response' pairs. There are some 
pcap files in the 'pcap' directory and annotated text files explaining 
them.

Display/Status updates (recorder -> computer)
--
These are 14 bytes starting "44:52:20:20:"

VU Meters:
44:52:20:20:12:00:02:02:00:00:00:00:d3:10
                  LL RR                    VU meter L/R values (00..0f, and 85..8f seen) 
                                    NN     possibly numeric value show in top-right of app
                                           (7f..ff seen)

Time Counter:
44:52:20:20:11:01:00:00:00:11:00:00:4c:f5
                           SS              decimal seconds counter (can be larger than 60)

Status Indicator:
44:52:20:20:00:82:00:00:00:00:00:00:00:00
               RR                          10=Stopped, 82=Record+Pause, 81=Record, 12, 16
                                           10=Stopped, 11=Play, 15

Streamed Audio (recorder -> computer)
--
These are like updates in that they are sent automatically, but obviously a
lot larger. No analysis (yet) on what they contain.

44:52:f0:20:20:01:10:00:00:20:2b:00:05:68:00:00:00:00:.... 
                                    __ __ (extra size :05:68 for total of 1398 bytes per packet)

