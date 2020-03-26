#!/usr/bin/env python3

from sys import argv
from struct import unpack, unpack_from, pack
from os import makedirs
from os.path import isdir
from json import dumps, loads


def unpack_wchar_str_from(bytes, pos):
    string = b""

    while bytes[pos] != 0 or bytes[pos + 1] != 0:
        string += unpack_from("2s", bytes, pos)[0]
        pos += 2

    return string


def bin_to_hex_string(bytes):
    string = ""

    for x in bytes:
        if x < 0x10:
            string += "0"
        string += hex(x)[2:]

    return string


def hex_string_to_bin(string):
    bytes = b""

    for x in range(0, len(string), 2):
        bytes += pack("B", int(string[x:x + 2], 16))

    return bytes


def decode_offsetlist(offsetlist):
    offsets = []
    append = 0
    for bit in offsetlist:
        if bit == 0:
            break
        if bit & 0x80:
            append <<= 7
            append |= bit & 0x7F
            continue
        bit &= 0x7F
        if append:
            bit |= append << 7
            append = 0
        if len(offsets) > 0:
            bit += offsets[-1]
        offsets.append(bit)
    return offsets


def encode_offsetlist(offsets):
    offsetlist = b""
    last_offset = 0
    for offset in offsets:
        offset -= last_offset
        last_offset += offset

        active = False
        for x in reversed(range(4)):
            cur = offset >> (x * 7) & 0x7F
            if cur or active:
                if x > 0:
                    cur |= 0x80
                    active = True
                offsetlist += pack("B", cur)
    return offsetlist + b"\0"


def extract_farc(farc):
    """
    Extract FARC archives.
    """

    # According to some, this "unknown data" contains the file count.
    # But in my experience, this hasn't been the case.
    # If you need to add new files to a farc archive,
    #   please modify the pack_farc function to place the file count where you
    #   think it is.
    unknown_data = farc[0x04:0x24]
    files = []

    offset = 0x24
    while unpack_from("<Q", farc, offset)[0] != 0:
        file_offset, file_length = unpack_from("<II", farc, offset)
        files.append(farc[file_offset:file_offset + file_length])
        offset += 8

    return unknown_data, files


def pack_farc(unknown_data, files):
    header = b"FARC" + unknown_data
    header_size = len(header) + len(files) * 8
    header_padding = b""
    if header_size % 128:
        padding = 128 - header_size % 128
        header_padding = b"\0" * padding
        header_size += padding

    file_data = b""
    offset_data = b""
    for file in files:
        if len(file_data) % 128:
            file_data += b"\0" * (128 - len(file_data) % 128)
        file_data += file
        offset_data += pack("<II", len(file_data) - len(file) + header_size,
                            len(file))

    return header + offset_data + header_padding + file_data


def extract_sirpack(info, sirpack):
    """
    There's times where there's a SIR file that gives info about the offsets
      and sizes of files inside another file.
    This function extracts such files.
    """

    subheader_ptr, offsetlist_ptr = unpack_from("<QQ", info, 8)
    filelist_ptr, file_count, unk1 = unpack_from("<QII", info, subheader_ptr)

    files = []
    for x in range(file_count):
        unknown, offset, size = unpack_from("<QII", info,
                                            filelist_ptr + 0x10 * x)
        files.append((unknown, sirpack[offset:offset + size]))

    return files


def pack_sirpack(files):
    file_list = b""
    sirpack = b""
    for file in files:
        sirpack += file[1]
        file_list += pack("<III", file[0], len(sirpack) - len(file[1]),
                          len(file[1]))

    subheader = pack("<III", 16, len(files), 1)

    offsetlist_offset = 16 + len(file_list) + len(subheader)
    if offsetlist_offset % 16:
        padding = 16 - offsetlist_offset % 16
        subheader += b"\0" * padding
        offsetlist_offset += padding

    header = pack("<4sIIxxxx", b"SIR0", 16 + len(file_list), offsetlist_offset)

    offsetlist = encode_offsetlist([4, 8, len(header) + len(file_list)])

    file_size = offsetlist_offset + len(offsetlist)
    if file_size % 16:
        offsetlist += b"\0" * (16 - file_size % 16)

    return header + file_list + subheader + offsetlist, sirpack


def extract_sir(sir):
    """
    The name of this function is misleading, since it doesn't extract "sir"
      files, it extracts the strings inside sir files that contain strings.
    """

    subheader_ptr, offsetlist_ptr = unpack_from("<QQ", sir, 8)
    string_count, unk3, string_info_ptr = unpack_from("<III", sir, subheader_ptr)

    offsets = []
    strings = []
    for x in range(string_count):
        offset, hash, unk1, unk2 = unpack_from("<QIhh", sir,
                                               string_info_ptr + x * 0x10)
        string = unpack_wchar_str_from(sir, offset)

        offsets.append(offset)
        strings.append({
            "string": string,
            "hash": hash,
            "unk1": unk1,
            "unk2": unk2
        })

    # The order of the strings differs in the string info list,
    #   and in the actual file.
    # We sort them by order of the string info,
    #   and add an "order" parameter to tell the order in the string table.
    # Why? Because it's easier to debug problems just comapring the binary
    #   files this way.
    offsets_sorted = sorted(offsets)
    for order in range(len(offsets_sorted)):
        strings[offsets.index(offsets_sorted[order])]["order"] = order

    return strings


def pack_sir(strings):
    offsets = []
    string_table = b""
    for string in sorted(strings, key=lambda k: k["order"]):
        offsets.append(len(string_table))
        string_table += string["string"] + b"\0\0"

    if len(string_table) % 4:
        string_table += b"\0" * (4 - len(string_table) % 4)

    string_info = b""
    for string in strings:
        string_info += pack("<IIhh", 16 + offsets[string["order"]],
                            string["hash"], string["unk1"], string["unk2"])

    subheader = pack("<II", len(strings), 16 + len(string_table))

    offsetlist_offset = (16 + len(string_table) + len(string_info) +
                         len(subheader))
    if offsetlist_offset % 16:
        padding = 16 - offsetlist_offset % 16
        subheader += b"\0" * padding
        offsetlist_offset += padding

    header = pack("<4sIIxxxx", b"SIR0",
                  16 + len(string_table) + len(string_info), offsetlist_offset)

    offsetlist = encode_offsetlist(
            [4, 8] +
            [len(header) + len(string_table) + 12 * x
                for x in range(len(strings))] +
            [len(header) + len(string_table) + len(string_info) + 4]
    )

    file_size = offsetlist_offset + len(offsetlist)
    if file_size % 16:
        offsetlist += b"\0" * (16 - file_size % 16)

    return header + string_table + string_info + subheader + offsetlist


def decode_ninty_utf(string):
    """
    Again a crappy function name.
    This is an attempt to decode strings that can't be decoded by normal means, usually because they contain weird characters.
    It'd be nice if all the different kinds of characters could be documented.
    My best guess is those characters are used for formatting.
    """

    decoded = ""
    for x in range(0, len(string), 2):
        chars = string[x:x + 2]

        # Chars under 0x20 are control characters. They're parsed in a weird way by some things, so I prefer saving them.
        if chars[0] < 0x20 and chars[1] == 0:
            chars = "{{ctrl:%i}}" % chars[0]

        if isinstance(chars, bytes):
            try:
                chars = chars.decode("utf_16_le")
            except:
                chars = "{{unk:%s}}" % bin_to_hex_string(chars)

        decoded += chars

    return decoded

def encode_ninty_utf(string):
    encoded = b""

    x = 0
    while x < len(string):
        if string[x:x + 2] == "{{":
            x += 2

            thing = ""
            while string[x:x + 2] != "}}":
                thing += string[x]
                x += 1
            x += 2

            thing = thing.split(":")
            if thing[0] == "unk":
                encoded += hex_string_to_bin(thing[1])
            elif thing[0] == "ctrl":
                encoded += chr(int(thing[1])).encode("utf_16_le")
            else:
                print("Huh? Unknown thingy?", thing[0])
        else:
            encoded += string[x].encode("utf_16_le")
            x += 1

    return encoded

if __name__ == "__main__":
    if argv[1] == "extract":
        source = open(argv[2], "rb").read()
        dest_dir = argv[3]

        if not isdir(dest_dir):
            makedirs(dest_dir)

        print("Extracting farc...")
        unknown_data, farc = extract_farc(source)
        print("Extracting sirpack...")
        sirpack = extract_sirpack(farc[0], farc[1])

        sirs = []
        for sir in sirpack:
            print("Extracting sir #%i..." % (sirpack.index(sir) + 1))
            filename = "%i.txt" % (sirpack.index(sir) + 1)
            sirs.append((sir[0], filename))

            file = open(dest_dir + "/" + filename, "w")
            strings = extract_sir(sir[1])
            for string in sorted(strings, key=lambda x: x["order"]):
                decoded_string = decode_ninty_utf(string["string"])
                file.write("%i %i %i %i %s\n" %
                           (string["hash"], string["unk1"],
                            string["unk2"], string["order"], decoded_string))
            file.close()

        open(dest_dir + "/info.json", "w").write(dumps((
            bin_to_hex_string(unknown_data), sirs)))

    elif argv[1] == "pack":
        source_dir = argv[2]
        dest = argv[3]

        unknown_data, sirs = loads(open(source_dir + "/info.json").read())

        packed_sirs = []
        for x in sirs:
            print("Packing sir #%i..." % (sirs.index(x) + 1))
            unknown, filename = x

            info = open(source_dir + "/" + filename).read().split(";;\n")
            while not info[-1]:
                del info[-1]

            strings = []
            for x in info:
                line = x.split(" ")

                strings.append({
                    "hash": int(line[0]),
                    "unk1": int(line[1]),
                    "unk2": int(line[2]),
                    "order": int(line[3]),
                    "string": encode_ninty_utf(" ".join(line[4:]))
                })

            packed_sirs.append((unknown, pack_sir(strings)))

        print("Packing sirpack...")
        sirpack = pack_sirpack(packed_sirs)

        print("Packing farc...")
        farc = pack_farc(hex_string_to_bin(unknown_data), sirpack)

        open(dest, "wb").write(farc)
