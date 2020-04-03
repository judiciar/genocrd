#!/usr/bin/env python3

# FOLOSIRE
# rotate.py input_file.tif output_file.tif [threshold/cleantext]
# Modul curatarii default este threshold (mai rapid)

import numpy
import cv2
import argparse


def modulstatistic(a, axis=0):
    """Calculeaza modulul statistic (cea mai frecventa valoare dintr-o serie)"""
    scores = numpy.unique(numpy.ravel(a))
    testshape = list(a.shape)
    testshape[axis] = 1
    oldmostfreq = numpy.zeros(testshape)
    oldcounts = numpy.zeros(testshape)

    for score in scores:
        template = a == score
        counts = numpy.expand_dims(numpy.sum(template, axis), axis)
        mostfrequent = numpy.where(counts > oldcounts, score, oldmostfreq)
        oldcounts = numpy.maximum(counts, oldcounts)
        oldmostfreq = mostfrequent

    return int(mostfrequent[0])


# 1.Afla numele fisierului imagine din linia de comanda si incarca fisierul
ap = argparse.ArgumentParser()
ap.add_argument("imagein", help="calea catre fisierul imagine de intrare")
ap.add_argument("imageout", help="calea catre fisierul imagine de iesire")
ap.add_argument(
    "modcuratare",
    help="modul curatarii imaginii pentru OCR (threshold/cleantext)",
    nargs="?",
    default="threshold",
)
args = vars(ap.parse_args())
im = cv2.imread(args["imagein"], cv2.IMREAD_GRAYSCALE)

# 2.Curata imaginea (adaptive threshold, dilate and erode, binary threshold,
# Gaussian blur, contrast level adjusting)
if args["modcuratare"] == "cleantext":
    inverted = cv2.bitwise_not(im)
    filtered = cv2.adaptiveThreshold(
        inverted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, -5
    )
    blur = cv2.GaussianBlur(filtered, (1, 1), 0)
    adjcontrast = cv2.addWeighted(blur, 0.5, blur, 0, 0)
    combine = cv2.bitwise_not(inverted * adjcontrast)
    blur = cv2.GaussianBlur(combine, (0, 0), 0.8)
    im = cv2.normalize(blur, 0, 255, norm_type=cv2.NORM_MINMAX)

else:
    filtered = cv2.adaptiveThreshold(
        im, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 20
    )
    kernel = numpy.ones((1, 1), numpy.uint8)
    # opening = cv2.morphologyEx(filtered, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(filtered, cv2.MORPH_CLOSE, kernel)
    # _, th1 = cv2.threshold(im, 200, 255, cv2.THRESH_BINARY)
    # _, th2 = cv2.threshold(th1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur = cv2.GaussianBlur(im, (1, 1), 0)
    # _, th3 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    im = cv2.bitwise_or(blur, closing)

# 3.Inverseaza albul cu negrul
inverted = cv2.bitwise_not(im)

# 4.Aplica algoritmul Hough probabilistic pentru a identifica liniile din imagine
lines = cv2.HoughLinesP(
    inverted, 1, numpy.pi / 180, 100, minLineLength=100, maxLineGap=20
)

# 4bis.Deseneaza liniile pe imagine - util in development si debug
"""
print ("Numarul de linii (si de unghiuri) detectate: %d" % len(lines))
cdst = cv2.cvtColor(inverted, cv2.COLOR_GRAY2BGR)
if lines is not None:
    for i in range(0, len(lines)):
        x1, y1, x2, y2 = lines[i][0]
        cv2.line(cdst, (x1, y1), (x2, y2), (0,0,255), 2, cv2.LINE_AA)
cv2.imwrite("hough"+args["imagein"], cdst)
#cv2.imshow(args["imagein"]+" Linii detectate (cu rosu) - Hough Probabilistic", cdst)
#cv2.waitKey(0)
"""

# 5.Calculeaza unghiul de inclinare - in radiani - a fiecarei linii fata de axa x
angles = []
for line in lines:
    x1, y1, x2, y2 = line[0]
    angles.append(numpy.arctan2(y2 - y1, x2 - x1))

# 6.Calculeaza unghiul mediu de inclinare a paginii - in grade si radiani -
# eliminand valorile extreme prin folosirea algoritmului k-means clustering.
elements = numpy.array(angles, dtype=numpy.float32)
#     6.1.Defineste criteriile ( type, max_iter = 10 , epsilon = 1.0 )
criterii = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
#     6.2.Aplica k-means clustering
_, labels, centers = cv2.kmeans(
    elements, 3, None, criterii, 10, cv2.KMEANS_RANDOM_CENTERS
)
#     6.3.Determina cluster-ul cel mai numeros (cel mai frecvent element
#     din label / modulul statistic) si afla unghiul
mostfreqlabel = modulstatistic(labels)
avg_radian = centers[mostfreqlabel]
avg_angle = avg_radian * 180 / numpy.pi

# 7.Sterge din imagine liniile verticale, care incurca OCR.
#     7.1.Determina cluster-ul cu unghiul mediu cel mai departat
#     fata de unghiul mediu al cluster-ului cel mai numeros.
maxdiff = 0
labelmaxdiff = -1
for i in range(0, 2):
    if abs(abs(centers[i]) - abs(centers[mostfreqlabel])) > maxdiff:
        maxdiff = abs(abs(centers[i]) - abs(centers[mostfreqlabel]))
        labelmaxdiff = i
#     7.2.Deseneaza linii albe in locul liniilor corespunzatoare 
#     cluster-ului cu unghiul mediu cel mai departat
for i in range(0, len(lines)):
    if labels[i] == labelmaxdiff:
        x1, y1, x2, y2 = lines[i][0]
        cv2.line(im, (x1, y1), (x2, y2), (255, 255, 255), 2, cv2.LINE_8)

# 7bis.Afiseaza graficul distributiei unghiurilor - util in development si debug
"""
import matplotlib.pyplot as plt
print ("Numarul de linii (si de unghiuri) detectate: %d" % len(lines))
plt.title('Histograma unghiurilor')
plt.xlabel('Unghiuri (in grade)')
plt.ylabel('Numar de unghiuri')
plt.hist((elements[numpy.ravel(labels)==0] * 180 / numpy.pi), 180, [-90,90], log = True, color = 'blue')
plt.hist((elements[numpy.ravel(labels)==1] * 180 / numpy.pi), 180, [-90,90], log = True, color = 'red')
plt.hist((elements[numpy.ravel(labels)==2] * 180 / numpy.pi), 180, [-90,90], log = True, color = 'green')
plt.hist((centers * 180 / numpy.pi), 90, [-90,90], log = True, color = 'yellow')
plt.savefig("hist"+args["imagein"])
#plt.show()
"""

# 8.Roteste imaginea initiala curatata cu unghiul mediu de inclinare.
# Se evita taierea imaginii rotite la margini prin marirea dimensiunii cadrului
# imaginii finale, adaugarea unei borduri si completarea cu alb.
# Daca unghiul este prea aproape de 0 sau +/-90 grade, imaginea
# va fi doar completata cu o bordura alba.
if 3.0 <= abs(avg_angle) <= 87.0:
    print(
        "Unghiul mediu de inclinare este %f grade si va fi folosit la rotirea paginii"
        % avg_angle
    )

    h, w = im.shape[:2]
    img_center = (w / 2, h / 2)

    rot = cv2.getRotationMatrix2D(img_center, avg_angle, 1)

    sin = numpy.sin(avg_radian)
    cos = numpy.cos(avg_radian)
    b_w = int((h * abs(sin)) + (w * abs(cos))) + 40
    b_h = int((h * abs(cos)) + (w * abs(sin))) + 40

    rot[0, 2] += (b_w / 2) - img_center[0]
    rot[1, 2] += (b_h / 2) - img_center[1]

    im_finala = cv2.warpAffine(
        im,
        rot,
        (b_w, b_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
else:
    print(
        "Unghiul mediu de inclinare %f grade este prea aproape de 0/+-90 grade. Pagina va fi curatata, nu rotita"
        % avg_angle
    )
    im_finala = cv2.copyMakeBorder(
        im, 20, 20, 20, 20, borderType=cv2.BORDER_CONSTANT, value=(255, 255, 255)
    )

# 9.Salveaza imaginea curatata si rotita.
# Daca fisierul este TIFF, imaginea finala va fi TIFF comprimat LZW.
cv2.imwrite(args["imageout"], im_finala)
# cv2.imshow(args["imageout"]+" Rotita", im_finala)
# cv2.waitKey(0)
