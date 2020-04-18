#!/usr/bin/env python3

from sys import stderr, exit
from datetime import datetime
import romdata

class NumberGenerator():
    def __init__(self, seed):
        # Algorithm is accurate for seeds up to 16 bits in size
        seed = 0x9A4EC86 - seed
        self.state = [None] * 56
        self.state[0] = 0
        self.state[55] = seed

        self.i1 = 0
        self.i2 = 31

        value = 1
        for x in range(1, 55):
            self.state[(x * 21) % 55] = value
            temp = seed - value
            seed = value
            value = ((temp >> 31) & 0x7FFFFFFF) + temp

        for x in range(4):
            for x in range(56):
                index = (((x + 30) & 0xFF) % 55) + 1
                temp = self.state[x] - self.state[index]
                self.state[x] = ((temp >> 31) & 0x7FFFFFFF) + temp

    def get(self):
        self.i1 += 1
        self.i2 += 1
        if self.i1 > 55:
            self.i1 = 1
        if self.i2 > 55:
            self.i2 = 1
        result = self.state[self.i1] - self.state[self.i2]
        if result < 0:
            result += 0x7FFFFFFF
        self.state[self.i1] = result
        return result

class BitstreamReader():
    def __init__(self, bytes, bytesize=8):
        self.bytes = bytes
        self.bytesize = bytesize
        self.pos = 0
        self.bits = 0
        self.value = 0

    def remaining(self):
        if self.pos < len(self.bytes):
            return True
        if self.bits > 0:
            return True
        return False

    def read(self, count):
        while self.bits < count:
            if self.pos >= len(self.bytes):
                break
            self.value |= (self.bytes[self.pos] & ((1 << self.bytesize) - 1)) << self.bits
            self.bits += self.bytesize
            self.pos += 1

        ret = self.value & ((1 << count) - 1)
        self.value >>= count
        self.bits -= count
        return ret

class BitstreamWriter():
    def __init__(self, bytesize=8):
        self.bytes = []
        self.bytesize = bytesize
        self.bits = 0
        self.value = 0

    def finish(self):
        if self.bits > 0:
            self.bytes.append(self.value & ((1 << self.bytesize) - 1))
        return self.bytes

    def write(self, value, bits):
        self.value |= (value & ((1 << bits) - 1)) << self.bits
        self.bits += bits
        while self.bits >= self.bytesize:
            self.bytes.append(self.value & ((1 << self.bytesize) - 1))
            self.value >>= self.bytesize
            self.bits -= self.bytesize

def apply_shuffle(code, reverse=False):
    # Shuffle the array around
    shuffle = [3, 27, 13, 21, 12, 9, 7, 4, 6, 17, 19, 16, 28, 29, 23, 20, 11, 0, 1, 22, 24, 14, 8, 2, 15, 25, 10, 5, 18, 26]
    newcode = [None] * len(shuffle)
    for i, x in enumerate(shuffle):
        if not reverse:
            newcode[i] = code[x]
        else:
            newcode[x] = code[i]
    return newcode

def apply_bitpack(code, origbits, destbits):
    # Bitpack the code
    newcode = []
    reader = BitstreamReader(code, origbits)
    while reader.remaining():
        newcode.append(reader.read(destbits))
    return newcode

def apply_crypto(code, encrypt=False):
    # Apply the "crypto"
    newcode = [code[0], code[1]]
    gen = NumberGenerator(code[0] | code[1] << 8)
    for x in code[2:]:
        val = gen.get()
        if encrypt:
            val = -val
        newcode.append((x - val) & 0xFF)

    # Ignore the part that's 0 as a result of bitpacking
    remain = 8 - (len(code) * 8 % 6)
    newcode[len(newcode) - 1] &= (1 << remain) - 1
    return newcode

def checksum(code):
    # Calculate checksum
    calc = code[0]
    for x in range(1, (len(code) - 1) // 2 * 2, 2):
        calc += code[x] | (code[x + 1] << 8)
    if len(code) % 2 == 0:
        calc += code[len(code) - 1]

    calc = ((calc >> 16) & 0xFFFF) + (calc & 0xFFFF)
    calc += calc >> 16
    calc = ((calc >> 8) & 0xFF) + (calc & 0xFF)
    calc += calc >> 8
    calc &= 0xFF
    calc ^= 0xFF
    return calc

def crc32(bytes):
    sum = 0xFFFFFFFF
    for x in bytes:
        sum = romdata.crc32table[(sum & 0xFF) ^ x] ^ (sum >> 8)
    return sum ^ 0xFFFFFFFF

def decode(code):
    origcode = code
    code = apply_shuffle(code)
    code = apply_bitpack(code, 6, 8)
    code = apply_crypto(code)

    info = {}
    info["incl_checksum"] = code[0]
    info["calc_checksum"] = checksum(code[1:])

    reader = BitstreamReader(code[1:])
    info["timestamp"] = reader.read(32)
    info["type"] = reader.read(1)
    info["unk1"] = reader.read(1)
    team = []
    for x in range(12):
        team.append(reader.read(9))
    info["team"] = team
    if info["type"] == 0:
        info["dungeon"] = reader.read(7)
        info["floor"] = reader.read(7)
        info["pokemon"] = reader.read(11)
        info["gender"] = reader.read(2)
        info["reward"] = reader.read(2)
        info["unk2"] = reader.read(1)

        charcode = ""
        for x in origcode:
            charcode += romdata.charmap[x]
        info["revive"] = crc32(charcode.encode("utf8")) & 0x3FFFFFFF
    else:
        info["revive"] = reader.read(30)

    return info

def encode(info, keep_checksum=False):
    writer = BitstreamWriter()
    writer.write(info["timestamp"], 32)
    writer.write(info["type"], 1)
    writer.write(info["unk1"], 1)
    for x in range(12):
        if x < len(info["team"]):
            writer.write(info["team"][x], 9)
        else:
            writer.write(0, 9)
    if info["type"] == 0:
        writer.write(info["dungeon"], 7)
        writer.write(info["floor"], 7)
        writer.write(info["pokemon"], 11)
        writer.write(info["gender"], 2)
        writer.write(info["reward"], 2)
        writer.write(info["unk2"], 1)
    else:
        writer.write(info["revive"], 30)

    code = writer.finish()
    if keep_checksum:
        code = [info["incl_checksum"]] + code
    else:
        code = [checksum(code)] + code
    code = apply_crypto(code, encrypt=True)
    code = apply_bitpack(code, 8, 6)
    code = apply_shuffle(code, reverse=True)

    return code

def print_info(info):
    info_text = ""

    info_text += "Checksum: 0x%02X (calculated: 0x%02X)\n" % (info["incl_checksum"], info["calc_checksum"])
    info_text += "Timestamp: %s\n" % datetime.utcfromtimestamp(info["timestamp"])
    info_text += "Revive: %s\n" % (info["type"] == 1)
    info_text += "Unk1: 0x%X\n" % info["unk1"]

    info_text += "Team Name: "
    for char in info["team"]:
        if char == 0:
            break
        if char < 402:
            info_text += romdata.charmap_text[char]
        else:
            info_text += "★"
    info_text += "\n"

    if info["type"] == 0:
        dungeon = romdata.get_index("dungeons", info["dungeon"])
        info_text += "Dungeon (%d): %s" % (info["dungeon"], dungeon["name"])
        if not dungeon["valid"]:
            info_text += " (!)"
        info_text += "\n"

        floor = "%dF" % info["floor"]
        if not dungeon["ascending"]:
            floor = "B" + floor
        info_text += "Floor: %s" % floor
        if info["floor"] == 0 or info["floor"] > dungeon["floors"]:
            info_text += " (!)"
        info_text += "\n"

        pokemon = romdata.get_index("pokemon", info["pokemon"])
        info_text += "Pokemon (%d): %s" % (info["pokemon"], pokemon["name"])
        if not pokemon["valid"]:
            info_text += " (!)"
        info_text += "\n"

        gender = romdata.get_index("genders", info["gender"])
        info_text += "Gender: %s" % gender["name"]
        if not gender["valid"]:
            info_text += " (!)"
        info_text += "\n"

        reward = romdata.get_index("rewards", info["reward"])
        info_text += "Reward: %s" % reward["name"]
        if not reward["valid"]:
            info_text += " (!)"
        info_text += "\n"

        info_text += "Unk2: 0x%X\n" % info["unk2"]

    info_text += "Revive value: 0x%08X\n" % info["revive"]
    return info_text

if __name__ == "__main__":
    charmap_symbols = [
        "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "PF", "MF", "DF", "XF",
        "1H", "2H", "3H", "4H", "5H", "6H", "7H", "8H", "9H", "PH", "MH", "DH", "XH",
        "1W", "2W", "3W", "4W", "5W", "6W", "7W", "8W", "9W", "PW", "MW", "DW", "XW",
        "1E", "2E", "3E", "4E", "5E", "6E", "7E", "8E", "9E", "PE", "ME", "DE", "XE",
        "1S", "2S", "3S", "4S", "5S", "6S", "7S", "8S", "9S", "PS", "MS", "DS", #"XS",
    ]

    import json

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--decode", action="store_true")
    parser.add_argument("-e", "--encode", action="store_true")
    parser.add_argument("-i", "--info", action="store_true")
    parser.add_argument("-k", "--keep-checksum", action="store_true")
    parser.add_argument("password")
    args = parser.parse_args()

    info = None

    if args.decode:
        code = "".join(args.password.split()).upper()
        if len(code) != 30 * 2:
            print("Invalid code length", file=stderr)
            exit(1)

        # Convert the characters to codepoints
        newcode = []
        for x in range(len(code) // 2):
            char = code[x * 2:x * 2 + 2]
            newcode.append(charmap_symbols.index(char))
        code = newcode

        info = decode(code)
        print(json.dumps(info))

    if args.encode:
        if not info:
            info = json.loads(args.password)

        code = encode(info, keep_checksum=args.keep_checksum)
        i = 0
        for x in code:
            print(charmap_symbols[x], end="")
            i += 1
            if i % 15 == 0:
                print()
            elif i % 5 == 0:
                print(" ", end="")
        info = decode(code)

    if args.info and info:
        print(print_info(info))
