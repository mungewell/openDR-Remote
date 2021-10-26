
import six

import signal
import socket
import argparse
import datetime
from construct import *
from time import sleep

import binascii

registers = Struct(
   "register" / Short,

   "Register" / Switch(this.register,
      {
         0x0100: "Format" / Struct(
                 "Format" / Enum(Short,
               BWF_24 = 0,
               BWF_16 = 1,
               WAV_24 = 2,
               WAV_16 = 3,
               MP3_320 = 4,
               MP3_256 = 5,
               MP3_192 = 6,
               MP3_128 = 7,
               MP3_96 = 8,
               )),
         0x0101: "SampleRate" / Struct(
                 "SampleRate" / Enum(Short,
                KHZ_44_1 = 0,
                KHZ_48 = 1,
                KHZ_96 = 2,
                )),
         0x0102: "PreRecord" / Struct(
                 "PreRecord" / Enum(Short,
                OFF = 0,
                ON = 1,
                )),
         0x0108: "Channels" / Struct(
                 "Channels" / Enum(Short,
                MONO = 0,
                STEREO = 1,
                )),
         0x0109: "DualFormat" / Struct(
                 "DualFormat" / Enum(Short,
               OFF = 0,
               MP3_320 = 1,
               MP3_256 = 2,
               MP3_192 = 3,
               MP3_128 = 4,
               MP3_96 = 5,
               MP3_64 = 6,
               MP3_32 = 7,
               )),
         0x0200: "TrackInc" / Struct(
                 "TrackInc" / Enum(Short,
               OFF = 0,
               MIN_5 = 1,
               MIN_10 = 2,
               MIN_15 = 3,
               MIN_30 = 4,
               MIN_60 = 5,
               )),
         0x0201: "AutoLevel" / Struct(
                 "AutoLevel" / Enum(Short,
               OFF = 0,
               DB_6 = 1,
               DB_12 = 2,
               DB_24 = 3,
               DB_48 = 4,
               )),
         0x0202: "PeakMark" / Struct(
                 "PeakMark" / Enum(Short,
               OFF = 0,
               ON = 1,
               )),
         0x0203: "AutoMark" / Struct(
                 "AutoMark" / Enum(Short,
               OFF = 0,
               LEVEL = 1,
               TIME = 2,
               )),
         0x0204: "AutoMarkLevel" / Struct(
                 "AutoMarkLevel" / Short,
               ),
         #0x0303: Value 0x01 seen?

         0x0600: "Reverb" / Struct(
                 "Reverb" / Enum(Short,
                OFF = 0,
                ON = 1,
                )),
         0x0601: "ReverbType" / Struct(
                 "ReverbType" / Enum(Short,
                HALL1 = 0,
                HALL2 = 1,
                ROOM = 2,
                STUDIO = 3,
                PLATE1 = 4,
                PLATE2 = 5,
                )),
         0x0602: "ReverbMode" / Struct(
                 "ReverbMode" / Enum(Short,
                MONITOR = 0,
                RECORD = 1,
                )),
         0x0603: "ReverbLevel" / Struct(
                 "ReverbLevel" / Short,
                ),
         0x0A02: "LCF" / Struct(
                Padding(2),
                "LCF" / Enum(Short,
                OFF = 0,
                HZ_40 = 1,
                HZ_80 = 2,
                HZ_120 = 3,
                HZ_220 = 4,
                )),
         0x0A03: "LV Control" / Struct(
                Padding(2),
                "LV Control" / Enum(Short,
                OFF = 0,
                LIMITER = 1,
                PEAK = 2,
                AUTO = 3,
                )),
         0x0B00: "RecordLevel" / Struct(
                 "RecordLevel" / Int16ul,
                ),
      },
   )
)

# =====================================================================
# Keep seperate as VU-Meters are very 'talkative'
vumeters = Struct(
   Padding(1),
   "Flags" / Peek(BitStruct(
      "Peek" / BitsInteger(1), 
      Padding(7),
      "12dB" / BitsInteger(1),
      Padding(7),
   )),
   "left" / Byte,
   "right" / Byte,

   "VU-Meters" / Struct(
   "Left" / Computed(this._.left & 0x7f),
   "Right" / Computed(this._.right & 0x7f),

   Padding(4),
   "Decimal-VU" / Int8sb,
   )
)

screeninfo = Struct(
   "type4" / Byte,

   "ScreenInfo" / Switch(this.type4,
      {
         0x03 :  "Audio Output" / Struct(
                     "Audio Output" / Enum(Byte,
                        SPEAKER = 0x01,
                        HEADPHONE = 0x02,
                     ),
                 ),
         0x05 :  "Battery" / Struct(
                     "Battery" / Enum(Byte,
                        BAR0 = 0x00,
                        BAR1 = 0x01,
                        BAR2 = 0x02,
                        BAR3 = 0x03,
                        USB = 0x04,
                     ),
                 ),
         0x07 : "Scene" / Struct(
                     "Scene" / Enum(Byte,
                        EASY = 0x00,
                        LOUD = 0x01,
                        MUSIC = 0x02,
                        INSTRUMENT = 0x03,
                        INTERVIEW = 0x04,
                        MANUAL = 0x05,
                        DUB = 0x06,
                        PRACTICE = 0x07,
                     ),
                 ),
      },
      default = Pass,
   ),
)

updates = Struct(
   "type3" / Byte,

   "Update" / Switch(this.type3,
      {
         0x00: "Status" / Struct("Status" / Enum(Byte,
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
                     ),
                     Padding(8),
                 ),
         0x11 : "Counter" / Struct(Padding(1),
                     "Counter" / Int,
                     Padding(4),
                 ),
         0x12 : "VU-Meters" / vumeters,
         0x20 : "ScreenInfo" / screeninfo
      },
      default = Pass,
   ),
)

# =====================================================================
file_entry = Struct(
   Peek("Directory" / BitStruct(
      "Directory" / BitsInteger(1),
      Padding(7),
   )),
   "index" / Short,
   "Index" / Computed(this.index & 0x7fff),
   Padding(8),
   "data" / Peek(RepeatUntil(lambda obj,lst,ctx: obj == 0x000d, Short)),
   "flength" / Computed(lambda ctx: (ctx.data.__len__() - 1) * 2),
   "FileEntry" / PaddedString(this.flength, "utf-16-le"),
   Padding(2),
)

file_name = Struct(
   "Filename" / PaddedString(this._._.length - 2, "utf-16-le"),
)

file_data = Struct(
   "FileData" / Bytes(this._._.length),
)

stream_data = Struct(
   "StreamData" / Bytes(this._._.length),
)

sys_message = Struct(
   "SysMessage" / Bytes(this._._.length),
)

input_info = Struct(
   Padding(4),
   Enum("LCF" / Short,
      OFF = 0,
      HZ_40 = 1,
      HZ_80 = 2,
      HZ_120 = 3,
      HZ_220 = 4,
      ),
   Enum("LV Control" / Short,
      OFF = 0,
      LIMITER = 1,
      PEAK = 2,
      AUTO = 3,
      ),
)
# =====================================================================
sys_info = Struct(
   "Name" / PaddedString(8, "utf8"),
   Padding(8),
   "Version" / Short,
   "Build" / Short,
   "Wifi1" / Short,
   "Wifi2" / Short,
)

# =====================================================================
check_packet = Struct(
   Const(b"DR"),
   "Flags" / BitStruct(
      Padding(1),
      "Long" / BitsInteger(1),
      Padding(6),
   ),
   Padding(9),
   "length" / Short,
)

short_packet = Struct(
   Const(b"DR"),
   "type" / Short,

   "Data" / Switch(this.type,
      {
         0x2020 : "Updates" / updates,
         0x3020 : "Registers" / registers,
      },
      default = Pass,
   ),
)

long_packet = Struct(
   Const(b"DR"),
   "type1" / Peek(Short),
   "Flags" / BitStruct(
      Padding(1),
      "Long" / BitsInteger(1),
      Padding(6),
   ),
   "type" / Short,

   Padding(7),
   "length" / Short,

   "System" / Switch(this.type,
      {
         0x2000 : "SysInfo" / Struct(
                  "SysInfo" / sys_info,
         ),
         0x2020 : "StreamData" / Struct(
                  "StreamData" / stream_data,
         ),
         0x2031 : "InputInfo" / Struct(
                  "InputInfo" / input_info,
         ),
         0x2032 : "FileName" / Struct(
                  "FileName" / IfThenElse(this._.type == 0xf0,
            file_data,
            file_name,
         )),
         0x2033 : "SysMessage" / Struct(
                  "SysMessage" / sys_message,
         ),
         0x2010 : "FileEntry" / Struct(
                  "FileEntry" / file_entry,
         ),
      },
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
   parser.add_argument("-k", "--key", dest="keycode", help="send a specific key-code")
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
   buffer = b""
   loop = 0
   storage_file = None

   sleep(1)
   while True:
      try:
         data = s.recv(14)
         buffer += data
      except socket.timeout:
         pass

      if loop == 0:
         s.send(b"\x44\x52\x20\x42\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00")

      if options.reg:
         for reg in range(16):
            s.send(bytes("\x44\x52\x30\x42" + chr(int(options.reg)) + chr(reg) + \
               "\x00\x00\x00\x00\x00\x00\x00\x00", "utf-8")) # Read 
         options.reg = False

      if options.info:
         s.send(b"\x44\x52\xf0\x41\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Request SysInfo

         s.send(b"\x44\x52\x30\x42\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read File Type
         s.send(b"\x44\x52\x30\x42\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00") # Read Sample Rate
         s.send(b"\x44\x52\x30\x42\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Read PreRecord
         s.send(b"\x44\x52\x30\x42\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00") # Read Channels
         s.send(b"\x44\x52\x30\x42\x01\x09\x00\x00\x00\x00\x00\x00\x00\x00") # Read Dual Mode

         s.send(b"\x44\x52\x30\x42\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Track Inc
         s.send(b"\x44\x52\x30\x42\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Level
         s.send(b"\x44\x52\x30\x42\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Mark
         s.send(b"\x44\x52\x30\x42\x02\x04\x00\x00\x00\x00\x00\x00\x00\x00") # Read Auto Mark Level

         s.send(b"\x44\x52\x30\x42\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read ???

         s.send(b"\x44\x52\x30\x42\x0a\x02\x00\x00\x00\x00\x00\x00\x00\x00") # Read low cut
         s.send(b"\x44\x52\x30\x42\x0a\x03\x00\x00\x00\x00\x00\x00\x00\x00") # Read level control

         s.send(b"\x44\x52\xf0\x41\x32\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Request Filename
         s.send(b"\x44\x52\x20\x42\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Counter
         s.send(b"\x44\x52\x20\x42\x20\x07\x00\x00\x00\x00\x00\x00\x00\x00") # Read Scene
         s.send(b"\x44\x52\x20\x42\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00") # Read Status
         options.info = False

      if (options.stream):
         s.send(b"\x44\x52\xf0\x41\x21\x01\x00\x00\x00\x00\x00\x00\x00\x00")
         stream_file = open("stream.dat", "wb")
         options.stream= False

      if (options.play):
         s.send(b"\x44\x52\x10\x41\x00\x09\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Play"
         options.play = False

      if (options.rec):
         s.send(b"\x44\x52\x10\x41\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Record"
         options.rec = False

      if (options.stop):
         s.send(b"\x44\x52\x10\x41\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00") # Press "Stop"
         options.stop= False

      if (options.keycode):
         '''
         Stop = 0x08, works - rec stops, play 2 needed = pause + stop
         Play = 0x09, works
         Pause = 0x0a, 10, not working
         Record = 0x0b = 11, works, 2nd pause
         FFSearch = 0x0c, 12, works - sticky
         RewSearch = 0x0d, 13, works - sticky
         FFSkip = 0x0e, 14, works
         RewSkip = 0x0f, 15, works
         Mark = 0x18, 24, works (in record)
         Repeat = 0x19, 25, not working (in play)
         F1 = 0x1c, 28, not works
         F2 = 0x1d, 29, not works
         F3 = 0x1e, 30, not works
         F4 = 0x1f, 31, not works

         54,86 = Init WiFi update
         '''
         s.send(bytes("\x44\x52\x10\x41\x00"+chr(int(options.keycode))+ \
             "\x00\x00\x00\x00\x00\x00\x00\x00")) # Send Keycode
         options.keycode = False

      if options.listing:
         s.send(b"\x44\x52\x40\x41\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00")
         options.listing = False

      if options.level:
         s.send(bytes("\x44\x52\x30\x41\x0b\x00" + \
            chr(int(options.level))+chr(int(options.level)) + \
            "\x00\x00\x00\x00\x00\x00"))
         options.level = False

      if options.clock:
         now = datetime.datetime.now()
         print("Setting the clock to:", now)
         # For some reason you have to send this twice
         s.send(bytes("\x44\x52\x30\x41\x07\x00" + \
            chr(int(now.year) >> 8) + chr(int(now.year) & 0xFF) + \
            chr(int(now.month)) +  chr(int(now.day)) + \
            chr(int(now.hour)) + chr(int(now.minute)) + \
            chr(int(now.second)) + "\x00"))
         s.send(bytes("\x44\x52\x30\x41\x07\x00" + \
            chr(int(now.year) >> 8) + chr(int(now.year) & 0xFF) + \
            chr(int(now.month)) +  chr(int(now.day)) + \
            chr(int(now.hour)) + chr(int(now.minute)) + \
            chr(int(now.second)) + "\x00"))
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
                     print("Buf:", binascii.hexlify(buffer[:32]), "...", log.length)
                  log = long_packet.parse(buffer)
                  buffer = buffer[log.length + 14:]
               else:
                  log = None
            else:
               if options.debug:
                  print("Buf:", binascii.hexlify(buffer[:14]))
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
         #print(log)
         if log.get('Data'):
            if log.Data.get('Update'):
               print(log.Data.Update)
            if log.Data.get('Register'):
               print(log.Data.Register)
            if log.Data.get('VU-Meters') and options.vu:
               print(log.Data.VUMeters)
         if log.get('System'):
            if log.System.get('Files'):
               for x in range(len(log.System.Files)):
                  if options.download:
                     if int(options.download) == log.System.Files[x].Index:
                        storage_file = open(log.System.Files[x].Filename, "wb")
                        s.send(bytes("\x44\x52\x40\x41\x30\x00\x00"+chr(int(options.download))
                            +"\x00\x00\x00\x00\x00\x00"))
                        print("*",)
                  print(log.System.Files[x].Index, "=", log.System.Files[x].Filename)
            elif log.System.get('FileData') and storage_file:
               storage_file.write(log.System.FileData)
            elif log.System.get('StreamData') and stream_file:
               stream_file.write(log.System.StreamData)
            elif log.System.get('FileEntry'):
               print(log.System.FileEntry.Index, ":", log.System.FileEntry.FileEntry)
            else:
               print(log.System)

if __name__ == '__main__':
   Run()
