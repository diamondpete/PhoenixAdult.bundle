import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchJAVID = None
    splitSearchTitle = searchData.title.split()
    searchResults = []
    bluRayExceptions = ['blu-ray', 'blue-ray', 'blue-lay']
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
    for searchResult in searchPageElements.xpath('//div[@class="video"]'):
        titleNoFormatting = PAutils.parseTitle(searchResult.xpath('./a/@title')[0].strip(), siteNum)
        JAVID = titleNoFormatting.split(' ')[0]
        sceneURL = '%s/en%s' % (PAsearchSites.getSearchBaseURL(siteNum), searchResult.xpath('./a/@href')[0].split('.')[-1].strip())
        curID = PAutils.Encode(sceneURL)
        searchResults.append(sceneURL)

        score = 80 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())

        for exception in  bluRayExceptions:
            if exception.lower() in titleNoFormatting.lower().replace(' ', ''):
                score = score - 1

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[%s] %s' % (JAVID, titleNoFormatting), score=score, lang=lang))
    else:
        googleResultsURLs = []
        if '?v=jav' in req.url:
            googleResultsURLs.append(req.url)
        googleResults = PAutils.getFromGoogleSearch('%s %s' % (splitSearchTitle[0], splitSearchTitle[1]), siteNum)
        for sceneURL in googleResults:
            if '?v=jav' in sceneURL and 'videoreviews' not in sceneURL:
                englishSceneURL = sceneURL.replace('/ja/', '/en/').replace('/tw/', '/en/').replace('/cn/', '/en/')
                if not englishSceneURL.lower().startswith('http'):
                    englishSceneURL = 'http://' + englishSceneURL

                if englishSceneURL not in searchResults and englishSceneURL not in googleResultsURLs:
                    googleResultsURLs.append(englishSceneURL)

        for sceneURL in googleResultsURLs:
            req = PAutils.HTTPRequest(sceneURL)
            if req.ok:
                try:
                    searchResult = HTML.ElementFromString(req.text)
                    titleNoFormatting = PAutils.parseTitle(searchResult.xpath('//h3[@class="post-title text"]/a')[0].text_content().strip().split(' ', 1)[1], siteNum)
                    JAVID = searchResult.xpath('//td[contains(text(), "ID:")]/following-sibling::td')[0].text_content().strip()
                    curID = PAutils.Encode(searchResult.xpath('//meta[@property="og:url"]/@content')[0].strip().replace('//www', 'https://www'))
                    score = 80 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())

                    for exception in  bluRayExceptions:
                        if exception.lower() in titleNoFormatting.lower().replace(' ', ''):
                            score = score - 1

                    results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[%s] %s' % (JAVID, titleNoFormatting), score=score, lang=lang))
                except:
                    pass

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    javID = detailsPageElements.xpath('//meta[@property="og:title"]/@content')[0].strip().split(' ', 1)[0]
    title = detailsPageElements.xpath('//meta[@property="og:title"]/@content')[0].strip().split(' ', 1)[-1].replace(' - JAVLibrary', '')

    if len(title) > 80:
        metadata.title = '[%s] %s' % (javID.upper(), PAutils.parseTitle(title, siteNum))
        metadata.summary = PAutils.parseTitle(title, siteNum)
    else:
        metadata.title = '[%s] %s' % (javID.upper(), PAutils.parseTitle(title, siteNum))

    # Studio
    studio = detailsPageElements.xpath('//td[contains(text(), "Maker:")]/following-sibling::td/span/a')
    if studio:
        metadata.studio = studio[0].text_content().strip()

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = detailsPageElements.xpath('//td[contains(text(), "Label:")]/following-sibling::td/span/a')
    if tagline:
        metadata.tagline = tagline[0].text_content().strip()
        metadata.collections.add(metadata.tagline)
    elif studio:
        metadata.collections.add(metadata.studio)
    else:
        metadata.collections.add('Japan Adult Video')

    # Director
    director = metadata.directors.new()
    directorName = detailsPageElements.xpath('//td[contains(text(), "Director:")]/following-sibling::td/span/a')
    if directorName:
        director.name = directorName[0].text_content().strip()

    # Release Date
    date = detailsPageElements.xpath('//td[contains(text(), "Release Date:")]/following-sibling::td')
    if date:
        date_object = datetime.strptime(date[0].text_content().strip(), '%Y-%m-%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Actors
    movieActors.clearActors()

    # Manually Add Actors By JAV ID
    actors = []
    for actorName, scenes in actorsDB.items():
        if javID.lower() in map(str.lower, scenes):
            actors.append(actorName)

    for actor in actors:
        movieActors.addActor(actor, '')

    for actor in detailsPageElements.xpath('//span[@class="star"]/a'):
        actorName = actor.text_content().strip()

        movieActors.addActor(actorName, '')

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//a[@rel="category tag"]'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Poster
    posterURL = detailsPageElements.xpath('//img[@id="video_jacket_img"]/@src')[0]
    if 'https' not in posterURL:
        posterURL = 'https:' + posterURL

    if '/removed.png' not in posterURL:
        art.append(posterURL)

    # Images
    urlRegEx = re.compile(r'-([1-9]+).jpg')
    for image in detailsPageElements.xpath('//div[@class="previewthumbs"]/img'):
        thumbnailURL = image.get('src')
        idxSearch = urlRegEx.search(thumbnailURL)
        if idxSearch:
            imageURL = thumbnailURL[:idxSearch.start()] + 'jp' + thumbnailURL[idxSearch.start():]
            art.append(imageURL)
        else:
            art.append(thumbnailURL)

    # JavBus Images
    # Manually Match JavBus to JAVLibrary
    for javLibraryID, javBusID in crossSiteDB.items():
        if javID.lower() == javLibraryID.lower():
            javID = javBusID
            break

    numLen = len(javID.split('-', 1)[-1])
    if int(numLen) < 3:
        for idx in range(1, 4 - numLen):
            javID = '%s-0%s' % (javID.split('-')[0], javID.split('-')[-1])

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

                if 'nowprinting' not in poster:
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
    'Lily Glee': ['ANCI-038'],
    'Lana Sharapova': ['ANCI-038'],
    'Madi Collins': ['KTKL-112'],
    'Tsubomi': ['WA-192'],
}


crossSiteDB = {
    'UMD-421': 'UD-597R',
    'UMD-354': 'UD-529R',
    'SS-028': 'SS-028_2009-08-04',
    'CHD-029': 'CHD-029_3trz',
    'STAR-128S': 'STAR-128_2008-11-06',
    'DVAJ-0003': 'DVAJ-003',
    'DVAJ-0013': 'DVAJ-013',
    'DVAJ-0021': 'DVAJ-021',
    'DVAJ-0027': 'DVAJ-027',
    'DVAJ-0031': 'DVAJ-031',
    'DVAJ-0032': 'DVAJ-032',
    'DVAJ-0039': 'DVAJ-039',
    'DVAJ-312': 'DVAJ-312_2018-02-11',
    'AKA-001': 'AKA-001_2013-06-28',
    'HODV-20467': 'HRDV-591',
    'SERO-0306': 'SERO-306_2016-02-12',
    'AKB-035': 'HITMA-130',
    'DBD-3008': 'DBD-008',
    'SW-041': 'SW-041_2011-07-04',
    'NTRD-021': 'NTRD-021_2015-03-05',
    'ONED-136': 'ONE-136',
    'ONED-104': 'ONE-104',
    'MILD-781': 'BDMILD-059',
    'MILD-787': 'BDMILD-063',
    'MILD-798': 'BDMILD-068',
    'MILD-752': 'BDMILD-045',
    'MILD-769': 'BDMILD-052',
    'MILD-776': 'BDMILD-057',
    'MILD-720': 'BDMILD-034',
    'MILD-729': 'BDMILD-036',
    'MILD-734': 'BDMILD-038',
    'MILD-748': 'BDMILD-044',
}
