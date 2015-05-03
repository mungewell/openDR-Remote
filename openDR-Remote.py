
import signal
import socket
import argparse
from datetime import timedelta
from construct import *

import binascii

registers = Struct("registers",
   UBInt16("register"),

   Switch("register-sw", lambda ctx: ctx.register,
      {
         0x0100: Struct("Format", Enum(UBInt16("Format"),
                     BFW_24 = 0,
                     BFW_16 = 1,
                     WAV_24 = 2,
                     WAV_16 = 3,
                     MP3_320 = 4,
                     MP3_256 = 5,
                     MP3_192 = 6,
                     MP3_128 = 7,
                     MP3_96 = 8,
                     _default_ = Pass
                 ),
                 ),
         0x0101: Enum(UBInt16("Sample Rate"),
                     ONE = 0,
                     TWO = 1,
                     TRHEE = 2,
                     _default_ = Pass
                 ),
      },
   )
)

"""
   Switch("data", lambda ctx: ctx.update,
      {
         0x00: Struct("Status", Enum(UBInt8("Status"),
                        STOPPED = 0x10,
                        PLAYING = 0x11,
                        PAUSED = 0x15,
                        RECORD = 0x81,
                        ARMED = 0x82,
                        _default_ = Pass
                     ),
                 ),
         0x07: Struct("Scene", Padding(1),
                     Enum(UBInt8("Scene"),
                        EASY = 0x00,
                        LOUD = 0x01,
                        MUSIC = 0x02,
                        INSTRUMENT = 0x03,
                        INTERVIEW = 0x04,
                        MANUAL = 0x05,
                        _default_ = Pass
                     ),
                 ),
         0x11: Struct("Counter", Padding(1),
                     UBInt32("Counter"),
                 ),
         0x12: Struct("VU-Meter", Padding(1),
                     UBInt8("Right"),
                     UBInt8("Right"),
                     Padding(4),
                     SBInt8("Decimal"),
                 ),
      },
   ),
"""
updates = Struct("updates",
   UBInt8("update"),

   Switch("update-sw", lambda ctx: ctx.update,
      {
         0x11: Struct("Counter", Padding(1),
                     UBInt32("Counter"),
                     Padding(4),
                 ),
      },
      default = Padding(9),
   ),
)

check_length = Struct("check_length",
   Const(Bytes("magic", 2), "DR"),
   UBInt8("type"),
   Padding(9),
   UBInt16("length"),
)

short_packet = Struct("short_packet",
   Const(Bytes("magic", 2), "DR"),
   UBInt16("type"),

   Switch("type-sw", lambda ctx: ctx.type,
      {
         0x2020: Embed(updates),
         0x3020: Embed(registers),
      },
      default = Padding(10),
   ),
)

long_packet = Struct("long_packet",
   Const(Bytes("magic", 2), "DR"),
   UBInt16("type"),
   Padding(8),
   UBInt16("length"),
)

# =====================================================================
def Run():
   global options

   parser = argparse.ArgumentParser(prog="openDR-Remote")

   # Network Option
   parser.set_defaults(tcp='192.168.1.1', port=8010)
   parser.add_argument("-t", "--tcp", dest="tcp", help="TCP/IP address")
   parser.add_argument("-p", "--port", dest="port", help="TCP/IP port")

   options = parser.parse_args()

   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((options.tcp, int(options.port)))
   buffer = ""

   while True:
      data = s.recv(4096)
      buffer += data

      if (len(buffer) >= 14):
         try:
            # ensure that there is enough data
            log = check_length.parse(buffer)

            if (log.type != 0xF0):
               print "Buf:", binascii.hexlify(buffer[:14])
               log = short_packet.parse(buffer)
               buffer = buffer[14:]
            else:
               if (len(buffer) >= log.length + 14):
                  print "Buf:", binascii.hexlify(buffer[:log.length + 14])
                  log = long_packet.parse(buffer)
                  buffer = buffer[log.length + 14:]
               else:
                  log = None
         except ConstError:
            # magic not found
            buffer = buffer[1:]
            log = None
      else:
         log = None

      if log:
         print log

if __name__ == '__main__':
   Run()
