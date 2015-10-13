catReplace = {}
colNames = OrderedDict( [
	('codesum', 'item_number'),
	('WNRC', 'Selling Price'),
	('RNRC', 'Price Level A, Qty Break 1'),
	# ('WNR', 'Price Level B, Qty Break 1'),
	# ('WNR', 'Price Level C, Qty Break 1'),
	# ('Cost Price', 'Price Level D, Qty Break 1'),
	# ('CVCo', 'Custom Field 1'),
	# ('D', 'Custom Field 2'),	
	# ('Sell', 'Sell'),
	# ('Tax Code When Sold', 'Tax Code When Sold'),
	# ('Sell Price Inclusive', 'Sell Price Inclusive'),
	# ('Income Acct', 'Income Acct'),
] )
# generated = [ 'Item Number', 'Description', 'Item Name' ]
# constants = [ 'Sell', 'Tax Code When Sold' ]
defaults = OrderedDict( defaults.items() + [
	('Sell', 'S'),
	('Tax Code When Sold', 'GST'),
	('Sell Price Inclusive', 'X'),
	('Income Acct', '41000'),
	('Use Desc. On Sale', ''),
	('Inactive Item', 'N'),
])	
nameReplace = OrderedDict( nameReplace.items() + [
	('Body Butter with Shimmer', 'Body Butter w/ Shimmer'),
	('Tan Saver Body Wash', 'Body Wash'),
	('Full Body Moisturizer', 'Moisturizer'),
	('Moisturizing Body Milk', 'Body Milk'),
	('Hair Brush', 'Brush'),
	('Training Session', 'Session'),
	('Skin Trial Pack', "Pack"),
	('Trial Pack', "Pack"),
	('Starter Package', 'Pack'),
	('Sample Pack', "Pack"),
	('Evaluation Package', 'Pack'),
	('Spare Pot & Hose', 'Pot, Hose'),
	('Spare Pots & Hose', 'Pots, Hose'),
	('spare pot + Hose', 'pot, hose'),
	('spare pots + Hose', 'pots, hose'),
	('extraction fans', 'xfan'),
	('Low Voltage', 'LV'),
	('Double Sided', '2Sided'),

	('TechnoTan', 'TT'),
	('VuTan', 'VT'),
	('EzeBreathe', 'EZB'), 
	('Sticky Soul', 'SS'),
	('My Tan', 'MT'),
	('TanSense', 'TS'),
	('Tanning Advantage', 'TA'),
	('Tanbience', 'TB'),
	('Mosaic Minerals', 'MM'),

	('Removal', 'Rem.'),
	('Application', 'App.'),
	('Peach & Vanilla', 'P&V'),
	('Tamarillo & Papaya', 'T&P'),
	('Tamarillo', 'TAM'),
	('Lavander & Rosmary', 'L&R'),
	('Coconut & Lime', 'C&L'),
	('Melon & Cucumber', 'M&C'),
	('Coconut Cream', 'CC'),
	('Black & Silver', 'B&S'),
	('Black & Gold', 'B&G'),
	('Hot Pink', 'PNK'),
	('Hot Lips (Red)', 'RED'),
	('Hot Lips Red', 'RED'),
	('Hot Lips', 'RED'),
	('Silken Chocolate (Bronze)', 'BRZ'),
	('Silken Chocolate', 'BRZ'),
	('Moon Marvel (Silver)', 'SLV'),
	('Dusty Gold', 'GLD'),

	('Black', 'BLK'),
	('Light Blue', 'LBLU'),
	('Dark Blue', 'DBLU'),
	('Blue', 'BLU'),
	('Green', 'GRN'),
	('Pink', 'PNK'),
	('White', 'WHI'),
	('Grey', 'GRY'),
	('Peach', 'PEA'),
	('Bronze', 'BRZ'),
	('Silver', 'SLV'),
	('Gold', 'GLD'),
	('Red', 'RED'),

	('Cyclone', 'CYC'),
	('Classic', 'CLA'),
	('Premier', 'PRE'),
	('Deluxe', 'DEL'),
	('ProMist Cube', 'CUBE'),
	('ProMist', 'PRO'),
	('Mini Mist', 'MIN'),

	('Choc Fudge', 'CFdg.'),
	('Choc Mousse', 'Cmou'),
	('Ebony', 'Ebny.'),
	('Creme Caramel', 'CCarm.'),
	('Caramel', 'Carm.'),
	('Cappuccino', 'Capp.'),
	('Evaluation', 'Eval.'),
	('Package', 'Pack'),
	('Sample', 'Samp.'),
	('sample', 'Samp.'),
	('Tan Care', 'TCare'),
	('After Care', "ACare"),
	('A-Frame', 'AFrm'),
	('X-Frame', 'XFrm'),
	('Tear Drop Banner', 'TDBnr'),
	('Roll Up Banner', 'RUBnr'),
	('Hose Fitting', 'Fit.'),
	('Magnetic', 'Mag.'),
	('Option ', 'Opt.'),
	('Style ', 'Sty.'),
	('Insert and Frame', 'ins. frm.'),
	('Insert Only', 'ins.'),
	('Insert', 'ins.'),
	('insert', 'ins.'),
	('Frame', 'frm.'),
	('Foundation', 'Found.'),
	('Economy', 'Econ.'),

	('Medium-Dark', 'MDark'),
	('Medium Dark', 'MDark'),
	('Medium', 'Med.'),
	('medium', 'med.'),
	('Extra Dark', 'XDark'),
	('Extra-Dark', 'XDark'),
	('Dark', 'Dark'),
	('Tanning', 'Tan.'),
	('Extra Small', 'XSml.'),
	('Small', 'Sml.'),
	('Extra Large', 'XLge.'),
	('Large', 'Lge.'),
	('Ladies', 'Ld.'),
	('Mens', 'Mn.'),
	('Non Personalized', 'Std.'),
	('Personalized', 'Per.'),
	('personalized', 'per.'),
	('Personalised', 'Per.'),
	('personalised', 'per.'),
	('Custom Designed', 'Cust.'),
	('Refurbished', 'Refurb.'),
	('Compressor', 'Cmpr.'),
	('Spray Gun', 'Gun'),
	('Permanent', 'Perm.'),
	('Shimmering', 'Shim.'),
	('Screen Printed', 'SP'),
	('Embroidered', 'Embr.'),
	('Athletic', 'Athl.'),
	('Singlet', 'Sing.'),
	('Solution', 'Soln.'),
	('Flash Tan', 'FTan'),
	('Original', 'Orig.'),
	('Exfoliating', 'Exfo.'),
	('Disposable', 'Disp.'),
	('Retractable', 'Ret.'),
	('Synthetic', 'SYN'),
	('Natural', 'NAT'),
	('Bayonet', 'BAY'),
	('Hexagonal', 'Hex.'),

	('one', '1'),
	('One', '1'),
	('two', '2'),
	('Two', '2'),
	('three', '3'),
	('Three', '3'),
	('four', '4'),
	('Four', '4'),
	# ('for', '4'),
	('five', '5'),
	('Five', '5'),
	('six', '6'),
	('Six', '6'),
	('seven', '7'),
	('seven', '7'),
	('eight', '8'),
	('Eight', '8'),
	('nine', '9'),
	('Nine', '9'),

	(' Plus', '+'),
	(' - ', ' '),
	(' Pack / ', ' x '),
	('with', 'w/'),
	('With', 'w/'),
	('Box of', 'Box/'),
	(' Fitting for ', ' Fit '),
	(' Fits ', ' Fit '),

	# (' (2hr)', ''),
	(' (sachet)', ''),
	(' (pump bottle)', ''),
	(' Bottle with Flip Cap', ''),
	(' (jar)', ''),
	(' (tube)', ''),
	(' (spray)', ''),

])