import xml.sax.handler
import xml.sax
import datetime
import os
import getopt, sys
import re
import gzip

class Protein:
  def __init__(self):
    self.mapping = {}
    self.sname = 0
    self.taxid = 0
   
  def addTag(self, tag, val):
    if tag in self.mapping :
      self.mapping[ tag ].append( val )
    else :  
      self.mapping[ tag ] = [ val ]
  
  def toDarwinFmt(self):
    buf = "<E>"
    for tag in self.mapping.iterkeys():
      self.mapping[tag].sort()
      buf += "<%s>"%(tag,)
      buf += "; ".join(self.mapping[tag])
      buf += "</%s>"%(tag,)
    buf += "</E>"
    return buf

class SeqXMLHandler(xml.sax.handler.ContentHandler):
  def __init__(self):
    self.vers = 0
    self.protein = 0
    self.inDesc = 0
    self.desc = ""
    self.inSeq = 0 
    self.seq = ""
    self.processors = []
    self.AAsubst = 0

  def addProteinProcessor(self, p):
    if not isinstance(p, ProteinProcessor) : raise ValueError('wrong type of p')
    self.processors.append(p)

  def startElement(self, name, attributes):
    if name == "seqXML":
      for proc in self.processors :
        proc.setDatasetVersion( attributes["sourceVersion"] )
        if 'ncbiTaxID' in attributes:
          proc.setDefaultSpecies( attributes["ncbiTaxID"], attributes["speciesName"]);
    elif name == "entry" :
      ac = attributes["id"];
      src = attributes["source"];
      self.protein = Protein()
      self.protein.addTag("AC",ac)
      self.protein.addTag(src,ac)
    elif name == "species":
      self.protein.sname = attributes["name"]
      self.protein.taxid = attributes["ncbiTaxID"]
    elif name == "description" : 
      self.inDesc = 1
    elif name == "AAseq" :
      self.inSeq = 1
    elif name == "DBRef" :
      self.protein.addTag( attributes["source"], attributes["id"] )

  def characters(self, data):
    if self.inDesc:
      self.desc += data
    elif self.inSeq :
      self.seq += data
 
  def endElement(self, name):
    if name == "description":
      self.inDesc = 0
      if len(self.desc)>0 : 
        self.protein.addTag("DE",self.desc)
        self.desc = ""
    elif name == "AAseq" :
      self.inSeq = 0
      if len(self.seq) == 0 : raise FormatError("No sequence stored")
      if self.seq[-1]=='*' :
        self.seq = self.seq[0:-2];
      self.seq, c = re.subn( '[UOBZJ*]','X',self.seq )
      self.AAsubst += c
      self.protein.addTag('SEQ',self.seq)
    elif name == "entry" :
      for proc in self.processors :
        proc.processProtein( self.protein )
      self.seq = ""
    elif name == "seqXML" :
      for proc in self.processors : proc.finish()
      print "Converted %d unknown AA to X\n"%(self.AAsubst)

class ProteinProcessor : 
  def __init__(self, path, oginfo):
    self.path = path
    self.oginfo = oginfo 
    self.fh = 0
    self.headerDone = 0
    self.version = "n.a."
    self.entryCnt = 0
    self.fiveName = ""
    self.defaultSpecies = 0

  def setDatasetVersion(self, version):
    self.version = version

  def setDefaultSpecies(self, taxid, sciname):
    self.defaultSpecies = {'taxid': taxid, 'sciname': sciname};

  def processProtein(self, p):
    if not self.headerDone:
      if p.taxid == 0 and self.defaultSpecies != 0:
        p.taxid = self.defaultSpecies['taxid']
        p.sname = self.defaultSpecies['sciname']
      t = self.oginfo[ p.taxid ]
      self.fiveName = t[ "fiveName" ]
      lin  = t[ "lin" ]
      king = t[ "king" ]
      buf = "<DBNAME>Non-redundant reference genome for %s</DBNAME>\n"%(p.sname)
      buf += "<DBRELEASE>%s</DBRELEASE>\n"%(self.version)
      buf += "<DATE>%s</DATE>\n"%( datetime.date.today().strftime("%B %d, %Y") )
      buf += "<SCINAME>%s</SCINAME>\n"%(p.sname)
      buf += "<5LETTERNAME>%s</5LETTERNAME>\n"%(self.fiveName)
      buf += "<OS>%s</OS>\n"%(lin)
      buf += "<KINGDOM>%s</KINGDOM>\n"%(king)
      buf += "<TAXONID>%s</TAXONID>\n"%(p.taxid)
      self.headerDone = 1
      if not os.path.isdir( "%s/%s"%(self.path, self.fiveName) ):
        os.mkdir( "%s/%s"%(self.path, self.fiveName) )
      versNbr = self.version.split(',')[0]
      f = "%s/%s/%s.%s.db"%(self.path, self.fiveName, self.fiveName, versNbr)
      self.fh = open( f, 'w')
      self.fh.write(buf)
      self.entryCnt=0
#      print buf

    self.fh.write( p.toDarwinFmt() )
    self.fh.write( "\n" )
    self.entryCnt += 1
      

  def finish(self):
    self.fh.close()
    self.headerDone = 0
    f = open( "%s/RemainingGenomes.txt"%(self.path), 'a')
    f.write("%s\tREF\t%d\n"%(self.fiveName, self.entryCnt))
    f.close()
    

def main() :
  try:
    oplist, args = getopt.getopt(sys.argv[1:], 's:d:',['speciesinfo=','datadir='])
  except getopt.GetoptError, err:
    print str(err)
    sys.exit(2)
  
  spfn = "SpeciesInfo.txt"
  ddir = "/home/darwin/DB/refgenomes/genomes/"
  for o,a in oplist:
    if o in ("-s", "--speciesinfo"):
      spfn = a
    elif o in ("-d", "--datadir"):
      ddir = a
  speciesInfo = eval('%s'%open(spfn).read())
  
  parser = xml.sax.make_parser()
  handler = SeqXMLHandler()
  handler.addProteinProcessor( ProteinProcessor(ddir, speciesInfo) )
  parser.setContentHandler( handler )
  print args

  for f in args:
    open_ = gzip.open if f.endswith('.gz') else open;
    with open_(f) as fh:
      parser.parse(fh)

  sys.exit(0)

if __name__ == "__main__":
   main()
