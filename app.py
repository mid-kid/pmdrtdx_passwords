from flask import Flask, Markup, render_template, request, escape
app = Flask(__name__)

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

value_fields = {
    "timestamp": 0xFFFFFFFF,
    "type": 1,
    "unk1": 1,
    "dungeon": 0x7F,
    "floor": 0x7F,
    "pokemon": 0x7FF,
    "gender": 3,
    "reward": 3,
    "unk2": 1,
    "revive": 0x3FFFFFFF
}

named_fields = {
    "dungeon": "dungeons",
    "pokemon": "pokemon",
    "gender": "genders",
    "reward": "rewards"
}

def password_char2val(password):
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

def password_val2char(code):
    password = ""
    for index, val in enumerate(code):
        symbol = charmap_symbols[val]
        password += symbol[0].upper()
        password += symbol[1].lower()
        if index % 15 == 14:
            password += "\n"
        elif index % 5 == 4:
            password += " "
    return password

def password_html(code):
    html = ""
    for char in range(len(code)):
        html += Markup(charmap_html[code[char]])
    return html

def get_warnings(info):
    warnings = []

    if "calc_checksum" in info and "incl_checksum" in info:
        if info["calc_checksum"] != info["incl_checksum"]:
            warnings.append("checksum")

    if info["type"] == 0:
        for field, array in named_fields.items():
            if not romdata.get_index(array, info[field])["valid"]:
                warnings.append(field)
        
        dungeon = romdata.get_index("dungeons", info["dungeon"])
        if info["floor"] == 0 or info["floor"] > dungeon["floors"]:
            warnings.append("floor")

    return warnings

def validate_info(info):
    if "timestamp" not in info or "type" not in info or "team" not in info:
        return False

    # TODO: Verify team name

    if "unk1" not in info:
        info["unk1"] = 0

    if info["type"] == 0:
        fields = ["dungeon", "floor", "pokemon", "gender", "reward"]
        if "unk2" not in info:
            info["unk2"] = 0
    elif info["type"] == 1:
        fields = ["revive"]

    for field in fields:
        if field not in info:
            print(field)
            return False

    return True

@app.route("/")
def index():
    return render_template("index.html",
            romdata=romdata.romdata,
            named=named_fields,
            value=value_fields)

@app.route("/decode", methods=["GET"])
def decode():
    info = None
    info_text = None
    warnings = None
    password_input = None
    password_output = None

    decode_failed = False
    if "c" in request.args:
        password_input = request.args.get("c")
        code = password_char2val(password_input)
        password_input = escape(password_input)
        if code:
            info = password.decode(code)
            info_text = escape(password.print_info(info))
            warnings = get_warnings(info)
            password_input = escape(password_val2char(code))
            password_output = escape(password_html(code))
        else:
            decode_failed = True

    return render_template("index.html",
            romdata=romdata.romdata,
            named=named_fields,
            value=value_fields,
            password=password_input,
            info=info,
            info_text=info_text,
            warnings=warnings,
            decode_failed=decode_failed,
            password_output=password_output)

@app.route("/encode", methods=["GET"])
def encode():
    warnings = None
    info_text = None
    password_input = None
    password_output = None

    encode_failed = False

    info = {}
    for field in value_fields:
        if field not in request.args:
            continue

        try:
            value = int(request.args.get(field), 0)
        except:
            encode_failed = True
            continue

        if value < 0 or value > value_fields[field]:
            encode_failed = True
            continue
        info[field] = value
    if "team" in request.args:
        info["team"] = request.args.get("team")

    if not encode_failed:
        if validate_info(info):
            warnings = get_warnings(info)
            info["team"] = [romdata.charmap_text.index(x) for x in "Passwd tool"]  # TODO
            code = password.encode(info)
            info_text = escape(password.print_info(password.decode(code)))
            password_input = escape(password_val2char(code))
            password_output = escape(password_html(code))
        else:
            encode_failed=True

    return render_template("index.html",
            romdata=romdata.romdata,
            named=named_fields,
            value=value_fields,
            info=info,
            info_text=info_text,
            warnings=warnings,
            password=password_input,
            password_output=password_output,
            encode_failed=encode_failed)
