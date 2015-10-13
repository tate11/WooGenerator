import csv
# import re
from collections import OrderedDict
import os
import shutil
from PIL import Image
import time
from metagator import MetaGator
from csvparse_woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo
from csvparse_myo import CSVParse_MYO
from csvparse_dyn import CSVParse_Dyn
from csvparse_flat import CSVParse_Special
from coldata import ColData_Woo, ColData_MYO #, ColData_User
import xml.etree.ElementTree as ET


importName = time.strftime("%Y-%m-%d %H:%M:%S")

taxoDepth = 3
itemDepth = 2
maxDepth = taxoDepth + itemDepth

inFolder = "../input/"
genPath = os.path.join(inFolder, 'generator.csv')
dprcPath= os.path.join(inFolder, 'DPRC.csv')
dprpPath= os.path.join(inFolder, 'DPRP.csv')
specPath= os.path.join(inFolder, 'specials.csv')
usPath 	= os.path.join(inFolder, 'US.csv')
xsPath	= os.path.join(inFolder, 'XS.csv')

outFolder = "../output/"
flaPath = os.path.join(outFolder , "flattened.csv")
flvPath = os.path.join(outFolder , "flattened-variations.csv")
catPath = os.path.join(outFolder , "categories.csv")
myoPath = os.path.join(outFolder , "myob.csv")
bunPath = os.path.join(outFolder , "bundles.csv")
xmlPath = os.path.join(outFolder , "items.xml")

imgFolder = "/Users/Derwent/Dropbox/TechnoTan/flattened"
refFolder = "/Users/Derwent/Dropbox/TechnoTan/reflattened"
logFolder = "../logs/"

thumbsize = 1920, 1200


rename = False
rename = False
resize = False
remeta = False
delete = False

# skip_images = False
skip_images = True
# rename = True
# detele = True
remeta = True
resize = True

myo_schemas = ["MY"]
woo_schemas = ["TT", "VT", "TS"]

# schema = "MY"
schema = "TT"
# schema = "VT"
# schema = "TS"

currentSpecial = None
# currentSpecial = "SP2015-09-18"

#########################################
# Import Info From Spreadsheets
#########################################

if schema in myo_schemas:
	colData = ColData_MYO()
	productParser = CSVParse_MYO(
		cols = colData.getImportCols(),
		defaults = colData.getDefaults(),
		importName = importName,
		itemDepth = itemDepth,
		taxoDepth = taxoDepth,
	)
elif schema in woo_schemas:

	dynParser = CSVParse_Dyn()
	dynParser.analyseFile(dprcPath)
	dprcRules = dynParser.rules
	dynParser.clearTransients()
	dynParser.analyseFile(dprpPath)
	dprpRules = dynParser.rules
	specialParser = CSVParse_Special()
	specialParser.analyseFile(specPath)
	specials = specialParser.items

	print specials

	colData = ColData_Woo()
	if schema == "TT":
		productParser = CSVParse_TT(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	elif schema == "VT":
		productParser = CSVParse_VT(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	else:
		productParser = CSVParse_Woo(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			schema = schema, 
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	# usrParser = CSVParse_Usr()

productParser.analyseFile(genPath)

# if schema in woo_schemas:

products = productParser.getProducts()
	
if schema in woo_schemas:
	allitems 		= productParser.getItems()
	attributes 	= productParser.attributes
	categories 	= productParser.getCategories()
	variations 	= productParser.getVariations()
	images 		= productParser.images

import_errors = productParser.errors

#########################################
# Export Info to Spreadsheets
#########################################

def joinOrderedDicts(a, b):
	return OrderedDict(a.items() + b.items())

def exportItemsCSV(filePath, colNames, items):
	assert filePath, "needs a filepath"
	assert colNames, "needs colNames"
	assert items, "meeds items"
	with open(filePath, 'w+') as outFile:
		dictwriter = csv.DictWriter(
			outFile,
			fieldnames = colNames.keys(),
			extrasaction = 'ignore',
		)
		dictwriter.writerow(colNames)
		dictwriter.writerows(items)
	print "WROTE FILE: ", filePath

def exportProductsXML(filePath, products, \
		productCols, variationCols, attributeCols, attributeMetaCols, pricingCols, shippingCols):
	print "exporting products"
	for k in productCols.keys():
		if k in pricingCols.keys() + shippingCols.keys():
			del productCols[k] 
	root = ET.Element('products')
	tree = ET.ElementTree(root)
	for product in products:
		productElement = ET.SubElement(root, 'product')
		for index, data in productCols.iteritems():
			tag = data.get('tag')
			# tag = label if label else index
			tag = tag if tag else index
			value = product.get(index)
			if value:
				# value = unicode(value, 'utf-8')
				print "value of", tag, "is", value
				value = str(value).decode('utf8', 'ignore')
				productFieldElement = ET.SubElement(productElement, tag)
				productFieldElement.text = value
			else:
				print "tag has no value"
	print ET.dump(root)
	tree.write(filePath)


def onCurrentSpecial(product):
	return currentSpecial in product.get('spsum')

productCols = colData.getProductCols()

# print "productCols", productCols

if schema in myo_schemas:
	#products
	exportItemsCSV(
		myoPath,
		colData.getColNames(productCols),
		products
	)
elif schema in woo_schemas:

	#products
	attributeCols = colData.getAttributeCols(attributes)
	# print 'attributeCols:', attributeCols

	exportItemsCSV(
		flaPath,
		colData.getColNames(
			joinOrderedDicts( productCols, attributeCols)
		),
		products
	)

	#variations
	variationCols = colData.getVariationCols()
	# print 'variationCols:', variationCols
	attributeMetaCols = colData.getAttributeMetaCols(attributes)
	# print 'attributeMetaCols:', attributeMetaCols

	exportItemsCSV(
		flvPath,
		colData.getColNames(
			joinOrderedDicts( variationCols, attributeMetaCols)
		),
		variations
	)

	#categories
	categoryCols = colData.getCategoryCols()

	exportItemsCSV(
		catPath,
		colData.getColNames(categoryCols),
		categories
	)

	#specials
	try:
		assert( currentSpecial, "currentSpecial should be set")
		specialProducts = filter(
			onCurrentSpecial,
			products
		)
		if specialProducts:
			flsPath = os.path.join(outFolder , "flattened-"+currentSpecial+".csv")
			exportItemsCSV(
					flsPath,
					colData.getColNames(
						joinOrderedDicts( productCols, attributeCols)
					),
					specialProducts
				)
		specialVariations = filter(
			onCurrentSpecial,
			variations
		)
		if specialVariations:
			flvsPath = os.path.join(outFolder , "flattened-variations-"+currentSpecial+".csv")
			exportItemsCSV(
				flvsPath,
				colData.getColNames(
					joinOrderedDicts( variationCols, attributeMetaCols)
				),
				specialVariations
			)
	except:
		pass

	pricingCols = colData.getPricingCols()
	shippingCols = colData.getShippingCols()

	#export items XML
	exportProductsXML(
		xmlPath,
		products,
		productCols,
		variationCols,
		attributeCols, 
		attributeMetaCols, 
		pricingCols,
		shippingCols
	)


#########################################
# Attempt import`
#########################################



#########################################
# Images
#########################################	

if skip_images: images = {}

print ""
print "Images:"
print "==========="

import_errors = {}

#prepare reflattened directory


if not os.path.exists(refFolder):
	os.makedirs(refFolder)
# if os.path.exists(refFolder):
# 	print "PATH EXISTS"
# 	shutil.rmtree(refFolder)
# os.makedirs(refFolder)
ls_flattened = os.listdir(imgFolder) 
ls_reflattened = os.listdir(refFolder)
for f in ls_reflattened:
	if f not in ls_flattened:
		print "DELETING", f, "FROM REFLATTENED"
		if delete:
			os.remove(os.path.join(refFolder,f))

cmp_vallen = lambda (ak, av), (bk, bv): cmp(len(av), len(bv))
cmp_codelen = lambda a, b: cmp( len(a.get('codesum',)), len(b.get('codesum')))
not_category = lambda x: x.get('thisDepth') >= 2

new_img = {}
changes_name = OrderedDict()
changes_meta = OrderedDict()
# for img, items in images.items():
for img, items in sorted(images.items(), cmp_vallen):
	if img not in changes_meta.keys():
		changes_meta[img] = []
	if img not in changes_name.keys():
		changes_name[img] = []
	cm = changes_meta[img]
	cn = changes_name[img]
	# print ""
	print img
	print "-> Associated items"
	for item in items:
		print " -> (%4d) %10s" % (item['rowcount'], item['codesum'])
	
	#image name and extention

	# extmatches = re.findall( r".[\w\d]+", img)
	# assert len(extmatches) > 0
	# ext = extmatches[-1]
	# name = img[:-len(ext)]

	name, ext = os.path.splitext(img)
	if(not name): continue

	# print "%s: name: %s, ext: %s" % (img, name, ext)

	noncategories = filter(not_category, items )
	# print noncategories
	if noncategories:
		head = sorted(noncategories, cmp_codelen)[0]
		name = head.get('codesum')
		title = filter(None, [head.get('itemsum'), head.get('fullname')])[0]
		description = head.get('descsum')
	else:
		head = sorted(items, cmp_codelen)[0]
		title = head.get('taxosum')
		description = head.get('descsum')

	#TODO: add exception for product categories
	if not description:
		description = title
	if not title:
		import_errors[img] = import_errors.get(img,[]) + ["no title"]
	if not description:
		import_errors[img] = import_errors.get(img,[]) + ["no description"]

	# ------
	# RENAME
	# ------

	for item in items:
		if item['rowcount'] in new_img.keys():
			new_img[item['rowcount']] += '|' + name + ext
		else:
			new_img[item['rowcount']] = name + ext

	if name + ext != img:
		cn.append("Changing name to %s" % (name + ext))
		if rename: 
			try:
				shutil.move(imgFolder + img, imgFolder + name + ext )
				img = name + ext
			except IOError:
				print "IMAGE NOT FOUND: ", img
				continue


	# ------
	# REMETA
	# ------

	fullname = os.path.join(imgFolder, img)
	# print "fullname", fullname
	try:
		metagator = MetaGator(os.path.join(imgFolder, img))
	except Exception, e:
		import_errors[img] = import_errors.get(img,[]) + ["error creating metagator: " + str(e)]
		continue

	try:
		oldmeta = metagator.read_meta()
	except Exception, e:
		import_errors[img] = import_errors.get(img,[]) + ["error reading from metagator: " + str(e)]	
		continue

	newmeta = {
		'title': title,
		'description': description
	}

	for oldval, newval in (
		(oldmeta['title'], newmeta['title']),
		(oldmeta['description'], newmeta['description']), 
	):
		if str(oldval) != str(newval):
			cm.append("changing imgmeta from %s to %s" % (repr(oldval), str(newval)[:10]+'...'+str(newval)[-10:]))

	if len(cm) > 0 and remeta:
		print ' -> errors', cm
		try:	
			metagator.write_meta(title, description)
		except Exception, e:
			import_errors[img] = import_errors.get(img,[]) + ["error writing to metagator: " + str(e)]


	# ------
	# RESIZE
	# ------

	if resize:
		imgsrcpath = imgFolder + img
		imgdstpath = refFolder + img
		if not os.path.isfile(imgsrcpath) :
			print "SOURCE FILE NOT FOUND:", imgsrcpath
			continue

		if os.path.isfile(imgdstpath) :
			imgsrcmod = os.path.getmtime(imgsrcpath)
			imgdstmod = os.path.getmtime(imgdstpath)
			# print "image mod (src, dst): ", imgsrcmod, imgdstmod
			if imgdstmod > imgsrcmod:
				# print "DESTINATION FILE NEWER: ", imgdstpath
				continue

		print "resizing:", img
		shutil.copy(imgsrcpath, imgdstpath)
		
		imgmeta = MetaGator(imgdstpath)
		imgmeta.write_meta(title, description)
		print imgmeta.read_meta()


		image = Image.open(imgdstpath)
		image.thumbnail(thumbsize)
		image.save(imgdstpath)

		# try:
		# except Exception as e:
		# 	print "!!!!!", type(e), str(e)
		# 	continue

		imgmeta = MetaGator(imgdstpath)
		imgmeta.write_meta(title, description)
		print imgmeta.read_meta()


if not os.path.exists(logFolder):

	os.makedirs(logFolder)

logname = importName + ".log"
with open( os.path.join(logFolder, logname), 'w+' ) as logFile:

	logFile.write( "import errors:\n")
	for code, errors in import_errors.items():
		logFile.write( "%s :\n" % code)
		for error in errors:
			logFile.write(" -> %s\n" % error)

	logFile.write("")
	logFile.write( "Changes:\n" )
	logFile.write( " -> name\n")
	for img, chlist in changes_name.iteritems():
		if chlist: 
			logFile.write( "%s: \n" % img )
			for change in chlist:
				logFile.write( "-> %s\n" % change	)
	logFile.write( " -> meta\n")
	for img, chlist in changes_meta.iteritems():
		if chlist: 
			logFile.write( "%s: \n" % img )
			for change in chlist:
				logFile.write( "-> %s\n" % change	)			

	logFile.write("")
	if rename:
		logFile.write( "Img column:\n" )
		i = 0
		while new_img:
			if i in new_img.keys():
				logFile.write( "%s\n" % new_img[i] )
				del new_img[i]
			else:
				logFile.write( "\n" )
			i += 1

with open( os.path.join(logFolder, logname) ) as logFile:

	for line in logFile:
		print line[:-1]