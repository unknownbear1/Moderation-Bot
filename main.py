import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit

CHANNEL_ID = 1193977639417937976
MOD_LOG_ID = 1561586130862735470
OUTPUT_CHANNEL_ID = 1516225222439735446
MODERATION_CHANNELS = {
    'live_links': CHANNEL_ID,
    'repost_output': OUTPUT_CHANNEL_ID,
    'channel_03': 1296257468577611856,
    'channel_04': 1296271765957378049,
    'channel_05': 1296926070649524375,
    'channel_06': 1296257558142652426,
    'channel_07': 1300335490142179331,
    'channel_08': 1419026528154550452,
    'channel_09': 1432855383482962000,
    'channel_10': 1513236368766140696,
    'channel_11': 1521599211433365616,
}
MODERATION_CATEGORY_IDS = set()
LINK_REPOST_RULES = {
    CHANNEL_ID: {
        'output_channel_id': OUTPUT_CHANNEL_ID,
        'source_permissions': ('view_channel', 'read_message_history', 'manage_messages'),
        'output_permissions': ('view_channel', 'send_messages', 'embed_links'),
    },
}
LIVE_LINKS_ONLY_CHANNEL_ID = next(iter(LINK_REPOST_RULES))
OUTPUT_CHANNEL_ID = LINK_REPOST_RULES[LIVE_LINKS_ONLY_CHANNEL_ID]['output_channel_id']
TROLL_FLAG_CHANNEL_IDS = set(MODERATION_CHANNELS.values()) - {0}

SCAN_MINUTES = 15
LIVE_LINKS_SCAN_MINUTES = 15
POLICY_VERSION = 'local-v12-video-completeness-and-review-logs'
LIVE_LINKS_POLICY = 'live-links-only-v6-gif-sticker-emoji-exceptions'
TROLL_FLAG_POLICY = 'troll-review-v7-racial-slur-triggers'

ALLOWED_ACCOUNT = 'unknownbear_'
CAUSE_EXCEPTION_USERNAME = 'thatzionistgirl'
CAUSE_EXCEPTION_USER_ID = int(
    os.getenv('CAUSE_EXCEPTION_USER_ID', '0').strip() or '0'
)
CAUSE_EXCEPTION_POLICY = 'cause-announcement-v1'

VIOLATION_TIMEOUT_SECONDS = 86400
TIMEOUT_ENABLED_AT = time.time()

MAX_MEDIA_BYTES = 25 * 1024 * 1024
MAX_VIDEO_SECONDS = 120
NUDITY_THRESHOLD = 0.65

ADULT_FEED_URL = 'https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/nsfw-onlydomains.txt'
FEED_REFRESH_SECONDS = 86400
FEED_MAX_BYTES = 5 * 1024 * 1024

FEED_EXCLUDED_ROOTS = {
    'discord.com', 'discord.gg', 'discordapp.com', 'discordapp.net',
    'x.com', 'twitter.com', 'tiktok.com', 'instagram.com',
    'facebook.com', 'youtube.com', 'youtu.be', 'reddit.com',
    'google.com', 'wikipedia.org', 'github.com',
}

ADULT_DOMAINS = set("""
21sextury.com 3movs.com 4tube.com 5movs.com 9porn.com
abbywinters.com adultempire.com adultfriendfinder.com adultwork.com aebn.com
allanal.com allinternal.com allover30.com alohatube.com amateur.tv
amateurallure.com amateurporn.me analdin.com analonly.com ancensored.com
anysex.com ashemaletube.com asstr.org av01.tv avdbs.com
avgle.com avizoone.com avsox.com aznude.com babeher.com
babepedia.com babes.com babesandstars.com babesnetwork.com babestation.tv
badoinkvr.com bang.com bangbros.com bangbrosnetwork.com bdsmlr.com
beeg.com bellesa.co bellesaplus.co bigboobsalert.com bigtits.com
blacked.com blacksonblondes.com bongacams.com boobpedia.com boundhub.com
boyfriendtv.com boysfood.com bravoporn.com bravotube.net brazzers.com
bustybloom.com cam4.com cambay.tv cambro.tv camcontacts.com
camonster.com camplace.com camrabbit.com cams.com camshowdownload.com
camsoda.com camster.com camvault.xyz camversity.com camvideos.org
camwhores.tv camwhores.video celebjihad.com chan.sankakucomplex.com chaturbate.com
cherry.tv cherrypimps.com cherrypimpsnetwork.com chyoa.com clips4sale.com
cum4k.com czechav.com czechcasting.com czechstreets.com czechvideo.com
daftsex.com danbooru.donmai.us deeper.com desiporn.tube desitales2.com
desixnxx.com desixxx.in digitaldesire.com digitalplayground.com dirtyship.com
dorcel.com dorcelclub.com drporn.com drtuber.com drtuber.xxx
e621.net efappy.com efukt.com empflix.com empireamateurs.com
eporner.com erome.com eroticbeauty.com eroticmonkey.ch ersties.com
escortbabylon.net escortfish.ch evilangel.com extremetube.com exxxtrasmall.com
fakehub.com faketaxi.com fakku.net family.xxx fancentro.com
fansly.com fanvue.com fapality.com fapcat.com fapello.com
fapelloleaks.com fapgon.com fapguru.com faphouse.com fapnado.com
fapnation.com fapnut.com fapomania.com faproulette.co faproulette.com
fapster.xxx faptitans.com fapvid.com femdom-joi.com femdomcc.net
fetishnetwork.com fistingcentral.com fleshbot.com fling.com flirt4free.com
freeones.com frolicme.com fuckbook.com fullporn.xxx fullporner.com
fuq.com fux.com fuxxx.com gamelink.com gay0day.com
gayboystube.com gaydemon.com gayforit.eu gayfuror.com gaymaletube.com
gayporn.fm gayporno.fm gaysonic.com gaystream.pw gaysuperman.com
gaytube.com gelbooru.com goodporn.se goodporn.to gosexpod.com
gotporn.com hanime.tv hardsextube.com hclips.com hdhole.com
hdporn.net hdporn92.com hdpornmax.net hdpornt.com hdpornvideo.xxx
hdsex.org hdsex2.com hdtube.xxx hdtubemovies.com hdzog.com
heavy-r.com hentai-foundry.com hentai.io hentai.tv hentai2read.com
hentai4manga.com hentaibam.com hentaidude.com hentaiforce.net hentaifox.com
hentaigasm.com hentaihaven.xxx hentaihere.com hentaiheroes.com hentaiplay.net
hentaipros.com hentaipulse.com hentairead.com hentaisea.com hentaistream.com
hentaistream.tv hentaitube.online hentaiworld.tv hentaixd.com hentaixxx.me
hentaiz.org hentaizap.com hentaizilla.com hitomi.la hot-sex-tube.com
hotmovies.com hotmovs.com hotpornfile.org hotporntubes.com hqporner.com
hustler.com hustlerunlimited.com iafd.com imhentai.xxx imlive.com
indexxx.com iwantclips.com jav.guru javbus.com javdb.com
javhd.com javhub.net javlibrary.com javmix.tv javmost.com
javmost.to javseen.tv javsubindo.com javtiful.com javtrailers.com
jerkmate.com jizzbunker.com jizzhut.com jizzoncam.com jizzparade.com
jizzplanet.com joyourself.com justfor.fans justporno.tv justporno.xxx
keezmovies.com kindgirls.com kink.com kissjav.com leakedmodels.com
leakxxx.com legalporno.com lesbian8.com letmejerk.com lewdzone.com
literotica.com livejasmin.com liveprivates.com loyalfans.com lubed.com
lushstories.com lustery.com madthumbs.com manyvids.com mature.nl
matureporn.com maturesex.com maturetube.com maturetubeporn.com melonstube.com
metart.com milfmovs.com milfporn.tv milftube.com milfzr.com
mofos.com momsbangteens.com motherless.com mrskin.com mydirtyhobby.com
myfreecams.com myhentaicomics.com myhentaigallery.com mylf.com myreadingmanga.info
naked.com nakedgirls.xxx nakednews.com nastyporn.net naughtyamerica.com
naughtyamericalive.com naughtyblog.org netvideogirls.com newtumbl.com nhentai.net
niteflirt.com nubiles-porn.com nubiles.net nudevista.com nudevista.net
nudogram.com nudography.com nudostar.com nutaku.net nuvid.com
nuvid.xxx onlyfans.com orgasms.xxx passion-hd.com peekshows.com
penthouse.com perfectgonzo.com playboyplus.com porn.com porn00.org
porn2012.com porn300.com porn4days.net porn4real.com porn555.com
porn7.xxx porn87.com porn93.co pornbang.com pornbimbo.com
pornbiz.com pornblade.com pornbox.com pornbraze.com pornburst.xxx
porncoven.com porndig.com porndish.com porndoe.com porndude.com
pornerbros.com pornfd.com pornfidelity.com pornflip.com pornfuror.com
porngo.com pornhat.com pornhd.com pornhd3x.com pornheed.com
pornhits.com pornhive.tv pornhub.com pornhub.de pornhub.es
pornhub.fr pornhub.it pornhub.net pornhub.org pornhub.xxx
pornhubpremium.com pornhubpremium.org pornhubselect.com pornkai.com pornktube.com
pornl.com pornmd.com pornmd.xxx pornmega.com pornmz.com
pornogratis.xxx pornomovies.com pornon.xxx pornone.com pornotube.com
pornoxo.com pornoxo.xxx pornpics.com pornplus.com pornpros.com
pornrabbit.com pornrewind.com pornrox.com pornsharing.com pornsocket.com
pornsos.com pornstarbyface.com pornstarhub.com porntopic.com porntrex.com
porntry.com porntube.com pornve.com pornvibe.org pornwatchers.com
pornwex.tv pornwhite.com pornwild.to pornworld.com pornyd.com
pornzog.com povd.com punishbang.com puretaboo.com realitykings.com
realitykingsnetwork.com reallifecam.com reallifecam.to rec-tube.com recurbate.com
redgifs.com redtube.com redwap.com redwap.me rule34.paheal.net
rule34.us rule34.xxx rule34video.com runetki.com sakuralive.com
sankakucomplex.com screwbox.com seancody.com seehimfuck.com sex.com
sex.xxx sex3.com sex8.cc sexandsubmission.com sexart.com
sexemulator.com sexlikereal.com sexmex.xxx sexstories.com sextpanther.com
sextvx.com sexu.com sexuria.com sexvid.xxx sexvideos.xxx
sexvids.tv shemale6.com shemaletubevideos.com shesfreaky.com simonscans.com
skyprivate.com slayed.com slutload.com spankbang.com spankbanglive.com
spankingtube.com spankwire.com spicytranny.com spizoo.com streamate.com
stripchat.com suicidegirls.com sunporno.com superbe.com superporn.com
sweetheartvideo.com sxyprn.com tastyblacks.com teamskeet.com teenfidelity.com
thefappening.plus thefappening.pro thefappeningblog.com thegay.com thehun.net
theporndude.com thisvid.com thumbs.pro thumbzilla.com tigerram.com
tiny4k.com tnaflix.com tnaflix.xxx tsescorts.com tsumino.com
tube8.com tubegalore.com tubeporn.com tubepornclassic.com tubepornstars.com
tubepornup.com tubesafari.com tubsexer.com tubxporn.com tushy.com
twistys.com txxx.com upornia.com vixen.com vjav.com
voyeur-house.tv voyeurhit.com voyeurweb.com vporn.com vrbangers.com
vrporn.com wankoz.com wankzvr.com watchmygf.com watchporn.to
whoreshub.com wicked.com wickedpictures.com woodmancastingx.com worldsex.com
x-art.com x18r.com x3vid.com xanimeporn.com xart.com
xbabe.com xcafe.com xcams.com xempire.com xfantazy.com
xfree.com xfreehd.com xgaytube.com xhamster.com xhamster.desi
xhamster2.com xhamster3.com xhamsterlive.com xkeezmovies.com xlovecam.com
xmissy.nl xmom.me xnxx.com xnxx.es xnxx.in
xnxx.tv xnxx2.com xnxx3.com xnxx4.com xogogo.com
xozilla.com xpee.com xrares.com xrares.net xredtube.com
xshr.online xsporn.com xtapes.to xtits.com xtube.com
xvideos-cdn.com xvideos.com xvideos.es xvideos.in xvideos.red
xvideos2.com xvidzz.com xvirgins.com xxnx.com xxnx.tv
xxx.com xxx18hot.com xxxbit.com xxxbp.tv xxxbullet.com
xxxbunker.com xxxcollections.net xxxdan.com xxxfiles.com xxxmovies.xxx
xxxporn123.com xxxporno.cam xxxporno.tv xxxsexvideos.com xxxsexzoo.com
xxxshake.com xxxstash.com xxxstreams.eu xxxstreams.org xxxtik.com
xxxvideo.blog xxxvideo.one xxxvideor.com xxxymovies.com yespornplease.com
yobt.com yobt.tv youav.com youfreeporn.com youjizz.com
youporn.com youporngay.com youpornpremium.com yourporn.sexy yourporntube.com
yoursexyteens.com yuvutu.com zbporn.com zoggy.com zooxtaboo.com
""".split())

SOCIAL_HOSTS = {
    'www.instagram.com', 'x.com', 'tiktok.com', 'instagram.com',
    'www.tiktok.com', 'www.twitter.com', 'www.x.com', 'twitter.com',
}

TEXT_PATTERNS = tuple(re.compile(pattern) for pattern in (
    r'\b(?:send|show|share|trade|swap|exchange)(?: me| us)? (?:your |some |more )?(?:nudes|nudies|dick pics?|cock pics?|pussy pics?|tits|boobs)\b',
    r'\b(?:send|show)(?: me| us)? (?:a |your )?naked (?:pics?|pictures?|photos?|videos?)\b',
    r'\b(?:send|show)(?: me| us)? (?:pics?|pictures?|photos?|videos?) of (?:your |my )?(?:dick|cock|pussy|tits|boobs|genitals)\b',
    r'\b(?:dm|pm|message|inbox)(?: me)? (?:for |your )?(?:nudes|sexting|sex chat|dick pics?|pussy pics?)\b',
    r'\b(?:buy|sell|selling|purchase|order|unlock) (?:my |your |her |his |some )?(?:nudes|nudies|sex videos?|porn videos?|explicit videos?|explicit photos?)\b',
    r'\b(?:nudes|sex videos?|porn videos?) (?:for sale|available|in (?:my )?(?:bio|dms|inbox))\b',
    r'\b(?:free|leaked|uncensored|hardcore|amateur) (?:porn|porno|pornography)\b',
    r'\b(?:watch|download|stream|watching|streaming) (?:some |my |this )?(?:porn|porno|pornography)\b',
    r'\b(?:porn|porno|pornography) (?:links?|videos?|clips?|collection|downloads?)\b',
    r'\b(?:suck|lick|stroke|ride|rub)(?: on)? (?:my|your|his|her) (?:dick|cock|pussy|clit)\b',
    r'\b(?:put|take) (?:my|your|his) (?:dick|cock) (?:in|inside|into)\b',
    r'\b(?:fuck|fucking) (?:my|your|his|her) (?:pussy|ass|mouth)\b',
    r'\b(?:fuck me|fuck my|cum on my|cum in my|cum inside me)\b',
    r'\b(?:cum|cumming|ejaculate|ejaculating) (?:in|inside|on|all over) (?:me|you|my|your|his|her)\b',
    r'\b(?:i want|i wanna|let me|going to|gonna) (?:fuck|suck|lick) (?:you|your|her|his)\b',
    r'\b(?:spread|open) (?:your|her) legs (?:for me|wide)\b',
    r'\b(?:blow ?jobs?|hand ?jobs?|gang ?bangs?|buk+ake|cum ?shots?|creampies?)\b',
    r'\bdeep ?throat(?:ing)? (?:my|your|his|her|me)\b',
    r'\b(?:anal|oral|hardcore|group|rough) sex (?:videos?|clips?|pics?|photos?|chat|with me)\b',
    r'\b(?:watch|show|send|selling) (?:my |her |his )?(?:masturbation|masturbating)\b',
    r'\b(?:jerk|jerking|jack|jacking) off (?:for|to|on) (?:me|you|my|your|her|his|camera|cam)\b',
    r'\b(?:finger|fingering) (?:my|your|her) pussy\b',
    r'\b(?:eat|eating) (?:my|your|her) pussy\b',
    r'\b(?:pussy|dick|cock|tits|boobs) (?:pics?|pictures?|photos?|videos?)\b',
    r'\b(?:naked|nude|explicit) (?:selfies|selfie)\b',
    r'\b(?:live|private|paid) (?:sex shows?|sex cams?|cam sex|cam shows?)\b',
    r'\b(?:sex|sexting|nudes) (?:on|over|via) (?:snapchat|telegram|whatsapp|discord|cam)\b',
    r'\b(?:join|visit|subscribe to|check out) (?:my |her |his )?(?:onlyfans|fansly|porn channel|sex channel)\b',
    r'\b(?:onlyfans|fansly) (?:leaks?|leaked|nudes|free content)\b',
    r'\b(?:buy|selling|sell|offering) (?:a |my )?(?:sexting session|sex chat|cam session)\b',
    r'\b(?:send|show|share|trade|swap)(?: me| us)? (?:your |some |more )?(?:n00des|noods|nudes?)\b',
    r'\b(?:send|show|share)(?: me| us)? (?:your )?(?:d1ck|c0ck|pu55y|puss[y1]) (?:pics?|photos?|videos?)\b',
    r'\b(?:send|show)(?: me| us)? (?:your )?(?:bare|exposed) (?:breasts|genitals|penis|vulva)\b',
    r'\b(?:want|wanna|need) (?:to see )?(?:your|her|his) (?:nudes|naked body|dick pics|pussy pics)\b',
    r'\b(?:dm|pm|message|inbox)(?: me)? (?:for )?(?:paid |private |exclusive )?(?:sexting|nudes|n00des|noods|sex vids)\b',
    r'\b(?:snap|snapchat|telegram|discord) (?:for )?(?:nudes|sexting|sex chat)\b',
    r'\b(?:add|follow|subscribe)(?: me)? (?:for )?(?:nudes|sexting|explicit content)\b',
    r'\b(?:uncensored|explicit|nude|naked) (?:content|pics|photos|videos) (?:in|on) (?:my )?(?:bio|profile|dms|channel)\b',
    r'\b(?:check|click|visit) (?:the |my )?(?:link|bio|profile) (?:for )?(?:nudes|porn|sex videos)\b',
    r'\b(?:selling|buy|unlock|order) (?:my )?(?:sex tapes?|custom porn|custom nudes|custom sex videos)\b',
    r'\b(?:sex tapes?|nude bundles?|porn bundles?) (?:for sale|available|for free)\b',
    r'\b(?:full|uncensored|leaked) (?:sex tapes?|sex scenes?|porn scenes?)\b',
    r'\b(?:free|premium|exclusive|uncensored) (?:xxx|adult) (?:videos?|pics?|photos?|content)\b',
    r'\b(?:18 plus|18 only|adults only) (?:sex chat|porn|nudes|sexting)\b',
    r'\b(?:looking for|anyone for|who wants|want to|wanna) (?:sext|sexting|cam sex|cybersex)\b',
    r'\b(?:sext|sexting|cybersex|cam sex) (?:with me|with you|now|tonight)\b',
    r'\b(?:make|watch) (?:me|you|her|him) (?:cum|masturbate)\b',
    r'\b(?:show|watch) (?:me|you|her|him) (?:cum|cumming|orgasm)\b',
    r'\b(?:i am|im|i m) (?:cumming|stroking my dick|stroking my cock|rubbing my clit)\b',
    r'\b(?:play|playing) with (?:my|your|her|his) (?:pussy|dick|cock|clit)\b',
    r'\b(?:rub|rubbing|touch|touching|stroke|stroking) (?:my|your|her|his) (?:pussy|dick|cock|clit)\b',
    r'\b(?:ride|riding) (?:my|your|his) (?:dick|cock)\b',
    r'\b(?:sit|sitting) on (?:my|your|his|her) (?:dick|cock|face)\b',
    r'\b(?:want|wanna|let me) (?:eat you out|eat her out)\b',
    r'\b(?:give|giving|want|wanting) (?:me |you |him |her )?(?:a )?(?:blowjob|handjob|rimjob)\b',
    r'\b(?:rimjobs?|titjobs?|footjobs?|facefucking|facefuck|cock sucking|dick sucking|pussy licking)\b',
    r'\b(?:anal|vaginal|double) penetration (?:videos?|clips?|porn)\b',
    r'\b(?:cum|jizz|semen) (?:on|in|inside) (?:my|your|her|his) (?:face|mouth|pussy|ass|tits)\b',
    r'\b(?:breed|breeding|impregnate) (?:me|my pussy)\b',
    r'\b(?:open|spread) (?:your|her) (?:pussy|ass|asshole)\b',
    r'\b(?:hard|erect|throbbing) (?:dick|cock) (?:pics?|photos?|videos?)\b',
    r'\b(?:wet|tight) pussy (?:pics?|photos?|videos?)\b',
    r'\b(?:naked|nude|topless|bottomless) (?:cam show|cam session|sex show)\b',
    r'\b(?:live sex|live masturbation|live porn)\b',
    r'\b(?:porn|nudes|sex videos) (?:mega|gdrive|google drive|dropbox|telegram) (?:links?|folders?|channels?)\b',
    r'\b(?:mega|gdrive|google drive|dropbox|telegram) (?:porn|nudes|sex videos) (?:links?|folders?|channels?)\b',
    r'\b(?:send|show|share|trade|swap)(?: me| us)? (?:your |some )?n[\s._*-]*[u0o][\s._*-]*d[\s._*-]*[e3][\s._*-]*s\b',
    r'\b(?:send|show|share)(?: me| us)? (?:your )?(?:d1ck|dick|c0ck|cock|pu55y|pussy|t1ts|b00bs) (?:p1cs|pics|pix|pictures|photos|vids|videos)\b',
    r'\b(?:selling|buy|watch|download|free|leaked|uncensored|hardcore) (?:p0rn|pr0n|pr0nz|porn0)\b',
    r'\b(?:p0rn|pr0n|pr0nz|porn0) (?:links?|videos?|vids|clips?|packs?|folders?)\b',
    r'\b(?:send|show|share|sell|selling|trade|swap) (?:me |us )?(?:your |my |some |more )?(?:nude|naked|explicit|uncensored) (?:pics?|pix|pictures?|photos?|vids|videos?|clips?|packs?|bundles?|content)\b',
    r'\b(?:dm|pm|message|inbox|contact)(?: me)? (?:for )?(?:a |some |my |exclusive |private |paid )?(?:nude|naked|explicit|uncensored) (?:pics?|pictures?|photos?|videos?|clips?|content|packs?)\b',
    r'\b(?:dm|pm|message)(?: me)? (?:your )?(?:onlyfans|fansly|porn links?|sex tapes?|nude packs?)\b',
    r'\b(?:i sell|i am selling|im selling|selling|buy my|purchase my) (?:private |exclusive |custom )?(?:nude|naked|explicit|porn) (?:pics?|photos?|videos?|content|packs?|bundles?)\b',
    r'\b(?:nude|naked|porn|xxx|explicit) (?:packs?|bundles?|collections?) (?:for sale|available|free|in my bio|in my dms)\b',
    r'\b(?:join|subscribe to|check out|visit) (?:my |our )?(?:18 plus |18 only |adults only )?(?:porn|xxx|sexting|nudes) (?:server|channel|group|page|account)\b',
    r'\b(?:porn|xxx|nude|nudes) (?:discord|telegram) (?:server|channel|group|invite|links?)\b',
    r'\b(?:discord|telegram) (?:server|channel|group) (?:for |with )?(?:porn|xxx|nudes|sexting)\b',
    r'\b(?:mega|gdrive|google drive|dropbox) (?:folder|links?|collection|packs?) (?:of |for |with )?(?:porn|nudes|sex videos)\b',
    r'\b(?:watch|download|stream|buy) (?:a |my |her |his |some )?(?:sex tape|sex tapes|porn movie|porn movies|porn scene|porn scenes)\b',
    r'\b(?:show|send)(?: me)? (?:your|her|his) (?:nude body|naked body|bare ass|bare tits|bare pussy|bare dick)\b',
    r'\b(?:show|send)(?: me)? (?:a |your )?(?:dick pic|cock pic|pussy pic|tit pic|boob pic|ass pic)\b',
    r'\b(?:get|getting|go|going) naked (?:for me|on cam|on camera|on webcam)\b',
    r'\b(?:take|taking) (?:your|her) (?:clothes|panties|underwear|bra) off (?:for me|on cam|on camera)\b',
    r'\b(?:show|showing) (?:your|her|his) (?:genitals|penis|vagina|vulva) (?:on cam|on camera|to me)\b',
    r'\b(?:masturbate|masturbating|jerk off|jerking off|jack off|jacking off) (?:on cam|on camera|on webcam|for me|for you)\b',
    r'\b(?:watch|want to watch|wanna watch) (?:me|her|him) (?:masturbate|jerk off|jack off|finger herself|cum)\b',
    r'\b(?:my|your|his) (?:dick|cock) (?:is |s )?(?:hard|throbbing|dripping|inside you|inside her)\b',
    r'\b(?:my|your|her) pussy (?:is |s )?(?:wet|dripping|soaked|tight)\b',
    r'\b(?:put|putting|stick|sticking|slide|sliding) (?:my|your|his) (?:dick|cock) (?:inside|into|in) (?:me|you|her|my|your|her)\b',
    r'\b(?:suck|sucking|lick|licking|stroke|stroking|ride|riding) (?:on )?(?:my|your|his|her) (?:dick|cock|pussy|clit|balls)\b',
    r'\b(?:suck|sucking) (?:me|him) off\b',
    r'\b(?:i want|i wanna|let me|please) (?:fuck you|fuck her|fuck him|finger you|finger her)\b',
    r'\b(?:fuck|fucking|pound|pounding|bang|banging) (?:my|your|her) (?:pussy|ass|asshole)\b',
    r'\b(?:cum|cumming|ejaculate|ejaculating) (?:all )?(?:over|on|inside|into) (?:my|your|her|his) (?:mouth|face|pussy|ass|tits|boobs)\b',
    r'\b(?:want|wanna|need) (?:you|him|her) to (?:cum|masturbate|fuck me|suck me off)\b',
    r'\b(?:pornografia|porno) (?:gratis|completo|sin censura|en vivo|videos?)\b',
    r'\b(?:envia|enviame|manda|mandame) (?:tus |mas )?(?:nudes|fotos desnudas|fotos desnudos|fotos intimas)\b',
    r'\b(?:vendo|compro) (?:mis |tus )?(?:nudes|fotos intimas|videos sexuales|videos porno)\b',
    r'\b(?:sexe|porno) (?:gratuit|en direct|sans censure)\b',
    r'\b(?:envoye|envoie|envoie moi) (?:tes |des )?(?:nudes|photos nues|photos intimes)\b',
    r'\b(?:porn|porno) (?:kostenlos|ungeschnitten|videos)\b',
    r'\b(?:manda|envia) (?:seus |suas |mais )?(?:nudes|fotos peladas|fotos intimas)\b',
    r'\b(?:vendo|compro) (?:meus |minhas )?(?:nudes|videos porno|fotos peladas)\b',
    r'\b(?:send|show|share|trade|swap)(?: me| us)? (?:your |some )?(?:noodz|nudz|nud3s|n00dz|n00d5|nudes?)\b',
    r'\b(?:dm|pm|message|inbox)(?: me)? (?:for )?(?:noodz|nudz|nud3s|n00dz|n00d5)\b',
    r'\b(?:send|show|share)(?: me| us)? (?:your )?(?:dick|cock|pussy|tits|boobs|d1ck|c0ck|pu55y|t1ts|b00bs) (?:p[i1]c(?:s|tures?)?|p[i1]x|phot[o0]s?|v[i1]ds?|v[i1]deos?)\b',
    r'\b(?:send|show|share|selling|sell|buy|trade|swap) (?:me |us )?(?:your |my |some )?(?:nude|naked|explicit|uncensored) (?:vids?|videos?|photos?|pics?|packs?|bundles?)\b',
    r'\b(?:check|visit|click|open) (?:my |the )?(?:bio|profile|link) (?:to see|to get|to watch|for) (?:my |some )?(?:nudes|naked pics|sex vids|porn clips)\b',
    r'\b(?:sexting|sex chat|cam sex|nude pics|nude videos) (?:sessions?|services?|packages?) (?:available|for sale|for free|in my bio)\b',
    r'\b(?:subscribe|join|follow|unlock) (?:my |her |his |our )?(?:private |exclusive )?(?:nudes|sex videos|porn content|xxx content)\b',
    r'\b(?:tips?|payment|pay|paid|cashapp|cash app|venmo|paypal) (?:me |for |to unlock )?(?:my )?(?:nudes|sexting|sex videos|porn clips|naked pics)\b',
    r'\b(?:nudes|sexting|sex videos|porn clips|naked pics) (?:for tips|for cash|for payment|for money)\b',
    r'\b(?:watch|download|stream|buy|free|hardcore) (?:p o r n|p0r n|p orn|p0rn0|pr0n|p0rn)\b',
    r'\b(?:porn|p0rn|pr0n) (?:torrent|torrents|magnet|zip|rar|archive|archives|dump|dumps)\b',
    r'\b(?:leaked|uncensored|free) (?:only fans|onlyfans|fansly|fanvue) (?:content|vids|videos|pics|photos|packs)\b',
    r'\b(?:only fans|onlyfans|fansly|fanvue) (?:nudes|porn|sex vids|sex videos|leaks|packs)\b',
    r'\b(?:hardcore|explicit|uncensored) (?:hentai|doujinshi|erotica|sex comics|adult comics)\b',
    r'\b(?:hentai|doujinshi|erotica) (?:porn|sex videos|sex clips|xxx|nudes)\b',
    r'\b(?:join|visit|watch|buy) (?:my |our |the )?(?:live masturbation show|nude cam show|naked cam show|live sex show)\b',
    r'\b(?:let me|i want to|i wanna|please) (?:lick|suck|stroke|ride) (?:your|his|her) (?:dick|cock|pussy|clit|balls)\b',
    r'\b(?:i want|i wanna|please|let me) (?:put|stick|slide) (?:my|your|his) (?:dick|cock) (?:in|inside|into)\b',
    r'\b(?:finger|fingering) (?:me|her) (?:on cam|on camera|until i cum|until she cums)\b',
    r'\b(?:show|send)(?: me)? (?:your |her |his )?(?:masturbation video|masturbation clip|sex tape|cum video|orgasm video)\b',
    r'\b(?:i am|im|i m|she is|he is) (?:naked|nude) (?:on cam|on camera|on webcam|for you)\b',
    r'\b(?:want|wanna|need|ready) to (?:sext with|have cam sex with|have cybersex with) (?:me|you|her|him)\b',
    r'\b(?:send|share|trade) (?:your |my |some )?(?:nsfw nudes|nsfw pics|nsfw videos|nsfw photos)\b',
    r'\b(?:watch|buy|download) (?:my |some )?(?:nsfw videos|nsfw sex clips|nsfw porn)\b',
))

TEXT_PATTERNS += tuple(re.compile(pattern) for pattern in (
    r'\b(?:send|show|share)(?: me| us)? (?:a|an|the|those|them) (?:nude|nudes|naked pics|nude pics|explicit photos|sex video)\b',
    r'\b(?:got|have|have you got|do you have|anyone got) (?:any |some |more )?(?:nudes|nude pics|naked pics|sex videos|porn clips)\b',
    r'\b(?:can|could|will|would) you (?:send|show|share) (?:me |us )?(?:your |some )?(?:nudes|nude pics|naked photos|sex videos)\b',
    r'\b(?:send|show|share)(?: me| us)? (?:your |some )?(?:full frontal|fully nude|fully naked|uncensored nude) (?:pics?|photos?|videos?|selfies)\b',
    r'\b(?:send|show)(?: me)? (?:your )?(?:tits|boobs|pussy|dick|cock|ass) (?:without clothes|without underwear|uncovered|uncensored)\b',
    r'\b(?:show|send)(?: me)? (?:a |your )?(?:close up|closeup) (?:of )?(?:your |her |his )?(?:pussy|dick|cock|genitals)\b',
    r'\b(?:send|show|share|trade|swap)(?: me| us)? (?:your )?(?:n u d e s|n u d 3 s|n o o d s|n 0 0 d s)\b',
    r'\b(?:send|show|share)(?: me)? (?:your )?(?:nudes|noods|nud3s|n00des) (?:please|pls|plz|rn|now|tonight)\b',
    r'\b(?:nudes|nude pics|naked pics|explicit pics|sex vids) (?:please|pls|plz|wanted|needed)\b',
    r'\b(?:trade|trading|swap|swapping|exchange|exchanging) (?:my |your |our |some )?(?:nude selfies|naked selfies|naked photos|nude photos|sex tapes|sex clips)\b',
    r'\b(?:rate|rating) (?:my|your|his|her) (?:dick|cock|pussy|nudes)\b',
    r'\b(?:dick|cock|pussy|nude) ratings? (?:available|for sale|in my dms|dm me)\b',
    r'\b(?:send|show|share|buy|selling) (?:me |my |your )?(?:dickpic|dickpics|cockpic|cockpics|pussypic|pussypics|nudevid|nudevids)\b',
    r'\b(?:dm|pm|message)(?: me)? (?:for |to get |to buy |to see )?(?:dickpics|cockpics|pussypics|nudevids|nude selfies|nude bundles)\b',
    r'\b(?:selling|offering|buy|purchase|book|order) (?:my |a |an |some )?(?:custom |private |exclusive |personalized )?(?:nude videos?|nude photos?|explicit clips?|masturbation videos?)\b',
    r'\b(?:custom|private|exclusive|personalized) (?:nude videos?|nude photos?|sex videos?|masturbation clips?) (?:available|for sale|on request|by request)\b',
    r'\b(?:prices?|price list|menu|rates?) (?:for |of )?(?:my )?(?:nudes|nude videos|sexting|sex chat|cam sex)\b',
    r'\b(?:nudes|nude videos|sexting|sex chat|cam sex) (?:menu|price list|rates|prices|for money|for payment)\b',
    r'\b(?:unlock|purchase|buy|pay for) (?:the |my |her |his )?(?:uncensored nudes|nude gallery|porn collection|sex tape|explicit bundle)\b',
    r'\b(?:tip|pay|send money|send cash)(?: me)? (?:to see|to watch|to unlock|for) (?:my |her |his )?(?:nudes|naked body|sex show|nude show|masturbation)\b',
    r'\b(?:click|open|visit|check)(?: out)? (?:my |the )?(?:bio|profile|link|page) (?:for |to see |to get )?(?:uncensored nudes|full nudes|full nude videos|porn collection)\b',
    r'\b(?:nudes|nude videos|porn clips|sex tapes) (?:at|through|via|behind) (?:the |my )?(?:link|paywall|profile link|bio link)\b',
    r'\b(?:join|enter|visit|subscribe to) (?:my |our |the )?(?:private |exclusive |premium )?(?:nude group|nude channel|nude server|porn server|porn group|sexting group)\b',
    r'\b(?:private|premium|exclusive) (?:porn group|nude group|nude channel|sexting server|sex chat room)\b',
    r'\b(?:invite|invites|links|access) (?:to|for) (?:my |our |the )?(?:porn server|porn group|nude channel|nude group|sexting server)\b',
    r'\b(?:download|watch|stream|buy|selling) (?:my |the |a |some )?(?:hardcore clips|hardcore videos|uncensored sex|explicit sex|masturbation clips|masturbation videos)\b',
    r'\b(?:porn|nudes|sex tapes|explicit videos) (?:zip files|rar files|file dumps|video dumps|download packs|download bundles)\b',
    r'\b(?:zip|rar|mega|gdrive|dropbox) (?:packs|bundles|dumps|archives) (?:of |with |for )?(?:porn|nudes|sex tapes|explicit videos)\b',
    r'\b(?:porn|porno|pornography|p0rn|pr0n) (?:channel|server|group|site|website) (?:link|links|invite|invites|in my bio)\b',
    r'\b(?:watch|download|free|leaked|uncensored|hardcore) (?:p[o0][r4]n(?:ography)?|p[o0]rn[o0]|pr[o0]n)\b',
    r'\b(?:p[o0][r4]n|pr[o0]n|p[o0]rn[o0]) (?:packs?|clips?|vids?|videos?|links?|streams?)\b',
    r'\b(?:onlyfans|only fans|fansly|fanvue) (?:content|photos|videos) (?:for free|leaked|uncensored|download)\b',
    r'\b(?:selling|sharing|trading|download|buy) (?:my |her |his |some )?(?:onlyfans|fansly|fanvue) (?:nudes|leaks|sex videos|porn clips)\b',
    r'\b(?:send|show|share|trade)(?: me| us)? (?:your )?(?:d i c k|c o c k|p u s s y|t i t s|b o o b s) (?:pics|photos|videos)\b',
    r'\b(?:show|send)(?: me)? (?:your|her|his) (?:naked|nude) (?:body|breasts|genitals|ass|butt)\b',
    r'\b(?:watch|see|show me) (?:you|her|him) (?:get naked|get fully nude|strip naked|strip for me)\b',
    r'\b(?:strip|stripping|undress|undressing) (?:for me|for you|on cam|on webcam|on camera)\b',
    r'\b(?:want|wanna|need|looking for) (?:a |some )?(?:sexting partner|cybersex partner|cam sex partner|nude trade)\b',
    r'\b(?:anyone|who) (?:want|wants|wanna|up for|down for) (?:sexting|cam sex|cybersex|nude trading)\b',
    r'\b(?:lets|let s|let us) (?:sext|have cam sex|have cybersex|trade nudes|swap nudes)\b',
    r'\b(?:dm|pm|message|call|video call)(?: me)? (?:for )?(?:cam sex|cybersex|nude chat|naked chat|private sex chat)\b',
    r'\b(?:nude|naked|explicit) (?:video call|webcam session|cam session|private session)\b',
    r'\b(?:i want|i wanna|let me|please) (?:see|watch) (?:you|her|him) (?:cum|masturbate|jerk off|jack off|play with your pussy)\b',
    r'\b(?:suck|lick|stroke|ride|rub|touch)(?: on)? (?:this|that|these|those) (?:dick|cock|pussy|clit|balls)\b',
    r'\b(?:show|send)(?: me)? (?:your |my |her |his )?(?:cumshot|creampie|blowjob|handjob|rimjob) (?:pics?|photos?|videos?|clips?)\b',
    r'\b(?:cum|cumming|jizz|jizzing) (?:all over|inside|on|in) (?:me|you|her|him)\b',
    r'\b(?:want|wanna|let me|please) (?:lick your pussy|suck your cock|suck your dick|ride your cock|ride your dick)\b',
    r'\b(?:take|taking|put|putting) (?:your|my|his) (?:cock|dick) (?:deep in|deep inside|in my mouth|in your mouth)\b',
    r'\b(?:selling|buy|watch|download) (?:my |her |his |some )?(?:hentai porn|animated porn|3d porn|vr porn|virtual reality porn)\b',
    r'\b(?:sex|nude|porn|xxx) (?:videos|clips|photos|pics) (?:for you|for sale|for free|dm me|message me)\b',
    r'\b(?:enviame|mandame|envia|manda) (?:una |unas |tus )?(?:foto desnuda|fotos desnudas|video sexual|videos sexuales|fotos sin ropa)\b',
    r'\b(?:manda|envia) (?:uma |umas |seus |suas )?(?:foto pelada|fotos peladas|video porno|videos porno|fotos sem roupa)\b',
))

MEDIA_REQUEST_INTENTS = (
    r'(?:send|show|share)(?: me| us)?',
    r'(?:give|get)(?: me| us)',
    r'(?:can|could|would|will) you(?: please)? (?:send|show|share)(?: me| us)?',
    r'(?:does anyone|anyone|who) (?:have|got|sell|selling|share|sharing)',
    r'(?:i am|im|i m) (?:looking for|buying|seeking)',
    r'(?:buy|purchase|order|download|watch|stream)',
    r'(?:selling|offering|sharing|trading|uploading|posting)',
    r'(?:trade|swap|exchange)(?: me| with me)?',
    r'(?:dm|pm|message|inbox|contact)(?: me| us)? (?:for|to get|to buy|to watch)',
    r'(?:click|open|visit) (?:my |the )?(?:bio|link|profile) (?:for|to see|to get|to watch)',
    r'(?:subscribe|sign up) (?:for|to get|to see|to watch)',
    r'(?:free access to|instant access to|unlock|pay to unlock|pay for)',
)

EXPLICIT_MEDIA_TYPES = (
    r'(?:nude|naked) (?:personal photos?|selfies|pics?|pictures?)',
    r'explicit sexual (?:images?|photos?|pictures?)',
    r'(?:genital|penis|vagina|vulva) (?:closeups?|close ups?|pics?|photos?)',
    r'pornographic (?:photos?|pictures?|images?)',
    r'pornographic (?:videos?|vids?|movies?)',
    r'hardcore sex (?:clips?|videos?|vids?)',
    r'(?:home ?made |private )?sex tapes?',
    r'uncensored (?:nude|naked) (?:images?|photos?|videos?)',
    r'masturbation (?:clips?|videos?|vids?)',
    r'explicit sex (?:livestreams?|live streams?|recordings?)',
    r'porn (?:download archives?|download collections?|download links?)',
    r'nude (?:photo|picture|image) (?:packs?|bundles?|collections?)',
    r'cumshot (?:videos?|clips?|compilations?)',
    r'oral sex (?:videos?|clips?|compilations?)',
    r'anal sex (?:videos?|clips?|compilations?)',
    r'pornographic (?:comics?|manga|doujinshi)',
    r'pornographic (?:animations?|cartoons?|animated videos?)',
    r'erotic nude (?:photo |image )?galleries',
    r'nsfw sexual (?:images?|pictures?|videos?)',
    r'explicit sexual (?:scenes?|compilations?|content packs?)',
)

SEXUAL_SERVICE_INTENTS = (
    r'(?:book|schedule|reserve|request)',
    r'(?:buy|purchase|order|pay for)',
    r'(?:selling|offering|providing|hosting)',
    r'(?:dm|pm|message|contact)(?: me| us)? (?:for|to book|to buy)',
    r'(?:tips? for|payment for|pay to unlock|unlock)',
    r'(?:join|enter|participate in|sign up for)',
    r'(?:looking for|seeking|anyone offering|who offers)',
    r'(?:available for|taking bookings for|taking requests for|now offering)',
)

EXPLICIT_SERVICE_TYPES = (
    r'(?:private |personalized |custom )?sexting sessions?',
    r'(?:private |personalized |custom )?explicit sex chats?',
    r'(?:private |personalized |custom )?nude webcam sessions?',
    r'(?:private |personalized |custom )?naked video calls?',
    r'(?:private |personalized |custom )?live sex shows?',
    r'(?:private |personalized |custom )?live masturbation shows?',
    r'(?:private |personalized |custom )?cam sex sessions?',
    r'(?:private |personalized |custom )?cybersex sessions?',
    r'(?:private |personalized |custom )?explicit sexual roleplay sessions?',
    r'(?:private |personalized |custom )?nude photo trades?',
)

ADDITIONAL_MEDIA_INTENTS = (
    r'(?:where|how) can i (?:find|get|buy|download|watch)',
    r'(?:anybody|somebody|anyone here) (?:have|got|selling|sharing|trading)',
    r'(?:could|would|can) somebody(?: please)? (?:send|show|share)(?: me| us)?',
    r'(?:looking|hoping|trying) to (?:buy|find|get|download|watch)',
    r'(?:i want|i wanna|i need|we want|we need) (?:to see|to watch|to buy|to download)',
    r'(?:please|pls|plz) (?:send|share|show|give)(?: me| us)?',
    r'(?:any|got any|does anyone have any) (?:links? to|download links? for|sources? for)',
    r'(?:check out|come see|come watch|come get|come download)',
    r'(?:now sharing|now selling|now trading|now uploading|currently offering)',
    r'(?:tap|follow|use) (?:my |the |our )?(?:link|bio link|profile link) (?:for|to see|to get|to watch)',
)

ADDITIONAL_SERVICE_INTENTS = (
    r'(?:can|could|would) you (?:provide|offer|arrange|schedule)',
    r'(?:does anyone|anybody|anyone here) (?:offer|provide|sell|host)',
    r'(?:i want|i wanna|i need|we want|we need) (?:to book|to buy|to schedule|to join)',
    r'(?:where|how) can i (?:book|buy|find|join|schedule)',
    r'(?:are you|is anyone|anyone here) (?:offering|selling|hosting|providing)',
    r'(?:now booking|currently booking|now selling|currently selling|now hosting)',
    r'(?:accepting bookings for|accepting requests for|accepting payment for)',
    r'(?:message|dm|pm|contact)(?: me| us)? (?:to schedule|to arrange|to reserve|to join)',
    r'(?:sign up|register|subscribe) (?:for|to book|to join|to access)',
    r'(?:looking|hoping|trying) to (?:book|buy|arrange|schedule|join)',
)

MEDIA_REQUEST_RULES = tuple(
    re.compile(
        rf'\b(?:{intent}) (?:please )?'
        rf'(?:(?:a|an|the|some|any|more|your|my|his|her|our|their) )?'
        rf'(?:{media})\b'
    )
    for intent in MEDIA_REQUEST_INTENTS
    for media in EXPLICIT_MEDIA_TYPES
)

SEXUAL_SERVICE_RULES = tuple(
    re.compile(
        rf'\b(?:{intent}) '
        rf'(?:(?:a|an|the|some|any|more|your|my|his|her|our|their) )?'
        rf'(?:{service})\b'
    )
    for intent in SEXUAL_SERVICE_INTENTS
    for service in EXPLICIT_SERVICE_TYPES
)

ADDITIONAL_MEDIA_RULES = tuple(
    re.compile(
        rf'\b(?:{intent}) (?:please )?'
        rf'(?:(?:a|an|the|some|any|more|your|my|his|her|our|their) )?'
        rf'(?:{media})\b'
    )
    for intent in ADDITIONAL_MEDIA_INTENTS
    for media in EXPLICIT_MEDIA_TYPES
)

ADDITIONAL_SERVICE_RULES = tuple(
    re.compile(
        rf'\b(?:{intent}) '
        rf'(?:(?:a|an|the|some|any|more|your|my|his|her|our|their) )?'
        rf'(?:{service})\b'
    )
    for intent in ADDITIONAL_SERVICE_INTENTS
    for service in EXPLICIT_SERVICE_TYPES
)

TEXT_PATTERNS = tuple({
    pattern.pattern: pattern
    for pattern in (
        *TEXT_PATTERNS,
        *MEDIA_REQUEST_RULES,
        *SEXUAL_SERVICE_RULES,
        *ADDITIONAL_MEDIA_RULES,
        *ADDITIONAL_SERVICE_RULES,
    )
}.values())

HOST_PATTERN = re.compile(
    r'(?<![\w@-])(?:[a-z0-9](?:[a-z0-9-]{0,62})\.)+[a-z]{2,63}(?![\w-])',
    re.I,
)
URL_PATTERN = re.compile(r'https?://[^\s<>]+', re.I)

LIVE_LINK_HOST_RULES = {
    'tiktok.com': r'/@[a-zA-Z0-9._]{1,24}/live/?',
    'www.tiktok.com': r'/@[a-zA-Z0-9._]{1,24}/live/?',
    'm.tiktok.com': r'/@[a-zA-Z0-9._]{1,24}/live/?',
    'youtube.com': r'/(?:@[^/]+|channel/[a-zA-Z0-9_-]+|c/[^/]+|user/[^/]+)/live/?',
    'www.youtube.com': r'/(?:@[^/]+|channel/[a-zA-Z0-9_-]+|c/[^/]+|user/[^/]+)/live/?',
    'm.youtube.com': r'/(?:@[^/]+|channel/[a-zA-Z0-9_-]+|c/[^/]+|user/[^/]+)/live/?',
    'instagram.com': r'/[a-zA-Z0-9._]+/live/?',
    'www.instagram.com': r'/[a-zA-Z0-9._]+/live/?',
    'facebook.com': r'/[a-zA-Z0-9.]+/live/?',
    'www.facebook.com': r'/[a-zA-Z0-9.]+/live/?',
    'twitch.tv': r'/[a-zA-Z0-9_]{1,25}/?',
    'www.twitch.tv': r'/[a-zA-Z0-9_]{1,25}/?',
}

LIVE_LINK_SAFE_QUERY_KEYS = {
    'is_from_webapp', 'sender_device', 'web_id', 'lang', 'enter_from',
    'share_app_id', 'share_link_id', 'timestamp', 'u_code', 'user_id',
    'utm_source', 'utm_medium', 'utm_campaign', '_r', '_t', 'si',
}

TWITCH_RESERVED_PATHS = {
    'directory', 'videos', 'downloads', 'login', 'signup', 'settings',
    'subscriptions', 'inventory', 'wallet', 'search', 'jobs', 'p',
    'turbo', 'prime', 'about', 'friends', 'following', 'products',
}

SECTION_URL_PATTERN = re.compile(
    r'(?<![\w@.])(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>]+'
    r'|(?<![\w@.])(?:[a-z0-9](?:[a-z0-9-]{0,62})\.)+'
    r'[a-z]{2,63}(?::[0-9]{1,5})?(?:/[^\s<>]*)?',
    re.I,
)

CAUSE_TOPIC_PATTERN = re.compile(
    r'\b(?:charit(?:y|ies|able)|nonprofit|non-profit|not-for-profit|'
    r'fundrais(?:er|ers|ing)|donat(?:e|es|ion|ions)|relief fund|'
    r'volunteer(?:s|ing)?|community service|mutual aid|humanitarian|'
    r'disaster relief|food bank|food drive|blood drive|awareness campaign|'
    r'advocacy|petition|voter registration|campaign(?:s|ing)?|'
    r'canvass(?:er|ers|ing)?|door knock(?:er|ers|ing)?|'
    r'community event|charity event|benefit event|rally|rallies|'
    r'peaceful protest|peaceful demonstration|support group|'
    r'community outreach|public service|make liberty win)\b',
    re.I,
)

CAUSE_ACTION_PATTERN = re.compile(
    r'\b(?:for anyone interested|i am working with|i m working with|'
    r'im working with|we are working with|we re working with|'
    r'looking to hire|now hiring|hiring|recruiting|'
    r'looking for volunteers|seeking volunteers|need volunteers|'
    r'get paid|paid to|paid opportunities|paid positions|'
    r'sign up|signup|register|registration|apply|application|'
    r'join us|join the|help us|help the|support the|support our|'
    r'donate|volunteer|participate|take action|get involved|'
    r'more info|more information|learn more|details below|'
    r'share this|spread the word|raising awareness|'
    r'attend|come along|come out|everyone is welcome)\b',
    re.I,
)

TIKTOK_SHARE_HOSTS = frozenset({
    'tiktok.com', 'www.tiktok.com', 'm.tiktok.com',
    'vm.tiktok.com', 'vt.tiktok.com',
})
TIKTOK_RESOLUTION_CACHE = {}

TROLL_PHRASES = (
    r'trump supporters (?:are|are in|belong to) (?:a |the )?cult',
    r'fuck trump supporters',
    r'i hate maga',
    r'maga (?:are|is) nazis?',
    r'trump supporters (?:are|are all) nazis?',
    r'i hate trump',
    r'fuck trump',
    r'fuck millie',
    r'i hate millie',
    r'millie is (?:a |an )?(?:whore|slut|cam ?girl|bitch|cunt)',
    r'nazis?',
    r'(?:fuck|f\*ck|f\*\*k)\s+zionism',
    r'screw\s+zionism',
    r'i\s+hate\s+zionism',
)

TROLL_JEWISH_TARGET = r'(?:jews|jewish\s+(?:people|men|women|families|communities))'
TROLL_ZIONIST_TARGET = r'(?:zionists?|zionism)'
TROLL_GROUP_TARGET = rf'(?:{TROLL_JEWISH_TARGET}|{TROLL_ZIONIST_TARGET})'

TROLL_EXPANDED_ABUSE = (
    rf'(?:fuck|f\*ck|f\*\*k|screw)\s+(?:(?:all|the|those)\s+)?{TROLL_GROUP_TARGET}',
    rf'i\s+(?:hate|despise|loathe)\s+(?:(?:all|the|those)\s+)?{TROLL_GROUP_TARGET}',
    rf'{TROLL_GROUP_TARGET}\s+(?:are|is)\s+(?:(?:all|just|nothing\s+but)\s+)?'
    r'(?:vermin|parasites|subhuman|scum|filth|a\s+disease|a\s+cancer)',
    rf'{TROLL_GROUP_TARGET}\s+(?:are|is)\s+(?:all\s+)?'
    r'(?:evil|disgusting|worthless|inferior)',
    rf'(?:kill|murder|exterminate|gas|eradicate)\s+(?:(?:all|the|those)\s+)?{TROLL_GROUP_TARGET}',
    rf'(?:wipe\s+out|round\s+up|get\s+rid\s+of)\s+(?:(?:all|the|those)\s+)?{TROLL_GROUP_TARGET}',
    rf'{TROLL_GROUP_TARGET}\s+(?:should|must|deserve\s+to)\s+(?:all\s+)?'
    r'(?:die|be\s+killed|be\s+exterminated|be\s+deported|be\s+expelled)',
    rf'(?:death\s+to|no\s+rights\s+for)\s+(?:the\s+)?{TROLL_GROUP_TARGET}',
    rf'(?:ban|expel|deport)\s+(?:all\s+)?{TROLL_JEWISH_TARGET}',
    rf'(?:all\s+)?{TROLL_JEWISH_TARGET}\s+(?:are\s+)?'
    r'(?:greedy|money\s+hungry|born\s+liars|inherently\s+evil)',
    rf'(?:the\s+)?{TROLL_JEWISH_TARGET}\s+(?:secretly\s+)?'
    r'(?:control|own|run)\s+(?:all\s+)?(?:the\s+)?'
    r'(?:world|banks|banking\s+system|media|governments?)',
    rf'(?:all\s+)?{TROLL_JEWISH_TARGET}\s+(?:are\s+)?'
    r'(?:responsible|to\s+blame)\s+for\s+(?:all\s+)?'
    r'(?:our\s+problems|the\s+world[\x27’]s\s+problems|every\s+war)',
    r'k[i1]kes?',
)

TROLL_PEOPLE_TARGET = (
    r'(?:(?:(?:all|the|those|these)\s+){0,2}'
    r'(?:jews|jewish\s+(?:people|men|women|families|communities)|zionists))'
)

TROLL_ADDITIONAL_ABUSE = (
    rf'(?:i|we)\s+(?:really\s+|absolutely\s+)?(?:hate|despise|loathe)\s+'
    rf'(?:(?:all|the|those)\s+)?{TROLL_GROUP_TARGET}',
    rf'{TROLL_PEOPLE_TARGET}\s+(?:are|are\s+all|are\s+just|are\s+nothing\s+but)\s+'
    r'(?:rats|cockroaches|animals|pigs|trash|garbage|human\s+garbage|'
    r'degenerates|a\s+plague|a\s+virus|a\s+scourge)',
    rf'{TROLL_PEOPLE_TARGET}\s+(?:do\s+not|don[\x27’]t)\s+'
    r'(?:deserve\s+(?:rights|to\s+live|to\s+exist)|belong\s+here)',
    rf'(?:i|we)\s+(?:hope|wish)\s+{TROLL_PEOPLE_TARGET}\s+'
    r'(?:(?:would|will|all)\s+){0,2}(?:die|disappear|get\s+killed|get\s+deported)',
    rf'{TROLL_PEOPLE_TARGET}\s+(?:should|must|need\s+to)\s+(?:all\s+)?'
    r'(?:be\s+removed|be\s+eliminated|be\s+wiped\s+out|leave\s+the\s+country|'
    r'be\s+locked\s+up|be\s+sent\s+to\s+camps)',
    rf'(?:shoot|hang|lynch|slaughter|burn)\s+{TROLL_PEOPLE_TARGET}',
    rf'(?:drive|kick|force)\s+{TROLL_PEOPLE_TARGET}\s+out',
    rf'{TROLL_PEOPLE_TARGET}\s+(?:are\s+)?not\s+welcome\s+(?:here|anywhere)',
    rf'(?:keep|ban)\s+{TROLL_PEOPLE_TARGET}\s+(?:out|from\s+our\s+(?:country|schools|neighborhoods))',
    r'(?:no|fewer)\s+(?:jews|jewish\s+people)\s+(?:allowed|wanted|welcome)',
    rf'(?:all\s+)?{TROLL_JEWISH_TARGET}\s+(?:are|are\s+all)\s+'
    r'(?:thieves|liars|criminals|traitors|cheats|con\s+artists)',
    rf'(?:the\s+)?{TROLL_JEWISH_TARGET}\s+(?:secretly\s+)?'
    r'(?:control|own|run)\s+(?:all\s+)?(?:the\s+)?'
    r'(?:press|news|politicians|politics|hollywood|economy|financial\s+system)',
    rf'(?:all\s+)?{TROLL_JEWISH_TARGET}\s+(?:are\s+)?'
    r'(?:responsible|to\s+blame)\s+for\s+(?:all\s+)?'
    r'(?:wars|our\s+suffering|society[\x27’]s\s+problems|the\s+world[\x27’]s\s+problems)',
    r'(?:jewish|jew)\s+(?:vermin|parasites|scum|filth)',
    r'(?:fuck|f\*ck|f\*\*k)\s+(?:all\s+)?(?:of\s+)?(?:the\s+)?zionists?',
)

TROLL_PHRASES += TROLL_EXPANDED_ABUSE + TROLL_ADDITIONAL_ABUSE

RACIAL_SLUR_PATTERNS = (
    r'n[i1!][g69]{2}(?:[e3]r|a)s?',
    r'k[i1!]kes?',
    r'sp[i1!](?:c|ck)s?',
    r'ch[i1!]nks?',
)

TROLL_PHRASES += RACIAL_SLUR_PATTERNS

TROLL_PATTERNS = tuple(
    re.compile(r'\b' + pattern + r'\b', re.I)
    for pattern in TROLL_PHRASES
)

TROLL_ATTRIBUTION = re.compile(
    r'(?:\b(?:he|she|they|someone|somebody|people|the troll|a troll|that person|'
    r'the commenter|a commenter|the user|a user|(?!(?:i|we)\b)[\w.@-]+)\s+'
    r'(?:(?:just|literally|actually|was|were|is|keeps|kept)\s+){0,2}'
    r'(?:said|says|saying|wrote|writes|writing|posted|posts|posting|commented|'
    r'commenting|called|calling|claimed|claiming|yelled|shouted|replied|told me)'
    r'|\b(?:i was told|i was called|we were called|the quote was|the message reads|'
    r'the comment reads|the screenshot says|the screenshot shows|they called us))'
    r'\s*(?:that\s+)?(?:["“‘:,\-]\s*)*$',
    re.I,
)

TROLL_DISCOURAGEMENT = re.compile(
    r'\b(?:do not say|don[’\x27]t say|stop saying|please stop saying|'
    r'please don[’\x27]t say|it is wrong to say|it[’\x27]s wrong to say)'
    r'\s*["“‘:]*\s*$',
    re.I,
)

TROLL_ENDORSEMENT = re.compile(
    r'\b(?:i agree|i agree with (?:him|her|them|that)|i think so too|'
    r'they[’\x27]re right|he[’\x27]s right|she[’\x27]s right|'
    r'that[’\x27]s true|that is true|i feel the same)\b',
    re.I,
)


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return ''.join(c for c in text if unicodedata.category(c) != 'Cf')


def allowed_account_url(url):
    try:
        parsed = urlsplit(url)
        segments = unquote(parsed.path).strip('/').split('/')
        return (
            (parsed.hostname or '').lower().rstrip('.') in SOCIAL_HOSTS
            and bool(segments)
            and segments[0].lstrip('@').casefold() == ALLOWED_ACCOUNT
        )
    except ValueError:
        return False


def blocked_domain(text, domain_lookup=None):
    text = re.sub(
        r'\s*(?:\[\.\]|\(\.\)|\{\.\})\s*',
        '.',
        normalize(text),
    )
    for candidate in HOST_PATTERN.findall(text):
        host = candidate.lower().rstrip('.')
        if (
            any(
                host == domain or host.endswith('.' + domain)
                for domain in ADULT_DOMAINS
            )
            or (domain_lookup is not None and domain_lookup(host))
        ):
            return host
    return None


def text_violation(text, domain_lookup=None):
    text = URL_PATTERN.sub(
        lambda match: '' if allowed_account_url(match.group()) else match.group(),
        normalize(text),
    )
    host = blocked_domain(text, domain_lookup)
    if host:
        return 'Blocked adult-site link: ' + host
    text = ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )
    text = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', text))
    if any(pattern.search(text) for pattern in TEXT_PATTERNS):
        return 'Explicit sexual phrase detected'
    return None


def parse_adult_feed(text):
    domains = set()
    for line in text.splitlines():
        domain = line.strip().lower().rstrip('.')
        if (
            len(domain) <= 253
            and HOST_PATTERN.fullmatch(domain)
            and domain not in FEED_EXCLUDED_ROOTS
        ):
            domains.add(domain)
    if not 1000 <= len(domains) <= 300000:
        raise ValueError('Adult domain feed failed validation')
    return domains


def section_link_candidates(message):
    texts = [message.content or '']
    texts.extend(embed.url for embed in message.embeds if embed.url)
    found = []
    seen = set()
    for text in texts:
        text = unicodedata.normalize('NFKC', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
        text = re.sub(r'\s*(?:\[\.\]|\(\.\)|\{\.\})\s*', '.', text)
        for match in SECTION_URL_PATTERN.finditer(text):
            candidate = match.group().rstrip("'\"`.,;:!?)]}")
            if '://' not in candidate:
                suffix = candidate.split('/')[0].rsplit('.', 1)[-1].lower()
                if suffix in {
                    'pdf', 'txt', 'doc', 'docx', 'xlsx', 'png',
                    'jpg', 'jpeg', 'gif', 'mp4', 'json', 'zip',
                }:
                    continue
            if candidate not in seen:
                seen.add(candidate)
                found.append(candidate)
    return found


def section_repost_body(message):
    content = message.content or ''
    if (
        re.search(r'(?im)^Posted:\s*', content)
        and re.search(r'(?im)^Comments:\s*', content)
    ):
        return re.sub(
            r'(?im)^[ \t]*Comments:[ \t]*(?:\r?\n[ \t]*)?'
            r'No comments\.?[ \t]*(?:\r?\n|$)',
            '', content,
        ).strip()
    comments = SECTION_URL_PATTERN.sub('', content).strip()
    body = (
        '\n'.join(section_link_candidates(message))
        + f'\nPosted: <@{message.author.id}>'
    )
    if comments:
        body += '\nComments:\n' + comments
    return body


def section_live_link_allowed(candidate):
    try:
        parsed = urlsplit(
            candidate if '://' in candidate else 'https://' + candidate
        )
        if parsed.scheme.lower() not in {'http', 'https'}:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.port is not None and parsed.port != (
            443 if parsed.scheme.lower() == 'https' else 80
        ):
            return False
        host = (parsed.hostname or '').casefold().rstrip('.')
        path = unquote(parsed.path)
        rule = LIVE_LINK_HOST_RULES.get(host)
        if not rule or not re.fullmatch(rule, path):
            return False
        if (
            host in {'twitch.tv', 'www.twitch.tv'}
            and path.strip('/').casefold() in TWITCH_RESERVED_PATHS
        ):
            return False
        if any(
            key.casefold() not in LIVE_LINK_SAFE_QUERY_KEYS
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ):
            return False
        return True
    except (ValueError, UnicodeError):
        return False


def tiktok_link_kind(candidate):
    try:
        parsed = urlsplit(
            candidate if '://' in candidate else 'https://' + candidate
        )
        host = (parsed.hostname or '').lower().rstrip('.')
        if host not in TIKTOK_SHARE_HOSTS:
            return 'other'
        if parsed.scheme.lower() not in {'http', 'https'}:
            return 'reject'
        if parsed.username is not None or parsed.password is not None:
            return 'reject'
        if parsed.port not in (
            None, 80 if parsed.scheme.lower() == 'http' else 443
        ):
            return 'reject'
        path = unquote(parsed.path)
        if re.fullmatch(r'/@[A-Za-z0-9._]{1,24}/live/?', path):
            return 'live'
        if re.fullmatch(r'/(?:share/live|live/share)/[0-9]+/?', path):
            return 'live'
        if re.fullmatch(
            r'/@[A-Za-z0-9._]{1,24}/(?:video|photo)/[0-9]+/?',
            path,
        ):
            return 'reject'
        if re.fullmatch(r'/share/(?:video|photo)/[0-9]+/?', path):
            return 'reject'
        if (
            host in {'vm.tiktok.com', 'vt.tiktok.com'}
            or re.fullmatch(r'/t/[^/]+/?', path)
        ):
            return 'short'
        return 'unknown'
    except (ValueError, UnicodeError):
        return 'reject'


async def resolve_tiktok_share(candidate):
    import aiohttp

    kind = tiktok_link_kind(candidate)
    if kind != 'short':
        return kind

    cached = TIKTOK_RESOLUTION_CACHE.get(candidate)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    current = candidate if '://' in candidate else 'https://' + candidate
    result = 'unknown'

    try:
        async with asyncio.timeout(15):
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=6),
                cookie_jar=aiohttp.DummyCookieJar(),
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'},
                trust_env=False,
            ) as session:
                visited = set()
                for _ in range(6):
                    if current in visited:
                        break
                    visited.add(current)
                    parsed = urlsplit(current)
                    host = (parsed.hostname or '').lower().rstrip('.')
                    if (
                        host not in TIKTOK_SHARE_HOSTS
                        or parsed.scheme.lower() not in {'http', 'https'}
                        or parsed.username is not None
                        or parsed.password is not None
                        or parsed.port not in (
                            None, 80 if parsed.scheme == 'http' else 443
                        )
                    ):
                        break

                    current_kind = tiktok_link_kind(current)
                    if current_kind in {'live', 'reject'}:
                        result = current_kind
                        break

                    async with session.get(
                        current, allow_redirects=False
                    ) as response:
                        if response.status in {301, 302, 303, 307, 308}:
                            location = response.headers.get('Location')
                            if not location:
                                break
                            destination = urljoin(str(response.url), location)
                        else:
                            break

                    destination_kind = tiktok_link_kind(destination)
                    if destination_kind in {'live', 'reject'}:
                        result = destination_kind
                        break
                    if destination_kind == 'other':
                        break
                    current = destination

    except (aiohttp.ClientError, TimeoutError, ValueError, UnicodeError):
        logger.warning(
            'TikTok share could not be resolved; leaving pending for retry'
        )

    if len(TIKTOK_RESOLUTION_CACHE) >= 2048:
        TIKTOK_RESOLUTION_CACHE.clear()

    TIKTOK_RESOLUTION_CACHE[candidate] = (
        time.monotonic() + (3600 if result != 'unknown' else 60),
        result,
    )
    return result


def section_gif_link_allowed(candidate):
    try:
        parsed = urlsplit(
            candidate if '://' in candidate else 'https://' + candidate
        )
        if parsed.scheme.lower() not in {'http', 'https'}:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.port not in (
            None, 443 if parsed.scheme.lower() == 'https' else 80
        ):
            return False
        host = (parsed.hostname or '').casefold().rstrip('.')
        path = unquote(parsed.path)
        if '\\' in path or any(part in {'.', '..'} for part in path.split('/')):
            return False
        rules = {
            'klipy.com': r'/gifs/[A-Za-z0-9_-]+/?',
            'www.klipy.com': r'/gifs/[A-Za-z0-9_-]+/?',
            'tenor.com': r'/view/[A-Za-z0-9_-]+/?',
            'www.tenor.com': r'/view/[A-Za-z0-9_-]+/?',
            'giphy.com': r'/gifs/[A-Za-z0-9_-]+/?',
            'www.giphy.com': r'/gifs/[A-Za-z0-9_-]+/?',
            'media.giphy.com': r'/media/[A-Za-z0-9_/-]+\.gif',
            'i.giphy.com': r'/(?:media/)?[A-Za-z0-9_/-]+\.gif',
            'media.tenor.com': r'/[A-Za-z0-9_/-]+\.gif',
            'cdn.discordapp.com': r'/attachments/[0-9]+/[0-9]+/[^/]+\.gif',
            'media.discordapp.net': r'/attachments/[0-9]+/[0-9]+/[^/]+\.gif',
        }
        rule = rules.get(host)
        return bool(rule and re.fullmatch(rule, path, flags=re.IGNORECASE))
    except (ValueError, UnicodeError):
        return False


def section_expression_link_allowed(candidate):
    try:
        parsed = urlsplit(
            candidate if '://' in candidate else 'https://' + candidate
        )
        if parsed.scheme.lower() not in {'http', 'https'}:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.port not in (
            None, 443 if parsed.scheme.lower() == 'https' else 80
        ):
            return False
        host = (parsed.hostname or '').casefold().rstrip('.')
        if host not in {'cdn.discordapp.com', 'media.discordapp.net'}:
            return False
        return bool(re.fullmatch(
            r'/(?:emojis/[0-9]+\.(?:png|webp|gif)'
            r'|stickers/[0-9]+\.(?:png|webp|gif|json))',
            unquote(parsed.path), flags=re.IGNORECASE,
        ))
    except (ValueError, UnicodeError):
        return False


async def section_link_allowed_resolved(candidate):
    if section_gif_link_allowed(candidate) or section_expression_link_allowed(candidate):
        return True
    kind = tiktok_link_kind(candidate)
    if kind == 'other':
        return section_live_link_allowed(candidate)
    if kind == 'short':
        kind = await resolve_tiktok_share(candidate)
    if kind == 'live':
        return True
    if kind == 'reject':
        return False
    return None


def is_cause_announcement(message):
    author = message.author
    if getattr(author, 'bot', False):
        return False

    if CAUSE_EXCEPTION_USER_ID:
        if author.id != CAUSE_EXCEPTION_USER_ID:
            return False
    elif str(getattr(author, 'name', '')).casefold() != CAUSE_EXCEPTION_USERNAME:
        return False

    content = URL_PATTERN.sub(' ', message.content or '')
    content = normalize(content).replace('’', "'")
    content = re.sub(r"['`]", ' ', content)
    content = re.sub(r'\s+', ' ', content).strip()

    return bool(
        len(re.findall(r'\b[a-z]{2,}\b', content)) >= 10
        and section_link_candidates(message)
        and CAUSE_TOPIC_PATTERN.search(content)
        and CAUSE_ACTION_PATTERN.search(content)
    )


def troll_comment_findings(content):
    text = unicodedata.normalize('NFKC', content or '')
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')

    matches = sorted(
        (m for pattern in TROLL_PATTERNS for m in pattern.finditer(text)),
        key=lambda m: (m.start(), -(m.end() - m.start())),
    )

    findings = []
    covered = -1

    for match in matches:
        if match.end() <= covered:
            continue
        covered = match.end()

        start = max(
            text.rfind('\n', 0, match.start()),
            text.rfind('!', 0, match.start()),
            text.rfind('?', 0, match.start()),
            text.rfind(';', 0, match.start()),
        ) + 1

        before = text[start:match.start()][-180:]
        after = text[match.end():].split('\n', 1)[0][:160]

        attributed = bool(
            TROLL_ATTRIBUTION.search(before)
            or TROLL_DISCOURAGEMENT.search(before)
        )
        endorsed = bool(TROLL_ENDORSEMENT.search(after))

        if attributed and not endorsed:
            continue

        quoted = before.rstrip().endswith(('"', '“', '‘'))
        blockquote = text[start:match.start()].lstrip().startswith('>')
        ambiguous = (
            quoted
            or blockquote
            or match.group().lower() in {'nazi', 'nazis'}
        )

        label = (
            'Possible endorsement; review context' if endorsed else
            'Ambiguous mention; review context' if ambiguous else
            'Possible direct statement; review context'
        )

        findings.append((match.group(), label))

    return findings


def media_worker(source):
    from nudenet import NudeDetector
    from PIL import Image, ImageOps

    blocked = {
        'FEMALE_BREAST_EXPOSED',
        'FEMALE_GENITALIA_EXPOSED',
        'MALE_GENITALIA_EXPOSED',
        'ANUS_EXPOSED',
        'BUTTOCKS_EXPOSED',
    }
    detector = NudeDetector()

    def check(path):
        return any(
            d['class'] in blocked and d['score'] >= NUDITY_THRESHOLD
            for d in detector.detect(str(path))
        )

    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        try:
            image = Image.open(source)
        except Exception:
            image = None

        if image is not None:
            with image:
                if not getattr(image, 'is_animated', False):
                    image = ImageOps.exif_transpose(image)
                    image.thumbnail((1280, 1280))
                    target = folder / 'image.jpg'
                    image.convert('RGB').save(target)
                    return {'blocked': check(target), 'complete': True, 'media_kind': 'image'}

        probe = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'json', str(source),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )

        duration = float(json.loads(probe.stdout)['format']['duration'])
        if not 0 < duration <= MAX_VIDEO_SECONDS:
            return {
                'blocked': False,
                'complete': False,
                'reason': 'Video/GIF exceeds the 120-second scan limit',
            }

        subprocess.run(
            [
                'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-threads', '1', '-protocol_whitelist', 'file,pipe',
                '-i', str(source), '-vf',
                'fps=2,scale=640:640:force_original_aspect_ratio=decrease',
                '-frames:v', str(MAX_VIDEO_SECONDS * 2 + 1),
                str(folder / 'frame-%04d.jpg'),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=True,
        )

        frames = sorted(folder.glob('frame-*.jpg'))
        if not frames:
            raise ValueError('No video frames decoded')

        for frame in frames:
            if check(frame):
                return {'blocked': True, 'complete': True, 'media_kind': 'video'}

        return {'blocked': False, 'complete': True, 'media_kind': 'video'}


if (
    __name__ == '__main__'
    and len(sys.argv) > 1
    and sys.argv[1] == '--media-worker'
):
    try:
        result = media_worker(sys.argv[2])
        print('SCAN_RESULT=' + json.dumps(result), flush=True)
    except Exception as exc:
        print(
            'SCAN_RESULT=' + json.dumps({
                'blocked': False,
                'complete': False,
                'reason': 'Media scan failed: ' + type(exc).__name__,
            }),
            flush=True,
        )
    sys.exit(0)

import discord
from discord.ext import tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('moderation')


EMBEDDED_MEDIA_HOSTS = frozenset({
    'pbs.twimg.com', 'video.twimg.com',
    'images-ext-1.discordapp.net', 'images-ext-2.discordapp.net',
    'media.discordapp.net', 'cdn.discordapp.com',
})

TEXT_PATTERNS += tuple(re.compile(pattern) for pattern in (
    r'\b(?:link to|see|watch|unlock|get|find) (?:the |my |a )?'
    r'(?:free |full |uncensored )?(?:nude|naked|nuddy|nudd[yi]e|nudie) '
    r'(?:version|content|videos?|pics?|photos?)\b',
    r'\b(?:free |full |uncensored )?(?:nude|naked|nuddy|nudie) '
    r'(?:version|content|videos?|pics?|photos?) '
    r'(?:is |available )?(?:in|on|at|through) (?:my |the )?'
    r'(?:profile|bio|page|link)\b',
))


def trusted_embedded_media_url(url):
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme.lower() == 'https'
            and (parsed.hostname or '').lower() in EMBEDDED_MEDIA_HOSTS
            and parsed.username is None and parsed.password is None
            and parsed.port in (None, 443)
        )
    except (ValueError, UnicodeError):
        return False


class EmbeddedMediaDownload:
    size = 0

    def __init__(self, url, expected_kind=None):
        self.url = url
        self.expected_kind = expected_kind

    async def save(self, destination):
        import aiohttp

        if not trusted_embedded_media_url(self.url):
            raise ValueError('Unapproved embedded-media URL')
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=55),
            cookie_jar=aiohttp.DummyCookieJar(), trust_env=False,
        ) as session:
            async with session.get(self.url, allow_redirects=False) as response:
                if response.status != 200:
                    raise ValueError(f'Embedded-media HTTP status {response.status}')
                content_type = response.headers.get('Content-Type', '').lower()
                if not content_type.startswith(('image/', 'video/')):
                    raise ValueError('Embedded URL did not return an image or video')
                if self.expected_kind == 'video' and not content_type.startswith('video/'):
                    raise ValueError('Video URL returned a preview image instead of video')
                if response.content_length and response.content_length > MAX_MEDIA_BYTES:
                    raise ValueError('Embedded media exceeds 25 MiB')
                size = 0
                with open(destination, 'wb') as output:
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > MAX_MEDIA_BYTES:
                            raise ValueError('Embedded media exceeds 25 MiB')
                        output.write(chunk)
                if not size:
                    raise ValueError('Empty embedded-media response')


class Moderator(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True

        super().__init__(
            intents=intents,
            max_messages=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        state = Path(os.getenv('STATE_PATH', './data/moderation.sqlite3'))
        state.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite3.connect(state)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')

        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS adult_feed_v7 (
                domain TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS actions_v5 (
                case_id TEXT PRIMARY KEY,
                message_id INTEGER NOT NULL,
                digest TEXT NOT NULL,
                report TEXT NOT NULL,
                state TEXT NOT NULL,
                updated REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS actions_v5_message
                ON actions_v5(message_id, state);
            CREATE TABLE IF NOT EXISTS events_v5 (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                body TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(case_id, stage)
            );
            CREATE TABLE IF NOT EXISTS jobs_v3 (
                id INTEGER PRIMARY KEY,
                due REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS results_v3 (
                id INTEGER PRIMARY KEY,
                digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings_v3 (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS logs_v3 (
                id INTEGER PRIMARY KEY,
                body TEXT NOT NULL
            );
        ''')

        self.db.commit()
        self.worker = None
        self.feed_revision = self.setting('feed_revision', 'none')
        self.message_lock = asyncio.Lock()

    def setting(self, key, default):
        row = self.db.execute(
            'SELECT value FROM settings_v3 WHERE key=?',
            (key,),
        ).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.db.execute(
            'INSERT OR REPLACE INTO settings_v3 VALUES (?,?)',
            (key, str(value)),
        )
        self.db.commit()

    def enqueue(self, message_id, edited=False):
        self.db.execute(
            'INSERT OR IGNORE INTO jobs_v3(id) VALUES (?)',
            (message_id,),
        )
        if edited:
            self.db.execute(
                'UPDATE jobs_v3 SET due=0 WHERE id=?',
                (message_id,),
            )
        self.db.commit()

    async def setup_hook(self):
        self.scanner.start()

    async def on_ready(self):
        logger.info(
            'Connected as %s | NSFW channel=%s | live-link channel=%s '
            '| log=%s | output=%s | text patterns=%s',
            self.user,
            CHANNEL_ID,
            LIVE_LINKS_ONLY_CHANNEL_ID,
            MOD_LOG_ID,
            OUTPUT_CHANNEL_ID,
            len(TEXT_PATTERNS),
        )

    async def on_message(self, message):
        if message.channel.id == CHANNEL_ID and message.author.id != self.user.id:
            self.enqueue(message.id)

    async def on_raw_message_edit(self, payload):
        if payload.channel_id == CHANNEL_ID:
            self.enqueue(payload.message_id, edited=True)

    async def on_raw_message_delete(self, payload):
        if payload.channel_id == CHANNEL_ID:
            self.db.execute(
                'DELETE FROM jobs_v3 WHERE id=?',
                (payload.message_id,),
            )
            self.db.commit()

    async def close(self):
        task = self.scanner.get_task()
        self.scanner.cancel()

        if task and task is not asyncio.current_task():
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.worker is not None and self.worker.returncode is None:
            self.worker.kill()
            await self.worker.wait()
            self.worker = None

        try:
            await super().close()
        finally:
            self.db.close()

    async def scan_attachment(self, attachment):
        if attachment.size > MAX_MEDIA_BYTES:
            return {
                'blocked': False,
                'complete': False,
                'reason': 'Attachment exceeds 25 MiB',
            }

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'media'
            await asyncio.wait_for(attachment.save(source), timeout=60)

            worker = await asyncio.create_subprocess_exec(
                sys.executable,
                str(Path(__file__).resolve()),
                '--media-worker',
                str(source),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={
                    **os.environ,
                    'OMP_NUM_THREADS': '1',
                    'OPENBLAS_NUM_THREADS': '1',
                },
            )
            self.worker = worker

            try:
                output, _ = await asyncio.wait_for(
                    worker.communicate(),
                    timeout=180,
                )
                results = [
                    line[12:]
                    for line in output.decode(errors='replace').splitlines()
                    if line.startswith('SCAN_RESULT=')
                ]
                if worker.returncode != 0 or not results:
                    raise RuntimeError('Media worker failed')
                return json.loads(results[-1])
            finally:
                if worker.returncode is None:
                    worker.kill()
                    await worker.wait()
                if self.worker is worker:
                    self.worker = None

    def message_text(self, message):
        parts = [message.content or '']
        for embed in message.embeds:
            parts.extend([
                embed.title or '',
                embed.description or '',
                embed.url or '',
            ])
            for field in embed.fields:
                parts.extend([field.name, field.value])
            for media in (embed.image, embed.thumbnail, embed.video):
                if media:
                    parts.append(media.url or '')
        return '\n'.join(parts)

    def fingerprint(self, message):
        data = {
            'policy': POLICY_VERSION + ':' + self.feed_revision,
            'text': self.message_text(message),
            'attachments': [
                (a.id, a.filename, a.size)
                for a in message.attachments
            ],
            'edited': str(message.edited_at),
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def feed_blocked_domain(self, host):
        labels = host.lower().rstrip('.').split('.')

        if any(
            '.'.join(labels[index:]) in FEED_EXCLUDED_ROOTS
            for index in range(len(labels) - 1)
        ):
            return False

        for index in range(len(labels) - 1):
            if self.db.execute(
                'SELECT 1 FROM adult_feed_v7 WHERE domain=?',
                ('.'.join(labels[index:]),),
            ).fetchone():
                return True

        return False

    async def refresh_adult_feed(self):
        import aiohttp

        now = time.time()
        if now < float(self.setting('feed_next_attempt', '0')):
            return

        self.set_setting('feed_next_attempt', now + 3600)

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                async with session.get(ADULT_FEED_URL) as response:
                    response.raise_for_status()
                    chunks = []
                    size = 0

                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > FEED_MAX_BYTES:
                            raise ValueError('Domain feed exceeds configured limit')
                        chunks.append(chunk)

            data = b''.join(chunks)
            domains = parse_adult_feed(data.decode('utf-8-sig'))
            revision = hashlib.sha256(data).hexdigest()

            with self.db:
                self.db.execute('DELETE FROM adult_feed_v7')
                self.db.executemany(
                    'INSERT INTO adult_feed_v7 VALUES (?)',
                    ((domain,) for domain in domains),
                )
                self.db.execute(
                    'INSERT OR REPLACE INTO settings_v3 VALUES (?,?)',
                    ('feed_revision', revision),
                )
                self.db.execute(
                    'INSERT OR REPLACE INTO settings_v3 VALUES (?,?)',
                    ('feed_next_attempt', str(now + FEED_REFRESH_SECONDS)),
                )

            self.feed_revision = revision
            logger.info('Adult domain cache refreshed: %s entries', len(domains))

        except Exception:
            logger.exception(
                'Adult domain refresh failed; using cached and built-in rules'
            )

    async def inspect(self, message):
        reason = text_violation(
            self.message_text(message),
            self.feed_blocked_domain,
        )
        if reason:
            return reason, []

        limitations = []

        for attachment in message.attachments:
            extension = Path(attachment.filename).suffix.lower()
            if not (
                (attachment.content_type or '').startswith(('image/', 'video/'))
                or extension in {
                    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
                    '.mp4', '.mov', '.webm', '.mkv',
                }
            ):
                limitations.append('Unsupported attachment type')
                continue

            result = await self.scan_attachment(attachment)
            if result['blocked']:
                return 'Nudity detected in attached media', []
            if not result['complete']:
                limitations.append(result.get('reason', 'Incomplete media scan'))

        seen_media = set()
        for embed in message.embeds:
            if getattr(embed, 'type', '') in {'video', 'gifv'} and not getattr(embed.video, 'url', None):
                limitations.append('Video embed has no downloadable full-video URL')
            for media_kind, media in (
                ('video', embed.video), ('image', embed.image), ('image', embed.thumbnail),
            ):
                if not media or not media.url or (media_kind, media.url) in seen_media:
                    continue
                seen_media.add((media_kind, media.url))
                candidates = list(dict.fromkeys(
                    value for value in (getattr(media, 'proxy_url', None), media.url)
                    if value and trusted_embedded_media_url(value)
                ))
                if not candidates:
                    limitations.append('Embedded media host is not approved for download')
                    continue
                completed = False
                errors = []
                for url in candidates:
                    try:
                        result = await self.scan_attachment(
                            EmbeddedMediaDownload(url, expected_kind=media_kind))
                        if result['blocked']:
                            return 'Nudity detected in linked or embedded media', []
                        if result['complete'] and (
                            media_kind != 'video' or result.get('media_kind') == 'video'
                        ):
                            completed = True
                            break
                        errors.append(result.get('reason', 'Media type or completeness not verified'))
                    except Exception as exc:
                        errors.append(f'{type(exc).__name__}: {str(exc)[:180]}')
                        logger.warning('Embedded %s scan incomplete | message=%s | %s',
                                       media_kind, message.id, errors[-1])
                if not completed:
                    limitations.append(
                        f'Embedded {media_kind} incomplete: ' + '; '.join(errors)[:400])

        x_posts = []
        for url in section_link_candidates(message):
            try:
                parsed = urlsplit(url if '://' in url else 'https://' + url)
                host = (parsed.hostname or '').lower().removeprefix('www.')
                if host in {
                    'x.com', 'twitter.com', 'vxtwitter.com', 'fxtwitter.com',
                    'fixupx.com', 'fixvx.com',
                } and re.fullmatch(r'/[^/]+/status/[0-9]+/?', parsed.path):
                    x_posts.append(url)
            except ValueError:
                continue
        if x_posts and not seen_media:
            limitations.append('X status link has no accessible media; cannot verify whether it contains media')

        if limitations:
            self.record_incomplete_scan(message, limitations)

        return None, limitations

    def record_incomplete_scan(self, message, limitations):
        digest = self.fingerprint(message)
        case_id = f'scan-review-{message.id}-{digest[:12]}'
        body = (
            f'MEDIA SCAN INCOMPLETE / REVIEW REQUIRED | Case {case_id}\n'
            f'Server ID: {message.guild.id}\nChannel ID: {message.channel.id}\n'
            f'Message ID: {message.id}\nAuthor ID: {message.author.id}\n'
            f'Original message: {message.jump_url}\n'
            f'Posted UTC: {message.created_at.isoformat()}\n'
            f'Reported UTC: {discord.utils.utcnow().isoformat()}\n'
            f'Details: {"; ".join(sorted(set(limitations)))[:650]}\n'
            'NSFW status is unconfirmed. This is not a clean result. '
            'No timeout is applied solely because media was inaccessible. '
            'Live-link reposting is withheld. Retry scheduled; moderator review required. '
            'No media is copied into this log.'
        )
        with self.db:
            self.record_event(case_id, 'media_review', body)
        logger.warning('Media requires review | message=%s | %s', message.id, limitations)

    def record_event(self, case_id, stage, body):
        self.db.execute(
            'INSERT OR IGNORE INTO events_v5(case_id,stage,body) VALUES (?,?,?)',
            (case_id, stage, body),
        )

    def start_action(self, message, digest, reason):
        case_id = uuid.uuid4().hex[:16]
        report = {
            'case_id': case_id,
            'guild_id': message.guild.id,
            'channel_id': message.channel.id,
            'message_id': message.id,
            'author_id': message.author.id,
            'message_link': message.jump_url,
            'posted_utc': message.created_at.isoformat(),
            'detected_utc': discord.utils.utcnow().isoformat(),
            'reason': reason,
            'fingerprint': digest,
            'attachment_ids': [a.id for a in message.attachments],
            'attachment_sizes': [a.size for a in message.attachments],
            'attachment_count': len(message.attachments),
        }

        with self.db:
            self.db.execute(
                'INSERT INTO actions_v5 VALUES (?,?,?,?,?,?)',
                (
                    case_id,
                    message.id,
                    digest,
                    json.dumps(report),
                    'planned',
                    time.time(),
                ),
            )
            self.record_event(
                case_id,
                'before',
                self.report_body(
                    report,
                    'BEFORE',
                    'Deletion planned; not yet confirmed.',
                ),
            )

        return case_id

    def report_body(self, report, stage, status):
        return (
            f"{stage} DELETION REPORT | Case {report['case_id']}\n"
            f"Status: {status}\n"
            f"Server ID: {report['guild_id']}\n"
            f"Channel ID: {report['channel_id']}\n"
            f"Message ID: {report['message_id']}\n"
            f"Author ID: {report['author_id']}\n"
            f"Original message: {report['message_link']}\n"
            f"Posted UTC: {report['posted_utc']}\n"
            f"Detected UTC: {report['detected_utc']}\n"
            f"Reported UTC: {discord.utils.utcnow().isoformat()}\n"
            f"Reason: {report['reason']}\n"
            f"Attachments: {report['attachment_count']}\n"
            f"Attachment IDs: {report['attachment_ids']}\n"
            f"Attachment sizes in bytes: {report['attachment_sizes']}\n"
            f"Fingerprint: {report['fingerprint']}\n"
            'Report contains metadata only; no message text or media copy.'
        )

    def complete_action(self, case_id, state, status):
        row = self.db.execute(
            'SELECT report FROM actions_v5 WHERE case_id=?',
            (case_id,),
        ).fetchone()
        if not row:
            return

        report = json.loads(row[0])

        with self.db:
            self.db.execute(
                'UPDATE actions_v5 SET state=?,updated=? WHERE case_id=?',
                (state, time.time(), case_id),
            )
            self.record_event(
                case_id,
                state,
                self.report_body(report, 'AFTER', status),
            )
            if state == 'confirmed':
                self.record_event(
                    case_id,
                    'output_confirmed',
                    f"Removed message {report['message_id']} in <#{report['channel_id']}>. "
                    f"Reason: {report['reason']} | Case {case_id}",
                )

    async def execute_action(self, channel, case_id):
        row = self.db.execute(
            'SELECT message_id,digest,report,state FROM actions_v5 WHERE case_id=?',
            (case_id,),
        ).fetchone()

        if not row or row[3] not in {'planned', 'deleting', 'retry'}:
            return

        message_id, digest, report_json, state = row
        report = json.loads(report_json)

        await self.flush_logs(case_id)

        try:
            latest = await channel.fetch_message(message_id)
        except discord.NotFound:
            self.complete_action(
                case_id,
                'missing',
                'Message is absent. Who removed it cannot be confirmed; '
                'a prior bot deletion may have succeeded before interruption.',
            )
            self.finish(message_id)
            await self.flush_logs(case_id)
            return

        if self.fingerprint(latest) != digest:
            self.complete_action(
                case_id,
                'changed',
                'Deletion cancelled because the message or policy changed; '
                'queued for a fresh scan.',
            )
            self.enqueue(message_id, edited=True)
            await self.flush_logs(case_id)
            return

        with self.db:
            self.db.execute(
                "UPDATE actions_v5 SET state='deleting',updated=? WHERE case_id=?",
                (time.time(), case_id),
            )

        try:
            await latest.delete()

        except discord.NotFound:
            self.complete_action(
                case_id,
                'missing',
                'Message disappeared before deletion was acknowledged; deleter unconfirmed.',
            )

        except Exception as exc:
            logger.exception(
                'NSFW deletion failed | case=%s | message=%s',
                case_id,
                message_id,
            )
            with self.db:
                self.db.execute(
                    "UPDATE actions_v5 SET state='retry',updated=? WHERE case_id=?",
                    (time.time(), case_id),
                )
                self.record_event(
                    case_id,
                    'failed',
                    self.report_body(
                        report,
                        'AFTER',
                        f'Deletion not confirmed: {type(exc).__name__}: {exc}; '
                        'retry scheduled.',
                    ),
                )
                self.db.execute(
                    'INSERT OR REPLACE INTO jobs_v3(id,due) VALUES (?,?)',
                    (message_id, time.time() + 600),
                )
            await self.flush_logs(case_id)
            return

        else:
            self.complete_action(
                case_id,
                'confirmed',
                'Discord acknowledged successful deletion by this bot.',
            )
            logger.info(
                'NSFW message deleted | case=%s | message=%s',
                case_id,
                message_id,
            )

        self.finish(message_id)
        await self.flush_logs(case_id)

    async def recover_actions(self, channel):
        rows = self.db.execute(
            "SELECT case_id FROM actions_v5 WHERE state IN ('planned','deleting','retry') "
            'ORDER BY updated LIMIT 100'
        ).fetchall()

        for (case_id,) in rows:
            try:
                async with self.message_lock:
                    await self.execute_action(channel, case_id)
            except Exception:
                logger.exception('Case recovery failed | case=%s', case_id)

    async def handle(self, channel, message_id):
        try:
            active = self.db.execute(
                "SELECT case_id FROM actions_v5 WHERE message_id=? "
                "AND state IN ('planned','deleting','retry') ORDER BY updated LIMIT 1",
                (message_id,),
            ).fetchone()

            if active:
                await self.execute_action(channel, active[0])
                return

            message = await channel.fetch_message(message_id)
            if message.author.id == self.user.id:
                self.finish(message_id)
                return

            digest = self.fingerprint(message)
            row = self.db.execute(
                'SELECT digest FROM results_v3 WHERE id=?',
                (message_id,),
            ).fetchone()

            if row and row[0] == digest:
                self.finish(message_id)
                return

            reason, limitations = await self.inspect(message)

            if reason:
                case_id = self.start_action(message, digest, reason)
                await self.execute_action(channel, case_id)

            elif limitations:
                logger.warning(
                    'Incomplete scan for %s: %s',
                    message_id,
                    '; '.join(set(limitations)),
                )
                self.db.execute(
                    'UPDATE jobs_v3 SET due=? WHERE id=?',
                    (time.time() + SCAN_MINUTES * 60, message_id),
                )
                self.db.commit()

            else:
                self.db.execute(
                    'INSERT OR REPLACE INTO results_v3 VALUES (?,?)',
                    (message_id, digest),
                )
                self.finish(message_id)

        except discord.NotFound:
            self.finish(message_id)

        except Exception:
            logger.exception('Message scan failed | message=%s', message_id)
            with self.db:
                self.db.execute(
                    'INSERT OR REPLACE INTO jobs_v3(id,due) VALUES (?,?)',
                    (message_id, time.time() + 600),
                )

    def finish(self, message_id):
        self.db.execute(
            'DELETE FROM jobs_v3 WHERE id=?',
            (message_id,),
        )
        self.db.commit()

    async def flush_logs(self, case_id=None):
        query = 'SELECT sequence,body,stage FROM events_v5 WHERE sent=0'
        params = ()

        if case_id:
            query += ' AND case_id=?'
            params = (case_id,)

        rows = self.db.execute(
            query + ' ORDER BY sequence LIMIT 100',
            params,
        ).fetchall()

        legacy = [] if case_id else self.db.execute(
            'SELECT id,body FROM logs_v3 ORDER BY id LIMIT 100'
        ).fetchall()

        for sequence, body, stage in rows:
            try:
                target_id = MOD_LOG_ID
                channel = (
                    self.get_channel(target_id)
                    or await self.fetch_channel(target_id)
                )
                await channel.send(
                    body[:2000],
                    suppress_embeds=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                self.db.execute(
                    'UPDATE events_v5 SET sent=1 WHERE sequence=?',
                    (sequence,),
                )
                self.db.commit()
            except Exception:
                logger.exception(
                    'Moderator report retained | sequence=%s',
                    sequence,
                )

        for message_id, body in legacy:
            try:
                channel = (
                    self.get_channel(MOD_LOG_ID)
                    or await self.fetch_channel(MOD_LOG_ID)
                )
                await channel.send(
                    body[:2000],
                    suppress_embeds=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                self.db.execute(
                    'DELETE FROM logs_v3 WHERE id=?',
                    (message_id,),
                )
                self.db.commit()
            except Exception:
                logger.exception(
                    'Legacy moderator report retained | message=%s',
                    message_id,
                )

    async def discover(self, channel):
        initial = discord.utils.time_snowflake(
            discord.utils.utcnow() - timedelta(hours=24)
        )
        cursor = int(self.setting('cursor', str(initial)))

        async for message in channel.history(
            limit=None,
            after=discord.Object(id=cursor),
            oldest_first=True,
        ):
            self.enqueue(message.id)
            self.set_setting('cursor', message.id)

        before_id = int(self.setting('audit_before', '0'))
        count = 0

        async for message in channel.history(
            limit=100,
            before=discord.Object(id=before_id) if before_id else None,
            oldest_first=False,
        ):
            self.enqueue(message.id)
            self.set_setting('audit_before', message.id)
            count += 1

        if count < 100:
            self.set_setting('audit_before', 0)

    @tasks.loop(minutes=SCAN_MINUTES)
    async def scanner(self):
        logger.info('NSFW scan started | channel=%s', CHANNEL_ID)

        try:
            channel = (
                self.get_channel(CHANNEL_ID)
                or await self.fetch_channel(CHANNEL_ID)
            )
            permissions = channel.permissions_for(channel.guild.me)

            if not (
                permissions.view_channel
                and permissions.read_message_history
                and permissions.manage_messages
            ):
                raise PermissionError(
                    'Bot needs View Channel, Read Message History, and Manage Messages '
                    f'in channel {CHANNEL_ID}'
                )

            await self.refresh_adult_feed()
            await self.recover_actions(channel)

            try:
                await self.discover(channel)
            except Exception:
                logger.exception(
                    'NSFW history discovery failed; processing queued messages'
                )

            jobs = self.db.execute(
                'SELECT id FROM jobs_v3 WHERE due<=? ORDER BY id LIMIT 300',
                (time.time(),),
            ).fetchall()

            for (message_id,) in jobs:
                async with self.message_lock:
                    await self.handle(channel, message_id)

            logger.info(
                'NSFW scan completed | queued messages processed=%s',
                len(jobs),
            )

        except Exception:
            logger.exception('NSFW scan cycle failed')

        await self.flush_logs()

    @scanner.before_loop
    async def before_scan(self):
        await self.wait_until_ready()
        await asyncio.sleep(SCAN_MINUTES * 60)


class LiveLinksOnlyGuard:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS section_jobs_v1 (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                due REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS section_clean_v1 (
                message_id INTEGER PRIMARY KEY,
                digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS section_cases_v1 (
                case_id TEXT PRIMARY KEY,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                digest TEXT NOT NULL,
                report TEXT NOT NULL,
                state TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS section_events_v1 (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                body TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(case_id, stage)
            );
            CREATE TABLE IF NOT EXISTS section_delivery_v1 (
                sequence INTEGER PRIMARY KEY,
                next_part INTEGER NOT NULL DEFAULT 0
            );
        ''')
        self.db.commit()

    def enqueue(self, channel_id, message_id, edited=False):
        if (
            not LIVE_LINKS_ONLY_CHANNEL_ID
            or channel_id != LIVE_LINKS_ONLY_CHANNEL_ID
        ):
            return

        self.db.execute(
            'INSERT OR IGNORE INTO section_jobs_v1(message_id,channel_id) VALUES (?,?)',
            (message_id, channel_id),
        )

        if edited:
            self.db.execute(
                'UPDATE section_jobs_v1 SET due=0 WHERE message_id=?',
                (message_id,),
            )

        self.db.commit()

    def digest(self, message):
        data = [
            LIVE_LINKS_POLICY,
            message.content,
            [e.url for e in message.embeds],
            str(message.edited_at),
        ]
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def event(self, case_id, stage, report, status):
        body = (
            f"{'BEFORE' if stage == 'before' else 'AFTER / ' + stage.upper()} "
            f"| LIVE LINKS ONLY | Case {case_id}\n"
            f'Status: {status}\n'
            f"Server ID: {report['guild_id']}\n"
            f"Channel ID: {report['channel_id']}\n"
            f"Message ID: {report['message_id']}\n"
            f"Author ID: {report['author_id']}\n"
            f"Original message: {report['message_link']}\n"
            f"Posted UTC: {report['posted']}\n"
            f"Detected UTC: {report['detected']}\n"
            f'Reported UTC: {discord.utils.utcnow().isoformat()}\n'
            f"Reason: {report['reason']}\n"
            f"Fingerprint: {report['digest']}\n"
            'Discord log contains metadata only; repost text is stored separately.'
        )

        self.db.execute(
            'INSERT OR IGNORE INTO section_events_v1(case_id,stage,body) VALUES (?,?,?)',
            (case_id, stage, body),
        )

        if stage == 'confirmed':
            notice = report.get('repost_body') or (
                f"Removed message {report['message_id']} in <#{report['channel_id']}>. "
                f"Reason: {report.get('repost_blocked_reason') or 'live-links-only section violation'}. "
                f"Case {case_id}"
            )
            self.db.execute(
                'INSERT OR IGNORE INTO section_events_v1(case_id,stage,body) VALUES (?,?,?)',
                (case_id, 'output_confirmed', notice),
            )

    def finish(self, message_id):
        self.db.execute(
            'DELETE FROM section_jobs_v1 WHERE message_id=?',
            (message_id,),
        )
        self.db.commit()

    def terminal(self, case_id, message_id, state, report, status):
        with self.db:
            self.db.execute(
                'UPDATE section_cases_v1 SET state=? WHERE case_id=?',
                (state, case_id),
            )
            self.event(case_id, state, report, status)
            self.db.execute(
                'DELETE FROM section_jobs_v1 WHERE message_id=?',
                (message_id,),
            )

    async def flush(self, case_id=None):
        sql = 'SELECT sequence,body,stage FROM section_events_v1 WHERE sent=0'
        args = ()

        if case_id:
            sql += ' AND case_id=?'
            args = (case_id,)

        rows = self.db.execute(
            sql + ' ORDER BY sequence LIMIT 100',
            args,
        ).fetchall()

        for sequence, body, stage in rows:
            try:
                target_id = (
                    OUTPUT_CHANNEL_ID
                    if stage == 'output_confirmed'
                    else MOD_LOG_ID
                )
                channel = (
                    self.bot.get_channel(target_id)
                    or await self.bot.fetch_channel(target_id)
                )

                if stage == 'output_confirmed':
                    rule = LINK_REPOST_RULES[LIVE_LINKS_ONLY_CHANNEL_ID]
                    member = channel.guild.me or await channel.guild.fetch_member(self.bot.user.id)
                    permissions = channel.permissions_for(member)
                    if not all(getattr(permissions, key, False) for key in rule['output_permissions']):
                        raise PermissionError('Link output channel is missing send/embed permissions')

                progress = self.db.execute(
                    'SELECT next_part FROM section_delivery_v1 WHERE sequence=?',
                    (sequence,),
                ).fetchone()

                next_part = progress[0] if progress else 0
                parts = [
                    body[offset:offset + 2000]
                    for offset in range(0, len(body), 2000)
                ]

                for index in range(next_part, len(parts)):
                    await channel.send(
                        parts[index],
                        suppress_embeds=(stage != 'output_confirmed'),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    with self.db:
                        self.db.execute(
                            'INSERT OR REPLACE INTO section_delivery_v1 VALUES (?,?)',
                            (sequence, index + 1),
                        )

                with self.db:
                    self.db.execute(
                        'UPDATE section_events_v1 SET sent=1 WHERE sequence=?',
                        (sequence,),
                    )
                    self.db.execute(
                        'DELETE FROM section_delivery_v1 WHERE sequence=?',
                        (sequence,),
                    )

                if stage == 'output_confirmed':
                    logger.info(
                        'Live-link output delivered | channel=%s | sequence=%s',
                        target_id,
                        sequence,
                    )

            except Exception:
                logger.exception(
                    'Live-link report/output retained | sequence=%s | stage=%s',
                    sequence,
                    stage,
                )

    async def process(self, channel, message_id):
        active = self.db.execute(
            "SELECT case_id,digest,report FROM section_cases_v1 WHERE message_id=? "
            "AND channel_id=? AND state IN ('planned','deleting','retry') LIMIT 1",
            (message_id, channel.id),
        ).fetchone()

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            if active:
                self.terminal(
                    active[0],
                    message_id,
                    'missing',
                    json.loads(active[2]),
                    'Message is absent; who removed it is unconfirmed.',
                )
                await self.flush(active[0])
            else:
                self.finish(message_id)
            return

        if message.author.id == self.bot.user.id:
            self.finish(message_id)
            return

        digest = self.digest(message)

        if active and active[1] != digest:
            self.terminal(
                active[0],
                message_id,
                'changed',
                json.loads(active[2]),
                'Deletion cancelled because the message or policy changed; '
                'fresh scan queued.',
            )
            self.enqueue(channel.id, message_id, edited=True)
            await self.flush(active[0])
            return

        if active:
            case_id, old_digest, report_json = active
            report = json.loads(report_json)

        else:
            clean = self.db.execute(
                'SELECT digest FROM section_clean_v1 WHERE message_id=?',
                (message_id,),
            ).fetchone()

            if clean and clean[0] == digest:
                self.finish(message_id)
                return

            links = section_link_candidates(message)
            rejected = []
            unresolved = False

            for link in links:
                decision = await section_link_allowed_resolved(link)
                if decision is False:
                    rejected.append(link)
                elif decision is None:
                    unresolved = True

            if unresolved and not rejected:
                self.db.execute(
                    'UPDATE section_jobs_v1 SET due=? WHERE message_id=?',
                    (time.time() + 600, message_id),
                )
                self.db.commit()
                logger.warning(
                    'TikTok share pending resolution | message=%s',
                    message_id,
                )
                return

            if not rejected:
                with self.db:
                    self.db.execute(
                        'INSERT OR REPLACE INTO section_clean_v1 VALUES (?,?)',
                        (message_id, digest),
                    )
                    self.db.execute(
                        'DELETE FROM section_jobs_v1 WHERE message_id=?',
                        (message_id,),
                    )
                return

            case_id = uuid.uuid4().hex[:16]
            blocked_reason = text_violation(
                self.bot.message_text(message),
                self.bot.feed_blocked_domain,
            )

            report = {
                'guild_id': message.guild.id,
                'channel_id': channel.id,
                'message_id': message_id,
                'author_id': message.author.id,
                'message_link': message.jump_url,
                'posted': message.created_at.isoformat(),
                'detected': discord.utils.utcnow().isoformat(),
                'digest': digest,
                'reason': (
                    f'{len(rejected)} link(s) did not match approved live-link formats.'
                ),
                'repost_body': (
                    section_repost_body(message)
                    if not blocked_reason
                    else None
                ),
                'repost_blocked_reason': blocked_reason,
            }

            with self.db:
                self.db.execute(
                    'INSERT INTO section_cases_v1 VALUES (?,?,?,?,?,?)',
                    (
                        case_id,
                        message_id,
                        channel.id,
                        digest,
                        json.dumps(report),
                        'planned',
                    ),
                )
                self.event(
                    case_id,
                    'before',
                    report,
                    'Deletion planned; not yet confirmed.',
                )

            logger.info(
                'Live-link violation detected | case=%s | message=%s '
                '| links=%s | rejected=%s',
                case_id,
                message_id,
                len(links),
                len(rejected),
            )

        await self.flush(case_id)

        try:
            latest = await channel.fetch_message(message_id)
        except discord.NotFound:
            self.terminal(
                case_id,
                message_id,
                'missing',
                report,
                'Message disappeared before deletion; deleter unconfirmed.',
            )
            await self.flush(case_id)
            return

        if self.digest(latest) != digest:
            self.terminal(
                case_id,
                message_id,
                'changed',
                report,
                'Deletion cancelled because the message changed; fresh scan queued.',
            )
            self.enqueue(channel.id, message_id, edited=True)
            await self.flush(case_id)
            return

        nsfw_reason, scan_limits = await self.bot.inspect(latest)

        if nsfw_reason:
            report['repost_body'] = None
            report['repost_blocked_reason'] = nsfw_reason
            self.terminal(
                case_id, message_id, 'blocked_nsfw', report,
                'Repost blocked by NSFW moderation: ' + nsfw_reason,
            )
            nsfw_case = self.bot.start_action(
                latest, self.bot.fingerprint(latest), nsfw_reason,
            )
            await self.bot.execute_action(channel, nsfw_case)
            await self.flush(case_id)
            return

        if scan_limits:
            with self.db:
                self.db.execute(
                    'UPDATE section_jobs_v1 SET due=? WHERE message_id=?',
                    (time.time() + 600, message_id),
                )
                self.event(
                    case_id, 'scan_pending', report,
                    'Repost withheld because media inspection is incomplete: '
                    + '; '.join(sorted(set(scan_limits))),
                )
            await self.flush(case_id)
            return

        if any(
            label.startswith('Possible direct statement')
            for phrase, label in troll_comment_findings(latest.content)
        ):
            self.bot.troll_flagger.enqueue(channel.id, message_id)
            with self.db:
                self.db.execute(
                    'UPDATE section_jobs_v1 SET due=? WHERE message_id=?',
                    (time.time() + 600, message_id),
                )
                self.event(
                    case_id, 'hate_pending', report,
                    'Repost withheld: direct hate-text match queued for moderation.',
                )
            await self.flush(case_id)
            return

        report['repost_body'] = (
            section_repost_body(latest)
            if not nsfw_reason
            else None
        )
        report['repost_blocked_reason'] = nsfw_reason

        if nsfw_reason and hasattr(self.bot, 'schedule_violation_timeout'):
            self.bot.schedule_violation_timeout(
                'nsfw-section-' + case_id,
                latest,
                'NSFW violation: ' + nsfw_reason,
            )

        with self.db:
            self.db.execute(
                "UPDATE section_cases_v1 SET state='deleting',report=? WHERE case_id=?",
                (json.dumps(report), case_id),
            )

        try:
            await latest.delete()

        except discord.NotFound:
            self.terminal(
                case_id,
                message_id,
                'missing',
                report,
                'Message disappeared during deletion; deleter unconfirmed.',
            )

        except Exception as exc:
            logger.exception(
                'Live-link deletion failed | case=%s | message=%s',
                case_id,
                message_id,
            )
            with self.db:
                self.db.execute(
                    "UPDATE section_cases_v1 SET state='retry' WHERE case_id=?",
                    (case_id,),
                )
                self.event(
                    case_id,
                    'failed',
                    report,
                    f'Deletion not confirmed: {type(exc).__name__}: {exc}; '
                    'retry scheduled.',
                )
                self.db.execute(
                    'UPDATE section_jobs_v1 SET due=? WHERE message_id=?',
                    (time.time() + 600, message_id),
                )

        else:
            self.terminal(
                case_id,
                message_id,
                'confirmed',
                report,
                'Discord acknowledged deletion by this bot.',
            )
            logger.info(
                'Live-link message deleted | case=%s | message=%s',
                case_id,
                message_id,
            )

        await self.flush(case_id)

    async def discover(self, channel):
        prefix = 'live_section_' + str(channel.id) + '_'
        initial = discord.utils.time_snowflake(
            discord.utils.utcnow() - timedelta(hours=24)
        )
        cursor = int(self.bot.setting(prefix + 'cursor', str(initial)))

        async for message in channel.history(
            limit=None,
            after=discord.Object(id=cursor),
            oldest_first=True,
        ):
            self.enqueue(channel.id, message.id)
            self.bot.set_setting(prefix + 'cursor', message.id)

        before_id = int(self.bot.setting(prefix + 'audit', '0'))
        count = 0

        async for message in channel.history(
            limit=100,
            before=discord.Object(id=before_id) if before_id else None,
            oldest_first=False,
        ):
            self.enqueue(channel.id, message.id)
            self.bot.set_setting(prefix + 'audit', message.id)
            count += 1

        if count < 100:
            self.bot.set_setting(prefix + 'audit', 0)

    @tasks.loop(minutes=LIVE_LINKS_SCAN_MINUTES)
    async def loop(self):
        if not LIVE_LINKS_ONLY_CHANNEL_ID:
            return

        logger.info(
            'Live-link scan started | channel=%s',
            LIVE_LINKS_ONLY_CHANNEL_ID,
        )

        try:
            channel = (
                self.bot.get_channel(LIVE_LINKS_ONLY_CHANNEL_ID)
                or await self.bot.fetch_channel(LIVE_LINKS_ONLY_CHANNEL_ID)
            )
            permissions = channel.permissions_for(channel.guild.me)

            if not (
                permissions.view_channel
                and permissions.read_message_history
                and permissions.manage_messages
            ):
                raise PermissionError(
                    'Live-link section needs View Channel, Read Message History, '
                    f'and Manage Messages in channel {channel.id}'
                )

            try:
                await self.discover(channel)
            except Exception:
                logger.exception(
                    'Live-link discovery failed; using queued messages'
                )

            rows = self.db.execute(
                'SELECT message_id FROM section_jobs_v1 '
                'WHERE channel_id=? AND due<=? ORDER BY message_id LIMIT 300',
                (channel.id, time.time()),
            ).fetchall()

            for (message_id,) in rows:
                try:
                    async with self.bot.message_lock:
                        await self.process(channel, message_id)
                except Exception:
                    logger.exception(
                        'Live-link processing failed | message=%s',
                        message_id,
                    )
                    self.db.execute(
                        'UPDATE section_jobs_v1 SET due=? WHERE message_id=?',
                        (time.time() + 600, message_id),
                    )
                    self.db.commit()

            logger.info(
                'Live-link scan completed | queued messages processed=%s',
                len(rows),
            )

        except Exception:
            logger.exception('Live-link section scan failed')

        await self.flush()

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(LIVE_LINKS_SCAN_MINUTES * 60)


class CauseAwareLiveLinksOnlyGuard(LiveLinksOnlyGuard):
    def digest(self, message):
        original = super().digest(message)
        policy = (
            f'{CAUSE_EXCEPTION_POLICY}:'
            f'{CAUSE_EXCEPTION_USERNAME}:'
            f'{CAUSE_EXCEPTION_USER_ID}'
        )
        return hashlib.sha256(
            f'{original}:{policy}'.encode()
        ).hexdigest()

    async def process(self, channel, message_id):
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await super().process(channel, message_id)

        qualifies = (
            channel.id == LIVE_LINKS_ONLY_CHANNEL_ID
            and is_cause_announcement(message)
        )

        if qualifies and text_violation(
            self.bot.message_text(message),
            self.bot.feed_blocked_domain,
        ):
            qualifies = False

        if not qualifies:
            return await super().process(channel, message_id)

        active_cases = self.db.execute(
            "SELECT case_id,report FROM section_cases_v1 "
            "WHERE message_id=? AND channel_id=? "
            "AND state IN ('planned','deleting','retry')",
            (message_id, channel.id),
        ).fetchall()

        for case_id, report_json in active_cases:
            report = json.loads(report_json)
            report.pop('repost_body', None)
            self.terminal(
                case_id,
                message_id,
                'exempt',
                report,
                'Link-rule deletion cancelled: designated account posted '
                'a qualifying cause announcement. NSFW moderation remains active.',
            )

        with self.db:
            self.db.execute(
                'INSERT OR REPLACE INTO section_clean_v1 VALUES (?,?)',
                (message_id, self.digest(message)),
            )
            self.db.execute(
                'DELETE FROM section_jobs_v1 WHERE message_id=?',
                (message_id,),
            )

        if channel.id == CHANNEL_ID:
            self.bot.enqueue(message_id)

        logger.info(
            'Cause announcement allowed | author_id=%s | message=%s',
            message.author.id,
            message_id,
        )

        if active_cases:
            await self.flush()


class LiveSectionModerator(Moderator):
    def __init__(self):
        super().__init__()
        self.live_link_guard = CauseAwareLiveLinksOnlyGuard(self)

    async def setup_hook(self):
        await super().setup_hook()
        if LIVE_LINKS_ONLY_CHANNEL_ID:
            self.live_link_guard.loop.start()

    async def on_message(self, message):
        await super().on_message(message)
        if message.author.id != self.user.id:
            self.live_link_guard.enqueue(
                message.channel.id,
                message.id,
            )

    async def on_raw_message_edit(self, payload):
        await super().on_raw_message_edit(payload)
        self.live_link_guard.enqueue(
            payload.channel_id,
            payload.message_id,
            edited=True,
        )

    async def close(self):
        task = self.live_link_guard.loop.get_task()
        self.live_link_guard.loop.cancel()

        if task and task is not asyncio.current_task():
            try:
                await task
            except asyncio.CancelledError:
                pass

        await super().close()


class TrollFlagger:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS troll_jobs_v1 (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS troll_seen_v1 (
                message_id INTEGER PRIMARY KEY,
                digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS troll_outbox_v1 (
                case_id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            );
        ''')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS hate_deletions_v1 (
                case_id TEXT PRIMARY KEY,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS hate_deletion_logs_v1 (
                case_id TEXT NOT NULL,
                part TEXT NOT NULL,
                body TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(case_id,part)
            );
        ''')
        self.db.commit()

    def enqueue(self, channel_id, message_id):
        if channel_id in self.bot.moderation_channel_ids():
            with self.db:
                self.db.execute(
                    'INSERT OR IGNORE INTO troll_jobs_v1 VALUES (?,?)',
                    (message_id, channel_id),
                )

    def deletion_log(self, case_id, part, body):
        self.db.execute(
            'INSERT OR IGNORE INTO hate_deletion_logs_v1 '
            '(case_id,part,body) VALUES (?,?,?)',
            (case_id, part, body),
        )

    async def flush_deletion_logs(self, case_id):
        channel = (self.bot.get_channel(MOD_LOG_ID)
                   or await self.bot.fetch_channel(MOD_LOG_ID))
        rows = self.db.execute(
            'SELECT part,body FROM hate_deletion_logs_v1 '
            'WHERE case_id=? AND sent=0 ORDER BY part', (case_id,),
        ).fetchall()
        for part, body in rows:
            await channel.send(body, suppress_embeds=True,
                               allowed_mentions=discord.AllowedMentions.none())
            with self.db:
                self.db.execute(
                    'UPDATE hate_deletion_logs_v1 SET sent=1 '
                    'WHERE case_id=? AND part=?', (case_id, part),
                )

    async def process_deletion(self, channel, row):
        case_id, message_id, original, state = row
        await self.flush_deletion_logs(case_id)
        if state != 'pending':
            return
        try:
            latest = await channel.fetch_message(message_id)
        except discord.NotFound:
            result = 'Message already absent; bot deletion cannot be confirmed.'
            final_state = 'absent'
        else:
            findings = troll_comment_findings(latest.content)
            if latest.content != original or not any(
                label.startswith('Possible direct statement')
                for phrase, label in findings
            ):
                result = 'Deletion cancelled: message changed; queued for rescan.'
                final_state = 'changed'
                with self.db:
                    self.db.execute('DELETE FROM troll_seen_v1 WHERE message_id=?',
                                    (message_id,))
                self.enqueue(channel.id, message_id)
            else:
                try:
                    await latest.delete()
                except discord.NotFound:
                    result = 'Message disappeared during deletion; outcome unconfirmed.'
                    final_state = 'absent'
                except Exception as exc:
                    with self.db:
                        self.deletion_log(
                            case_id, 'failed-' + uuid.uuid4().hex,
                            f'AFTER / FAILED | HATE TEXT | Case {case_id}\n'
                            f'Message ID: {message_id}\n'
                            f'{type(exc).__name__}: {exc}\nRetry next scan.',
                        )
                    await self.flush_deletion_logs(case_id)
                    return
                else:
                    result = 'Discord confirmed message deletion.'
                    final_state = 'deleted'
        with self.db:
            self.db.execute('UPDATE hate_deletions_v1 SET state=? WHERE case_id=?',
                            (final_state, case_id))
            self.deletion_log(
                case_id, 'z-after',
                f'AFTER | HATE TEXT | Case {case_id}\n'
                f'Message ID: {message_id}\n{result}',
            )
        await self.flush_deletion_logs(case_id)

    async def check(self, channel, message_id):
        pending = self.db.execute(
            'SELECT case_id,message_id,content,state FROM hate_deletions_v1 '
            "WHERE message_id=? AND state='pending'", (message_id,),
        ).fetchall()
        for row in pending:
            await self.process_deletion(channel, row)
        if pending:
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            with self.db:
                self.db.execute(
                    'DELETE FROM troll_jobs_v1 WHERE message_id=?',
                    (message_id,),
                )
            return

        findings = (
            []
            if message.author.id == self.bot.user.id
            else troll_comment_findings(message.content)
        )

        digest = hashlib.sha256(
            (TROLL_FLAG_POLICY + ':' + (message.content or '')).encode()
        ).hexdigest()

        previous = self.db.execute(
            'SELECT digest FROM troll_seen_v1 WHERE message_id=?',
            (message_id,),
        ).fetchone()

        with self.db:
            if findings and (not previous or previous[0] != digest):
                case_id = uuid.uuid4().hex[:16]
                details = '\n'.join(
                    f'{label}: {phrase}' for phrase, label in findings
                )
                excerpt = (message.content or '')[:900]

                body = (
                    f'TROLL COMMENT REVIEW | Case {case_id}\n'
                    f'Author ID: {message.author.id}\n'
                    f'Channel: <#{channel.id}>\n'
                    f'Message ID: {message_id}\n'
                    f'Original: {message.jump_url}\n'
                    f'Posted UTC: {message.created_at.isoformat()}\n'
                    f'Flagged UTC: {discord.utils.utcnow().isoformat()}\n'
                    f'{details[:600]}\nMessage excerpt:\n{excerpt}\n'
                    'Intent is unconfirmed. Ambiguous matches are review-only. '
                    'Direct matches queue a 24-hour timeout; see timeout reports.'
                )

                self.db.execute(
                    'INSERT INTO troll_outbox_v1(case_id,body) VALUES (?,?)',
                    (case_id, body[:2000]),
                )

                if any(
                    label.startswith('Possible direct statement')
                    for phrase, label in findings
                ):
                    self.db.execute(
                        'INSERT INTO hate_deletions_v1 '
                        '(case_id,message_id,channel_id,content) VALUES (?,?,?,?)',
                        (case_id, message_id, channel.id, message.content or ''),
                    )
                    self.deletion_log(
                        case_id, 'a-before',
                        f'BEFORE | HATE TEXT | Case {case_id}\n'
                        f'Author ID: {message.author.id}\n'
                        f'Channel ID: {channel.id}\nMessage ID: {message_id}\n'
                        f'Posted UTC: {message.created_at.isoformat()}\n'
                        'Original message text follows in numbered parts. '
                        'Attachments are not copied.',
                    )
                    content = message.content or ''
                    parts = [content[i:i + 500] for i in range(0, len(content), 500)] or ['']
                    for index, part in enumerate(parts):
                        self.deletion_log(
                            case_id, f'b-text-{index:05d}',
                            f'BEFORE TEXT | Case {case_id} | '
                            f'Part {index + 1}/{len(parts)}\n' + part,
                        )
                    self.bot.schedule_violation_timeout(
                        'hate-' + case_id,
                        message,
                        'Direct hate-text pattern violation',
                    )

            self.db.execute(
                'INSERT OR REPLACE INTO troll_seen_v1 VALUES (?,?)',
                (message_id, digest),
            )
            self.db.execute(
                'DELETE FROM troll_jobs_v1 WHERE message_id=?',
                (message_id,),
            )

    async def flush(self):
        cases = self.db.execute(
            'SELECT case_id,message_id,channel_id,content,state '
            "FROM hate_deletions_v1 WHERE state='pending' OR case_id IN "
            '(SELECT case_id FROM hate_deletion_logs_v1 WHERE sent=0) LIMIT 300'
        ).fetchall()
        for case_id, message_id, channel_id, content, state in cases:
            try:
                channel = (self.bot.get_channel(channel_id)
                           or await self.bot.fetch_channel(channel_id))
                await self.process_deletion(channel, (case_id, message_id, content, state))
            except Exception:
                logger.exception('Hate deletion retained for retry | case=%s', case_id)
        rows = self.db.execute(
            'SELECT case_id,body FROM troll_outbox_v1 WHERE sent=0 LIMIT 100'
        ).fetchall()

        for case_id, body in rows:
            try:
                channel = (
                    self.bot.get_channel(MOD_LOG_ID)
                    or await self.bot.fetch_channel(MOD_LOG_ID)
                )
                await channel.send(
                    body,
                    suppress_embeds=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                with self.db:
                    self.db.execute(
                        'UPDATE troll_outbox_v1 SET sent=1 WHERE case_id=?',
                        (case_id,),
                    )
            except Exception:
                logger.exception(
                    'Troll review log retained | case=%s',
                    case_id,
                )

    @tasks.loop(minutes=SCAN_MINUTES)
    async def loop(self):
        for channel_id in self.bot.moderation_channel_ids():
            try:
                channel = (
                    self.bot.get_channel(channel_id)
                    or await self.bot.fetch_channel(channel_id)
                )
                key = f'troll_cursor_{channel_id}'
                initial = discord.utils.time_snowflake(
                    discord.utils.utcnow() - timedelta(hours=24)
                )
                cursor = int(self.bot.setting(key, str(initial)))

                async for message in channel.history(
                    limit=1000,
                    after=discord.Object(id=cursor),
                    oldest_first=True,
                ):
                    self.enqueue(channel_id, message.id)
                    self.bot.set_setting(key, message.id)

                async for message in channel.history(
                    limit=100,
                    oldest_first=False,
                ):
                    self.enqueue(channel_id, message.id)

                rows = self.db.execute(
                    'SELECT message_id FROM troll_jobs_v1 WHERE channel_id=? '
                    'ORDER BY message_id LIMIT 300',
                    (channel_id,),
                ).fetchall()

                for (message_id,) in rows:
                    try:
                        await self.check(channel, message_id)
                    except Exception:
                        logger.exception(
                            'Troll comment check failed | message=%s',
                            message_id,
                        )

            except Exception:
                logger.exception(
                    'Troll comment channel scan failed | channel=%s',
                    channel_id,
                )

        await self.flush()

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(SCAN_MINUTES * 60)


RELATED_COMMENT_WINDOW_SECONDS = 120


class ReliableTrollFlagger(TrollFlagger):
    def __init__(self, bot):
        super().__init__(bot)
        self.flush_lock = asyncio.Lock()
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS hate_context_jobs_v2 (
                parent_case TEXT PRIMARY KEY,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                posted_at REAL NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS hate_context_targets_v2 (
                case_id TEXT PRIMARY KEY,
                parent_case TEXT NOT NULL,
                author_id INTEGER NOT NULL
            );
        ''')
        self.db.commit()

    async def safe_flush_logs(self, case_id):
        try:
            await self.flush_deletion_logs(case_id)
        except Exception:
            logger.exception('Deletion log delivery pending | case=%s', case_id)

    async def check(self, channel, message_id):
        try:
            original = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await super().check(channel, message_id)
        await super().check(channel, message_id)
        direct = any(
            label.startswith('Possible direct statement')
            for phrase, label in troll_comment_findings(original.content)
        )
        if not direct or original.author.id == self.bot.user.id:
            return
        row = self.db.execute(
            'SELECT case_id FROM hate_deletions_v1 WHERE message_id=? '
            'ORDER BY rowid DESC LIMIT 1', (message_id,),
        ).fetchone()
        if row:
            with self.db:
                self.db.execute(
                    'INSERT OR IGNORE INTO hate_context_jobs_v2 '
                    '(parent_case,message_id,channel_id,author_id,posted_at) '
                    'VALUES (?,?,?,?,?)',
                    (row[0], message_id, channel.id, original.author.id,
                     original.created_at.timestamp()),
                )

    async def capture_related(self, job):
        parent, anchor_id, channel_id, author_id, posted_at = job
        channel = (self.bot.get_channel(channel_id)
                   or await self.bot.fetch_channel(channel_id))
        start = datetime.fromtimestamp(
            posted_at - RELATED_COMMENT_WINDOW_SECONDS, timezone.utc)
        end = datetime.fromtimestamp(
            posted_at + RELATED_COMMENT_WINDOW_SECONDS, timezone.utc)
        count = 0
        async for message in channel.history(
            limit=None, after=start - timedelta(milliseconds=1),
            before=end + timedelta(milliseconds=1), oldest_first=True,
        ):
            if (message.author.id != author_id or message.id == anchor_id
                    or not start <= message.created_at <= end):
                continue
            existing = self.db.execute(
                'SELECT 1 FROM hate_deletions_v1 WHERE message_id=?',
                (message.id,),
            ).fetchone()
            if existing:
                continue
            case_id = f'context-{parent}-{message.id}'
            with self.db:
                self.db.execute(
                    'INSERT OR IGNORE INTO hate_deletions_v1 '
                    '(case_id,message_id,channel_id,content) VALUES (?,?,?,?)',
                    (case_id, message.id, channel_id, message.content or ''),
                )
                self.db.execute(
                    'INSERT OR IGNORE INTO hate_context_targets_v2 VALUES (?,?,?)',
                    (case_id, parent, author_id),
                )
                self.deletion_log(
                    case_id, 'a-before',
                    f'BEFORE | RELATED USER COMMENT | Case {case_id}\n'
                    f'Parent flagged case: {parent}\n'
                    f'Server ID: {message.guild.id}\n'
                    f'Channel ID: {channel_id}\nAuthor ID: {author_id}\n'
                    f'Message ID: {message.id}\n'
                    f'Posted UTC: {message.created_at.isoformat()}\n'
                    f'Flagged message ID: {anchor_id}\n'
                    f'Window: {start.isoformat()} through {end.isoformat()}\n'
                    'Reason: same user and channel within the configured time window. '
                    'This message was not independently classified as hate text.\n'
                    f'Attachment IDs: {[a.id for a in message.attachments]}\n'
                    'Media is not copied. Full message text follows.',
                )
                content = message.content or '[No message text]'
                parts = [content[i:i + 500] for i in range(0, len(content), 500)]
                for index, part in enumerate(parts):
                    self.deletion_log(
                        case_id, f'b-text-{index:05d}',
                        f'BEFORE TEXT | Case {case_id} | '
                        f'Part {index + 1}/{len(parts)}\n{part}',
                    )
            count += 1
        if time.time() >= end.timestamp():
            with self.db:
                self.db.execute(
                    "UPDATE hate_context_jobs_v2 SET state='complete' WHERE parent_case=?",
                    (parent,),
                )
                total = self.db.execute(
                    'SELECT count(*) FROM hate_context_targets_v2 WHERE parent_case=?',
                    (parent,),
                ).fetchone()[0]
                self.deletion_log(
                    parent, 'zz-window-complete',
                    f'RELATED COMMENT SEARCH COMPLETE | Case {parent}\n'
                    f'Author ID: {author_id}\nChannel ID: {channel_id}\n'
                    f'Window: {start.isoformat()} through {end.isoformat()}\n'
                    f'Related messages queued: {total}. '
                    'Each message has its own deletion outcome report.',
                )
        return count

    async def process_deletion(self, channel, row):
        async with self.bot.message_lock:
            case_id = row[0]
            current = self.db.execute(
                'SELECT case_id,message_id,content,state FROM hate_deletions_v1 '
                'WHERE case_id=?', (case_id,),
            ).fetchone()
            if not current:
                return
            case_id, message_id, original, state = current
            await self.safe_flush_logs(case_id)
            if state != 'pending':
                return
            related = self.db.execute(
                'SELECT parent_case,author_id FROM hate_context_targets_v2 WHERE case_id=?',
                (case_id,),
            ).fetchone()
            try:
                latest = await channel.fetch_message(message_id)
                if related:
                    eligible = latest.author.id == related[1]
                else:
                    eligible = any(
                        label.startswith('Possible direct statement')
                        for phrase, label in troll_comment_findings(latest.content)
                    )
                if not eligible or latest.content != original:
                    final_state = 'changed'
                    status = 'Deletion cancelled: content or eligibility changed; queued for rescan.'
                    with self.db:
                        self.db.execute(
                            'DELETE FROM troll_seen_v1 WHERE message_id=?', (message_id,))
                    self.enqueue(channel.id, message_id)
                else:
                    await latest.delete()
                    final_state = 'deleted'
                    status = 'Discord acknowledged successful deletion by this bot.'
            except discord.NotFound:
                final_state = 'absent'
                status = 'Message already absent; who deleted it cannot be confirmed.'
            except Exception as exc:
                logger.exception('Comment deletion failed | case=%s', case_id)
                with self.db:
                    self.deletion_log(
                        case_id, 'failure-' + uuid.uuid4().hex,
                        f'AFTER / FAILED | COMMENT REMOVAL | Case {case_id}\n'
                        f'Channel ID: {channel.id}\nMessage ID: {message_id}\n'
                        f'{type(exc).__name__}: {str(exc)[:350]}\n'
                        'Deletion remains queued; retry in the next worker cycle. '
                        'If Forbidden, check Manage Messages in this channel.',
                    )
                await self.safe_flush_logs(case_id)
                return
            with self.db:
                self.db.execute(
                    'UPDATE hate_deletions_v1 SET state=? WHERE case_id=?',
                    (final_state, case_id),
                )
                self.deletion_log(
                    case_id, 'z-after',
                    f'AFTER / {final_state.upper()} | COMMENT REMOVAL | Case {case_id}\n'
                    f'Channel ID: {channel.id}\nMessage ID: {message_id}\n'
                    f'Reported UTC: {discord.utils.utcnow().isoformat()}\n{status}',
                )
            await self.safe_flush_logs(case_id)

    async def flush(self):
        async with self.flush_lock:
            jobs = self.db.execute(
                'SELECT parent_case,message_id,channel_id,author_id,posted_at '
                "FROM hate_context_jobs_v2 WHERE state='pending' LIMIT 100",
            ).fetchall()
            for job in jobs:
                try:
                    await self.capture_related(job)
                except Exception as exc:
                    logger.exception('Related comment discovery retained | case=%s', job[0])
                    with self.db:
                        self.deletion_log(
                            job[0], 'context-failed-' + uuid.uuid4().hex,
                            f'RELATED COMMENT SEARCH FAILED | Case {job[0]}\n'
                            f'{type(exc).__name__}: {str(exc)[:350]}\nRetry scheduled.',
                        )
            await super().flush()

    @tasks.loop(seconds=30)
    async def deletion_worker(self):
        try:
            await self.flush()
        except Exception:
            logger.exception('Comment deletion worker failed; retry next cycle')

    @deletion_worker.before_loop
    async def before_deletion_worker(self):
        await self.bot.wait_until_ready()



class TrollAwareModerator(LiveSectionModerator):
    def __init__(self):
        super().__init__()
        self.troll_flagger = ReliableTrollFlagger(self)

    async def setup_hook(self):
        await super().setup_hook()
        self.troll_flagger.loop.start()
        self.troll_flagger.deletion_worker.start()

    async def on_message(self, message):
        await super().on_message(message)
        if message.author.id != self.user.id:
            self.troll_flagger.enqueue(
                message.channel.id,
                message.id,
            )

    async def on_raw_message_edit(self, payload):
        await super().on_raw_message_edit(payload)
        self.troll_flagger.enqueue(
            payload.channel_id,
            payload.message_id,
        )

    async def close(self):
        deletion_task = self.troll_flagger.deletion_worker.get_task()
        self.troll_flagger.deletion_worker.cancel()
        if deletion_task and deletion_task is not asyncio.current_task():
            try:
                await deletion_task
            except asyncio.CancelledError:
                pass
        task = self.troll_flagger.loop.get_task()
        self.troll_flagger.loop.cancel()

        if task and task is not asyncio.current_task():
            try:
                await task
            except asyncio.CancelledError:
                pass

        await super().close()


class ViolationTimeouts:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS violation_timeouts_v1 (
                case_key TEXT PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                until_at REAL NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS timeout_reports_v1 (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_key TEXT NOT NULL,
                stage TEXT NOT NULL,
                body TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(case_key, stage)
            );
        ''')
        self.db.commit()

    def report(
        self,
        key,
        stage,
        guild_id,
        member_id,
        message_id,
        reason,
        until_at,
        status,
    ):
        body = (
            f'TIMEOUT / {stage.upper()} | Case {key}\n'
            f'Server ID: {guild_id}\n'
            f'User ID: {member_id}\n'
            f'Message ID: {message_id}\n'
            f'Reason: {reason}\n'
            f'Scheduled expiry: <t:{int(until_at)}:F>\n'
            f'Reported UTC: {discord.utils.utcnow().isoformat()}\n'
            f'Status: {status}'
        )

        self.db.execute(
            'INSERT OR IGNORE INTO timeout_reports_v1 '
            '(case_key,stage,body) VALUES (?,?,?)',
            (key, stage, body[:2000]),
        )

    def enqueue(self, key, guild_id, member_id, message_id, reason):
        until_at = time.time() + VIOLATION_TIMEOUT_SECONDS

        inserted = self.db.execute(
            'INSERT OR IGNORE INTO violation_timeouts_v1 '
            '(case_key,guild_id,member_id,message_id,reason,until_at) '
            'VALUES (?,?,?,?,?,?)',
            (key, guild_id, member_id, message_id, reason, until_at),
        ).rowcount

        if inserted:
            self.report(
                key,
                'queued',
                guild_id,
                member_id,
                message_id,
                reason,
                until_at,
                '24-hour timeout queued. Not yet applied.',
            )

    async def apply(self, row):
        (
            key,
            guild_id,
            member_id,
            message_id,
            reason,
            until_at,
            state,
        ) = row

        def finish(stage, status):
            with self.db:
                self.db.execute(
                    'UPDATE violation_timeouts_v1 SET state=? WHERE case_key=?',
                    (stage, key),
                )
                self.report(
                    key,
                    stage,
                    guild_id,
                    member_id,
                    message_id,
                    reason,
                    until_at,
                    status,
                )

        if state == 'attempting':
            finish(
                'uncertain',
                'Previous attempt was interrupted. Administrator review required; '
                'not automatically reapplying a timeout an administrator '
                'may have removed.',
            )
            return

        if until_at <= time.time():
            finish(
                'expired',
                'Queued timeout expired before application; no action taken.',
            )
            return

        try:
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                finish(
                    'failed',
                    'Bot is not connected to the original server.',
                )
                return

            member = await guild.fetch_member(member_id)
            me = guild.me or await guild.fetch_member(self.bot.user.id)

            if (
                member.id == guild.owner_id
                or member.guild_permissions.administrator
            ):
                finish(
                    'skipped',
                    'Discord does not allow timing out the server owner '
                    'or administrators.',
                )
                return

            if member.bot:
                finish('skipped', 'Bot accounts are not timed out.')
                return

            if not me.guild_permissions.moderate_members:
                finish(
                    'failed',
                    'Bot is missing Moderate Members permission.',
                )
                return

            if member.top_role >= me.top_role:
                finish(
                    'failed',
                    'Member role is equal to or higher than the bot role.',
                )
                return

            existing = member.timed_out_until

            if existing and existing.timestamp() >= until_at - 1:
                finish(
                    'already_active',
                    'An equal or longer timeout is already active; '
                    'not shortened or extended.',
                )
                return

            with self.db:
                self.db.execute(
                    "UPDATE violation_timeouts_v1 SET state='attempting' "
                    "WHERE case_key=?",
                    (key,),
                )
                self.report(
                    key,
                    'attempt',
                    guild_id,
                    member_id,
                    message_id,
                    reason,
                    until_at,
                    'Requesting timeout from Discord.',
                )

            await self.flush()

            await member.timeout(
                datetime.fromtimestamp(until_at, timezone.utc),
                reason=f'{reason} | Case {key}'[:512],
            )

            finish(
                'applied',
                'Discord acknowledged the timeout. Administrators can remove '
                'it early. This case will not reapply a confirmed timeout.',
            )

        except discord.NotFound:
            finish(
                'skipped',
                'Member no longer exists in this server.',
            )

        except Exception as exc:
            logger.exception('Timeout attempt failed | case=%s', key)
            finish(
                'failed',
                f'{type(exc).__name__}: {exc}. '
                'Administrator review required; no automatic retry.',
            )

    async def flush(self):
        rows = self.db.execute(
            'SELECT report_id,body FROM timeout_reports_v1 WHERE sent=0 '
            'ORDER BY report_id LIMIT 100'
        ).fetchall()

        for report_id, body in rows:
            try:
                channel = (
                    self.bot.get_channel(MOD_LOG_ID)
                    or await self.bot.fetch_channel(MOD_LOG_ID)
                )
                await channel.send(
                    body,
                    suppress_embeds=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                with self.db:
                    self.db.execute(
                        'UPDATE timeout_reports_v1 SET sent=1 WHERE report_id=?',
                        (report_id,),
                    )
            except Exception:
                logger.exception(
                    'Timeout log retained | report=%s',
                    report_id,
                )

    @tasks.loop(seconds=30)
    async def loop(self):
        try:
            rows = self.db.execute(
                'SELECT case_key,guild_id,member_id,message_id,'
                'reason,until_at,state '
                'FROM violation_timeouts_v1 '
                "WHERE state IN ('pending','attempting') "
                'ORDER BY until_at LIMIT 50'
            ).fetchall()

            for row in rows:
                await self.apply(row)

            await self.flush()

        except Exception:
            logger.exception('Timeout processing cycle failed')

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


class TimeoutModerator(TrollAwareModerator):
    def __init__(self):
        super().__init__()
        self.violation_timeouts = ViolationTimeouts(self)

        self.timeout_enabled_at = float(
            self.setting(
                'timeout_enabled_at_v1',
                str(TIMEOUT_ENABLED_AT),
            )
        )
        self.set_setting(
            'timeout_enabled_at_v1',
            self.timeout_enabled_at,
        )

    def schedule_violation_timeout(self, key, message, reason):
        if message.created_at.timestamp() < self.timeout_enabled_at:
            return

        with self.db:
            self.violation_timeouts.enqueue(
                key,
                message.guild.id,
                message.author.id,
                message.id,
                reason,
            )

    def start_action(self, message, digest, reason):
        case_id = super().start_action(message, digest, reason)

        self.schedule_violation_timeout(
            'nsfw-' + case_id,
            message,
            'NSFW violation: ' + reason,
        )

        return case_id

    async def setup_hook(self):
        await super().setup_hook()
        self.violation_timeouts.loop.start()

    async def close(self):
        task = self.violation_timeouts.loop.get_task()
        self.violation_timeouts.loop.cancel()

        if task and task is not asyncio.current_task():
            try:
                await task
            except asyncio.CancelledError:
                pass

        await super().close()


class ChannelListModerator(TimeoutModerator):
    def __init__(self):
        super().__init__()
        if len(LINK_REPOST_RULES) != 1:
            raise ValueError('Configure exactly one special link-repost source channel.')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS nsfw_job_channels_v1 (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        ''')
        self.db.commit()

    def moderation_channel_ids(self):
        selected = {value for value in MODERATION_CHANNELS.values() if value}
        source = self.get_channel(LIVE_LINKS_ONLY_CHANNEL_ID)
        scope_guild = source.guild.id if source else None
        for name, channel_id in MODERATION_CHANNELS.items():
            if channel_id:
                continue
            matches = [
                channel for guild in self.guilds for channel in guild.text_channels
                if channel.name.casefold() == name.casefold()
                and (scope_guild is None or guild.id == scope_guild)
            ]
            if len(matches) == 1:
                selected.add(matches[0].id)
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.category_id in MODERATION_CATEGORY_IDS:
                    selected.add(channel.id)
        selected.update(LINK_REPOST_RULES)
        selected.discard(MOD_LOG_ID)
        return selected

    def enqueue(self, message_id, edited=False, channel_id=None):
        if channel_id is not None:
            self.db.execute(
                'INSERT OR REPLACE INTO nsfw_job_channels_v1 VALUES (?,?)',
                (message_id, channel_id),
            )
        else:
            self.db.execute(
                'INSERT OR IGNORE INTO nsfw_job_channels_v1 VALUES (?,?)',
                (message_id, CHANNEL_ID),
            )
        super().enqueue(message_id, edited=edited)

    async def on_ready(self):
        await super().on_ready()
        selected = self.moderation_channel_ids()
        descriptions = [
            f'{channel_id}: {getattr(self.get_channel(channel_id), "name", "unresolved")}'
            for channel_id in sorted(selected)
        ]
        body = (
            'MODERATION CHANNEL CONFIGURATION\n'
            'NSFW and hate-text moderation enabled for:\n'
            + '\n'.join(descriptions)
            + f'\nNSFW/hate logs: {MOD_LOG_ID}'
            + f'\nSpecial link-repost source ONLY: {LIVE_LINKS_ONLY_CHANNEL_ID}'
            + f'\nOrdinary non-live link destination: {OUTPUT_CHANNEL_ID}'
        )
        if 'testy' in MODERATION_CHANNELS and not MODERATION_CHANNELS.get('testy') and not any(
            getattr(self.get_channel(channel_id), 'name', '').casefold() == 'testy'
            for channel_id in selected
        ):
            body += (
                '\nWARNING: testy could not be resolved uniquely. Set TESTY_CHANNEL_ID '
                'to its numeric channel ID. It is not monitored until resolved.'
            )
        with self.db:
            self.record_event(uuid.uuid4().hex[:16], 'configuration', body)
        logger.info('%s', body)
        await self.flush_logs()

    async def on_message(self, message):
        await super().on_message(message)
        if message.channel.id in self.moderation_channel_ids() and message.author.id != self.user.id:
            self.enqueue(message.id, channel_id=message.channel.id)
            self.troll_flagger.enqueue(message.channel.id, message.id)

    async def on_raw_message_edit(self, payload):
        await super().on_raw_message_edit(payload)
        if payload.channel_id in self.moderation_channel_ids():
            self.enqueue(payload.message_id, edited=True, channel_id=payload.channel_id)
            self.troll_flagger.enqueue(payload.channel_id, payload.message_id)

    async def on_raw_message_delete(self, payload):
        if payload.channel_id in self.moderation_channel_ids():
            with self.db:
                self.db.execute('DELETE FROM jobs_v3 WHERE id=?', (payload.message_id,))

    async def discover(self, channel):
        prefix = f'nsfw_channel_{channel.id}_'
        initial = discord.utils.time_snowflake(
            discord.utils.utcnow() - timedelta(hours=24))
        cursor = int(self.setting(prefix + 'cursor', str(initial)))
        async for message in channel.history(
            limit=None, after=discord.Object(id=cursor), oldest_first=True,
        ):
            self.enqueue(message.id, channel_id=channel.id)
            self.set_setting(prefix + 'cursor', message.id)
        before_id = int(self.setting(prefix + 'audit', '0'))
        count = 0
        async for message in channel.history(
            limit=100, before=discord.Object(id=before_id) if before_id else None,
            oldest_first=False,
        ):
            self.enqueue(message.id, channel_id=channel.id)
            self.set_setting(prefix + 'audit', message.id)
            count += 1
        if count < 100:
            self.set_setting(prefix + 'audit', 0)

    async def recover_actions(self, channel):
        rows = self.db.execute(
            "SELECT case_id,report FROM actions_v5 WHERE state IN ('planned','deleting','retry') "
            'ORDER BY updated',
        ).fetchall()
        matching = [row for row in rows if json.loads(row[1])['channel_id'] == channel.id]
        for case_id, report in matching[:100]:
            try:
                async with self.message_lock:
                    await self.execute_action(channel, case_id)
            except Exception:
                logger.exception('NSFW recovery failed | channel=%s | case=%s', channel.id, case_id)

    @tasks.loop(minutes=SCAN_MINUTES)
    async def scanner(self):
        await self.refresh_adult_feed()
        for channel_id in sorted(self.moderation_channel_ids()):
            try:
                channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
                member = channel.guild.me or await channel.guild.fetch_member(self.user.id)
                permissions = channel.permissions_for(member)
                if not all(getattr(permissions, key, False) for key in (
                    'view_channel', 'read_message_history', 'manage_messages',
                )):
                    raise PermissionError(f'Missing NSFW moderation permissions in {channel_id}')
                await self.recover_actions(channel)
                try:
                    await self.discover(channel)
                except Exception:
                    logger.exception('Channel discovery failed | channel=%s', channel_id)
                jobs = self.db.execute(
                    'SELECT j.id FROM jobs_v3 j LEFT JOIN nsfw_job_channels_v1 c '
                    'ON c.message_id=j.id WHERE j.due<=? AND COALESCE(c.channel_id,?)=? '
                    'ORDER BY j.id LIMIT 300',
                    (time.time(), CHANNEL_ID, channel_id),
                ).fetchall()
                for (message_id,) in jobs:
                    async with self.message_lock:
                        await self.handle(channel, message_id)
            except Exception as exc:
                logger.exception('Channel NSFW scan failed | channel=%s', channel_id)
                with self.db:
                    self.record_event(
                        uuid.uuid4().hex[:16], 'channel_error',
                        f'NSFW CHANNEL SCAN FAILED\nChannel ID: {channel_id}\n'
                        f'{type(exc).__name__}: {str(exc)[:500]}',
                    )
        await self.flush_logs()

    @scanner.before_loop
    async def before_scan(self):
        await self.wait_until_ready()
        await asyncio.sleep(SCAN_MINUTES * 60)


if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN', '').strip()
    if not token:
        raise SystemExit('Set DISCORD_TOKEN in your hosting environment.')
    ChannelListModerator().run(token, log_handler=None)
