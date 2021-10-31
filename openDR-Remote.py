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
    "Register" / Switch(
        this.register,
        {
            0x0100:
            "Format" / Struct("Format" / Enum(
                Short,
                BWF_24=0,
                BWF_16=1,
                WAV_24=2,
                WAV_16=3,
                MP3_320=4,
                MP3_256=5,
                MP3_192=6,
                MP3_128=7,
                MP3_96=8,
                MP3_64=9,
                MP3_32=10,
            )),
            0x0101:
            "SampleRate" / Struct("SampleRate" / Enum(
                Short,
                KHZ_44_1=0,
                KHZ_48=1,
                KHZ_96=2,
            )),
            0x0102:
            "PreRecord" / Struct("PreRecord" / Enum(
                Short,
                OFF=0,
                ON=1,
            )),
            0x0103:
            "SelfTimer" / Struct("SelfTimer" / Enum(
                Short,
                OFF=0,
                SEC_5=1,
                SEC_10=2,
            )),
            0x0104:
            "DualRec" / Struct("DualRec" / Enum(
                Short,
                OFF=0,
                LEVEL=1,
                FORMAT=2,
            )),
            0x0105:
            "DualFormat44" / Struct("DualFormat44" / Enum(
                Short,
                OFF=0,
                MP3_320=1,
                MP3_256=2,
                MP3_192=3,
                MP3_128=4,
                MP3_96=5,
                MP3_64=6,
                MP3_32=7,
            )),
            0x0106:
            "MSDecode" / Struct("MSDecode" / Enum(
                Short,
                OFF=0,
                REC=1,
                PLAY=2,
            )),
            0x0107:
            "MSSource" / Struct("MSSource" / Enum(
                Short,
                ONE_TWO=0,
                THREE_FOUR=1,
            )),
            0x0108:
            "Channels" / Struct("Channels" / Enum(
                Short,
                MONO=0,
                STEREO=1,
            )),
            0x0109:
            "DualFormat22" / Struct("DualFormat22" / Enum(
                Short,
                OFF=0,
                MP3_320=1,
                MP3_256=2,
                MP3_192=3,
                MP3_128=4,
                MP3_96=5,
                MP3_64=6,
                MP3_32=7,
            )),
            0x0200:
            "TrackInc" / Struct("TrackInc" / Enum(
                Short,
                OFF=0,
                MIN_5=1,
                MIN_10=2,
                MIN_15=3,
                MIN_30=4,
                MIN_60=5,
            )),
            0x0201:
            "AutoLevel" / Struct("AutoLevel" / Enum(
                Short,
                OFF=0,
                DB_6=1,
                DB_12=2,
                DB_24=3,
                DB_48=4,
            )),
            0x0202:
            "PeakMark" / Struct("PeakMark" / Enum(
                Short,
                OFF=0,
                ON=1,
            )),
            0x0203:
            "AutoMark" / Struct("AutoMark" / Enum(
                Short,
                OFF=0,
                LEVEL=1,
                TIME=2,
            )),
            0x0204:
            "AutoMarkLevel" / Struct("AutoMarkLevel" / Enum(
                Short,
                DB_6=0,  # for LEVEL
                DB_12=1,
                DB_24=2,
                DB_48=3,
                MIN_5=4,  # for TIME
                MIN_10=5,
                MIN_15=6,
                MIN_30=7,
                MIN_60=8,
                OFF=9,
            )),
            0x0205:
            "AutoPunch" / Struct("AutoPunch" / Enum(
                Short,
                OFF=0,
                ON=1,
            )),
            #0x0303: Value 0x01 seen?
            0x0303:
            "Unknown303" / Struct("Unknown303" / Bytes(4),
            ),
            0x0304:
            "Unknown304" / Struct("Unknown304" / Bytes(4),
            ),
            0x0305:
            "Unknown305" / Struct("Unknown305" / Bytes(4),
            ),
            0x0600:
            "Reverb" / Struct("Reverb" / Enum(
                Short,
                OFF=0,
                ON=1,
            )),
            0x0601:
            "ReverbType" / Struct("ReverbType" / Enum(
                Short,
                HALL1=0,
                HALL2=1,
                ROOM=2,
                STUDIO=3,
                PLATE1=4,
                PLATE2=5,
            )),
            0x0602:
            "ReverbSource" / Struct("ReverbSource" / Enum(
                Short,
                MIX=0,
                INT_MIC=1,
                EXT_IN=2,
            )),
            0x0603:
            "ReverbLevel" / Struct("ReverbLevel" / Short),
            0x0A02:
            "LCF" / Struct(
                Padding(2), "LCF" / Enum(
                    Short,
                    OFF=0,
                    HZ_40=1,
                    HZ_80=2,
                    HZ_120=3,
                    HZ_220=4,
                )),
            0x0A03:
            "LVControl" / Struct(
                Padding(2), "LVControl" / Enum(
                    Short,
                    OFF=0,
                    LIMITER=1,
                    PEAK=2,
                    AUTO=3,
                )),
            0x0B00:
            "RecordLevel" / Struct(
                "INT_L" / Byte,
                "INT_R" / Byte,
                "EXT_1" / Byte,
                "EXT_2" / Byte,
                "unknown" / Array(4, Byte),
            ),
        },
    ))

# =====================================================================
# Keep seperate as VU-Meters are very 'talkative'

vumeters = Struct(
    Padding(1),
    "VUMeters" / Array(
        3,
        BitStruct(  # CH1&2, CH3&4, Stereo
            "Peek" / BitsInteger(1),
            "BarL" / BitsInteger(7),
            "12dB" / BitsInteger(1),
            "BarR" / BitsInteger(7),
        )),
    "DecimalVU" / Int8sb,
)

screeninfo = Struct(
    "type4" / Byte,
    "ScreenInfo" / Switch(
        this.type4,
        {
            0x02:
            "Reverb" / Struct("Reverb" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
                SEND=0x02,
            )),
            0x03:
            "AudioOut" / Struct("AudioOut" / Enum(
                Byte,
                SPEAKER=0x01,
                HEADPHONE=0x02,
            )),
            0x04:
            "Phantom" / Struct("Phantom" / Enum(
                Byte,
                OFF=0x00,
                ON_48=0x01,
                ON_24=0x02,
            )),
            0x05:
            "Battery" / Struct("Battery" / Enum(
                Byte,
                BAR0=0x00,
                BAR1=0x01,
                BAR2=0x02,
                BAR3=0x03,
                USB=0x04,
            )),
            0x07:
            "Scene" / Struct("Scene" / Enum(
                Byte,
                EASY=0x00,
                LOUD=0x01,
                MUSIC=0x02,
                INSTRUMENT=0x03,
                INTERVIEW=0x04,
                MANUAL=0x05,
                DUB=0x06,
                PRACTICE=0x07,
            )),
            0x09:
            "LCF" / Struct("LCF" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
            )),
            0x0A:
            "LMT" / Struct("LMT" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
            )),
            0x0B:
            "PEAK" / Struct("PEAK" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
                AUTO=0x02
            )),
            0x0E:
            "AUTOREC" / Struct("AUTOREC" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
            )),
            0x0F:
            "MIC_PWR" / Struct("MIC_PWR" / Enum(
                Byte,
                OFF=0x00,
                ON=0x01,
            )),
        },
        default=Pass,
    ),
)

updates = Struct(
    "type3" / Byte,
    "Update" / Switch(
        this.type3,
        {
            0x00:
            "Status" / Struct(
                "Status" / Enum(
                    Byte,
                    STOPPED=0x10,
                    PLAYING=0x11,
                    PLAYPAUSED=0x12,
                    FORWARD=0x13,
                    REWIND=0x14,
                    PAUSED=0x15,
                    STOPPING=0x16,
                    RECORD=0x81,
                    ARMED=0x82,
                    TIMER=0x83,
                ),
                Padding(8),
            ),
            0x11:
            "Counter" / Struct(
                Padding(1),
                "Counter" / Int,
                Padding(4),
            ),
            0x12:
            "VUMeters" / vumeters,
            0x20:
            "ScreenInfo" / screeninfo,
            # Buf: b'4452202021800000020200000000' - track active
            #                ^^??11223344
            0x21:
            "Arm" / Struct(
                Padding(1),
                "CH1" / Byte,
                "CH2" / Byte,
                "CH3" / Byte,
                "CH4" / Byte,
            ),
        },
        default=Pass,
    ),
)

# =====================================================================
file_entry = Struct(
    "Meta" / BitStruct(
        "Directory" / BitsInteger(1),
        "Index" / BitsInteger(15),
    ),
    Padding(8),
    "data" / Peek(RepeatUntil(lambda obj, lst, ctx: obj == 0x000d, Short)),
    "flength" / Computed(lambda ctx: (ctx.data.__len__() - 1) * 2),
    "Name" / PaddedString(this.flength, "utf-16-le"),
)

file_name = Struct("Filename" / PaddedString(this._._.length - 2, "utf-16-le"))

file_data = Struct("FileData" / Bytes(this._._.length))

stream_data = Struct("StreamData" / Bytes(this._._.length))

sys_message = Struct("SysMessage" / Bytes(this._._.length))

input_info = Struct(
    "Channels" / IfThenElse(
        this._._.length == 0x14,
        "Channels" / Computed(1),
        "Channels" / Computed(4),
    ),
    "InputInfo" / Array(this.Channels, "InputInfo" / Struct(
        Padding(1),
        "Link" / Enum(
            Byte,
            OFF=0,
            ON=1,
        ),
        "Delay" / Short,
        "LCF" / Enum(
            Short,
            OFF=0,
            HZ_40=1,
            HZ_80=2,
            HZ_120=3,
            HZ_220=4,
        ),
        "LVControl" / Enum(
            Short,
            OFF=0,
            LIMITER=1,
            PEAK=2,
            AUTO=3,
        ),
        Padding(2),
    )),
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
    "Short" / Switch(
        this.type,
        {
            0x2020: "Updates" / updates,
            0x2022: "Ready" / Struct("Ready" / Computed(1)),
            0x3020: "Registers" / registers,
        },
        default=Pass,
    ),
)

long_packet = Struct(
    Const(b"DR"),
    "Flags" / BitStruct(
        Padding(1),
        "Long" / BitsInteger(1),
        Padding(6),
    ),
    "type" / Short,
    Padding(7),
    "length" / Short,
    "Long" / Switch(
        this.type,
        {
            0x2000:
            "SysInfo" / Struct("SysInfo" / sys_info),
            0x2020:
            "StreamData" / Struct("StreamData" / stream_data),
            # Buf: b'4452202280000000000000000000' ?
            0x2031:
            "InputInfo" / Struct("InputInfo" / input_info),
            0x2032:
            "File" / Struct("File" / IfThenElse(
                this._.type == 0xf0,
                file_name,
                file_data,
            )),
            0x2033:
            "SysMessage" / Struct("SysMessage" / sys_message),
            0x2010:
            "FileEntry" / Struct("FileEntry" / file_entry),
            # Buf: b'445230200a000040000100000000' - Track1 link
            # Buf: b'445230200a010040000100000000' - Track1 delay
        },
    ),
)

# =====================================================================
# For setting configuration

# Note Ch3&4 on DR-44WL have differ scale/range
set_level = Struct(
    Const(b"\x44\x52\x30\x41\x0b\x00"),
    "Level1" / Byte,
    "Level2" / Byte,
    "Level3" / Byte,
    "Level4" / Byte,
    Const(b"\x00\x00\x00\x00"),
)

set_clock = Struct(
    Const(b"\x44\x52\x30\x41\x07\x00"),
    "Year" / Short,
    "Month" / Byte,
    "Day" / Byte,
    "Hour" / Byte,
    "Minute" / Byte,
    "Second" / Byte,
    Const(b"\x00"),
)

get_reg_bank = Struct(
    Const(b"\x44\x52\x30\x42"),
    "Bank" / Byte,
    "Reg" / Byte,
    Const(b"\x00\x00\x00\x00\x00\x00\x00\x00"),
)

req_download = Struct(
    Const(b"\x44\x52\x40\x41\x30\x00"),
    "Index" / Short,
    Const(b"\x00\x00\x00\x00\x00\x00"),
)

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
send_keycode = Struct(
    Const(b"\x44\x52\x10\x41\x00"),
    "Keycode" / Byte,
    Const(b"\x00\x00\x00\x00\x00\x00\x00\x00"),
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
    parser.add_argument(
        "-i",
        "--info",
        action="store_true",
        dest="info",
        help="request info from recorder")
    parser.add_argument(
        "-R", "--rec", action="store_true", dest="rec", help="start recording")
    parser.add_argument(
        "-p",
        "--play",
        action="store_true",
        dest="play",
        help="start playback")
    parser.add_argument(
        "-s",
        "--stop",
        action="store_true",
        dest="stop",
        help="stop playback/recording")
    parser.add_argument(
        "-k", "--key", dest="keycode", help="send a specific key-code")
    parser.add_argument(
        "-S",
        "--stream",
        action="store_true",
        dest="stream",
        help="use streaming audio")
    parser.add_argument(
        "-L",
        "--level",
        dest="level",
        help="set input level for recording [0-90]")
    parser.add_argument(
        "-v",
        "--vu",
        action="store_true",
        dest="vu",
        help="show vu meters (verbose)")
    parser.add_argument(
        "-m",
        "--mtr",
        action="store_true",
        dest="mtr",
        help="mtr mode (DR-44WL only)")

    parser.add_argument(
        "-c",
        "--clock",
        action="store_true",
        dest="clock",
        help="set clock to match PC's")
    parser.add_argument(
        "-r", "--reg", dest="reg", help="read register bank [0-9]")

    # File actions for device
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="listing",
        help="list stored files")
    parser.add_argument(
        "-d",
        "--download",
        dest="download",
        help="download file [index from listing]")

    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        dest="debug",
        help="dump received packets in hex")
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

        # Send keycodes immediately
        if (options.play):
            s.send(send_keycode.build({"Keycode": 0x09}))
            options.play = False
        elif (options.rec):
            s.send(send_keycode.build({"Keycode": 0x0b}))
            options.rec = False
        elif (options.stop):
            s.send(send_keycode.build({"Keycode": 0x08}))
            options.stop = False
        elif (options.keycode):
            s.send(send_keycode.build({"Keycode": int(options.keycode)}))
            options.keycode = False

        if options.level:
            if options.mtr:
                l = options.level.split(",")
                s.send(set_level.build({ \
                    "Level1": int(l[0]),
                    "Level2": int(l[1]),
                    "Level3": int(l[2]),
                    "Level4": int(l[3]),
                    }))
            else:
                s.send(set_level.build({ \
                    "Level1": int(options.level),
                    "Level2": int(options.level),
                    "Level3": 0,
                    "Level4": 0,
                    }))
            options.level = False

        if (options.stream):
            s.send(b"\x44\x52\xf0\x41\x21\x01\x00\x00\x00\x00\x00\x00\x00\x00")
            stream_file = open("stream.dat", "wb")
            options.stream = False

        if options.clock:
            now = datetime.datetime.now()
            print("Setting the clock to:", now)

            clock = set_clock.build({ \
                "Year":   now.year,
                "Month":  now.month,
                "Day":    now.day,
                "Hour":   now.hour,
                "Minute": now.minute,
                "Second": now.second,
                })

            # For some reason you have to send this twice
            s.send(clock)
            s.send(clock)
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
                            print("Buf:", binascii.hexlify(buffer[:32]), "...",
                                  log.length)
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
                print("Magic not found!")
                buffer = ""
                log = None
        else:
            log = None

        if log:
            if log.get('Short'):
                if log.Short.get('Ready'):
                    # Only send one new request at a time, and wait for 'ready'
                    if options.reg:
                        for reg in range(16):  # Read block of registers
                            s.send(get_reg_bank.build({ "Bank": int(options.reg), "Reg": reg}))
                        options.reg = False

                    elif options.info:
                        s.send(b"\x44\x52\xf0\x41\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Request SysInfo

                        s.send(b"\x44\x52\x30\x42\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read File Type
                        s.send(b"\x44\x52\x30\x42\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Sample Rate
                        s.send(b"\x44\x52\x30\x42\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read PreRecord
                        s.send(b"\x44\x52\x30\x42\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Channels
                        s.send(b"\x44\x52\x30\x42\x01\x09\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Dual Mode

                        s.send(b"\x44\x52\x30\x42\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Auto Track Inc
                        s.send(b"\x44\x52\x30\x42\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Auto Level
                        s.send(b"\x44\x52\x30\x42\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Auto Mark
                        s.send(b"\x44\x52\x30\x42\x02\x04\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Auto Mark Level

                        s.send(b"\x44\x52\x30\x42\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read ???

                        s.send(b"\x44\x52\x30\x42\x0a\x02\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read low cut
                        s.send(b"\x44\x52\x30\x42\x0a\x03\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read level control

                        s.send(b"\x44\x52\xf0\x41\x32\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Request Filename
                        s.send(b"\x44\x52\x20\x42\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Counter
                        s.send(b"\x44\x52\x20\x42\x20\x07\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Scene
                        s.send(b"\x44\x52\x20\x42\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                               )  # Read Status
                        options.info = False

                    elif options.listing:
                        s.send(b"\x44\x52\x40\x41\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                        options.listing = False

                    elif options.download and storage_file:
                        s.send(req_download.build({"Index": int(options.download)}))
                        print("Downloading Index:", int(options.download))
                        options.download = False


                elif log.Short.get('Update'):
                    if log.Short.Update.get('VUMeters'):
                        if options.vu:
                            bar = (" " * 32) + ("*" * 32) + (" " * 32)
                            if options.mtr:
                                pick = [2, 0, 1]
                            else:
                                pick = [0]

                            for p in pick:
                                l = log.Short.Update.VUMeters[p].BarL
                                r = log.Short.Update.VUMeters[p].BarR
                                if p == pick[0]:
                                    d = log.Short.Update.DecimalVU
                                else:
                                    d = "   "

                                print("%s : %4s : %s" % (bar[l:l + 32], d,
                                                         bar[64 - r:96 - r]))
                    else:
                        print("Update :", log.Short.Update)
                elif log.Short.get('Register'):
                    print("Register :", log.Short.Register)
                else:
                    print(log.Short)

            if log.get('Long'):
                if log.Long.get('File'):
                    if log.Long.File.get('FileData') and storage_file:
                        storage_file.write(log.Long.File.FileData)
                elif log.Long.get('StreamData') and stream_file:
                    stream_file.write(log.Long.StreamData)
                elif log.Long.get('FileEntry'):
                    print(log.Long.FileEntry.Meta.Index, ":",
                          log.Long.FileEntry.Name)

                    if options.download:
                        if int(options.download) == log.Long.FileEntry.Meta.Index:
                            storage_file = open(log.Long.FileEntry.Name, "wb")
                else:
                    print(log.Long)

        loop = loop + 1

if __name__ == '__main__':
    Run()
