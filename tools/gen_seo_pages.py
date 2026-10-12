#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yongli buyer-intent page generator.

Two page families, both built from data the site already has:

  guides/<slug>/      buyer-intent content pages. The topic list is taken from
                      the store's own keyword report on 2026-10-12 - the
                      "top inquiry words" (sourdough starter kit, titanium
                      cutting board, garlic press, bread proofing box) and the
                      "top traffic words" (kitchen accessories, kitchen gadgets,
                      lunch box, baby, yogurt) - plus the five main product lines
                      the store advertises. No invented demand figures:
                      nothing here claims a search volume, and no page links out
                      to a marketplace.
  product/<code>/     one page per catalogue item that has a printed code, so
                      the site stops being only catalogue/category layers.
                      Codes/names/pages come from search-index.json.

Also written: guides/index.html, product/index.html (crawlable hubs), the
"buyer guides" block on the homepage, and a merged sitemap.xml.

Usage:
    python tools/gen_seo_pages.py
    python tools/gen_seo_pages.py --limit 60      # smaller product pages batch
    python tools/gen_seo_pages.py --no-sitemap

Run it AFTER gen_pages.py: that script rewrites sitemap.xml from scratch, this
one merges its own URLs into whatever is already there.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_pages import (  # noqa: E402  (same folder, single source of truth)
    BRAND_LINE, CATS, ROOT, SITE, TEMPLATE_CSS, esc, slugify,
)

GUIDE_DIR = ROOT / "guides"
PRODUCT_DIR = ROOT / "product"
SITEMAP = ROOT / "sitemap.xml"
INDEX_HTML = ROOT / "index.html"
CERT_CHIPS = ["BSCI", "ISO 9001", "FDA", "LFGB", "EN71", "REACH", "RoHS"]

CAPABILITIES = [
    "Custom mould and tooling design, with samples before mass production",
    "Pantone colour matching and food-grade silicone hardness tuning",
    "Logo printing, debossing and fully custom retail packaging",
    "Material options tested to FDA, LFGB, EN71 and REACH",
    "BSCI and ISO 9001 audited factory with in-process and pre-shipment inspection",
    "One-stop OEM/ODM, packaging, design and logistics support",
]

# slug, h1, meta title, meta description, lede, intro paragraphs, match terms,
# capability bullets, FAQs, store links. `words` records which backend keyword
# this page answers, so the mapping stays auditable.
GUIDES_DATA = [
    {
        "slug": "sourdough-starter-kit-manufacturer",
        "h1": "Sourdough Starter Kit Manufacturer &amp; OEM Supplier",
        "meta_title": "Sourdough Starter Kit Manufacturer | OEM &amp; Wholesale",
        "meta_desc": "BSCI &amp; ISO 9001 certified OEM/ODM maker of sourdough starter kits, jars, "
                     "thermometers and cloth covers. Custom logo, packaging and colours.",
        "lede": "Yongli manufactures sourdough starter kits and starter jars for private-label "
                "and wholesale programmes - glass or plastic jars, metal or silicone lids, cloth "
                "covers, thermometers and printed labels, assembled in one order.",
        "intro": [
            "A sourdough starter kit is a bundled product: the jar, its lid, a cover, sometimes a "
            "thermometer, scale or proofing basket, plus the label or booklet that tells the buyer "
            "how to feed the starter. We make the whole bundle - the silicone and plastic parts "
            "in house, the glass and metal parts through long-standing suppliers - so a private "
            "label order arrives as one finished, carton-ready product.",
            "Because the jar is the item that carries your brand, most of the work is in the "
            "finish: lid colour and material, lid embossing, cover fabric, label artwork, and the "
            "retail carton. We match colour to Pantone numbers and can produce samples of the "
            "complete kit before tooling is released for mass production.",
        ],
        "match": ["sourdough", "starter kit", "starter jar", "sour dough", "fermentation jar"],
        "words": "top inquiry words: sourdough starter kit",
        "bullets": [
            "Glass or plastic starter jars, 24 oz and 34 oz class capacities",
            "Metal, plastic or silicone lids; breathable cloth covers",
            "Thermometer, scale, bread lame, whisk and scraper add-ons",
            "Printed labels, recipe cards and gift-box assembly",
            "Also available as a kit with a round or oval proofing basket",
        ],
        "faqs": [
            ("Do you supply the full kit or only the jar?",
             "Both. We can quote the jar on its own, or the complete kit - jar, lid, cover, "
             "thermometer, label and carton - assembled and packed in one shipment."),
            ("Can the lid and cover carry our logo?",
             "Yes. We print or deboss logos on lids and jars, and print or embroider cloth "
             "covers. Artwork is proofed on a physical sample before mass production."),
            ("Which materials are available for the jar?",
             "Soda-lime glass and BPA-free plastic are standard. Food-contact parts are produced "
             "to FDA and LFGB requirements, with test reports available on request."),
            ("What is the minimum order?",
             "It depends on the configuration - glass, tooling and packaging all move the number. "
             "Send us your target quantity and the exact kit contents and we will quote against it."),
        ],
    },
    {
        "slug": "bread-proofing-basket-manufacturer",
        "h1": "Bread Proofing Basket Manufacturer (Banneton &amp; Dough Boxes)",
        "meta_title": "Bread Proofing Basket Manufacturer | Banneton OEM Supplier",
        "meta_desc": "OEM manufacturer of bread proofing baskets, banneton sets, linen liners and "
                     "dough proofing boxes. BSCI &amp; ISO 9001 certified, custom sizes and branding.",
        "lede": "We produce banneton proofing baskets, linen liners, collapsible proofing bowls and "
                "stackable dough proofing boxes - the baker's-tool side of a sourdough programme.",
        "intro": [
            "Proofing baskets are sold in sets far more often than individually: a basket with its "
            "cloth liner and often a scraper, lame, whisk or dough whisk alongside it. Our tooling "
            "covers the round and oval shapes, the coiled rattan look and the collapsible silicone "
            "or plastic bowls that fold flat for shipping - whichever the retail price point calls for.",
            "For brands that sell a dough proofing box rather than a basket, we make airtight-lid "
            "containers in food-grade silicone and BPA-free plastic, sized to standard pizza and "
            "loaf doughs and stackable for retail shelving.",
        ],
        "match": ["proofing basket", "banneton", "proofing bowl", "proofing box",
                  "proofing container", "dough basket", "bread basket"],
        "words": "top inquiry words: bread proofing box",
        "bullets": [
            "Round, oval and extra-large banneton baskets with cloth liners",
            "Collapsible silicone and plastic proofing bowls that ship flat",
            "Airtight-lid dough proofing boxes, stackable and freezer safe",
            "Optional add-ons: dough whisk, scraper, bread lame, brotform cloth",
            "Retail-ready cartons, printed sleeves and colour-matched sets",
        ],
        "faqs": [
            ("Which shapes and sizes can you tool?",
             "Round from 5 in to 10 in, oval, and custom sizes. Send a drawing or a sample and we "
             "will quote tooling and unit price for that exact shape."),
            ("Do you supply the linen liner as well?",
             "Yes - liners are cut and sewn to fit the basket, printed with your logo if you want, "
             "and floured-ready when the buyer opens the box."),
            ("Are the baskets food safe?",
             "They are made from food-contact materials and produced to FDA and LFGB requirements. "
             "Test reports can be issued with the shipment."),
            ("Can we mix several shapes in one order?",
             "Yes. Mixed configurations are normal for our export customers; the quote is built per "
             "shape, then combined into one production and shipping plan."),
        ],
    },
    {
        "slug": "cutting-board-manufacturer",
        "h1": "Cutting Board Manufacturer — Titanium, Stainless Steel &amp; Foldable",
        "meta_title": "Cutting Board Manufacturer | Titanium &amp; Steel OEM Supplier",
        "meta_desc": "OEM/ODM manufacturer of titanium, stainless steel and foldable cutting boards "
                     "for kitchen and outdoor use. Custom sizes, corners, logos and packaging.",
        "lede": "Yongli makes metal cutting boards and cutting mats - pure titanium, stainless steel, "
                "double-sided boards with juice grooves, and foldable boards that double as a sink.",
        "intro": [
            "Metal boards live or die on detail: sheet thickness, edge finishing, the silicone "
            "corners that stop slipping, whether the board is double sided, and if it carries a "
            "juice groove, knife sharpener or garlic grater. We tool and finish these boards "
            "ourselves, which is why the same design can be quoted at two or three thicknesses "
            "for different retail price points.",
            "The foldable version is a different product for a different buyer - camping, caravan "
            "and small-apartment retail - where the board folds into a colander or washing tub. "
            "Both lines are produced to the same food-contact and packaging standard.",
        ],
        "match": ["cutting board", "chopping board", "cutting mat", "chopping mat",
                  "kitchen board", "defrosting tray"],
        "words": "top inquiry words: titanium cutting board, cutting board",
        "bullets": [
            "100% titanium and titanium/stainless double-sided boards",
            "Stainless steel boards with lip, juice groove or mesh finish",
            "Silicone non-slip corners and removable sleeves",
            "Foldable boards that convert into a colander or washing tub",
            "Laser-etched logos, printed sleeves and custom carton sizes",
        ],
        "faqs": [
            ("What thicknesses are available for metal boards?",
             "Several sheet gauges are available from the same tooling, so a heavier premium board "
             "and a lighter value board can be quoted from one design."),
            ("Is a titanium board genuinely antibacterial?",
             "Titanium resists odour and knife scoring better than soft plastics. We describe the "
             "board by its material and finish and can supply the material test reports that apply "
             "to the order - we do not make health claims of our own."),
            ("Can the board carry our brand?",
             "Yes: laser etching or printing on the board, plus printed or debossed logo on the "
             "carton and product sleeve."),
            ("Do you also make the foldable camping boards?",
             "Yes. The collapsible cutting board with colander is one of our long-running lines and "
             "is tooled at several sizes."),
        ],
    },
    {
        "slug": "garlic-press-manufacturer",
        "h1": "Garlic Press Manufacturer &amp; Kitchen Gadget OEM Supplier",
        "meta_title": "Garlic Press Manufacturer | OEM Kitchen Gadget Supplier",
        "meta_desc": "OEM supplier of garlic presses, mincers and graters in stainless steel and "
                     "die-cast zinc. BSCI &amp; ISO 9001 certified factory, custom packaging.",
        "lede": "Garlic presses, mincers, graters, zesters and peelers - the small, high-rotation "
                "kitchen tools we make in die-cast zinc and stainless steel, finished to your retail spec.",
        "intro": [
            "Small tools are ordered in volume and judged on feel, so the metal, the hinge and the "
            "coating decide whether a press survives a year of kitchens. We build presses in "
            "die-cast zinc and stainless steel, with the handle, hole pattern and finish matched to "
            "the price point you are aiming at.",
            "The same tooling family covers the neighbouring items a buyer usually wants in the same "
            "carton: garlic graters, rotary and hand graters, zesters, peelers and ginger tools. "
            "That keeps one order, one inspection, one carton spec.",
        ],
        "match": ["garlic", "grater", "peeler", "zester", "ginger", "masher"],
        "words": "top inquiry words: garlic press",
        "bullets": [
            "Die-cast zinc and stainless steel garlic presses and mincers",
            "Soft-grip or stainless handles, mirror or brushed finishing",
            "Companion tools: graters, zesters, peelers, ginger tools",
            "Retail packaging with printed card, blister or gift box",
            "Rust and finish testing before pre-shipment inspection",
        ],
        "faqs": [
            ("Which material should we choose for a garlic press?",
             "Die-cast zinc gives the solid feel buyers associate with a premium press; stainless "
             "steel suits a dishwasher-led, rust-resistance message. We quote both and you compare."),
            ("Can the press be dishwasher safe?",
             "Yes, the stainless steel and zinc versions are produced to dishwasher-safe finishing. "
             "We confirm the exact specification on the approved sample."),
            ("Do you offer custom colour or coating?",
             "Yes - colour coating matching a Pantone reference, with the sample approved before "
             "the production run."),
            ("What is the pack-out like?",
             "Printed card, blister, colour box or polybag with label, decided with you at quoting "
             "stage so the carton dimensions are agreed early."),
        ],
    },
    {
        "slug": "kitchen-gadgets-manufacturer",
        "h1": "Kitchen Gadgets &amp; Kitchen Accessories Manufacturer",
        "meta_title": "Kitchen Gadgets Manufacturer | Kitchen Accessories OEM",
        "meta_desc": "OEM/ODM manufacturer of kitchen gadgets and accessories - utensils, scissors, "
                     "openers, measuring tools - in silicone, stainless steel and BPA-free plastic.",
        "lede": "Yongli is the factory behind many kitchen gadget programmes: utensil sets, scissors, "
                "can openers, strainers, measuring tools, mixing and prep gadgets.",
        "intro": [
            "Kitchen gadgets are rarely bought one at a time, so the practical question is how many "
            "items one factory can tool and pack together. Ours covers silicone and wooden-handled "
            "utensil sets, stainless steel scissors and shears, can openers, spiral and rotary "
            "graters, measuring cups and spoons, mixing bowls and prep accessories.",
            "That breadth is also the cheapest way to build a private-label range: one colour "
            "system, one logo treatment, one carton language, applied across a dozen SKUs. We keep "
            "the colour and material spec on file so repeat orders match the first shipment.",
        ],
        "match": ["kitchen utensil", "utensil set", "gadget", "scissor", "can opener",
                  "measuring", "spatula", "whisk", "strainer", "peeler set"],
        "words": "top traffic words: kitchen gadgets, kitchen accessories",
        "bullets": [
            "Silicone and wooden-handled utensil sets, spatulas, turners, whisks",
            "Stainless steel scissors, shears, can openers and bottle openers",
            "Prep tools: graters, slicers, mashers, strainers and colanders",
            "Consistent colour and logo system across a multi-SKU range",
            "Food-grade silicone, stainless steel and BPA-free plastics",
        ],
        "faqs": [
            ("Can we build a whole range with one colour system?",
             "Yes - that is the usual shape of a private-label programme. We hold the approved "
             "colour and material spec so every SKU in the range matches."),
            ("How many items can we mix in one order?",
             "As many as you need, within one carton spec. Each item is quoted separately and then "
             "combined into a single production and inspection plan."),
            ("Do you make both silicone and stainless versions of the same gadget?",
             "Often yes. A turner, for example, exists in all-silicone, silicone with a wooden "
             "handle, and stainless with a silicone head - three price points from one product idea."),
            ("Which certifications apply?",
             "The factory is BSCI and ISO 9001 audited; food-contact materials are produced to FDA "
             "and LFGB requirements, with EN71 for children's items and REACH/RoHS where relevant."),
        ],
    },
    {
        "slug": "lunch-box-food-storage-manufacturer",
        "h1": "Lunch Box &amp; Food Storage Manufacturer",
        "meta_title": "Lunch Box Manufacturer | Food Storage Container OEM Supplier",
        "meta_desc": "OEM manufacturer of silicone lunch boxes, collapsible food containers, snack "
                     "boxes and bento sets. BSCI &amp; ISO 9001 certified, custom colours and printing.",
        "lede": "Collapsible silicone lunch boxes, bento sets, snack boxes and food storage "
                "containers - leak-resistant, microwave and dishwasher safe, stackable for retail.",
        "intro": [
            "A lunch box is judged twice: at the till, where the silhouette and colour do the "
            "selling, and at home, where the lid seal and the ability to collapse decide whether "
            "it gets used again. We make the silicone-bodied, telescopic lunch box that folds down "
            "after the meal, and the rigid container with a clip or press lid for buyers who want "
            "a stacked, snap-together set.",
            "Storage containers sold as a family - three or four sizes in one carton - are also a "
            "core line, in food-grade silicone and BPA-free plastic, with printed lids and "
            "colour-coded sizing for shelf impact.",
        ],
        "match": ["lunch box", "lunchbox", "bento", "snack box", "food storage",
                  "storage container", "meal prep"],
        "words": "top traffic words: lunch box",
        "bullets": [
            "Collapsible silicone lunch boxes that fold flat for shipping",
            "Bento-style divided boxes and multi-compartment lunch sets",
            "Snack boxes and trays with lids, handles and compartments",
            "Multi-size food storage container families in one carton",
            "Microwave, freezer and dishwasher safe configurations",
        ],
        "faqs": [
            ("Are the collapsible boxes leak proof?",
             "Leak resistance is a function of the lid and seal design. We quote the seal option "
             "that matches the use case and confirm it on the approved sample."),
            ("Can the whole box be printed with our design?",
             "Yes - lid printing, body printing, or both, plus a printed sleeve or insert card for "
             "the retail carton."),
            ("Do you supply mixed sizes in one order?",
             "Yes, container families are quoted per size and produced together so the carton mix "
             "is exactly what you plan to sell."),
            ("Which materials do you use?",
             "Food-grade silicone and BPA-free plastic, produced to FDA and LFGB requirements, with "
             "test reports available for the order."),
        ],
    },
    {
        "slug": "baby-kids-dining-manufacturer",
        "h1": "Baby &amp; Kids Dining Manufacturer",
        "meta_title": "Baby &amp; Kids Dining Manufacturer | Silicone Feeding OEM",
        "meta_desc": "OEM manufacturer of silicone baby plates, suction bowls, spoons, bibs and "
                     "placemats for kids dining ranges. EN71 and FDA compliant, custom printing.",
        "lede": "Divided plates with suction bases, bowls, spoons and forks, bibs, placemats and "
                "toddler snack cups - the feeding set a kids-dining range is built around.",
        "intro": [
            "Children's tableware is the most demanding thing we mould: the silicone has to be soft "
            "enough not to hurt, firm enough for high-chair suction to hold, and compliant with "
            "EN71 as well as the food-contact rules. We produce divided plates, suction bowls, "
            "spoons and forks, bibs with catch pockets, full-coverage placemats and snack cups.",
            "Sets are usually where the value sits - a plate, bowl, spoon and bib sharing one "
            "colour and one animal or shape motif. We tool the motif into the mould so it prints "
            "in relief rather than being painted on, which is what keeps a children's range "
            "consistent across SKUs and safe through washing.",
        ],
        "match": ["baby", "kids", "toddler", "infant", "children", "bib", "suction plate",
                  "feeding set", "spoon and fork", "divided plate", "placemat"],
        "words": "top traffic words: baby",
        "bullets": [
            "Divided plates and bowls with high-chair suction bases",
            "Soft-tip spoons, forks and toddler training cutlery",
            "Bibs with catch pockets; full-coverage silicone placemats",
            "Snack cups and toddler snack containers with spill-proof lids",
            "EN71 and FDA compliant materials, third-party test reports",
        ],
        "faqs": [
            ("Which safety standards apply to children's tableware?",
             "EN71 for toy-safety aspects plus FDA and LFGB for food contact. Test reports are "
             "issued against the specific order."),
            ("Can we have our own character or shape?",
             "Yes. Shapes and motifs are tooled into the mould, so they survive washing. Send the "
             "artwork and we will confirm tooling cost and sample timing."),
            ("Do you make the stainless steel kids plates?",
             "Yes - stainless plate with removable silicone sleeve is one of our listed items."),
            ("Can one order cover a full feeding set?",
             "Yes. Plate, bowl, cutlery, bib and placemat can be quoted as a set and packed in one "
             "retail carton."),
        ],
    },
    {
        "slug": "silicone-bakeware-manufacturer",
        "h1": "Silicone Bakeware &amp; Mould Manufacturer",
        "meta_title": "Silicone Bakeware Manufacturer | Custom Silicone Mould OEM",
        "meta_desc": "OEM/ODM manufacturer of silicone bakeware, cake pans, moulds, mats and ice "
                     "trays. In-house tooling, Pantone colour matching, FDA and LFGB materials.",
        "lede": "Silicone cake pans, baking mats, moulds, ice cube trays and baking accessories, "
                "tooled in house so custom shapes and logo embossing are part of the design.",
        "intro": [
            "Silicone moulds are where tooling decides everything: wall thickness controls how the "
            "cake releases, the base needs to hold its shape empty, and the embossed logo has to "
            "read after demoulding. We run our own tool shop, so a custom cavity, a name embossed "
            "in the base or a proprietary shape is a tooling job rather than a compromise.",
            "Alongside the mould itself we make the bakeware accessories that get sold with it: "
            "baking mats and liners, air fryer liners, freezer and soup-cube trays, chocolate and "
            "candy moulds, ice cube trays and reusable ice accessories.",
        ],
        "match": ["silicone mold", "silicone mould", "cake pan", "baking mat", "bakeware",
                  "ice tray", "ice cube", "freezer", "gummy", "chocolate", "muffin", "baking"],
        "words": "store main product line: Silicone Mold",
        "bullets": [
            "Custom cavities, embossed logos and proprietary shapes from in-house tooling",
            "Cake pans, muffin and loaf moulds, candy and chocolate moulds",
            "Silicone baking mats, oven liners and air fryer liners",
            "Ice cube trays, freezer trays and soup-cube moulds",
            "Pantone colour matching and food-grade hardness options",
        ],
        "faqs": [
            ("Can you tool a completely new mould shape?",
             "Yes - that is the standard ODM route. Send a drawing, a 3D file or even a sketch, and "
             "we quote tooling plus unit price, then produce a sample from the new mould."),
            ("How is the logo applied to a silicone mould?",
             "It is embossed or debossed in the mould so it is part of the part itself, not a print "
             "that can wash off."),
            ("Which silicone hardness should we specify?",
             "It depends on the item: release-heavy bakeware and grippy mats want different "
             "shore hardness. We propose a value and you confirm it on the sample."),
            ("Are the materials certified?",
             "Food-grade silicone produced to FDA and LFGB requirements, with REACH and RoHS "
             "documentation where relevant to the order."),
        ],
    },
    {
        "slug": "coffee-tea-accessories-manufacturer",
        "h1": "Coffee &amp; Tea Accessories Manufacturer",
        "meta_title": "Coffee &amp; Tea Accessories Manufacturer | OEM Supplier",
        "meta_desc": "OEM manufacturer of milk frothers, tea infusers, pour-over and matcha sets and "
                     "coffee accessories. CE and RoHS compliant electronics where needed.",
        "lede": "Milk frothers, tea infusers, pour-over drippers, matcha sets and coffee tools - "
                "from a simple stainless ball infuser to an electric frother with CE/RoHS paperwork.",
        "intro": [
            "Coffee and tea accessories split into two production worlds: the purely mechanical "
            "items - infusers, drippers, strainers, measuring scoops, stands - and the electrical "
            "ones such as milk frothers, where CE and RoHS compliance and battery or mains "
            "configuration become part of the brief.",
            "We produce both, which means a coffee programme can be quoted as one order: the "
            "frother as the hero SKU, the infuser, scoop and stand as the accessory items sharing "
            "its colour and finish, all packed under one retail design.",
        ],
        "match": ["coffee", "tea", "matcha", "milk frother", "frother", "pour over",
                  "pour-over", "infuser", "espresso", "cup"],
        "words": "store main product line: Coffee & Tea Accessories",
        "bullets": [
            "Electric and battery milk frothers with CE/RoHS compliance",
            "Stainless steel tea infusers, strainers and filter baskets",
            "Pour-over drippers, stands and measuring scoops",
            "Matcha sets with bowl, whisk, scoop and sifter",
            "Custom finishes, logo printing and gift-box assembly",
        ],
        "faqs": [
            ("Can you supply the electrical certification?",
             "Electrical items are produced to CE and RoHS requirements with the paperwork that "
             "applies to the destination market confirmed before production."),
            ("Is the frother available with our own branding?",
             "Yes - logo printing on the body and stand, plus printed packaging and manuals under "
             "your brand."),
            ("Do you supply mechanical accessories only?",
             "Yes. Infusers, drippers, strainers and scoops are quoted on their own; many buyers "
             "start there before adding an electrical SKU."),
            ("Can the accessory items match the frother finish?",
             "Yes, that is the point of quoting the range together: one colour and finish system "
             "across the hero product and its accessories."),
        ],
    },
    {
        "slug": "collapsible-foldable-storage-manufacturer",
        "h1": "Collapsible &amp; Foldable Storage Manufacturer",
        "meta_title": "Collapsible Storage Manufacturer | Foldable Container OEM",
        "meta_desc": "OEM manufacturer of collapsible silicone food storage, foldable bowls, "
                     "collapsible cups and space-saving kitchen storage. Custom colours and branding.",
        "lede": "Collapsible food containers, folding bowls and colanders, telescopic cups and "
                "space-saving kitchen storage - products designed around the shipping volume they save.",
        "intro": [
            "Collapsible goods are a logistics decision as much as a product one: a bowl that folds "
            "flat ships in a fraction of the carton, which changes the landed cost of an entire "
            "container load. We mould the silicone body and the rigid rim separately and assemble "
            "them so the fold line keeps its memory through repeated use.",
            "The family covers food storage containers and lunch boxes, folding bowls and "
            "colanders, collapsible travel and camping cups, folding cutting boards that turn into "
            "a tub, and drawer and cabinet organisers for the storage side of the same retailer.",
        ],
        "match": ["collapsible", "foldable", "folding", "telescopic", "space saving",
                  "organizer", "organiser", "storage"],
        "words": "store main product line: Foldable Storage",
        "bullets": [
            "Collapsible food storage containers and lunch boxes",
            "Folding bowls, colanders and dish tubs",
            "Telescopic travel, camping and drinking cups",
            "Folding cutting boards with colander function",
            "Drawer, cabinet and utensil organisers in the same colour system",
        ],
        "faqs": [
            ("How much shipping volume does a collapsible design save?",
             "It depends on the fold ratio of the specific item. We give the flat-packed carton "
             "dimensions at quoting stage so you can compare landed cost directly."),
            ("Does the fold line stay strong after many uses?",
             "The body is moulded for a long fold life and the rim is a separate rigid part. We "
             "confirm fold performance on the approved sample."),
            ("Can you supply the whole storage range in one order?",
             "Yes - containers, bowls, cups and organisers are quoted item by item and produced "
             "together under one colour and packaging spec."),
            ("Are these items food safe?",
             "Food-contact parts are food-grade silicone and BPA-free plastic, produced to FDA and "
             "LFGB requirements."),
        ],
    },
    {
        "slug": "mats-pads-and-placemats-manufacturer",
        "h1": "Silicone Mats, Pads &amp; Placemats Manufacturer",
        "meta_title": "Silicone Mat &amp; Placemat Manufacturer | Mats and Pads OEM",
        "meta_desc": "OEM manufacturer of silicone placemats, table mats, drying mats, baking mats "
                     "and high-chair mats. Custom sizes, printed surfaces and Pantone colour matching.",
        "lede": "Silicone placemats, table mats, drying mats and high-chair mats - flat goods where "
                "the printed surface, edge finish and thickness carry the whole design.",
        "intro": [
            "Mats are the simplest silicone product to make and the hardest to make well: the edge "
            "has to stay flat after washing, the printed decoration has to survive heat, and the "
            "thickness has to feel deliberate rather than thin. We mould them in house and control "
            "all three, from a plain table mat to a full-coverage high-chair mat with a printed "
            "pattern.",
            "The neighbouring lines are the ones retailers usually order with them: dish drying "
            "mats in absorbent diatomaceous stone, baking and oven mats, fridge and drawer liners, "
            "and coaster sets in matching colours.",
        ],
        "match": ["mat", "mats", "placemat", "coaster", "pad", "liner"],
        "words": "store main product line: Mats & Pads",
        "bullets": [
            "Silicone table mats, placemats and high-chair mats",
            "Dish drying mats, including absorbent stone mats",
            "Baking mats, oven liners and grilling mats",
            "Coaster sets and drawer/fridge liners in matching colours",
            "Printed decoration, debossed logos and Pantone colour matching",
        ],
        "faqs": [
            ("Will the printed pattern survive washing?",
             "Decoration is applied so it withstands normal washing and heat. The exact method is "
             "confirmed on the sample for your intended use."),
            ("Can you make an odd size for our table?",
             "Yes, mats are cut from moulds we tool ourselves, so a non-standard size is a tooling "
             "job rather than a limitation."),
            ("What thicknesses are available?",
             "Several, from thin placemat stock to thicker high-chair mats. We recommend one for "
             "the use case and you approve it on the sample."),
            ("Do you supply them with retail packaging?",
             "Yes - printed sleeve, hang tag, roll or flat pack, agreed during quoting."),
        ],
    },
    {
        "slug": "bbq-grill-accessories-manufacturer",
        "h1": "BBQ &amp; Grill Accessories Manufacturer",
        "meta_title": "BBQ Accessories Manufacturer | Grill Tools OEM Supplier",
        "meta_desc": "OEM manufacturer of BBQ grill tool sets, basting brushes, spatulas, gloves and "
                     "prep tubs. Stainless steel and heat-resistant silicone, custom branded sets.",
        "lede": "BBQ tool sets, spatulas, tongs, basting brushes, heat-resistant gloves and prep tubs "
                "- grill accessories usually sold as a boxed set, which is how we make them.",
        "intro": [
            "Grill accessories sell as a gift-ready set far more often than as loose tools, so the "
            "set logic - how many pieces, which ones, and how they stack in the case - is part of "
            "the brief. We make the stainless steel tools, the heat-resistant silicone heads and "
            "brushes, the gloves and the folding prep tub that doubles as a cutting board.",
            "Because the same factory runs the kitchen tooling, a BBQ set can borrow handles, "
            "finishes and colourways already in production, which shortens tooling time and keeps "
            "a spring/summer range consistent with the rest of the catalogue.",
        ],
        "match": ["bbq", "barbecue", "grill", "smoker", "basting", "tongs",
                  "grill press", "burger press"],
        "words": "store window category: BBQ",
        "bullets": [
            "Multi-piece BBQ tool sets in case or boxed packaging",
            "Heat-resistant silicone heads with stainless or wooden handles",
            "Basting brushes, tongs, spatulas, forks and grill presses",
            "Heat-resistant gloves, mats and smoker accessories",
            "Folding prep tubs and collapsible boards for grill-side prep",
        ],
        "faqs": [
            ("Can we choose the exact set contents?",
             "Yes. Tell us the piece count and which tools, and we build the set, its case and its "
             "carton around that composition."),
            ("How heat resistant are the silicone parts?",
             "Heat resistance depends on the grade specified for the item. We propose a grade for "
             "the intended grill use and confirm it on the sample."),
            ("Do you produce the seasonal volumes in time?",
             "Spring and summer ranges are planned with the production and shipping calendar in "
             "advance - share your in-store date and we build the schedule backwards from it."),
            ("Is gift packaging possible?",
             "Yes - printed carry case, colour box or insert card, which is the usual format for "
             "boxed grill sets."),
        ],
    },
]


def load_products():
    """Every (catalogue, page, section, name, code) row the search index knows."""
    idx = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
    rows, seen = [], set()
    for entry in idx["entries"]:
        cid, pn, section = entry.get("id"), entry.get("pn"), entry.get("section") or ""
        for name, code in entry.get("items") or []:
            name = re.sub(r"\s+", " ", (name or "")).strip()
            code = (code or "").upper().replace(" ", "")
            if not code or not name or len(name) < 8 or code in seen:
                continue
            if sum(ch.isalpha() for ch in name) < 6:
                continue
            seen.add(code)
            rows.append({"cid": cid, "pn": pn, "section": section,
                         "name": name, "code": code})
    return rows


def esc_amp(url):
    """Attribute-safe for & in query strings."""
    return url.replace("&", "&amp;")


def clip(s, n):
    """Trim to n chars on a word boundary - titles/descriptions have hard budgets."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return (cut[:cut.rfind(" ")].rstrip(" ,;:-") or cut).strip()


def product_title(name, code, budget=64):
    """Keep the item code in the title when it fits, drop it when it does not.

    Codes are for the buyer matching a PDF line, not something anyone searches,
    so the name and the OEM wording win the character budget."""
    full = "%s | %s OEM Manufacturer" % (name, code)
    if len(full) <= budget:
        return full
    return "%s | OEM Manufacturer" % clip(name, budget - len(" | OEM Manufacturer"))


CAT_BY_ID = {c["id"]: c for c in CATS}
# Every page this script writes carries this marker, so a later run can safely
# delete only its own stale output and never a page written by gen_pages.py.
MARK = "<!-- gen_seo_pages.py -->"
HEAD = MARK + """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Yongli Kitchenware">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{ld}
</script>
<style>{css}</style>
</head>
<body>
<header class="topbar">
  <a class="logo" href="/"><img src="/assets/logo.png" alt="Yongli — silicone kitchenware manufacturer"></a>
  <nav>
    <a href="/">3D Catalog</a>
    <a href="/catalog/">Categories</a>
    <a href="/guides/">Buyer Guides</a>
    <a href="/product/">All Products</a>
    <a class="wa" href="https://wa.me/8613824296558" target="_blank" rel="noopener">WhatsApp</a>
  </nav>
</header>
<main class="wrap">
"""

FOOT = """</main>
<footer class="foot">&copy; 2026 Huizhou Yongli Industrial Co., Ltd. All rights reserved.
<a href="/">3D catalog</a> &middot; <a href="/catalog/">categories</a> &middot;
<a href="/guides/">buyer guides</a> &middot; <a href="/product/">all products</a> &middot;
Sourcing and OEM enquiries: info@yonglicc.com</footer>
</body>
</html>
"""

EXTRA_CSS = """
.facts { width: 100%; border-collapse: collapse; font-size: .9rem; }
.facts th { text-align: left; font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: #a0a0a0; font-weight: 600; padding: 0 12px 8px 0; border-bottom: 1px solid #eee; width: 34%; }
.facts td { padding: 9px 0; border-bottom: 1px solid #f4f4f4; color: #333; }
.facts tr:last-child th, .facts tr:last-child td { border-bottom: 0; }
/* FAQ is collapsed by default: a buyer scanning seven answers should see seven
   questions, not a wall of paragraphs. The text stays in the DOM for indexing. */
.faq { margin-top: 2px; border-top: 1px solid #f0ede7; }
.faq details { border-bottom: 1px solid #f0ede7; }
.faq summary { cursor: pointer; list-style: none; position: relative; padding: 15px 30px 15px 0;
               font-weight: 600; color: #1a1a2e; font-size: .96rem; line-height: 1.5; }
.faq summary::-webkit-details-marker { display: none; }
.faq summary:hover { color: #8a6d2f; }
.faq summary::after { content: '+'; position: absolute; right: 2px; top: 13px; color: #a08b5f;
                      font-size: 1.2rem; font-weight: 400; line-height: 1; }
.faq details[open] summary::after { content: '\\2013'; }
.faq dd { color: #555; font-size: .95rem; line-height: 1.8; padding: 0 30px 16px 0; }
/* Guide pages: a hero with the guide's own product shot, a measured column of
   prose, then the range as photo cards. A catalogue page no longer reaches the
   full 1040 px text width - long lines were the main readability complaint. */
.g-eyebrow { font-size: .73rem; text-transform: uppercase; letter-spacing: .11em; color: #a08b5f;
             font-weight: 700; margin-bottom: 8px; }
/* these note lines were running ~120 characters across the full column, which
   is the one place the prose was still hard to read */
.block-sub, .kw-note { max-width: 74ch; }
.g-hero { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr); gap: 34px;
          align-items: start; margin: 2px 0 32px; }
.g-hero .lede { margin-bottom: 18px; }
.g-copy { max-width: 72ch; }
.g-copy p { color: #4a4a4a; font-size: 1.01rem; line-height: 1.85; margin-bottom: 16px; }
.g-copy p.lead { font-size: 1.1rem; line-height: 1.8; color: #333; }
.g-shot { margin: 0; border: 1px solid #eee; border-radius: 14px; background: #faf9f7; overflow: hidden; }
.g-shot img { width: 100%; height: auto; display: block; }
.g-shot figcaption { padding: 12px 14px; font-size: .8rem; color: #8b8577; line-height: 1.55;
                     border-top: 1px solid #f0ede7; }
.g-shot figcaption b { display: block; color: #1a1a2e; font-size: .85rem;
                       font-variant-numeric: tabular-nums; margin-bottom: 2px; }
/* The range listing: photo over text, six across. It replaced both the old
   five-column table and a separate preview strip of 8 cards - the strip was a
   near-identical photo wall sitting a few hundred pixels above this one, and
   this listing already carries the page link the strip existed for. */
.item-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 18px 14px; }
.item { display: flex; flex-direction: column; border: 1px solid #f0ede7; border-radius: 12px;
        background: #fff; overflow: hidden; transition: border-color .15s, box-shadow .15s,
        transform .15s; }
.item:hover { border-color: #d9cfb9; box-shadow: 0 9px 22px rgba(0,0,0,.06); transform: translateY(-2px); }
.item .ii { display: block; aspect-ratio: 1 / 1; background: #faf9f7; overflow: hidden; }
.item .ii img { width: 100%; height: 100%; object-fit: contain; display: block; }
.item .it { padding: 9px 11px 11px; }
.item .it b { display: block; font-size: .72rem; letter-spacing: .04em; color: #8a6d2f;
              font-variant-numeric: tabular-nums; }
.item .it .nm { display: block; margin-top: 4px; font-size: .83rem; line-height: 1.35;
                color: #1a1a2e; text-decoration: none; }
.item .it .nm:hover { color: #8a6d2f; text-decoration: underline; text-underline-offset: 2px; }
.item .it i { display: block; margin-top: 7px; font-style: normal; font-size: .71rem; color: #b0a893; }
.item .it i a { color: #8a6d2f; text-decoration: none; }
.item .it i a:hover { text-decoration: underline; text-underline-offset: 2px; }
@media (max-width: 1100px) { .item-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 860px) { .item-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 560px) { .item-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 10px; } }
.prod-table td.thumb { width: 52px; padding: 8px 10px 8px 0; }
.prod-table td.thumb img { width: 46px; height: 46px; object-fit: contain; border-radius: 8px;
                           background: #faf9f7; display: block; }
.prod-table tbody tr:nth-child(even) { background: #fcfbf8; }
.prod-table td.pg a { display: inline-block; border: 1px solid #e8e2d4; border-radius: 20px;
                      padding: 3px 11px; font-size: .75rem; color: #8a6d2f; text-decoration: none; }
.prod-table td.pg a:hover { border-color: #8a6d2f; text-decoration: none; }
/* display:block matters: as an inline span the aspect-ratio is ignored, the
   img then resolves height:100% against the whole card, and every card gets a
   half-empty letterbox. */
.hub-card .thumb { display: block; aspect-ratio: 4 / 3; background: #faf9f7; overflow: hidden;
                   border-radius: 9px; margin-bottom: 14px; }
.hub-card .thumb img { width: 100%; height: 100%; object-fit: contain; display: block; }
a.hub-card { display: flex; flex-direction: column; text-decoration: none; color: inherit;
             transition: border-color .15s, box-shadow .15s, transform .15s; }
a.hub-card:hover { border-color: #d9cfb9; box-shadow: 0 9px 22px rgba(0,0,0,.06); transform: translateY(-2px); }
.hub-card .more { display: inline-block; margin-top: 10px; color: #8a6d2f; font-size: .83rem;
                  font-weight: 600; }
.pill { display: inline-block; border: 1px solid #e2d9c4; background: #fdfaf2; color: #8a6d2f;
        border-radius: 20px; padding: 4px 12px; font-size: .75rem; margin: 0 6px 6px 0; }
.prod-table { width: 100%; border-collapse: collapse; font-size: .89rem; }
.prod-table th { text-align: left; font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: #a0a0a0; font-weight: 600; padding: 0 12px 8px 0; border-bottom: 1px solid #eee; }
.prod-table td { padding: 9px 12px 9px 0; border-bottom: 1px solid #f4f4f4; color: #333; vertical-align: top; }
.prod-table td.code { white-space: nowrap; color: #8a6d2f; font-weight: 700; }
.prod-table a { text-decoration: none; }
.prod-table a:hover { text-decoration: underline; text-underline-offset: 3px; }
.kw-note { font-size: .78rem; color: #b0a893; margin-top: 10px; }
.hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;
            align-items: start; }
.hub-card { border: 1px solid #eee; border-radius: 12px; padding: 18px 18px 16px; background: #fff; }
.hub-card h3 { font-size: 1rem; color: #1a1a2e; margin-bottom: 6px; }
.hub-card p { font-size: .85rem; color: #777; line-height: 1.6; }
.hub-card a { text-decoration: none; color: #8a6d2f; font-size: .83rem; font-weight: 600; }
@media (max-width: 860px) {
  .g-hero { grid-template-columns: 1fr; gap: 22px; }
  .g-hero .g-shot { max-width: 420px; }
}
@media (max-width: 700px) {
  .facts th, .prod-table td.code { white-space: normal; }

  /* the item table becomes one card per item: a five-column table on a phone
     is unreadable, and the columns are exactly the facts a buyer wants stacked */
  .prod-table thead, .prod-table tr:first-child th { display: none; }
  .prod-table, .prod-table tbody, .prod-table tr, .prod-table td { display: block; width: 100%; }
  /* :has() keeps this to tables that really carry a thumbnail column, so a
     plain list is never squeezed into the 46 px first column */
  .prod-table tr:has(td.thumb) { display: grid; grid-template-columns: 46px minmax(0, 1fr);
                                 column-gap: 12px; padding: 12px 0;
                                 border-bottom: 1px solid #f0ede7; }
  .prod-table tbody tr:nth-child(even) { background: none; }
  .prod-table td { border: 0; padding: 0; }
  .prod-table td.thumb { grid-row: 1 / span 4; width: auto; padding: 0; }
  .prod-table td.code { margin-top: 3px; }
  .prod-table td.pg { margin-top: 7px; }
}
"""


def css():
    return TEMPLATE_CSS + EXTRA_CSS


SHOTS_INDEX = ROOT / "assets" / "guide-images" / "index.json"


def load_shots():
    """Which item codes have a cut-out product photo (see gen_guide_images.py).

    Returns {} when the images have not been generated, and then every page
    simply renders without pictures instead of pointing at missing files.
    """
    if not SHOTS_INDEX.exists():
        return {}
    try:
        return json.loads(SHOTS_INDEX.read_text(encoding="utf-8")).get("codes", {})
    except Exception:
        return {}


def shot_img(code, shots, size="big", **attrs):
    """<img> for an item code, or '' when that code has no photo."""
    if code not in shots:
        return ""
    src = "/assets/guide-images/%s%s.webp" % ("t/" if size == "thumb" else "", code)
    extra = "".join(' %s="%s"' % (k.rstrip("_"), esc(v)) for k, v in attrs.items())
    return '<img src="%s"%s>' % (src, extra)


def shot_figure(code, shots, caption=None):
    """The hero/lead figure for one item: photo plus its printed code."""
    if code not in shots:
        return ""
    m = shots[code]
    cat = CAT_BY_ID.get(m["c"])
    src_name = cat["name"] if cat else m["c"]
    cap = caption or m["n"]
    return ('<figure class="g-shot">%s<figcaption><b>%s</b>%s &middot; %s, p.%d</figcaption>'
            '</figure>' % (shot_img(code, shots, alt=cap), esc(code), esc(cap),
                           esc(src_name), m["p"]))


def section_dir_url(cid, section):
    """URL of the generated section page, if this catalogue has one."""
    if not section:
        return "/catalog/%s/" % cid
    slug = slugify(section)
    if (ROOT / "catalog" / cid / slug / "index.html").exists():
        return "/catalog/%s/%s/" % (cid, slug)
    return "/catalog/%s/" % cid


def guide_matches(products, guide, limit=40):
    """Products whose name looks like it belongs to this guide's cluster."""
    terms = guide["match"]
    hits = []
    for p in products:
        low = p["name"].lower()
        if any(t in low for t in terms):
            hits.append(p)
    return hits[:limit]


def hero_code(guide, products, shots):
    """The item whose photo leads this guide.

    The first `match` term is the guide's own subject, so an item whose name
    carries it is more representative than whatever happens to come first in
    the catalogue; the shortest such name is the plainest example of it.
    """
    with_shot = [p for p in products if p["code"] in shots]
    if not with_shot:
        return None
    key = guide["match"][0].lower()
    named = [p for p in with_shot if key in p["name"].lower()]
    pool = named or with_shot
    # A name that ends in the term is the thing itself; a name that continues
    # past it is an accessory ("Cutting Board Rack" is not a cutting board).
    return sorted(pool, key=lambda p: (0 if p["name"].lower().rstrip().endswith(key) else 1,
                                       len(p["name"]), p["code"]))[0]["code"]


def guide_label(g):
    """The short label for a guide: h1 up to its first qualifier."""
    return re.sub("&amp;", "&", g["h1"]).split(" — ")[0].split(" (")[0]


def card_html(g, shots, code=None):
    """One guide as a card, with its lead photo when it has one."""
    thumb = shot_img(code, shots, alt="", loading="lazy")
    # div, not span: an inline box ignores aspect-ratio, and then height:100% on
    # the img resolves against the whole card and letterboxes every photo
    return ('<a class="hub-card" href="/guides/%s/">'
            '%s<h3>%s</h3><p>%s</p><span class="more">Read the guide &rarr;</span></a>'
            % (g["slug"],
               '<div class="thumb">%s</div>' % thumb if thumb else "",
               esc(guide_label(g)), esc(re.sub("&amp;", "&", g["meta_desc"]))))


def crumbs(items):
    """items: list of (label, href or None)."""
    out = []
    for label, href in items:
        out.append('<a href="%s">%s</a>' % (esc_amp(href), esc(label)) if href
                   else "<span>%s</span>" % esc(label))
    return '<nav class="crumbs" aria-label="Breadcrumb">%s</nav>' % " &rarr; ".join(out)


def cta_row(subject, wa_text):
    return ("<div class=\"cta-row\">"
            '<a class="cta primary" href="mailto:info@yonglicc.com?subject=%s">'
            'Email a Quote Request</a>'
            '<a class="cta whatsapp" href="https://wa.me/8613824296558?text=%s" '
            'target="_blank" rel="noopener">WhatsApp Us</a>'
            "</div>") % (esc(subject), esc(wa_text))


def chip_row():
    return ('<div class="chips">%s</div>'
            % "".join('<span class="chip">%s</span>' % esc(c) for c in CERT_CHIPS))


# --------------------------------------------------------------------------- #
# Guide pages
# --------------------------------------------------------------------------- #
def guide_html(guide, products, all_guides, have_product, shots=None, hero_of=None):
    shots = shots if shots is not None else {}
    hero_of = hero_of or {}
    url = "%s/guides/%s/" % (SITE, guide["slug"])
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Buyer Guides",
                     "item": SITE + "/guides/"},
                    {"@type": "ListItem", "position": 3, "name": re.sub("&amp;", "&", guide["h1"]),
                     "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q,
                     "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in guide["faqs"]
                ],
            },
            {
                "@type": "ItemList",
                "name": "Products in this range",
                "numberOfItems": len(products),
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "name": p["name"],
                     "url": "%s/product/%s/" % (SITE, p["code"]) if have_product(p["code"]) else
                            SITE + section_dir_url(p["cid"], p["section"])}
                    for i, p in enumerate(products)
                ],
            },
        ],
    }
    # One card per item, photo over text. A five-column table made the buyer
    # read the range as data; the same content as pictures is scanned.
    cards = []
    for p in products:
        link = "/product/%s/" % p["code"] if have_product(p["code"]) else section_dir_url(p["cid"], p["section"])
        cat_name = CAT_BY_ID[p["cid"]]["name"] if p["cid"] in CAT_BY_ID else p["cid"]
        cards.append(
            '<div class="item"><a class="ii" href="%s">%s</a>'
            '<div class="it"><b>%s</b><a class="nm" href="%s">%s</a>'
            '<i>%s &middot; <a href="/?catalog=%s&amp;page=%d">p.%d</a></i></div></div>'
            % (link, shot_img(p["code"], shots, alt=p["name"], loading="lazy"),
               esc(p["code"]), link, esc(p["name"]), esc(cat_name),
               p["cid"], p["pn"], p["pn"]))
    prod_block = ""
    if cards:
        prod_block = """
  <section class="block">
    <h2>%s items in our catalogues</h2>
    <p class="block-sub">Every item below is printed in a Yongli catalogue, with the photo we shoot
    of it. Open an item for the code and the range, or use the page number to jump straight into
    the flip-book.</p>
    <div class="item-grid">
      %s
    </div>
    <p class="kw-note">%s</p>
  </section>""" % (esc(re.sub("&amp;", "&", guide["h1"]).split(" Manufacturer")[0]),
                   "".join(cards), esc(guide.get("words", "")))

    hero = hero_code(guide, products, shots)
    hero_fig = shot_figure(hero, shots) if hero else ""
    faq = "\n".join('<details><summary>%s</summary><dd>%s</dd></details>' % (esc(q), esc(a))
                    for q, a in guide["faqs"])
    related = "\n".join(card_html(g, shots, hero_of.get(g["slug"]))
                        for g in all_guides if g["slug"] != guide["slug"])
    intro = "\n".join('<p%s>%s</p>' % (' class="lead"' if i == 0 else "", esc(t))
                      for i, t in enumerate(guide["intro"]))
    bullets = "".join("<li>%s</li>" % esc(b) for b in guide["bullets"])
    caps = "".join("<li>%s</li>" % esc(c) for c in CAPABILITIES)
    wa = "Hi, I would like a quote for %s (%s)." % (
        re.sub("&amp;", "&", guide["h1"]), guide["slug"])

    body = HEAD.format(title=guide["meta_title"], desc=guide["meta_desc"], url=url,
                       image=SITE + "/assets/covers/new2026.jpg",
                       ld=json.dumps(ld, ensure_ascii=False, indent=1), css=css())
    body += crumbs([("Home", "/"), ("Buyer Guides", "/guides/"),
                    (re.sub("&amp;", "&", guide["h1"]), None)])
    # The hero pairs the promise with one of the range's own photos, so the
    # first thing on the page is a product rather than a paragraph.
    hero_open = '<article class="g-hero">' if hero_fig else ""
    hero_txt = ('<div class="g-hero-copy"><p class="g-eyebrow">Buyer guide</p>'
                '<h1>%s</h1>\n<p class="lede">%s</p>\n%s</div>%s'
                % (guide["h1"], esc(guide["lede"]),
                   cta_row("Quote request - " + re.sub("&amp;", "&", guide["h1"]), wa),
                   hero_fig))
    body += hero_open + hero_txt + ("</article>\n" if hero_fig else "\n")
    body += '<div class="g-copy">\n%s\n</div>\n' % intro
    body += '<div class="grid2">\n'
    body += ('  <section class="block"><h2>Customisation &amp; quality</h2><ul class="ticks">%s</ul></section>\n'
             '  <section class="block"><h2>Compliance</h2>%s'
             '<p style="font-size:.88rem;color:#666;margin-top:12px">%s</p></section>\n</div>\n'
             % (caps, chip_row(), esc(BRAND_LINE)))
    body += prod_block
    body += '\n  <section class="block"><h2>Questions buyers ask</h2><div class="faq">%s</div></section>\n' % faq
    body += ('  <section class="block"><h2>More ways to browse</h2>'
             '<p class="block-sub">Every item listed above is printed in one of our catalogues, '
             'with its code and page number on its own page.</p><div class="siblings">'
             '<a class="sibling" href="/product/">All products</a>'
             '<a class="sibling" href="/guides/">All buyer guides</a>'
             '<a class="sibling" href="/catalog/">Catalogue categories</a>'
             '<a class="sibling" href="/#viewCustomize">Customisation process</a>'
             '<a class="sibling" href="/#viewAbout">About the factory</a>'
             '</div></section>\n')
    body += ('  <section class="block"><h2>Other buyer guides</h2><div class="hub-grid">%s</div>'
             '<p class="block-sub" style="margin-top:16px">Or browse '
             '<a href="/product/">every product we print a code for</a> and the '
             '<a href="/catalog/">catalogue category pages</a>.</p></section>\n' % related)
    body += FOOT
    return body


def guides_hub_html(all_guides, shots=None, hero_of=None):
    shots = shots if shots is not None else {}
    hero_of = hero_of or {}
    url = SITE + "/guides/"
    desc = ("Buyer guides for sourcing kitchenware, bakeware, tableware and kids dining from a "
            "BSCI &amp; ISO 9001 certified OEM/ODM manufacturer in Huizhou, China.")
    ld = {"@context": "https://schema.org", "@type": "CollectionPage",
          "name": "Yongli buyer guides", "url": url, "description": re.sub("&amp;", "&", desc)}
    cards = "\n".join(card_html(g, shots, hero_of.get(g["slug"])) for g in all_guides)
    body = HEAD.format(title="Buyer Guides — OEM Kitchenware Sourcing | Yongli",
                       desc=desc, url=url, image=SITE + "/assets/covers/new2026.jpg",
                       ld=json.dumps(ld, ensure_ascii=False, indent=1), css=css())
    body += crumbs([("Home", "/"), ("Buyer Guides", None)])
    body += '<h1>Buyer guides</h1>\n'
    body += ('<p class="lede">Short, practical pages for the ranges we are asked about most - what '
             'we make, what can be customised, which materials and standards apply, and how the '
             'quote works. Written for the buyer, not for search engines.</p>\n')
    body += cta_row("Wholesale quote request", "Hi, I would like a quote for one of your ranges.")
    body += '<section class="block"><h2>All guides</h2><div class="hub-grid">%s</div></section>\n' % cards
    body += ('<section class="block"><h2>Prefer to browse the catalogues?</h2>'
             '<p class="block-sub">Our flip-book catalogues hold the printed range with every product '
             'code: <a href="/catalog/new2026/">2026 New</a>, <a href="/catalog/2023/">2023</a>, '
             '<a href="/catalog/kitchen/">Kitchen Gadgets</a>, <a href="/catalog/baby/">Baby Care</a>, '
             '<a href="/catalog/ladies/">Ladies&rsquo; Appliances</a>, '
             '<a href="/catalog/balls/">Christmas Balls</a>. You can also open the '
             '<a href="/product/">full product list</a>.</p></section>\n')
    body += FOOT
    return body


# --------------------------------------------------------------------------- #
# Product pages
# --------------------------------------------------------------------------- #
def product_html(p, have_product, siblings, shots=None):
    shots = shots if shots is not None else {}
    cat = CAT_BY_ID.get(p["cid"])
    cat_name = cat["name"] if cat else p["cid"]
    url = "%s/product/%s/" % (SITE, p["code"])
    sec_url = section_dir_url(p["cid"], p["section"])
    title = product_title(p["name"], p["code"])
    desc = ("%s (item %s) from Yongli's %s range. BSCI & ISO 9001 certified OEM/ODM manufacturer of "
            "%s - custom moulds, colours, logo and packaging." %
            (p["name"], p["code"], cat_name, (cat or {}).get("materials", "food-grade products")))
    desc = desc[:158]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Categories", "item": SITE + "/catalog/"},
                    {"@type": "ListItem", "position": 3, "name": cat_name, "item": SITE + "/catalog/%s/" % p["cid"]},
                    {"@type": "ListItem", "position": 4, "name": p["name"], "item": url},
                ],
            },
            {
                "@type": "Product",
                "name": p["name"],
                "sku": p["code"],
                "mpn": p["code"],
                "url": url,
                "description": "%s, catalogue item %s in Yongli's %s range." %
                               (p["name"], p["code"], cat_name),
                "category": p["section"] or cat_name,
                "brand": {"@type": "Brand", "name": "Yongli"},
                "manufacturer": {"@type": "Organization", "name": "Huizhou Yongli Industrial Co., Ltd.",
                                 "url": SITE + "/"},
                "additionalProperty": [
                    {"@type": "PropertyValue", "name": "Catalogue", "value": cat_name},
                    {"@type": "PropertyValue", "name": "Range", "value": p["section"] or cat_name},
                    {"@type": "PropertyValue", "name": "Catalogue page", "value": "p.%d" % p["pn"]},
                ],
            },
        ],
    }
    wa = "Hi, I would like a quote for %s (%s)." % (p["name"], p["code"])
    body = HEAD.format(title=esc(title), desc=esc(desc), url=url,
                       image=SITE + "/assets/covers/%s.jpg" % p["cid"],
                       ld=json.dumps(ld, ensure_ascii=False, indent=1), css=css())
    body += crumbs([("Home", "/"), ("Categories", "/catalog/"), (cat_name, "/catalog/%s/" % p["cid"]),
                    (p["name"], None)])
    top = '<p class="g-eyebrow">Catalogue item %s</p><h1>%s</h1>\n' % (esc(p["code"]), esc(p["name"]))
    top += ('<p class="lede">%s is catalogue item <strong>%s</strong> in the %s range, printed on '
            'page %d of the %s catalogue. Yongli is a BSCI &amp; ISO 9001 certified OEM/ODM '
            'manufacturer in Huizhou, China, producing for private-label and wholesale programmes '
            'since 2010.</p>\n' % (esc(p["name"]), esc(p["code"]), esc(p["section"] or cat_name),
                                    p["pn"], esc(cat_name)))
    top += cta_row("Quote request - %s %s" % (p["code"], p["name"])[:120], wa)
    fig = shot_figure(p["code"], shots, caption=p["name"])
    body += ('<article class="g-hero"><div class="g-hero-copy">%s</div>%s</article>\n' % (top, fig)
             if fig else top)
    body += """
  <div class="stat-strip">
    <div class="stat"><span class="k">Product code</span><span class="v">%s</span></div>
    <div class="stat"><span class="k">Catalogue</span><span class="v sm">%s</span></div>
    <div class="stat"><span class="k">Range</span><span class="v sm">%s</span></div>
    <div class="stat"><span class="k">Catalogue page</span><span class="v"><a href="/?catalog=%s&amp;page=%d">p.%d</a></span></div>
  </div>
""" % (esc(p["code"]), esc(cat_name), esc(p["section"] or cat_name), p["cid"], p["pn"], p["pn"])
    body += """
  <div class="grid2">
    <section class="block"><h2>At a glance</h2>
      <table class="facts">
        <tr><th>Item code</th><td>%s</td></tr>
        <tr><th>Catalogue</th><td><a href="/catalog/%s/">%s</a></td></tr>
        <tr><th>Range</th><td><a href="%s">%s</a></td></tr>
        <tr><th>Materials</th><td>%s</td></tr>
        <tr><th>Customisation</th><td>Mould design, Pantone colour matching, logo printing, custom packaging</td></tr>
        <tr><th>Minimum order</th><td>Quoted per item - send your target quantity</td></tr>
      </table>
    </section>
    <section class="block"><h2>What we can do on this item</h2><ul class="ticks">%s</ul></section>
  </div>
  <section class="block"><h2>Compliance</h2>%s
    <p style="font-size:.88rem;color:#666;margin-top:12px">%s</p></section>
""" % (esc(p["code"]), p["cid"], esc(cat_name), sec_url,
       esc(p["section"] or cat_name), esc((cat or {}).get("materials", "Food-grade materials")),
       "".join("<li>%s</li>" % esc(c) for c in CAPABILITIES), chip_row(), esc(BRAND_LINE))
    if siblings:
        items = "".join(
            '<div class="range-link"><a href="/product/%s/" style="flex:1;text-decoration:none;'
            'color:#1a1a2e">%s</a><span class="pg">%s</span></div>'
            % (s["code"], esc(s["name"]), esc(s["code"])) for s in siblings)
        body += ('  <section class="block"><h2>More items in %s</h2>'
                 '<p class="block-sub">Same range, same materials and compliance route.</p>'
                 '<div class="range-grid">%s</div></section>\n'
                 % (esc(p["section"] or cat_name), items))
    body += ('  <section class="block"><h2>Keep browsing</h2><div class="siblings">'
             '<a class="sibling" href="/product/">All products</a>'
             '<a class="sibling" href="/guides/">Buyer guides</a>'
             '<a class="sibling" href="/catalog/">Categories</a>'
             '<a class="sibling" href="/catalog/%s/">%s catalogue</a>'
             '<a class="sibling" href="%s">%s range</a>'
             '</div></section>\n'
             % (p["cid"], esc(cat_name), sec_url, esc(p["section"] or cat_name)))
    body += FOOT
    return body


def product_index_html(rows, all_guides, shots=None):
    shots = shots if shots is not None else {}
    url = SITE + "/product/"
    desc = ("Every product Yongli prints a code for, across the 2026, 2023, kitchen, baby, "
            "personal care and festive catalogues - with the catalogue page for each item.")
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": "Yongli product index", "url": url, "numberOfItems": len(rows),
          "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "name": r["name"],
               "url": "%s/product/%s/" % (SITE, r["code"])}
              for i, r in enumerate(rows[:200])]}
    tb = "".join(
        '<tr><td class="thumb">%s</td><td><a href="/product/%s/">%s</a></td>'
        '<td class="code">%s</td><td>%s</td>'
        '<td class="pg"><a href="/?catalog=%s&amp;page=%d">p.%d</a></td></tr>'
        % (shot_img(r["code"], shots, size="thumb", alt=r["name"], loading="lazy"),
           r["code"], esc(r["name"]), esc(r["code"]),
           esc(CAT_BY_ID[r["cid"]]["name"] if r["cid"] in CAT_BY_ID else r["cid"]),
           r["cid"], r["pn"], r["pn"]) for r in rows)
    guides = "".join('<a class="sibling" href="/guides/%s/">%s</a>'
                     % (g["slug"], esc(re.sub("&amp;", "&", g["h1"]).split(" — ")[0].split(" (")[0]))
                     for g in all_guides)
    body = HEAD.format(title="All Products — OEM Kitchenware Item Codes | Yongli", desc=desc,
                       url=url, image=SITE + "/assets/covers/new2026.jpg",
                       ld=json.dumps(ld, ensure_ascii=False, indent=1), css=css())
    body += crumbs([("Home", "/"), ("All Products", None)])
    body += '<h1>All products</h1>\n<p class="lede">%s</p>\n' % esc(desc)
    body += cta_row("Wholesale quote request", "Hi, I would like a quote for the item codes below.")
    body += ('<section class="block"><h2>Item codes (%d)</h2>'
             '<p class="block-sub">Each code links to its own page with the range, materials and '
             'catalogue page. Search inside a catalogue? Open the flip-book from the '
             '<a href="/">home page search box</a>.</p>'
             '<table class="prod-table"><tr><th></th><th>Product</th><th>Code</th>'
             '<th>Catalogue</th><th>Page</th></tr>%s</table></section>\n' % (len(rows), tb))
    body += '<section class="block"><h2>Buyer guides</h2><div class="siblings">%s</div></section>\n' % guides
    body += FOOT
    return body


# --------------------------------------------------------------------------- #
# Homepage block + sitemap
# --------------------------------------------------------------------------- #
HOME_START, HOME_END = "<!-- GUIDES:BEGIN -->", "<!-- GUIDES:END -->"


def home_block(all_guides, n_products):
    cols = "".join(
        '<div class="hi-col"><h3>%s</h3><p class="hi-sub">%s</p>'
        '<a class="hi-all" href="/guides/%s/">Read the guide &rarr;</a></div>'
        % (esc(re.sub("&amp;", "&", g["h1"]).split(" (")[0]),
           esc(clip(re.sub("&amp;", "&", g["meta_desc"]), 110)), g["slug"]) for g in all_guides)
    cols += ('<div class="hi-col"><h3>All products</h3>'
             '<p class="hi-sub">%d printed item codes with their own pages</p>'
             '<a class="hi-all" href="/product/">Open the product list &rarr;</a></div>' % n_products)
    return (HOME_START + "\n"
            '<div class="home-index">\n'
            "<h2>Sourcing guides &amp; full product list</h2>\n"
            '<p class="hi-lede">Buyer-intent pages for the ranges we are asked about most - what we '
            "make, what can be customised, materials and compliance - plus a page for every item code "
            "we print.</p>\n"
            '<div class="hi-grid">%s</div>\n'
            "</div>\n" % cols + HOME_END)


def update_home(all_guides, n_products):
    if not INDEX_HTML.exists():
        return
    html = INDEX_HTML.read_text(encoding="utf-8")
    block = home_block(all_guides, n_products)
    if HOME_START in html and HOME_END in html:
        html = re.sub(re.escape(HOME_START) + r".*?" + re.escape(HOME_END), block, html, flags=re.S)
    elif "<!-- INDEX:END -->" in html:
        html = html.replace("<!-- INDEX:END -->", "<!-- INDEX:END -->\n\n" + block, 1)
    else:
        print("homepage markers missing - guides block skipped")
        return
    INDEX_HTML.write_text(html, encoding="utf-8")
    print("homepage guides block rewritten")


def merge_sitemap(new_urls):
    """Add our URLs to whatever gen_pages.py already wrote."""
    entries, seen = [], set()
    if SITEMAP.exists():
        raw = SITEMAP.read_text(encoding="utf-8")
        for loc, cf, pr in re.findall(
                r"<loc>(.*?)</loc>\s*<changefreq>(.*?)</changefreq>\s*<priority>(.*?)</priority>",
                raw, re.S):
            if loc in seen:
                continue
            seen.add(loc)
            entries.append((loc, cf, pr))
    added = 0
    for u, cf, pr in new_urls:
        if u in seen:
            continue
        seen.add(u)
        entries.append((u, cf, pr))
        added += 1
    body = "\n".join('  <url>\n    <loc>%s</loc>\n    <changefreq>%s</changefreq>\n'
                     '    <priority>%s</priority>\n  </url>' % e for e in entries)
    SITEMAP.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                       + body + "\n</urlset>\n", encoding="utf-8")
    print("sitemap.xml: %d urls total (%d added)" % (len(entries), added))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200,
                    help="max product pages to generate (default 200)")
    ap.add_argument("--no-sitemap", action="store_true")
    args = ap.parse_args()

    products = load_products()
    print("index rows with a code+name:", len(products))

    # Guide-matched products get a page first: they are the ranges buyers
    # actually ask this store about.
    by_guide = {g["slug"]: guide_matches(products, g, limit=20) for g in GUIDES_DATA}
    chosen = {}
    for slug, rows in by_guide.items():
        if len(chosen) >= args.limit:
            break
        for p in rows:
            if len(chosen) >= args.limit:
                break
            chosen.setdefault(p["code"], p)
    for p in products:                      # then the current decks, then the rest
        if len(chosen) >= args.limit:
            break
        if p["code"] not in chosen and p["cid"] in ("new2026", "2023"):
            chosen[p["code"]] = p
    for p in products:
        if len(chosen) >= args.limit:
            break
        chosen.setdefault(p["code"], p)
    chosen = list(chosen.values())
    print("product pages:", len(chosen), "| guide-matched:",
          sum(1 for s, r in by_guide.items() for _ in r))

    have = {p["code"] for p in chosen}
    shots = load_shots()
    # Each guide's lead photo, so the hub and the sibling cards can show it.
    hero_of = {g["slug"]: hero_code(g, by_guide[g["slug"]], shots) for g in GUIDES_DATA}
    print("item photos available:", len(shots), "| guides with a lead photo:",
          sum(1 for v in hero_of.values() if v))
    by_section = {}
    for p in chosen:
        by_section.setdefault((p["cid"], p["section"]), []).append(p)

    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    for p in chosen:
        sibs = [s for s in by_section[(p["cid"], p["section"])] if s["code"] != p["code"]][:8]
        d = PRODUCT_DIR / p["code"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(product_html(p, lambda c: c in have, sibs, shots),
                                      encoding="utf-8")
    print("wrote %d product pages" % len(chosen))

    # Drop product folders a previous run wrote (they are shrinking sets when the
    # limit changes). Only folders whose page carries our marker are removed.
    stale = 0
    for d in PRODUCT_DIR.iterdir():
        if not d.is_dir() or d.name in have:
            continue
        page = d / "index.html"
        if not page.exists():
            continue
        txt = page.read_text(encoding="utf-8", errors="ignore")
        # MARK covers any page this script wrote from now on; class="facts" is a
        # template signature only these pages carry, so output from the first run
        # (before the marker existed) is still recognised as ours.
        if MARK in txt or 'class="facts"' in txt:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
            stale += 1
    if stale:
        print("removed %d stale product pages from an earlier run" % stale)

    (PRODUCT_DIR / "index.html").write_text(
        product_index_html(chosen, GUIDES_DATA, shots), encoding="utf-8")
    print("wrote product/index.html")

    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    for g in GUIDES_DATA:
        rows = by_guide[g["slug"]]
        d = GUIDE_DIR / g["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            guide_html(g, rows, GUIDES_DATA, lambda c: c in have, shots, hero_of),
            encoding="utf-8")
        print("guide:", g["slug"], "(%d products)" % len(rows))
    (GUIDE_DIR / "index.html").write_text(guides_hub_html(GUIDES_DATA, shots, hero_of),
                                          encoding="utf-8")
    print("wrote guides/index.html")

    update_home(GUIDES_DATA, len(chosen))

    if not args.no_sitemap:
        urls = [(SITE + "/guides/", "weekly", "0.8"), (SITE + "/product/", "weekly", "0.8")]
        urls += [("%s/guides/%s/" % (SITE, g["slug"]), "monthly", "0.7") for g in GUIDES_DATA]
        urls += [("%s/product/%s/" % (SITE, p["code"]), "monthly", "0.6") for p in chosen]
        merge_sitemap(urls)


if __name__ == "__main__":
    main()
