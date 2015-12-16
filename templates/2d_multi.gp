set terminal png medium size 800,800 font "FreeSans,12" enhanced
set output '<DVAR name="outfile">'
set format y "%4.3f"
set xlabel "<DVAR name="xlabel">"
set ylabel "<DVAR name="ylabel">"
set key outside bottom center
set style line 200 lc rgb "#333333" lw 2 pt 1
set style line 300 lt 0 lc rgb "#6a6a6a" lw 2 ps 0 pi 2

set style arrow 1 head filled size screen 0.015,25,55 ls 200
<DBOOL name="betterSE">
set arrow from graph 0.90,0.15 to graph 0.95,0.05 as 1
set label "better" at graph 0.91,0.10 right
<DELSE>
set arrow from graph 0.90,0.85 to graph 0.95,0.95 as 1
set label "better" at graph 0.92,0.92 right
</DBOOL>


plot \
  <DBOOL name="add_pareto">'<DVAR name="datafile">' i <DVAR name="pareto_index"> u 1 2 notit w l ls 300, </DBOOL>\
<DLOOP name="plot"> \
  '<DVAR name="datafile">' i <DLVAR name="index"> u 1:2:3 tit '<DLVAR name="title">' w yerror ls <DLVAR name="style">,\
</DLOOP> \
1/0 notit
