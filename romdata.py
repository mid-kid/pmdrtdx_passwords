import json

with open("data.json") as f:
    romdata = json.load(f)

charmap = romdata["charmap"]
charmap_text = romdata["charmap_text"]
crc32table = romdata["crc32table"]

def get_index(table, index):
    if index >= len(romdata[table]):
        if table == "dungeons":
            return {
                "ascending": False,
                "const": "",
                "floors": 0,
                "name": "",
                "valid": False
            }
        return {
            "const": "",
            "name": "",
            "valid": False
        }
    return romdata[table][index]
