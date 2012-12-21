import os
import cgi
import string
import cStringIO

params={"base":["n/a"],"dup":((10,1),(20,1),(30,1),(40,1),(10,3),(30,0.333),(40,0)), "lgto":(10,20,40,60,80), "seqerr":range(6,19,3),"indel":(0.000125,0.000250,0.000500,0.00100,0.002)}
trees ={"Vertabrate-like":range(1,4), "Bacteria-like":range(1,4)}
repl=xrange(1,6)

paramHeading={"base":"","dup":"Dupl [%], Dupl-Loss-Ratio","lgto":"LGTs [%]", "seqerr":"Sites [%]", "indel":"InDel-Rate"}

treeMap ={"Vertabrate-like":"v","Bacteria-like":"g"}

templateString=string.Template('''
<!DOCTYPE>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>

<style type="text/css">
 body { font-size: 80%; font-family: Verdana, Arial, Sans-Serif; }
 ul#tabs { list-style-type: none; margin: 30px 0 0 0; padding: 0 0 0.3em 0; }
 ul#tabs li { display: inline; }
 ul#tabs li a { color: #42454a; background-color: #dedbde; border: 1px solid #c9c3ba; border-bottom: none; padding: 0.3em; text-decoration: none; }
 ul#tabs li a:hover { background-color: #f1f0ee; }
 ul#tabs li a.selected { color: #000; background-color: #f1f0ee; font-weight: bold; padding: 0.7em 0.3em 0.38em 0.3em; }
 div.tabContent { border: 1px solid #c9c3ba; padding: 0.5em; background-color: #f1f0ee; }
 div.tabContent.hide { display: none; }
 div.tabContent table{ width:80%; }
 table { text-align:center; vertical-align:top; border-spacing:0; border-width:0;}
 .oddRow{ background-color: #cccccc;}
 .endHeaderRow td{ border-bottom: solid 1px; }
 .frstTreeKindCol{ border-left: solid 1px; }
 .paramCol{ width: 20em; }
</style>


<script type="text/javascript">
//<![CDATA[

var tabLinks = new Array();
var contentDivs = new Array();

function init() {

    // Grab the tab links and content divs from the page
    var tabListItems = document.getElementById('tabs').childNodes;
    for ( var i = 0; i < tabListItems.length; i++ ) {
        if ( tabListItems[i].nodeName == "LI" ) {
            var tabLink = getFirstChildWithTagName( tabListItems[i], 'A' );
            var id = getHash( tabLink.getAttribute('href') );
            tabLinks[id] = tabLink;
            contentDivs[id] = document.getElementById( id );
        }
    }

    // Assign onclick events to the tab links, and
    // highlight the first tab
    var i = 0;

    for ( var id in tabLinks ) {
        tabLinks[id].onclick = showTab;
        tabLinks[id].onfocus = function() { this.blur() };
        if ( i == 0 ) tabLinks[id].className = 'selected';
        i++;
    }

    // Hide all content divs except the first
    var i = 0;

    for ( var id in contentDivs ) {
        if ( i != 0 ) contentDivs[id].className = 'tabContent hide';
        i++;
    }
}

function showTab() {
    var selectedId = getHash( this.getAttribute('href') );

    // Highlight the selected tab, and dim all others.
    // Also show the selected content div, and hide all others.
    for ( var id in contentDivs ) {
        if ( id == selectedId ) {
            tabLinks[id].className = 'selected';
            contentDivs[id].className = 'tabContent';
        } else {
            tabLinks[id].className = '';
            contentDivs[id].className = 'tabContent hide';
        }
    }

    // Stop the browser following the link
    return false;
}

function getFirstChildWithTagName( element, tagName ) {
    for ( var i = 0; i < element.childNodes.length; i++ ) {
        if ( element.childNodes[i].nodeName == tagName ) return element.childNodes[i];
    }
}

function getHash( url ) {
    var hashPos = url.lastIndexOf ( '#' );
    return url.substring( hashPos + 1 );
}

//]]>
</script>
</head>

<body onload="init()">
<h1>Simulated datasets</h1>

<ul id="tabs">
<li><a href="#base">Base case</a></li>
<li><a href="#dupl">Duplication/Loss</a></li>
<li><a href="#lgt">LGT</a></li>
<li><a href="#seqerr">Sequencing Errors</a></li>
<li><a href="#indel">Indels</a></li>
</ul>

<div class="tabContent" id="base">
<h2>This is the base case</h2>
<div>
<p>In this dataset, no only amino acid substitutions at a fixed rate are modeled. This is the base case for any further analysis.</p>
${base}
</div>
</div>

<div class="tabContent" id="dupl">
<h2>Variation of Gene Duplication and Loss Rate</h2>
<div>
<p>In addition to amino acid substitutions, for these datasets the gene duplication rate is varied (in percent of affected genes in the present day genomes) and also the loss rate (given as the ratio of loss rate and duplication rate).</p>
${dup}
</div>
</div>

<div class="tabContent" id="lgt">
<h2>Variation of Lateral Gene Transfer Rate</h2>
<div>
<p>On these datasets we model different rates of lateral gene transfers with orthologous replacement.</p>
${lgto}
</div>
</div>

<div class="tabContent" id="seqerr">
<h2>Variation of Base-Calling Error Rate</h2>
<div>
<p>On these datasets we model errors in the sequencing step. We replace a random fraction of positions with other amino acids.</p>
${seqerr}
</div>
</div>

<div class="tabContent" id="indel">
<h2>Variation of Insertion/Deletion Rate</h2>
<div>
<p>For these datasets we varied the insertion/deletion rate during the evolution.</p>
${indel}
</div>
</div>

</body>
</html>
''')


tables = dict()

for effect in params.keys():
    f=cStringIO.StringIO()
    f.write('<table>\n');
    oddRow = True
    
    f.write('<tr><th>Disturbance</th><th colspan="3" class="frstTreeKindCol">{0} Tree</th><th colspan="3" class="frstTreeKindCol">{1} Tree</th><tr>\n'.format(*trees.keys()))
    treeStr=""
    for t in trees.keys():
        for cnt in trees[t]:
            treeStr += '<td'
            if cnt==1:
                treeStr += ' class="frstTreeKindCol"'
            treeStr += '>Tree %d</td>'%(cnt)
    
    f.write('<tr class="endHeaderRow"><td>%s</td>%s</tr>\n'%(paramHeading[effect], treeStr))
    for param in params[effect]:
        f.write(' <tr');
        if oddRow: f.write(' class="oddRow"')
        f.write('>');

        if isinstance(param,str):pStr=param
        elif isinstance(param,tuple):pStr="{0}%, {1}".format(*param)
        else: pStr=str(param)

        f.write('<td class="paramCol">%s</td>'%pStr)
        for treeKind in trees.keys():
            for treeSamp in trees[treeKind]:
                fnBase = effect
                if isinstance(param,float) or isinstance(param,int):
                    fnBase += "%d"%(params[effect].index(param)+1)
                elif isinstance(param, tuple):
                    fnBase += "%d"%(param[0]/10)
                    if param[1] != 1:
                        if param[1]==0:
                            fnBase += "_noloss";
                        else: 
                            fnBase += "_loss%d"%(round(param[0]*param[1]/10))
                repStr = "<br/>".join( ['<a href="/simdata/%s_%s%d_%d.tar.gz">Repl %d</a>'%(fnBase,treeMap[treeKind],treeSamp,z,z) for z in repl])
                cellStyle = ""
                if treeSamp==1:
                    cellStyle = ' class="frstTreeKindCol"'
                f.write('<td%s>'%(cellStyle) + repStr + '</td>')
        f.write('</tr>\n')
        oddRow = not oddRow
    f.write('</table>\n')
    tables[ effect ] = f.getvalue()

page = templateString.substitute( tables )
f= open('simdata.html', 'w')
f.write(page)
f.close()

