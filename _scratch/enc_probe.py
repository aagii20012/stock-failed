s = "em—dash minus−here — literal: →"
lit = "em—dash minus−here — arrow →"
print("repr_lit:", [hex(ord(c)) for c in lit if ord(c) > 127])
print("equal:", lit.count(chr(0x2014)), lit.count(chr(0x2212)), lit.count(chr(0x2192)))
