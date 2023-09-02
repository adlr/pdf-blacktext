#!/usr/bin/env python

import argparse
import fitz

parser = argparse.ArgumentParser(description="A utility with two positional arguments.")
parser.add_argument("infile", help="Input file")
# Optional positional argument: outfile
parser.add_argument("outfile", help="Output file")
args = parser.parse_args()

doc = fitz.open(args.infile)

def log(b):
    print(b.decode('utf-8'))

def should_blacken(page, color, opacity):
    threshold = 0.3
    if color.endswith(b" gs"):
        key = color.split(b" ")[0].decode('utf-8')
        if page.parent.xref_get_key(page.xref, "Resources/ExtGState" + key + "/ca")[1] == '0':
            return False
    components = list(map(lambda x : float(x), color.split(b' ')[:-1]))

    def mean(arr):
        return sum(arr) / len(arr)

    return threshold > mean(components)

def change_text_color_to_black(xref, lines):
    didblacken = False  # only makes sense after a BT
    lastFillColor = b''
    lastOpacity = 1  # opaque by default
    fillColorSpaceOp = b''
    def handleLine(line):
        nonlocal didblacken
        nonlocal lastFillColor
        nonlocal lastOpacity
        nonlocal fillColorSpaceOp

        parts = line.split(b' ')
        if parts[-1] == b'cs':
            assert False  # need to handle this
        if parts[-1] == b'sc' or parts[-1] == b'scn':
            assert fillColorSpaceOp != b''
            parts[-1] = fillColorSpaceOp
            line = b' '.join(parts)
        if parts[-1] == b'g':
            fillColorSpaceOp = parts[-1]
            lastFillColor = line
        if parts[-1] == b'k':
            fillColorSpaceOp = parts[-1]
            lastFillColor = line
        if parts[-1] == b'rg':
            fillColorSpaceOp = parts[-1]
            lastFillColor = line
        if parts[-1] == b'gs':
            opacity = page.parent.xref_get_key(page.xref,
                                               "Resources/ExtGState" +
                                               parts[0].decode('utf-8') + "/cb")
            if opacity[1] != 'null':
                lastOpacity = float(opacity[1])
        if parts[-1] == b'BT':
            didblacken = should_blacken(page, lastFillColor, lastOpacity)
            if didblacken:
                return b'0 g BT'
        if parts[-1] == b'ET':
            if didblacken:
                return b'ET ' + lastFillColor
        return line

    for i in range(len(lines)):
        lines[i] = handleLine(lines[i])
    doc.update_stream(xref, b"\n".join(lines))

for page in doc:
    page.clean_contents()
    xref = page.get_contents()[0]
    lines = page.read_contents().splitlines()
    change_text_color_to_black(xref, lines)

    # Find xobject and change text color to black
    xobjects = page.get_xobjects()
    for xobj in xobjects:
        xref = xobj[0]
        lines = doc.xref_stream(xref).splitlines()
        change_text_color_to_black(xref, lines)

doc.ez_save(args.outfile, pretty=True)
doc.close()

