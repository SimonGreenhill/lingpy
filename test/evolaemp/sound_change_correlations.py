from numpy import *
from lingpy2 import *

# switch namespace to evolaemp
from lingpy2.data.names.evolaemp import *
from lingpy2.align.sca import get_consensus
from lingpy2.thirdparty import cogent as cg
from ete2 import Tree, TextFace

import math

graphicalOutput = True

def ensure_dir(f):
    try:
        os.makedirs(f)
    except OSError:
        pass
    #d = os.path.dirname(f)
    #if not os.path.exists(d):
    #    os.makedirs(d)

def printTree(node, depth, names=None, field=None, func=None):
    name = node.Name
    if name == None:
        name = "no name"
    else:
        if names != None and name != "root":
            name = name + ": " + names[int(name)]
    if field != None and hasattr(node,field):
        if func != None:
            name = name + " " + func(getattr(node,field))
        else:
            name = name + " " + str(getattr(node,field))
    else:
        name = name + "NO FIELD " + field + "!"
    name = depth * "  " + name;
    print name;
    for child in node.Children:
        printTree(child, depth + 1, names, field, func)

def printTreeWithOrigPointers(node, depth, names=None):
    name = node.Name
    if name == None:
        name = "no name"
    else:
        if names != None:
            name = names[int(name)]
    name = depth * "  " + name;
    orig = node
    while hasattr(orig, "orig"):
        name += " -> " + str(orig.orig)
        orig = orig.orig
    print name;
    for child in node.Children:
        printTreeWithOrigPointers(child, depth + 1, names)

#READING IN THE ASJP DATA

f = open('data/asjp/sounds41.txt','r')
sounds = array([x.strip() for x  in f.readlines()]).tolist()
f.close()

# reading in 'asjpMatrix.txt' into a numpy array
mfile = open("data/asjp/asjpMatrix.txt","r")
asjpRaw = mfile.readlines()
mfile.close()

asjpMatrix = array([x.strip().split('\t') for x in asjpRaw])


# restricting asjpMatrix to the languages in world_names.txt
f = open('data/asjp/world_names.txt','r')
rl = f.readlines()
f.close()

names = array([x.strip() for x in rl])

asjpMatrix = array([x for x in asjpMatrix if x[0] in names])

internal_asjp = Model("asjp_el")

#load long language names
f = open('data/asjp/world_longnames.txt','r')
rl = f.readlines()
f.close()
longnames = array([x.strip() for x in rl])
nameToID = dict({(longnames[i],i) for i in range(0,len(longnames))})

#load long language names
f = open('data/asjp/world_names.txt','r')
rl = f.readlines()
f.close()
names = array([x.strip() for x in rl])

guideTree = cg.LoadTree("data/asjp/world-NWPV.nwk")
#convert guideTree node names to integers as expected by Lingpy MSA
for leaf in guideTree.tips():
    leaf.Name = str(nameToID[leaf.Name])   

for familyName in unique(asjpMatrix[1426:1459,2]):
    langs = where(asjpMatrix[:,2] == familyName)[0].tolist()
    phylName = str(asjpMatrix[langs[0],1])
    print phylName + "." + str(familyName)
    if len(langs) == 1: 
        continue
        print "only one language, skipped"

    ensure_dir("output/" + phylName + "/" + familyName)

#langs = range(1603,1670) #iranian languages
#langs = range(1426,1459) #germanic languages
#langs = range(1461,1602) #indic languages
#langs = range(1690,1707) #slavic languages
#langs = range(1671,1690) #romance languages

#phylName = "IE"
    print langs
    familyGuideTree = subGuideTree(guideTree,langs)
    familyNameTable = [longnames[lang] for lang in langs]
    nameTable = [names[lang] for lang in langs]
    #printTree(familyGuideTree,0,names=familyNameTable)
    
    for conceptID in range(4,44):
        #repeat the cognate detection process to generate cognate sets
        lexdict = {}
        lexdict[0] = ["ID", "concept", "ipa", "doculect"]
        ID = 1
        #create a dictionary for cognate detection
        for langID in langs:
            entries = asjpMatrix[langID,conceptID] #originally: 39 for "mountain"
            for entry in entries.split('-'):
                if not entry == '0':
                    lexdict[ID] = [langID, "concept" + str(conceptID), entry, asjpMatrix[langID,0]]
                    ID += 1
        
        #cluster words into cognate sets
        lexstat = LexStat(lexdict,model=internal_asjp,merge_vowels=False)
        lexstat.get_scorer()
        lexstat.cluster(method='sca',threshold=0.55,verbose=True)
        etym_dict = lexstat.get_etymdict(ref='scaid', entry='', loans=False)
        
        for cognateID in etym_dict.keys():
            entry_msq_file = open("cognate" + str(cognateID) + ".msq", 'w')
            entry_msq_file.write("ASJP database\n")
            entry_msq_file.write("Cognate " + str(cognateID) + " for Germanic languages\n")
            for IDList in etym_dict[cognateID]:
                if (IDList != 0):
                    [langID, word, entry, langName] = lexdict[IDList[0]][:4]
                    entry_msq_file.write(langName + "\t" + entry + "\n")
            entry_msq_file.close()
            cognateLangs = [int(lexdict[IDList[0]][0]) - langs[0] for IDList in etym_dict[cognateID] if IDList != 0]
            #print "cognate set " + str(cognateID) + " - cognate langs: " + str(cognateLangs)
            if len(cognateLangs) > 1:  #cognate sets of size 1 are useless
                cognateGuideTree = subGuideTree(familyGuideTree,cognateLangs)       
                #print("\nAligning cognate " + str(cognateID) + ":")
                #print "  cognate langs = " + str(cognateLangs)
                #printTree(cognateGuideTree,0,names=[germanicNameTable[lang] for lang in cognateLangs])
                cognateNameTable = [nameTable[lang] for lang in cognateLangs]
                multi = MSA("./cognate" + str(cognateID) + ".msq",merge_vowels=False,unique_seqs=False)
                tree_mtx = convert.newick.nwk2guidetree(str(cognateGuideTree))
                multi.prog_align(model=internal_asjp,gop=-4,scale=0.9,guide_tree=tree_mtx)
                #print(multi)
                #old version of call had taxa=[str(i) for i in range(len(langs))]
                cons = get_consensus(multi, cognateGuideTree, gaps=True, classes=False)
                print("Reconstructed proto-" + familyName + " word for concept " + str(conceptID - 3) + ":\t" + cons)  
                 
                #PRINT OUT RECONSTRUCTION STEPS IN A TREE VISUALIZATION
                if graphicalOutput:
                    outputTree = Tree()
                    outputTree.add_face(TextFace(str("".join(cognateGuideTree.reconstructed))), column=0, position = "branch-right")
                    def copyChildrenIntoOutput(treeNode, outputTreeNode):
                        for child in treeNode.Children:
                            outputChild = outputTreeNode.add_child()
                            if child.isTip():
                                outputChild.name = str("".join(child.reconstructed)) + " (" + cognateNameTable[int(child.Name)] + ")"
                            else:
                                outputChild.add_face(TextFace(str("".join(child.reconstructed))), column=0, position = "branch-right")
                                copyChildrenIntoOutput(child, outputChild) 
                    copyChildrenIntoOutput(cognateGuideTree,outputTree)
                    outputTree.render("output/" + phylName + "/" + familyName + "/" + str(conceptID - 3) + "." + cons.replace("-","") +".png")
                
                #print("\nDetermining and counting sound changes at the edges of the guide tree, and cascading them to the supertrees:")
                for node in cognateGuideTree.postorder():
                    if not hasattr(node, "recon_changes"):
                        node.recon_changes = {}
                    if not node.isRoot():
                        for i in range (0,len(node.reconstructed)):
                            #if node.reconstructed[i] != node.Parent.reconstructed[i]:
                            (seg1, seg2) = (str(node.Parent.reconstructed[i]), str(node.reconstructed[i]))
                            origNode = node
                            while origNode != None:
                                if not hasattr(origNode, "recon_changes"):
                                    origNode.recon_changes = {}
                                if seg1 not in origNode.recon_changes:
                                    origNode.recon_changes[seg1] = {}
                                if seg2 not in origNode.recon_changes[seg1]:
                                    origNode.recon_changes[seg1][seg2] = 0.0
                                origNode.recon_changes[seg1][seg2] += 1.0
                                #if change not in origNode.recon_changes.keys():
                                #    origNode.recon_changes[change] = 1
                                #else:
                                #    origNode.recon_changes[change] += 1
                                if hasattr(origNode, "orig"):
                                    origNode = origNode.orig
                                else:
                                    origNode = None
                #for node in cognateGuideTree.postorder():
                #    print str(node.Name)
                #    print str(node.Name) + ": " + str(node.recon_changes)
                #printTree(cognateGuideTree,0,names=[germanicNameTable[lang] for lang in cognateLangs], field="recon_changes")
                
#guideTree = familyGuideTree

print("\nSupertree with collected sound changes at the edges:")
printTree(guideTree,0,names=None, field="recon_changes")

for node in guideTree.postorder():
  if hasattr(node, "recon_changes"):
      for phon1 in node.recon_changes.keys():
        entries = node.recon_changes[phon1]
        entrySum = sum(entries.values())
        for phon2 in entries.keys():
          #print("  " + taxon1 + "->" + taxon2 + ", " + phon1 + "->" + phon2 + ": " + str(entries[phon2]) + "/" + str(entrySum))
          entries[phon2] = entries[phon2] / entrySum

#extract covariances and correlation coefficients for the phoneme replacements in a list
#replacements = ["a-","ae","ai","ao","au","aE","a8","e-","ea","ei","eo","eu","eE","e8",\
#"i-", "ia","ie","io","iu","iE","i8","o-","oa","oe","oi","ou","oE","o8",\
#"u-","ua","ue","ui","uo","uE","u8","E-","Ea","Ee","Ei","Eo","Eu","E8",\
#"8-","8a","8e","8i","8o","8u","8E""-a","-e","-i","-o","-u","-E","-8"]
replacements = ["kg","pb","td","kx","pf","ts","t8","bv","gx","dz","d8"]

def generate_replacements(symbList, threshold):
    result = []
    for symb1 in symbList:
        for symb2 in symbList:
            result.append(symb1 + symb2)
    return result

#replacements = generate_replacements(["k","t","p","b","d","g","f","v","s","8","x"],1)
#replacements = generate_replacements(["k","g","x"],1)
#print(replacements)

replacements = generate_replacements(sounds + ["-"], 1)

covariances = {}
correlations = {}
replacementsDict = dict((pair,{}) for pair in replacements)
#print(replacementsDict)
for node in guideTree.postorder():
    if hasattr(node, "recon_changes"):
      for phon1 in node.recon_changes.keys():
        entries = node.recon_changes[phon1]
        for phon2 in entries.keys():
          if phon1 + phon2 in replacementsDict:
            replacementsDict[phon1 + phon2][node] = entries[phon2]
    #else:
    #  print node.Name + "has no recon_changes!"
for pair1 in replacementsDict.keys():
  for pair2 in replacementsDict.keys():
    print("measuring the covariance of " + pair1 + " and " + pair2 + ": ")
    sharedTaxonPairs = set(replacementsDict[pair1].keys()) & set(replacementsDict[pair2].keys())
    if (len(sharedTaxonPairs) > 0):
      pair1Values = []
      pair2Values = []
      for taxonPair in sharedTaxonPairs:
        pair1Value = replacementsDict[pair1][taxonPair]
        pair2Value = replacementsDict[pair2][taxonPair]
        pair1Values.append(pair1Value)
        pair2Values.append(pair2Value)
        #print("  " + taxonPair + ": " + str(pair1Value) + " vs. " + str(pair2Value))
      #print("  pair1Values: " + str(pair1Values))
      #print("  pair2Values: " + str(pair2Values))    
      pair1E = sum(pair1Values) / len(pair1Values)
      pair2E = sum(pair2Values) / len(pair2Values)
      print("  pair1E: " + str(pair1E))
      print("  pair2E: " + str(pair2E))
      covarianceList = []
      variance1List = []
      variance2List = []
      for i in range(0,len(sharedTaxonPairs)):
        covarianceList.append((pair1Values[i] - pair1E)*(pair2Values[i] - pair2E))
        variance1List.append((pair1Values[i] - pair1E)**2.0)
        variance2List.append((pair2Values[i] - pair2E)**2.0)
      covariance = sum(covarianceList) / len(covarianceList)
      pair1Variance = sum(variance1List) / len(variance1List)
      pair2Variance = sum(variance2List) / len(variance2List)
      print("  pair1Variance: " + str(pair1Variance))
      print("  pair2Variance: " + str(pair2Variance))
      print("  covariance: " + str(covariance))
      covariances["(" + pair1 + "," + pair2 + ")"] = covariance
      if covariance == 0.0:
        correlations["(" + pair1 + "," + pair2 + ")"] = 0.0
      else:
        normalizer = math.sqrt(pair1Variance)*math.sqrt(pair2Variance)
        correlations["(" + pair1 + "," + pair2 + ")"] = covariance/normalizer
      print("  correlation: " + str(correlations["(" + pair1 + "," + pair2 + ")"]))

for key, value in sorted(correlations.iteritems(), key=lambda (k,v): (v,k)):
    print "%s: %s" % (key, value)
    
print("Storing the covariance matrix in replacement-covariances.txt")
covarianceFile = open("replacement-covariances.txt",'w')
covarianceFile.write("\t".join(sorted(replacementsDict.keys())) + "\n")
for pair1 in sorted(replacementsDict.keys()):
    covarianceFile.write("\t".join([str(covariances.get("(" + pair1 + "," + pair2 + ")",0.0)) for pair2 in sorted(replacementsDict.keys())]) + "\n")
    
print("Storing the correlation matrix in replacement-correlations.txt")
correlationFile = open("replacement-correlations.txt",'w')
correlationFile.write("\t".join(sorted(replacementsDict.keys())) + "\n")
for pair1 in sorted(replacementsDict.keys()):
    correlationFile.write("\t".join([str(correlations.get("(" + pair1 + "," + pair2 + ")",0.0)) for pair2 in sorted(replacementsDict.keys())]) + "\n")