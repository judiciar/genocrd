#!/bin/bash

# FOLOSIRE
# genocrfile.sh input_file.pdf
#
# Prelucreaza prin OCR fisierul input_file.pdf si salveaza
# rezultatul intr-un fisier cu denumirea input_file.txt 

if [ ! -f "$1" ]
  then
    echo "Nu am gasit fisierul $1"
    exit 2
  fi
filename="$1"
filename=${filename##*/}
filename=${filename%.*}
rezolutie=200
cleanmode=threshold
tessmode="/home/localadmin/genocr/tessmediu"

export OMP_THREAD_LIMIT=1
export IFS=$'
'

rm -f "$filename*.tif" "out_$filename"*.txt
convert -density $rezolutie "$1" -depth 8 -strip -background white -alpha off "$filename"_%05d.tif
find . -type f -name "$filename*.tif" | parallel -j-3 --nice 3 "python /home/localadmin/genocr/rotate.py {1} out_{1/} $cleanmode; tesseract out_{1/} out_{1/.} -l ron --oem 1 --psm 1 --dpi $rezolutie --tessdata-dir '$tessmode'" :::: -
cat $(find . -type f -name "out_$filename*.txt" | sort -V) > "$filename".txt
perl -i -p -e 's/([^.:])\n/$1 /; s/\n/\r\n/; s/\f//' "$filename".txt
rm -f "out_$filename"*.tif "$filename"*.tif "out_$filename"*.txt
 
# Script-ul proceseaza fisierul indicat in linia de comanda. Daca fisierul nu exista, se iese cu cod de eroare. In variabila $filename este extras din cale (path) numele de fisier fara extensie. Apoi, aplicatia convert extrage fiecare pagina din fisierul pdf si o transforma in tiff grayscale 8-bit, dandu-i o numerotare cu respectarea ordinii initiale a paginilor. Tiff este formatul intern al Tesseract si de aceea l-am preferat si noi. Variabila $rezolutie este folosita de aplicatia convert si este util - desi nu necesar - sa se potriveasca cu rezolutia in dpi la care a fost scanat fisierul pdf (de ex. 150, 200 sau 300 dpi). Daca rezolutia nu se potriveste, pot fi mici pierderi de calitate la conversie. Este bine de setat aceeasi valoare de la inceput in variabila si in aplicatia folosita de scanere.
# Script-ul cauta apoi fisierele tif rezultate din conversie si le preda aplicatiei GNU parallel. GNU parallel prelucreaza cate un fisier tif pe fiecare core al procesorului in paralel, obtinand astfel viteze foarte mari. Aplicatia lasa cateva core-uri libere pentru alte programe (-j-x). Pentru fiecare fisier, GNU parallel ruleaza script-ul rotate.py, care curata si indreapta imaginea si apoi livreaza rezultatul denumit out_$filename.tif aplicatiei OCR tesseract. Script-ul rotate.py nu face diferenta intre orientarea 0 grade si 180 grade, insa Tesseract poate in aproape toate cazurile. Tesseract produce un fisier text out_$filename.txt .
# Apoi, toate fisierele out_$filename.txt sunt sortate in ordinea paginilor initiale si concatenate (cat) in fisierul text final. Cu ajutorul unui script PERL, din fisierul text se elimina randurile goale si newline-urile de la capatul fiecarui rand din interiorul paragrafelor, se inlocuiesc newline-urile de Unix cu newline de Windows si se elimina caracterele sfarsit de pagina (form feed). Astfel, rezultatul este potrivit pentru copy-paste in Word sau in celelalte aplicatii folosite de utilizatori.
# Script-ul foloseste Shell script, care este optimizat pentru operatiuni cu fisierele si lansarea de aplicatii, precum si Python, care este potrivit pentru prelucrari matematice de imagine.

# perl -i -p -e 's/^\n//; s/([^.:])\n/$1 /; s/\n/\r\n/; s/\f//' "$filename".txt - Varianta cu newline-uri mult reduse
