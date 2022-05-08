def srgb2lin(color):
    result = []
    for srgb in color:
        if srgb <= 0.0404482362771082:
            lin = srgb / 12.92
        else:
            lin = pow(((srgb + 0.055) / 1.055), 2.4)
        result.append(lin)
    return result

def lin2srgb(color):
    result = []
    for lin in color:
        if lin > 0.0031308:
            srgb = 1.055 * (pow(lin, (1.0 / 2.4))) - 0.055
        else:
            srgb = 12.92 * lin
        result.append(srgb)
    return result
