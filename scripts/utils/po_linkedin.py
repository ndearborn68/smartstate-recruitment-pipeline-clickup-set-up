# Parse the pasted Product Owner data
data = """jsubhong@gmail.com|Jinsub Hong|https://www.linkedin.com/in/jinsub-hong
lfilipos@gmail.com|Luke Filipos|https://www.linkedin.com/in/lfilipos
william.guinter@gmail.com|Billy Guinter|https://www.linkedin.com/in/william-guinter
stevenszopinski@gmail.com|Steven Szopinski|https://www.linkedin.com/in/steven-szopinski-a4a50265
geoff.barruel@gmail.com|Geoffroy Barruel|https://www.linkedin.com/in/geoffroy-barruel
ncp007@bucknell.edu|Nicholas Palmer|https://www.linkedin.com/in/nicholaspalmer1
ckakai17@gsb.columbia.edu|Tony Kakai|https://www.linkedin.com/in/tonykakai
yutian.q@columbia.edu|Aurora Qiu|https://www.linkedin.com/in/aurora-qiu
katie.topper10@gmail.com|Katie Fikke|https://www.linkedin.com/in/katie-topper
shhaaaaaron@gmail.com|Sharon Casalino|https://www.linkedin.com/in/sharonkmoon
jesspaolee@gmail.com|Jessica Lee|https://www.linkedin.com/in/leejessi
lukas.staniszewski@hotmail.com|Lukas Staniszewski|https://www.linkedin.com/in/lukas-staniszewski-b1154340
kiersten8johnston@gmail.com|Kiersten Johnston|https://www.linkedin.com/in/kiersten8johnston
atamanchuk.alexa@gmail.com|Alexa Atamanchuk|https://www.linkedin.com/in/aatamanchuk
juliencgreco@gmail.com|Julien Greco|https://www.linkedin.com/in/juliengreco
jeffrey.soo@gmail.com|Jeffrey Soo|https://www.linkedin.com/in/jeffreysoo
jfeni1347@aol.com|John Fenimore|https://www.linkedin.com/in/john-fenimore-4a711414
laurenn.berger@gmail.com|Laurenn Berger|https://www.linkedin.com/in/laurenn-berger-1425b862
declancallisto@gmail.com|Declan Callisto|https://www.linkedin.com/in/declan-callisto-367b97124
jimmyyang1@gmail.com|Jimmy Yang|https://www.linkedin.com/in/jimmyjyang
pnwilson15@gmail.com|Paige Peter|https://www.linkedin.com/in/paigewilson2
elenkaxmel@gmail.com|Elena Khmelevski|https://www.linkedin.com/in/elena-khmelevski-b7390866
alexdobis@gmail.com|Alex Dobis|https://www.linkedin.com/in/alexdobis
christopher.slowik@gmail.com|Chris Danison|https://www.linkedin.com/in/chris-danison-34383ab8
darkassain942@aol.com|Jeriel Acosta|https://www.linkedin.com/in/jeriela
saralee158@gmail.com|Sara Lee|https://www.linkedin.com/in/saralee158
abigailbeecher4@gmail.com|Abigail Beecher|https://www.linkedin.com/in/abigailbeecher
zhen.xiao@fedex.com|Ray X|https://www.linkedin.com/in/zhenwenxiao
michaelallencolasurdo@gmail.com|Mike Colasurdo|https://www.linkedin.com/in/mike-colasurdo-73a957220
michelle.gbolumah@yahoo.com|Michelle Gbolumah|https://www.linkedin.com/in/michelle-gbolumah
gideon.kalischer@gmail.com|Gideon Kalischer|https://www.linkedin.com/in/gideon-kalischer-5a49628
hammerbd@aol.com|Anthony Demaio|https://www.linkedin.com/in/anthony-demaio-475ba749
wleung2@hotmail.com|Ellen Li|https://www.linkedin.com/in/ellenpli
diamond64697@gmail.com|Michael Diamond|https://www.linkedin.com/in/michael-m-diamond
paul.carey@alumni.upenn.edu|Paul Carey|https://www.linkedin.com/in/paul-carey-9884411b
sararatto7@gmail.com|Sara Ratto|https://www.linkedin.com/in/sara-ratto-5a5a06a2
michael.desposito@gmail.com|Mike D'esposito|https://www.linkedin.com/in/mikedesposito
melaynahope@gmail.com|Melayna Ingram|https://www.linkedin.com/in/melayna-ingram-757b195
jverzosa@me.com|Justin Verzosa|https://www.linkedin.com/in/justin-verzosa-46bb4055
scott.stokke@gmail.com|Scott Stokke|https://www.linkedin.com/in/scottstokke
dawnhoogmoed@gmail.com|Dawn Samphel|https://www.linkedin.com/in/dawnsamphel
cfalvo01@gmail.com|Christopher Falvo|https://www.linkedin.com/in/chrisfalvo
harrisonobeid@gmail.com|Harrison Obeid|https://www.linkedin.com/in/harrisonobeid
leilasearching@yahoo.com|Marte Schaffmeyer|https://www.linkedin.com/in/marteschaffmeyer
maddockjack@live.co.uk|Jack Maddock|https://www.linkedin.com/in/jack-maddock-510b9733
sbosoy0@gmail.com|Steven Bosoy|https://www.linkedin.com/in/stevenbosoy
alihoops894@aol.com|Allison Franz|https://www.linkedin.com/in/allison-hupalo-franz-64b996a3
catfishdroid@aol.com|Jon Sheinfeld|https://www.linkedin.com/in/jon-sheinfeld-a754b984
ahmed_hassan5155@yahoo.com|Ahmed Hassan|https://www.linkedin.com/in/ahmed-s-hassan
xbillabong13@gmail.com|Janine Moody|https://www.linkedin.com/in/janine-moody"""

import json
email_to_linkedin = {}
for line in data.strip().split('\n'):
    parts = line.split('|')
    if len(parts) == 3:
        email, name, linkedin = parts
        email_to_linkedin[email.strip()] = {'linkedin': linkedin.strip(), 'name': name.strip()}

print(f"Parsed {len(email_to_linkedin)} email->LinkedIn mappings")
with open('/sessions/eloquent-trusting-pasteur/po_linkedin_map.json', 'w') as f:
    json.dump(email_to_linkedin, f)
