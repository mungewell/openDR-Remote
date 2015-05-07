
import six

import signal
import socket
import argparse
from datetime import timedelta
from construct import *

import binascii

registers = Struct("registers",
   UBInt16("register"),

   Switch("Register", lambda ctx: ctx.register,
      {
         0x0100: Struct("Data", Enum(UBInt16("Format"),
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
         0x0101: Struct("Data", Enum(UBInt16("SampleRate"),
                _44_1KHZ = 0,
                _48KHZ = 1,
                _96KHZ = 2,
                _default_ = Pass
                ),
            ),
      },
   )
)

# Keep seperate as VU-Meters are very 'talkative'
vumeters = Struct("VUMeters", Padding(1),
   UBInt8("Left-VU"),
   UBInt8("Right-VU"),
   Padding(4),
   SBInt8("Decimal-VU"),
)

updates = Struct("updates",
   Byte("type3"),

   If(lambda ctx: ctx.type3 == 0x12,
      vumeters,
   ),
   If(lambda ctx: ctx.type3 != 0x12,
   Switch("Update", lambda ctx: ctx.type3,
      {
         0x00: Struct("Data", Enum(Byte("Status"),
                        STOPPED = 0x10,
                        PLAYING = 0x11,
                        PLAYPAUSED = 0x12,
                        FORWARD = 0x13,
                        REWIND = 0x14,
                        PAUSED = 0x15,
                        STOPPING = 0x16,
                        RECORD = 0x81,
                        ARMED = 0x82,
                        _default_ = Pass
                     ),
                     Padding(8),
                 ),
         0x11 : Struct("Data", Padding(1),
                     UBInt32("Counter"),
                     Padding(4),
                 ),
         0x20: Struct("Data", Magic('\x07'),
                     Enum(UBInt8("Scene"),
                        EASY = 0x00,
                        LOUD = 0x01,
                        MUSIC = 0x02,
                        INSTRUMENT = 0x03,
                        INTERVIEW = 0x04,
                        MANUAL = 0x05,
                        DUB = 0x06,
                        PRACTICE = 0x07,
                        _default_ = Pass
                     ),
                 ),
      },
      default = Pass,
   ),
   ),
)

sys_info = Struct("sys_info",
   String("Name", 8),
   Padding(8),
   UBInt16("version"),
   Value("Version", lambda ctx: ctx.version / 100),
   UBInt16("Build"),
   UBInt16("wifi1"),
   Value("Wifi1", lambda ctx: ctx.wifi1 / 100),
   UBInt16("wifi2"),
   Value("Wifi2", lambda ctx: ctx.wifi2 / 100),
)

check_packet = Struct("check_packet",
   Magic("DR"),
   UBInt8("type1"),
   UBInt8("type2"),
   UBInt8("type3"),
   Padding(7),
   UBInt16("length"),
)

short_packet = Struct("short_packet",
   Magic("DR"),
   UBInt16("type"),

   Switch("Type", lambda ctx: ctx.type,
      {
         0x2020 : Embed(updates),
      },
      default = Pass,
   ),
)

long_packet = Struct("long_packet",
   Magic("DR"),
   UBInt8("type1"),
   UBInt16("type"),
   Padding(7),
   UBInt16("length"),

   Switch("System", lambda ctx: ctx.type,
      {
         0x2000 : sys_info,
         0x2032 : Struct("Filename",
            String("Filename", lambda ctx: ctx._.length - 2, "utf-16-le"),
         ),
      },
      default = Pass,
   ),
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
   s.settimeout(0.001)
   buffer = ""

   while True:
      try:
         data = s.recv(4096)
         buffer += data
      except socket.timeout:
         pass

      if (len(buffer) >= 14):
         try:
            # ensure that there is enough data
            log = check_packet.parse(buffer)

            if (log.type1 != 0xF0):
               #print "Buf:", binascii.hexlify(buffer[:14])
               log = short_packet.parse(buffer)
               buffer = buffer[14:]
            else:
               if (len(buffer) >= log.length + 14):
                  #print "Buf:", binascii.hexlify(buffer[:log.length + 14])
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
         if log.get('Update'):
            print log.Update
         if log.get('System'):
            print log.System

if __name__ == '__main__':
   Run()
