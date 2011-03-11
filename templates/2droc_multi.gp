set terminal png medium size 640,480 enhanced
set output '<DVAR name="outfile">'
set format y "%4.3f"
set xlabel "<DVAR name="xlabel">"
set ylabel "<DVAR name="ylabel">"
set key outside bottom center

plot \
<DLOOP name="plot"> \
  '<DVAR name="datafile">' i <DLVAR name="index"> u 2:3:4:5 tit '<DLVAR name="title">' w xyerror ls <DLVAR name="style">,\
</DLOOP> \
f(x)=0
