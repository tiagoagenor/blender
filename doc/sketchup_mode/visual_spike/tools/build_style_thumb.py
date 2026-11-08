"""Draw an original 'Estilo simples' thumbnail (sky, gray ground, white box + cylinder, black edges)."""
import sys
from PIL import Image, ImageDraw
S = 128
im = Image.new("RGB", (S, S)); d = ImageDraw.Draw(im)
hz = 52
for y in range(hz):
    t = y / hz
    d.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip((30, 166, 221), (191, 229, 245))))
d.rectangle([0, hz, S, S], fill=(191, 191, 198))
k = (0, 0, 0)
# box
front = [(22, 62), (62, 70), (62, 110), (22, 100)]; side = [(62, 70), (96, 60), (96, 98), (62, 110)]
top = [(22, 62), (56, 54), (96, 60), (62, 70)]
d.polygon(top, fill=(232, 232, 232), outline=k); d.polygon(front, fill=(248, 248, 248), outline=k)
d.polygon(side, fill=(196, 196, 196), outline=k)
# cylinder
d.rectangle([84, 40, 112, 84], fill=(236, 236, 236)); d.line([(84, 40), (84, 84)], fill=k); d.line([(112, 40), (112, 84)], fill=k)
d.ellipse([84, 35, 112, 45], fill=(244, 244, 244), outline=k); d.arc([84, 79, 112, 89], 0, 180, fill=k)
d.rectangle([0, 0, S - 1, S - 1], outline=(170, 170, 180))
im.save(sys.argv[1])
