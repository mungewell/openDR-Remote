
import six

import signal
import socket
import argparse
import datetime
from construct import *
from time import sleep

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
                KHZ_44_1 = 0,
                KHZ_48 = 1,
                KHZ_96 = 2,
                _default_ = Pass
                ),
            ),
         0x0102: Struct("Data", Enum(UBInt16("PreRecord"),
                OFF = 0,
                ON = 1,
                _default_ = Pass
                ),
            ),
         0x0108: Struct("Data", Enum(UBInt16("Channels"),
                MONO = 0,
                STEREO = 1,
                _default_ = Pass
                ),
            ),
         0x0109: Struct("Data", Enum(UBInt16("DualFormat"),
               OFF = 0,
               MP3_320 = 1,
               MP3_256 = 2,
               MP3_192 = 3,
               MP3_128 = 4,
               MP3_96 = 5,
               MP3_64 = 6,
               MP3_32 = 7,
               _default_ = Pass
                ),
            ),
         0x0200: Struct("Data", Enum(UBInt16("TrackInc"),
               OFF = 0,
               MIN_5 = 1,
               MIN_10 = 2,
               MIN_15 = 3,
               MIN_30 = 4,
               MIN_60 = 5,
               _default_ = Pass
                ),
            ),
         0x0201: Struct("Data", Enum(UBInt16("AutoLevel"),
               OFF = 0,
               DB_6 = 1,
               DB_12 = 2,
               DB_24 = 3,
               DB_48 = 4,
               _default_ = Pass
                ),
            ),
         0x0203: Struct("Data", Enum(UBInt16("AutoMark"),
               OFF = 0,
               LEVEL = 1,
               TIME = 2,
               _default_ = Pass
                ),
            ),
         0x0204: Struct("Data", UBInt16("AutoMarkLevel")),
         #0x0303: Value 0x01 seen?
         0x0600: Struct("Data", Enum(UBInt16("Reverb"),
                OFF = 0,
                ON = 1,
                _default_ = Pass
                ),
            ),
         0x0601: Struct("Data", Enum(UBInt16("ReverbType"),
                HALL1 = 0,
                HALL2 = 1,
                ROOM = 2,
                STUDIO = 3,
                PLATE1 = 4,
                PLATE2 = 5,
                _default_ = Pass
                ),
            ),
         0x0602: Struct("Data", Enum(UBInt16("ReverbMode"),
                MONITOR = 0,
                RECORD = 1,
                _default_ = Pass
                ),
            ),
         0x0603: Struct("Data", UBInt16("ReverbLevel")),
         0x0A02: Struct("Data", Padding(2), Enum(UBInt16("LCF"),
                OFF = 0,
                _40HZ = 1,
                _80HZ = 2,
                _120HZ = 3,
                _220HZ = 4,
                _default_ = Pass
                ),
            ),
         0x0A03: Struct("Data", Padding(2), Enum(UBInt16("LV Control"),
                OFF = 0,
                LIMITER = 1,
                PEAK = 2,
                AUTO = 3,
                _default_ = Pass
                ),
            ),
         0x0B00: Struct("Data", ULInt16("RecordLevel")),
      },
      default = Pass,
   )
)

# =====================================================================
# Keep seperate as VU-Meters are very 'talkative'
vumeters = Struct("VUMeters", Padding(1),
   Peek(BitStruct("Flags",
      Flag("Peek"),
      Padding(7),
      Flag("12dB"),
      Padding(7),
   )),
   UBInt8("left"),
   UBInt8("right"),

   Value("Left", lambda ctx: ctx.left & 0x7f),
   Value("Right", lambda ctx: ctx.right & 0x7f),

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
                        TIMER = 0x83,
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
file_entry = Struct("Files",
   Peek(BitStruct("Directory",
      Flag("Directory"),
      Padding(7),
   )),
   UBInt16("index"),
   Value("Index", lambda ctx: ctx.index & 0x7fff),
   Padding(8),

   Peek(RepeatUntil(lambda obj, ctx: obj == "\x00\x0d", Field("data",2))),
   Value("flength", lambda ctx: (len(ctx.data) - 1) * 2),
   String("Filename", lambda ctx: ctx.flength, "utf-16-le"),
   Padding(2),
)

file_name = Struct("Filename",
   String("Filename", lambda ctx: ctx._.length - 2, "utf-16-le"),
)

file_data = Struct("FileData",
   Bytes("FileData", lambda ctx: ctx._.length),
)

stream_data = Struct("StreamData",
   Bytes("StreamData", lambda ctx: ctx._.length),
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
   BitStruct("Flags",
      Padding(1),
      Flag("Long"),
      Padding(6),
   ),
   Padding(9),
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
   Peek(UBInt8("type1")),
   BitStruct("Flags",
      Padding(1),
      Flag("Long"),
      Padding(6),
   ),
   UBInt16("type"),

   Padding(7),
   UBInt16("length"),

   Switch("System", lambda ctx: ctx.type,
      {
         0x2000 : sys_info,
         0x2020 : stream_data,
         0x2032 : IfThenElse("data", lambda ctx: ctx.type1 == 0xf0,
            file_name,
            file_data,
         ),
         0x2010 : Struct("Files",
            GreedyRange(file_entry),
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
   parser.add_argument("-i", "--info", action="store_true", dest="info", help="request info from recorder")
   parser.add_argument("-R", "--rec", action="store_true", dest="rec", help="start recording")
   parser.add_argument("-p", "--play", action="store_true", dest="play", help="start playback")
   parser.add_argument("-s", "--stop", action="store_true", dest="stop", help="stop playback/recording")
   parser.add_argument("-S", "--stream", action="store_true", dest="stream", help="use streaming audio")
   parser.add_argument("-L", "--level", dest="level", help="set input level for recording [0-90]")
   parser.add_argument("-v", "--vu", action="store_true", dest="vu", help="show vu meters (verbose)")

   parser.add_argument("-c", "--clock", action="store_true", dest="clock", help="set clock to match PC's")
   parser.add_argument("-r", "--reg", dest="reg", help="read register bank [0-9]")

   # File actions for device
   parser.add_argument("-l", "--list", action="store_true", dest="listing", help="list stored files")
   parser.add_argument("-d", "--download", dest="download", help="download file [index from listing]")

   parser.add_argument("-D", "--debug", action="store_true", dest="debug", help="dump received packets in hex")
   options = parser.parse_args()

   if options.download:
      options.listing = True

   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.connect((options.tcp, int(options.port)))
   s.settimeout(0.001)
   buffer = ""
   loop = 0
   store_file = None

   sleep(1)
   while True:
      try:
         data = s.recv(14)
         buffer += data
      except socket.timeout:
         pass

      if loop == 0:
         s.send("\x44\x52\x20\x42\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00")

      if options.reg:
         for reg in range(10):
            s.send("\x44\x52\x30\x42" + chr(int(options.reg)) + chr(reg) + \
               "\x00\x00\x00\x00\x00\x00\x00\x00") # Read 
         options.reg = False

      if options.info:
         s.send("\x44\x52\xf0\x41\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Request SysInfo

         s.send("\x44\x52\x30\x42\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read File Type
         s.send("\x44\x52\x30\x42\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00") # Read Sample Rate
         s.send("\x44\x52\x30\x42\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Read PreRecord
         s.send("\x44\x52\x30\x42\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00") # Read Channels
         s.send("\x44\x52\x30\x42\x01\x09\x00\x00\x00\x00\x00\x00\x00\x00") # Read Dual Mode

         s.send("\x44\x52\x30\x42\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Track Inc
         s.send("\x44\x52\x30\x42\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Level
         s.send("\x44\x52\x30\x42\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Mark
         s.send("\x44\x52\x30\x42\x02\x04\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Mark Level

         s.send("\x44\x52\x30\x42\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read ???

         s.send("\x44\x52\x30\x42\x0a\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Read low cut
         s.send("\x44\x52\x30\x42\x0a\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read level control

         s.send("\x44\x52\xf0\x41\x32\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Request Filename
         s.send("\x44\x52\x20\x42\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Counter
         s.send("\x44\x52\x20\x42\x20\x07\x00\x00\x00\x00\x00\x00\x00\x00") # Read Scene
         s.send("\x44\x52\x20\x42\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Status
         options.info = False

      if (options.stream):
         s.send("\x44\x52\xf0\x41\x21\x01\x00\x00\x00\x00\x00\x00\x00\x00")
         stream_file = open("stream.dat", "wb")
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

      if options.listing:
         s.send("\x44\x52\x40\x41\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00")
         options.listing = False

      if options.level:
         s.send("\x44\x52\x30\x41\x0b\x00" + \
            chr(int(options.level))+chr(int(options.level)) + \
            "\x00\x00\x00\x00\x00\x00")
         options.level = False

      if options.clock:
         now = datetime.datetime.now()
         print "Setting the clock to:", now
         # For some reason you have to send this twice
         s.send("\x44\x52\x30\x41\x07\x00" + \
            chr(int(now.year) >> 8) + chr(int(now.year) & 0xFF) + \
            chr(int(now.month)) +  chr(int(now.day)) + \
            chr(int(now.hour)) + chr(int(now.minute)) + \
            chr(int(now.second)) + "\x00")
         s.send("\x44\x52\x30\x41\x07\x00" + \
            chr(int(now.year) >> 8) + chr(int(now.year) & 0xFF) + \
            chr(int(now.month)) +  chr(int(now.day)) + \
            chr(int(now.hour)) + chr(int(now.minute)) + \
            chr(int(now.second)) + "\x00")
         options.clock = False

      if (len(buffer) >= 14):
         try:
            # ensure that there is enough data
            log = check_packet.parse(buffer)

            if log.Flags.Long:
               if log.length:
                  try:
                     data = s.recv(log.length)
                     buffer += data
                  except socket.timeout:
                     pass

               if (len(buffer) >= log.length + 14):
                  if options.debug:
                     print "Buf:", binascii.hexlify(buffer[:14]), "...", log.length
                  log = long_packet.parse(buffer)
                  buffer = buffer[log.length + 14:]
               else:
                  log = None
            else:
               if options.debug:
                  print "Buf:", binascii.hexlify(buffer[:14])
               log = short_packet.parse(buffer)
               buffer = buffer[14:]
         except ConstError:
            # magic not found
            buffer = ""
            log = None
      else:
         log = None

      loop = loop + 1

      if log:
         if log.get('Update'):
            print log.Update
         if log.get('Register'):
            print log.Register
         if log.get('VUMeters') and options.vu:
            print log.VUMeters
         if log.get('System'):
            if log.System.get('Files'):
               for x in range(len(log.System.Files)):
                  if options.download:
                     if int(options.download) == log.System.Files[x].Index:
                        storage_file = open(log.System.Files[x].Filename, "wb")
                        s.send("\x44\x52\x40\x41\x30\x00\x00"+chr(int(options.download))+"\x00\x00\x00\x00\x00\x00")
                        print "*",
                  print log.System.Files[x].Index, "=", log.System.Files[x].Filename
            elif log.System.get('FileData') and storage_file:
               storage_file.write(log.System.FileData)
            elif log.System.get('StreamData') and stream_file:
               stream_file.write(log.System.StreamData)
            else:
               print log.System

if __name__ == '__main__':
   Run()
