Pokémon Mystery Dungeon: Rescue Team DX password tool
=====================================================

This is a tool, with a rudimentary web interface to encode and decode rescue and revival passwords for the Rescue Team remake. It doesn't and won't ever generate Wonder Mail passwords, since those are hardcoded into the game.

Running instance: https://mid-kid.root.sx/pmdrtdx/

How to use
----------

### Local

`./password.py` can be run directly, with just Python 3. You can decode passwords like this:
```
./password.py -d -i '<password>'
```
The `<password>` parameter is a string of the symbols in the password encoded as two characters per symbol. The first character is the letter or number on top of the symbol, the second character represents the background symbol. For example "1F" stands for 1 fire.

F = fire  
H = heart  
W = water  
E = emerald  
S = star  

The tool will produce a json, which can be re-encoded using `./password.py -e '<json>'`.


### Flask

This tool has been wrapped into a web interface, written in Flask, given my ineptitude at writing javascript (javascript ports/pull requests are welcome).

The flask app can be ran like you would run any other flask app. Install flask through either your package manager or `pip`, then run:
```
FLASK_ENV=development flask run
```

Related works
-------------

Here's some works I've found that are either partially based on this or otherwise on the subject:
- [Documentation of the password structure](https://gist.github.com/zaksabeast/fed5730156e26fb3e805e234fcbea60b), better than I could (independent research)
- [A go-based generator with web interface](https://pmd-gen.herokuapp.com/) ([Source code](https://github.com/Karthik99999/pmd-gen))
- [A pyodide-based web interface integrating this code](https://tusharc.dev/rescue/) ([Source code](https://github.com/tuchandra/rescue)), with a series of [blog posts](https://tusharc.dev/tags/password-tool.html) detailing the process

Made something else cool? [Let me know](https://github.com/mid-kid/pmdrtdx_passwords/issues)!
