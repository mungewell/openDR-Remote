
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
      default = Pass,
   )
)

# =====================================================================
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

# =====================================================================
file_entry = Struct("file_entry",
   Peek(BitStruct("Directory",
      Flag("Directory"),
      Padding(7),
   )),
   UBInt16("Index"),
   Padding(8),

   Peek(RepeatUntil(lambda obj, ctx: obj == "\x00\x0d", Field("data",2))),
   Value("length", lambda ctx: (len(ctx.data) - 1) * 2),
   String("Filename", lambda ctx: ctx.length, "utf-16-le"),
   Padding(2),
)

file_table = Struct("file_table",
   Padding(3),
   UBInt16("Count"),
   Padding(4),

   Array(lambda ctx: ctx.Count, file_entry),
)

# =====================================================================
sys_info = Struct("sys_info",
   String("Name", 8),
   Padding(8),
   UBInt16("Version"),
   UBInt16("Build"),
   UBInt16("Wifi1"),
   UBInt16("Wifi2"),
)

# =====================================================================
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
         0x3020 : Embed(registers),
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
   parser.add_argument("-T", "--tcp", dest="tcp", help="TCP/IP address")
   parser.add_argument("-P", "--port", dest="port", help="TCP/IP port")

   # Perform actions on the recorder
   parser.add_argument("-r", "--reg", action="store_true", dest="reg", help="read registers")
   parser.add_argument("-R", "--rec", action="store_true", dest="rec", help="start recording")
   parser.add_argument("-p", "--play", action="store_true", dest="play", help="start playback")
   parser.add_argument("-s", "--stop", action="store_true", dest="stop", help="stop playback/recording")
   parser.add_argument("-S", "--stream", action="store_true", dest="stream", help="use streaming audio")
   options = parser.parse_args()

   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((options.tcp, int(options.port)))
   s.settimeout(0.001)
   buffer = ""

   while True:
      try:
         data = s.recv(256)
         buffer += data
      except socket.timeout:
         pass

      if (options.reg):
         print "Attempt to read register"
         # s.send("\x44\x52\x20\x42\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00")
         s.send("\x44\x52\x30\x42\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read File Type
         s.send("\x44\x52\x30\x42\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00") # Read Sample Rate
         # s.send("\x44\x52\x30\x42\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x04\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x05\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x06\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x07\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x01\x09\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x05\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x02\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x02\x04\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00")
         # s.send("\x44\x52\x30\x42\x0a\x80\x00\x00\x00\x00\x00\x00\x00\x00")
         s.send("\x44\x52\xf0\x41\x32\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Request Filename
         s.send("\x44\x52\xf0\x41\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Request SysInfo
         options.reg = False

      if (options.stream):
         s.send("\x44\x52\xf0\x41\x21\x01\x00\x00\x00\x00\x00\x00\x00\x00")
         options.stream= False

      if (options.play):
         s.send("\x44\x52\x10\x41\x00\x09\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Play"
         options.play = False

      if (options.rec):
         s.send("\x44\x52\x10\x41\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Record"
         options.rec = False

      if (options.stop):
         s.send("\x44\x52\x10\x41\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Stop"
         options.stop= False

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
                  print "Buf:", binascii.hexlify(buffer[:14]), "..."
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
         if log.get('Register'):
            print log.Register
         if log.get('System'):
            print log.System

if __name__ == '__main__':
   Run()
