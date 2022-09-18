import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchResults = []
    siteResults = []
    temp = []
    count = 0

    if siteNum != 1071:
        searchData.encoded = '%s connectto %s' % (PAsearchSites.getSearchSiteName(siteNum), searchData.title)
        siteNum = 1071

    sceneID = None
    parts = searchData.title.split()
    if unicode(parts[0], 'UTF-8').isdigit():
        sceneID = parts[0]

        if int(sceneID) > 100:
            searchData.encoded = searchData.title.replace(sceneID, '', 1).strip()
            sceneURL = '%s/scenes/%s' % (PAsearchSites.getSearchBaseURL(siteNum), sceneID)
            searchResults.append(sceneURL)

    searchData.encoded = searchData.encoded.replace('\'', '').replace(',', '').replace('& ', '')
    searchURL = '%s%s&key2=%s&next=1&page=0' % (PAsearchSites.getSearchSearchURL(siteNum), searchData.encoded, searchData.encoded)
    req = PAutils.HTTPRequest(searchURL, headers={'Referer': 'https://www.data18.com'})
    searchPageElements = HTML.ElementFromString(req.text)

    searchPages = re.search(r'(?<=pages:\s).*(?=])', req.text)
    if searchPages:
        numSearchPages = int(searchPages.group(0))
        if numSearchPages > 10:
            numSearchPages = 10
    else:
        numSearchPages = 1

    for idx in range(0, numSearchPages):
        for searchResult in searchPageElements.xpath('//a'):
            sceneURL = searchResult.xpath('./@href')[0]

            if ('/scenes/' in sceneURL and sceneURL not in searchResults):
                urlID = re.sub(r'.*/', '', sceneURL)

                try:
                    siteDisplay = PAutils.parseTitle(searchResult.xpath('.//i')[0].text_content().strip(), siteNum)
                except:
                    siteDisplay = ''

                titleNoFormatting = PAutils.parseTitle(searchResult.xpath('.//p[@class="gen12 bold"]')[0].text_content(), siteNum)
                curID = PAutils.Encode(sceneURL)

                if '...' in titleNoFormatting:
                    searchResults.append(sceneURL)
                else:
                    siteResults.append(sceneURL)

                    try:
                        date = searchResult.xpath('.//span[@class="gen11"]/text()')[0].strip()
                    except:
                        date = ''

                    if date and not date == 'unknown':
                        releaseDate = datetime.strptime(date, "%B %d, %Y").strftime('%Y-%m-%d')
                    else:
                        releaseDate = searchData.dateFormat() if searchData.date else ''
                    displayDate = releaseDate if date else ''

                    if sceneID == urlID:
                        score = 100
                    elif searchData.date and displayDate:
                        score = 80 - Util.LevenshteinDistance(searchData.date, releaseDate)
                    else:
                        score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower().replace('-', ' ').replace('\'', ''))

                    if score == 80:
                        count += 1
                        temp.append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, siteDisplay, displayDate), score=score, lang=lang))
                    else:
                        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, siteDisplay, displayDate), score=score, lang=lang))

        if numSearchPages > 1 and not idx + 1 == numSearchPages:
            searchURL = '%s%s&key2=%s&next=1&page=%d' % (PAsearchSites.getSearchSearchURL(siteNum), searchData.encoded, searchData.encoded, idx + 1)
            req = PAutils.HTTPRequest(searchURL, headers={'Referer': 'https://www.data18.com'})
            searchPageElements = HTML.ElementFromString(req.text)

    googleResults = PAutils.getFromGoogleSearch(searchData.title, siteNum)
    for sceneURL in googleResults:
        sceneURL = sceneURL.replace('/content/', '/scenes/').replace('http:', 'https:')
        if ('/scenes/' in sceneURL and '.html' not in sceneURL and sceneURL not in searchResults and sceneURL not in siteResults):
            searchResults.append(sceneURL)

    for sceneURL in searchResults:
        req = PAutils.HTTPRequest(sceneURL)
        detailsPageElements = HTML.ElementFromString(req.text)
        urlID = re.sub(r'.*/', '', sceneURL)

        try:
            siteName = detailsPageElements.xpath('//b[contains(., "Network")]//following-sibling::b')[0].text_content().strip()
        except:
            try:
                siteName = detailsPageElements.xpath('//b[contains(., "Studio")]//following-sibling::a')[0].text_content().strip()
            except:
                siteName = ''

        try:
            subSite = detailsPageElements.xpath('//p[contains(., "Site:")]//following-sibling::a[@class="bold"]')[0].text_content().strip()
        except:
            subSite = ''

        if siteName:
            siteDisplay = '%s/%s' % (siteName, subSite) if subSite else siteName
        else:
            siteDisplay = subSite

        titleNoFormatting = PAutils.parseTitle(detailsPageElements.xpath('//h1')[0].text_content(), siteNum)
        curID = PAutils.Encode(sceneURL)

        try:
            date = detailsPageElements.xpath('//@datetime')[0].strip()
        except:
            date = ''

        if date and not date == 'unknown':
            releaseDate = parse(date).strftime('%Y-%m-%d')
        else:
            releaseDate = searchData.dateFormat() if searchData.date else ''
        displayDate = releaseDate if date else ''

        if sceneID == urlID:
            score = 100
        elif searchData.date and displayDate:
            score = 80 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower().replace('-', ' ').replace('\'', ''))

        if 'Error 404' not in titleNoFormatting:
            if score == 80:
                count += 1
                temp.append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, siteDisplay, displayDate), score=score, lang=lang))
            else:
                results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, siteDisplay, displayDate), score=score, lang=lang))

    for result in temp:
        if count > 1 and result.score == 80:
            results.Append(MetadataSearchResult(id=result.id, name=result.name, score=79, lang=lang))
        else:
            results.Append(MetadataSearchResult(id=result.id, name=result.name, score=result.score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    if not detailsPageElements:
        Log('Possible IP BAN: Retry on VPN')
        return metadata

    # Title
    title = PAutils.parseTitle(detailsPageElements.xpath('//h1')[0].text_content(), siteNum)

    # Reorder Title to Put Scene Number at the End
    match = re.search(r'^Scene.*(?<=(:|-))', title)
    if match:
        title = re.sub(r'^Scene.*(?<=(:|-))', '', title)
        sceneNum = re.sub('[^A-Za-z0-9\s]+', '', match.group(0))
        title = '%s - %s' % (title, sceneNum)

    metadata.title = title

    # Summary
    try:
        summary = detailsPageElements.xpath('//div[@class="gen12"]/div[contains(., "Story")]')[0].text_content().split('Story -')[-1].strip()
    except:
        try:
            summary = detailsPageElements.xpath('//div[@class="gen12"]/div[contains(., "Description")][contains(., "Studio ") or contains(., "Network ")]')[0].text_content().split('---')[-1].split('Description -')[-1].strip()
        except:
            summary = ''

    metadata.summary = summary. replace('�', '\'')

    # Studio
    try:
        studio = detailsPageElements.xpath('//b[contains(., "Network")]//following-sibling::b')[0].text_content().strip()
    except:
        try:
            studio = detailsPageElements.xpath('//b[contains(., "Studio")]//following-sibling::a')[0].text_content().strip()
        except:
            studio = ''

    metadata.studio = PAutils.parseTitle(PAutils.studio(studio, siteNum), siteNum)

    # Tagline and Collection(s)
    metadata.collections.clear()
    try:
        try:
            tagline = detailsPageElements.xpath('//p[contains(., "Site:")]//following-sibling::a[@class="bold"]')[0].text_content().strip()
        except:
            tagline = detailsPageElements.xpath('//p[contains(., "Movie:")]/a')[0].text_content()
            metadata.collections.add(metadata.studio)

        if len(metadata_id) > 3:
            Log('Using original series information')
            tagline = PAutils.parseTitle(PAutils.studio(detailsPageElements.xpath('//p[contains(., "Serie")]//a[@title]')[0].text_content().strip(), siteNum), siteNum)
            metadata.title = ("%s [Scene %s]" % (metadata_id[3], metadata_id[4]))

        if not metadata.studio:
            metadata.studio = PAutils.studio(tagline, siteNum)
        else:
            metadata.tagline = PAutils.parseTitle(tagline, siteNum)
        metadata.collections.add(PAutils.parseTitle(tagline, siteNum))
    except:
        metadata.collections.add(metadata.studio)

    # Release Date
    date = detailsPageElements.xpath('//span[contains(., "Release date")]//following-sibling::a/b')
    if date:
        date = date[0].text_content().strip()
    else:
        date = sceneDate if sceneDate else None

    if date:
        date_object = parse(date)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//div[./b[contains(., "Categories")]]//a'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    # runOnce = 0
    actors = detailsPageElements.xpath('//h3[contains(., "Cast")]//following::div//a[contains(@href, "/name/")]/img')
    for actorLink in actors:
        actorName = actorLink.xpath('./@alt')[0].strip()
        actorPhotoURL = ''

        actorPhotoNode = actorLink.xpath('./@data-src')

        if 'nopic' in actorPhotoURL:
            actorPhotoURL = ''

        if actorPhotoNode:
            actorPhotoURL = actorPhotoNode[0].strip()

        # if ' in ' in title and runOnce == 0:
        #     if actorName.lower() in title.lower():
        #             sceneActor = title.split(' in ', 1)[0].strip()
        #             sceneTitle = title.split(' in ', 1)[1].strip()
        #             title = '%s - %s' % (sceneTitle, sceneActor)
        #             metadata.title = PAutils.parseTitle(title, siteNum)
        #             runOnce = 1

        if actorName:
            movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    xpaths = [
        '//img[@id="photoimg"]/@src',
        '//img[contains(@src, "th8")]/@src',
        '//img[contains(@data-original, "th8")]/@data-original',
    ]

    try:
        if siteNum == 1073 or siteNum == 1370:
            cover = '//a[@class="pvideof"]/@href'
            img = detailsPageElements.xpath(cover)[0]
            art.append(img)
    except:
        pass

    try:
        galleries = detailsPageElements.xpath('//div[@id="galleriesoff"]//div')
        sceneID = re.sub(r'.*/', '', sceneURL)

        for gallery in galleries:
            galleryID = gallery.xpath('./@id')[0].replace('gallery', '')
            photoViewerURL = ("%s/sys/media_photos.php?s=1&scene=%s&pic=%s" % (PAsearchSites.getSearchBaseURL(siteNum), sceneID[1:], galleryID))
            req = PAutils.HTTPRequest(photoViewerURL)
            photoPageElements = HTML.ElementFromString(req.text)

            for xpath in xpaths:
                for img in photoPageElements.xpath(xpath):
                    art.append(img.replace('/th8', '').replace('-th8', ''))
    except:
        pass

    try:
        img = detailsPageElements.xpath('//div[@id="moviewrap"]//@src')[0]
        art.append(img)
    except:
        pass

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl, headers={'Referer': 'http://i.dt18.com'})
                images.append(image)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    posterExists = True
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
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
