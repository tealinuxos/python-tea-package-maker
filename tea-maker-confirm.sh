#!/bin/bash

echo -e "\n~~ tea_maker ~~"
echo "pembuat file .tea"
echo "versi 1"

##################
# --konfigurasi--
##################
  #1
folder_penyimpanan="$HOME"
nama_keterangan="dan_dependensinya"
  # Setting untuk penyimpanan .tea yang dibuat.
  # misalnya jika kita meminta tea_maker untuk membuat tea untuk aplikasi "gedit", maka
  # otomatis akan disimpan di <folder_penyimpanan> dengan nama "gedit_<nama_keterangan>.tea"
#
  #2
apt_archives="/var/cache/apt/archives"
  # directory repository lokal Anda
#

errchk="/tmp/TEA/errchk"
errdisp="/tmp/TEA/errdisp"
show="/tmp/TEA/show"
treeview="/tmp/TEA/tree"

profil=$1
nama_aplikasi=$2


##################
# --functions--
##################

function keluar0 {
	rm -rf "$ruangkerja"
	rm -f "$filekerja"*
	exit 0
}

function keluar1 {
	rm -rf "$ruangkerja"
	rm -f "$filekerja"*
	exit 1
}


##################
# --utama--
##################

ruangkerja="/tmp/TEA/workspace"
filekerja="/tmp/TEA/list"
profile_dir="/tmp/TEA/pro"
rm -rf /tmp/TEA/
mkdir /tmp/TEA/
mkdir "$ruangkerja"
mkdir "$ruangkerja/partial"
mkdir /tmp/TEA/pro/
cp -f $profil /tmp/TEA/pro/

echo -e "\nMembuat file tea untuk profil tujuan :"
ls -1 --hide="lock" "$profile_dir"

  #step 1 : menyusun daftar paket

echo -e "\nAplikasi yang akan dipasang: $nama_aplikasi\n"

echo -e "Memeriksa daftar dependensi...\n"
>"$filekerja"
semua_dependensi=`apt-get --print-uris -y -o dir::state::status="$filekerja" -o dir::cache::archives="$ruangkerja" install $nama_aplikasi | grep '\.deb' | wc -l`
if [ $semua_dependensi -eq 0 ]; then
	echo -e "\nMaaf, aplikasi yang Anda inginkan tidak tersedia di Software Sources yang Anda gunakan.\n"
	keluar1
fi
echo -e "Aplikasi $nama_aplikasi memiliki $semua_dependensi paket dependensi\n" # >> $show
for stat in `ls -1 --hide="lock" "$profile_dir"`; do
echo "Membaca profil : $stat"
apt-get --print-uris -y -o dir::state::status="$profile_dir"/"$stat" -o dir::cache::archives=$ruangkerja install $nama_aplikasi 2> "$filekerja"-err | grep '\.deb' > "$filekerja"-tmp
cat "$filekerja"-err
if [ `cat "$filekerja"-err | wc -l` -gt 0 ]; then
	echo -e "\nMaaf, tidak dapat menyusun dependensi untuk profil : $stat\nProses dibatalkan.\n"
	keluar1
fi
jumlah_diperlukan=`cat "$filekerja"-tmp | wc -l`
jumlah_terinstall=$(( $semua_dependensi - $jumlah_diperlukan ))
cat "$filekerja"-tmp >> "$filekerja"
echo -e "diperlukan $jumlah_diperlukan paket tambahan ( $jumlah_terinstall paket telah terinstall )\n" # >> $show
done

sort "$filekerja" | uniq | awk '{print $2"^"$3}' > "$filekerja"-tmp
mv "$filekerja"-tmp "$filekerja"
NUMdeb=`wc -l "$filekerja" | cut -f1 "-d "`
echo -e "\nTotal diperlukan $NUMdeb file .deb\n"
if [ $NUMdeb -eq 0 ]; then
	echo -e "Aplikasi $nama_aplikasi telah terinstall di profil yang dituju.\nFile tea tidak diperlukan.\n"
	keluar0
fi
sleep 1

  #step 2 : memeriksa file yang tersedia
echo -e "\n# Memerikasi ketersediaan file .deb di APT archives #\nAPT archives Anda : $apt_archives\n"
sleep 1
touch $treeview
jml_tak_ada=0
size_download=0
for q in `cat "$filekerja"`; do
q1=`echo $q|cut -f1 -d^`
q2=`echo $q|cut -f2 -d^`
if [ `ls -1 "$apt_archives" | grep $q1 | wc -l` -gt 0 ]; then
	echo -e "$q1 Yes" >> "$treeview"
else
	echo -e "$q1 No" >> "$treeview"
	jml_tak_ada=$(( $jml_tak_ada + 1 ))
	size_download=$(( $size_download + $q2 ))
fi
done
echo -e '\e[00m'
if [ $jml_tak_ada -eq 0 ]; then
	echo -e "\nSemua file tersedia\n" >> $show
else
	if [ $size_download -ge 10000000000 ]; then
		size_download=$(( $size_download / 1000000000 ))
		satuan="GB"
	elif [ $size_download -ge 10000000 ]; then
		size_download=$(( $size_download / 1000000 ))
		satuan="MB"
	elif [ $size_download -ge 10000 ]; then
		size_download=$(( $size_download / 1000 ))
		satuan="kB"
	else
		satuan="Bytes"
	fi
	semua_dep=$(($jml_tak_ada - $jumlah_diperlukan))
	echo -e "$jml_tak_ada of $jumlah_diperlukan file(s) not available in APT Cache.\nNeed to download $size_download $satuan\n" >> $show
fi



##################
# --notes--
##################
##september 2013
#script ini bebas dan gratis dimanfaatkan untuk tujuan yang benar
#jika ada pertanyaan/masukan silahkan kirim email ke
#elektronifa[at]yahoo.co.id (maaf, hanya email)

#############################################################################
#  di-edit seperlunya untuk keperluan pembuatan Tea Package Maker GUI       #
#  mnirfan, DOSCOM, 2015-2016                                               #
#  kritik & saran : twitter @mnirfan25 atau @doscomedia; http://doscom.org  #
#############################################################################
