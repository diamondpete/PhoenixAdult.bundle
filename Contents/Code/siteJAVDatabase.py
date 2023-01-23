import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchJAVID = None
    splitSearchTitle = searchData.title.split()

    if splitSearchTitle[0].startswith('3dsvr'):
        splitSearchTitle[0] = splitSearchTitle[0].replace('3dsvr', 'dsvr')
    elif splitSearchTitle[0].startswith('13dsvr'):
        splitSearchTitle[0] = splitSearchTitle[0].replace('13dsvr', 'dsvr')

    if len(splitSearchTitle) > 1:
        if unicode(splitSearchTitle[1], 'UTF-8').isdigit():
            searchJAVID = '%s-%s' % (splitSearchTitle[0], splitSearchTitle[1])

    if searchJAVID:
        searchData.encoded = searchJAVID

    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchPageElements = HTML.ElementFromString(req.text)
    for searchResult in searchPageElements.xpath('//div[@class="card h-100"]'):
        titleNoFormatting = PAutils.parseTitle(searchResult.xpath('.//div[@class="mt-auto"]/a')[0].text_content().strip(), siteNum)
        JAVID = searchResult.xpath('.//h2')[0].text_content().strip()
        sceneURL = searchResult.xpath('.//h2//@href')[0].strip()
        curID = PAutils.Encode(sceneURL)

        date = searchResult.xpath('.//div[@class="mt-auto"]/text()')
        if date:
            releaseDate = parse(date[1].strip()).strftime('%Y-%m-%d')
        else:
            releaseDate = searchData.dateFormat() if searchData.date else ''

        displayDate = releaseDate if date else ''

        if searchJAVID:
            score = 80 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())
        elif searchData.date and displayDate:
            score = 80 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='[%s] %s %s' % (JAVID, displayDate, titleNoFormatting), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    javID = detailsPageElements.xpath('//tr[./td[contains(., "DVD")]]//td[@class="tablevalue"]')[0].text_content().strip()
    title = detailsPageElements.xpath('//tr[./td[contains(., "Translated")]]//td[@class="tablevalue"]')[0].text_content().replace(javID, '').strip()

    for word, correction in censoredWordsDB.items():
        if word in title:
            title = title.replace(word, correction)

    if len(title) > 80:
        metadata.title = '[%s] %s' % (javID.upper(), PAutils.parseTitle(title, siteNum))
        metadata.summary = PAutils.parseTitle(title, siteNum)
    else:
        metadata.title = '[%s] %s' % (javID.upper(), PAutils.parseTitle(title, siteNum))

    # Studio
    studio = detailsPageElements.xpath('//tr[./td[contains(., "Studio")]]//td[@class="tablevalue"]')
    if studio:
        metadata.studio = studio[0].text_content().strip()

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = detailsPageElements.xpath('//tr[./td[contains(., "Label")]]//td[@class="tablevalue"]')
    if tagline:
        metadata.tagline = tagline[0].text_content().strip()
        metadata.collections.add(metadata.tagline)
    elif studio:
        metadata.collections.add(metadata.studio)
    else:
        metadata.collections.add('Japan Adult Video')

    # Director
    director = metadata.directors.new()
    directorName = detailsPageElements.xpath('//tr[./td[contains(., "Director")]]//td[@class="tablevalue"]')
    if directorName:
        director.name = directorName[0].text_content().strip()

    # Release Date
    date = detailsPageElements.xpath('//tr[./td[contains(., "Release Date")]]//td[@class="tablevalue"]')
    if date:
        date_object = datetime.strptime(date[0].text_content().strip(), '%Y-%m-%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//tr[./td[contains(., "Genre")]]//td[@class="tablevalue"]//a'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    for actor in detailsPageElements.xpath('//div/div[./h2[contains(., "Featured Idols")]]//div[@class="idol-thumb"]'):
        actorName = actor.xpath('.//@alt')[0].strip().split('(')[0]
        actorPhotoURL = actor.xpath('.//img/@src')[0].replace('melody-marks', 'melody-hina-marks')

        req = PAutils.HTTPRequest(actorPhotoURL)
        if 'unknown.' in req.url:
            actorPhotoURL = ''

        movieActors.addActor(actorName, actorPhotoURL)

    # Manually Add Actors By JAV ID
    actors = []
    for actorName, scenes in actorsDB.items():
        if javID.lower() in map(str.lower, scenes):
            actors.append(actorName)

    for actor in actors:
        movieActors.addActor(actor, '')

    # Posters
    xpaths = [
        '//tr[@class="moviecovertb"]//img/@src',
        '//div/div[./h2[contains(., "Images")]]/a/@href'
    ]

    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            art.append(img)

    # JavBus Images
    # Manually Match JavBus to JAVLibrary
    for javLibraryID, javBusID in crossSiteDB.items():
        if javID.lower() == javLibraryID.lower():
            javID = javBusID
            break

    javBusURL = PAsearchSites.getSearchSearchURL(912) + javID
    req = PAutils.HTTPRequest(javBusURL)
    javbusPageElements = HTML.ElementFromString(req.text)

    if '404 Page' in req.text and date:
        javBusURL = '%s_%s' % (javBusURL, date_object.strftime('%Y-%m-%d'))
        req = PAutils.HTTPRequest(javBusURL)
        javbusPageElements = HTML.ElementFromString(req.text)

    if '404 Page' not in req.text:
        xpaths = [
            '//a[contains(@href, "/cover/")]/@href',
            '//a[@class="sample-box"]/@href',
        ]

        for xpath in xpaths:
            for poster in javbusPageElements.xpath(xpath):
                if not poster.startswith('http'):
                    poster = PAsearchSites.getSearchBaseURL(912) + poster

                if 'nowprinting' not in poster and poster not in art:
                    art.append(poster)

        coverImage = javbusPageElements.xpath('//a[contains(@href, "/cover/")]/@href|//img[contains(@src, "/sample/")]/@src')
        if coverImage:
            coverImageCode = coverImage[0].rsplit('/', 1)[1].split('.')[0].split('_')[0]
            imageHost = coverImage[0].rsplit('/', 2)[0]
            coverImage = imageHost + '/thumb/' + coverImageCode + '.jpg'
            if coverImage.count('/images.') == 1:
                coverImage = coverImage.replace('thumb', 'thumbs')

            if not coverImage.startswith('http'):
                coverImage = PAsearchSites.getSearchBaseURL(912) + coverImage

            art.append(coverImage)

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                if 'now_printing' not in image.url:
                    im = StringIO(image.content)
                    images.append(image)
                    resized_image = Image.open(im)
                    width, height = resized_image.size
                    # Add the image proxy items to the collection
                    if height > width:
                        # Item is a poster
                        metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)

                        if 'javbus.com/pics/thumb' not in posterUrl:
                            posterExists = True
                    if width > height:
                        # Item is an art item
                        metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    if not posterExists:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[art[idx - 1]] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata


actorsDB = {
    'Chigusa Hara': ['SAIT-004'],
    'Darcia Lee': ['CRDD-004'],
    'Eimi Fukada': ['MIAA-448'],
    'Gabbie Carter': ['CRDD-001', 'CRDD-013'],
    'Jillian Janson': ['CRDD-004', 'CRDD-013'],
    'June Lovejoy': ['DVDMS-553'],
    'Lily Glee': ['ANCI-038'],
    'Lana Sharapova': ['ANCI-038'],
    'Madi Collins': ['KTKL-112'],
    'Megan Marx': ['CRDD-001'],
    'Tiffany Tatum': ['CRDD-004'],
    'Tsubomi': ['WA-192'],
    'Vanna Bardot': ['CRDD-001'],
}


censoredWordsDB = {
    'C***d': 'Child',
    'D***kest': 'Drunkest',
    'D***king': 'Drinking',
    'D******e': 'Disgrace',
    'G*******g': 'Gangbang',
    'M****t': 'Molest',
    'I****t': 'Incest',
    'R**e': 'Rape',
    'S***e': 'Slave',
    'SK**led': 'Skilled',
    'T******e': 'Tentacle',
    'T*****e': 'Torture',
    'V*****e': 'Violate',
}


crossSiteDB = {
    'STAR-128': 'STAR-128_2008-11-06',
    'STAR-134': 'STAR-134_2008-12-18',
}
