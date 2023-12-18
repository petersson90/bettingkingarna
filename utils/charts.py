# utils/charts.py

colorPalette = ["#55efc4", "#81ecec", "#a29bfe", "#ffeaa7", "#fab1a0", "#ff7675", "#fd79a8"]
colorPrimary, colorSuccess, colorDanger = "#79aec8", colorPalette[0], colorPalette[5]


def generate_color_palette(item_count):
    ''' Generates a color palette with one color for each item in item_count '''
    palette = []

    i = 0
    while i < len(colorPalette) and len(palette) < item_count:
        palette.append(colorPalette[i])
        i += 1
        if i == len(colorPalette) and len(palette) < item_count:
            i = 0

    return palette
