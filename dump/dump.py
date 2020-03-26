#!/usr/bin/env python3

from struct import unpack_from

# Shit so we can get dungeon/pokemon names
import messagetool
farc = messagetool.extract_farc(open("rom/romfs/Data/StreamingAssets/native_data/message_us.bin", "rb").read())[1]
sir = messagetool.extract_sirpack(farc[0], farc[1])[0]
strings = {}
for string in messagetool.extract_sir(sir[1]):
    strings[string["hash"]] = messagetool.decode_ninty_utf(string["string"])

import il2cppdumper

dump = {}

mainbin = open("rom/exefs/main.uncompressed", "rb")
pokemon_data_info = open("rom/romfs/Data/StreamingAssets/native_data/pokemon/pokemon_data_info.bin", "rb").read()
dungeon_data_info = open("rom/romfs/Data/StreamingAssets/native_data/dungeon/dungeon_data_info.bin", "rb").read()
dungeon_request_level = open("rom/romfs/Data/StreamingAssets/native_data/dungeon/request_level.bin", "rb").read()

mainbin.seek(0x406ce70)
dump["charmap"] = mainbin.read(64 * 2).decode("utf-16le")
mainbin.seek(0x4077aee)
dump["charmap_text"] = mainbin.read(0x324).decode("utf-16le")

mainbin.seek(0x4076f50)
dump["crc32table"] = [int.from_bytes(mainbin.read(4), 'little') for x in range(256)]

dungeon_request_level_base = unpack_from("<Q", dungeon_request_level, 8)[0]
num_dungeons = unpack_from("<Q", dungeon_request_level, dungeon_request_level_base)[0]
dump["dungeons"] = []
for dungeon in range(num_dungeons):
    data = {}

    data["ascending"] = unpack_from("<B", dungeon_data_info,
            dungeon * 28 + 0)[0] & 1 == 1
    dungeon_name_id = unpack_from("<H", dungeon_data_info,
            dungeon * 28 + 8)[0]
    dungeon_rescue_count = unpack_from("<b", dungeon_data_info,
            dungeon * 28 + 19)[0]

    dungeon_request_level_ptr = unpack_from("<Q", dungeon_request_level,
            dungeon_request_level_base + 8 + dungeon * 16)[0]
    data["floors"] = unpack_from("<H", dungeon_request_level,
            dungeon_request_level_ptr + 2)[0]

    valid = True
    if dungeon == 0 or dungeon >= 100:
        valid = False
    if dungeon_rescue_count < 0:
        valid = False
    data["valid"] = valid

    mainbin.seek(0x4baaee0 + dungeon_name_id * 4)
    data["name"] = strings[int.from_bytes(mainbin.read(4), 'little')]
    data["const"] = il2cppdumper.Const_dungeon_Index(dungeon).name

    dump["dungeons"].append(data)

dump["pokemon"] = []
for pokemon in range(1007):
    data = {}

    pokemon_info = unpack_from("<H", pokemon_data_info, pokemon * 224 + 96)[0]

    valid = True
    if pokemon == 0 or pokemon > 1006:
        valid = False
    if pokemon_info & 0x8000 == 0:  # Not implemented in the game
        valid = False
    if ~pokemon_info & 0x9000 != 0:  # Is an alt forme
        # Deoxys is the only allowed alt forme
        if not (pokemon >= 493 and pokemon <= 495):
            valid = False
    data["valid"] = valid

    mainbin.seek(0x4ba6e28 + pokemon * 4)
    data["name"] = strings[int.from_bytes(mainbin.read(4), 'little')]
    data["const"] = il2cppdumper.Const_creature_Index(pokemon).name

    dump["pokemon"].append(data)

dump["genders"] = []
genders = ["Male", "Female", "Unknown"]
for gender in range(3):
    data = {}
    data["valid"] = True
    data["name"] = genders[gender]
    data["const"] = il2cppdumper.Const_pokemon_GenderType(gender).name
    dump["genders"].append(data)

dump["rewards"] = []
rewards = ["", "Regular", "Special", "Deluxe"]
for reward in range(4):
    data = {}
    data["valid"] = reward != 0
    data["name"] = rewards[reward]
    data["const"] = il2cppdumper.Const_ThunksPresentType(reward).name
    dump["rewards"].append(data)

import json
json.dump(dump, open("data.json", "w"), ensure_ascii=False, sort_keys=True, indent=4)
