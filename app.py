from flask import Flask, Markup, render_template, request
app = Flask(__name__)

from datetime import datetime
import password
import romdata

charmap_symbols = [
    "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "PF", "MF", "DF", "XF",
    "1H", "2H", "3H", "4H", "5H", "6H", "7H", "8H", "9H", "PH", "MH", "DH", "XH",
    "1W", "2W", "3W", "4W", "5W", "6W", "7W", "8W", "9W", "PW", "MW", "DW", "XW",
    "1E", "2E", "3E", "4E", "5E", "6E", "7E", "8E", "9E", "PE", "ME", "DE", "XE",
    "1S", "2S", "3S", "4S", "5S", "6S", "7S", "8S", "9S", "PS", "MS", "DS", #"XS",
]

charmap_html = [
    "<div class=\"pwdchar pwdchar_%s\">%s</div>" % (y, x)
    for y in ["F", "H", "W", "E", "S"]
    for x in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "P", "M", "D", "X"]
]

def password_translate(password):
    code = "".join(password.split()).upper()
    if len(code) != 30 * 2:
        return None

    # Convert the characters to codepoints
    newcode = []
    for x in range(len(code) // 2):
        char = code[x * 2:x * 2 + 2]
        try:
            index = charmap_symbols.index(char)
        except:
            return None
        newcode.append(index)
    return newcode

def password_html(code):
    html = ""
    for char in range(len(code)):
        html += Markup(charmap_html[code[char]])
    return html

@app.route("/")
def index():
    return render_template("index.html")

def get_info_text(info):
    info_text = ""
    info_text += "Checksum: 0x%02X (calculated: 0x%02X)\n" % (info["incl_checksum"], info["calc_checksum"])
    info_text += "Timestamp: %s\n" % datetime.fromtimestamp(info["timestamp"])
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
        info_text += "Dungeon (%d): %s\n" % (info["dungeon"], dungeon["name"])

        floor = "%dF" % info["floor"]
        if not dungeon["ascending"]:
            floor = "B" + floor
        info_text += "Floor: %s\n" % (floor)

        pokemon = romdata.get_index("pokemon", info["pokemon"])
        info_text += "Pokemon (%d): %s\n" % (info["pokemon"], pokemon["name"])

        gender = romdata.get_index("genders", info["gender"])
        info_text += "Gender: %s\n" % gender["name"]
        reward = romdata.get_index("rewards", info["reward"])
        info_text += "Reward: %s\n" % reward["name"]
        info_text += "Unk2: 0x%X\n" % info["unk2"]

    info_text += "Revive value: 0x%08X\n" % info["revive"]
    return info_text

def get_warnings(info):
    warnings = []
    if info["calc_checksum"] != info["incl_checksum"]:
        warnings.append("checksum")

    if info["type"] == 0:
        items = {
            "dungeons": "dungeon",
            "pokemon": "pokemon",
            "genders": "gender",
            "rewards": "reward"
        }
        for item, index in items.items():
            if not romdata.get_index(item, info[index])["valid"]:
                warnings.append(index)
        
        dungeon = romdata.get_index("dungeons", info["dungeon"])
        if info["floor"] == 0 or info["floor"] > dungeon["floors"]:
            warnings.append("floor")

    return warnings

@app.route("/decode", methods=["GET"])
def decode():
    info = None
    info_text = None
    password_input = None
    warnings = None
    decode_failed = False

    if "c" in request.args:
        password_input = request.args.get("c")
        code = password_translate(password_input)
        if code:
            info = password.decode(code)
            info_text = get_info_text(info)
            warnings = get_warnings(info)
        else:
            decode_failed = True

    output_password = None
    if info and not warnings:
        output_password = password_html(password.encode({
            "timestamp": info["timestamp"],
            "type": 1,
            "unk1": 0,
            "team": [romdata.charmap_text.index(x) for x in "Passwd tool"],
            "revive": info["revive"]
        }))

    return render_template("index.html",
            password=password_input,
            info=info,
            info_text=info_text,
            warnings=warnings,
            decode_failed=decode_failed,
            output_password=output_password)
