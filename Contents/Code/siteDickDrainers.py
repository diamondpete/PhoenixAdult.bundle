import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchData.encoded = searchData.title.replace(' ', '+').lower()
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchResults = HTML.ElementFromString(req.text)

    googleResults = PAutils.getFromGoogleSearch(searchData.title, siteNum)
    for sceneURL in googleResults:
        if 'trailers' in sceneURL and sceneURL not in searchResults.xpath('//div[@class="item-video hover"]//h4//@href'):
            req = PAutils.HTTPRequest(sceneURL)
            detailsPageElements = HTML.ElementFromString(req.text)

            detailsPageElements = HTML.ElementFromString(req.text)
            titleNoFormatting = detailsPageElements.xpath('//h3')[0].text_content().strip()
            curID = PAutils.Encode(sceneURL)

            date = detailsPageElements.xpath('//div[@class="videoInfo clear"]/p/text()')[0].strip()
            if date:
                releaseDate = parse(date).strftime('%Y-%m-%d')
            else:
                releaseDate = searchData.dateFormat() if searchData.date else ''

            if searchData.date and releaseDate:
                score = 80 - Util.LevenshteinDistance(searchData.date, releaseDate)
            else:
                score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    for searchResult in searchResults.xpath('//div[@class="item-video hover"]'):
        titleNoFormatting = searchResult.xpath('.//h4')[0].text_content().strip()
        sceneURL = searchResult.xpath('.//h4//@href')[0]
        curID = PAutils.Encode(sceneURL)

        date = searchResult.xpath('.//div[@class="date"]')[0].text_content().strip()
        if date:
            releaseDate = parse(date).strftime('%Y-%m-%d')
        else:
            releaseDate = searchData.dateFormat() if searchData.date else ''

        if searchData.date and releaseDate:
            score = 80 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 80 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h3')[0].text_content().strip()

    # Summary
    metadata.summary = ' '.join(detailsPageElements.xpath('//div[@class="videoDetails clear"]//p/span//text()')).replace('FULL VIDEO', '')

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.studio = tagline
    metadata.collections.add(tagline)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//li[contains(., "Tags")]//parent::ul//a'):
        genreName = PAutils.parseTitle(genreLink.text_content().strip(), siteNum)

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    actors = detailsPageElements.xpath('//li[@class="update_models"]')

    if not actors:
        match = re.search(r'(?<=s/).*(?=\.html)', sceneURL)
        if match:
            for key, value in actorsDB.items():
                for sceneID in value:
                    if sceneID.lower() == match.group(0).lower():
                        movieActors.addActor(key, '')
                        break

    for actorLink in actors:
        actorName = actorLink.text_content().strip()

        modelURL = actorLink.xpath('.//@href')[0]
        req = PAutils.HTTPRequest(modelURL)
        actorPageElements = HTML.ElementFromString(req.text)

        try:
            actorPhotoURL = actorPageElements.xpath('//div[@class="profile-pic"]//@src0_3x')[0]
            if 'http' not in actorPhotoURL:
                actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL
        except:
            actorPhotoURL = ''

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    xpaths = [
        '//div[@class="player_thumbs"]//@src0_3x',
        '//div[@class="player full_width"]/script/text()',
    ]

    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            search = re.search(r'(?<=src0_3x=").*?(?=")', img)
            if search:
                img = search.group(0)
            if 'http' not in img:
                img = PAsearchSites.getSearchBaseURL(siteNum) + img
            art.append(img)

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata


actorsDB = {
    'Anna Blaze': ['big-tit-mindfuck'],
    'Tristan Summers': ['issa-test-on-bbc-today'],
    'Penny Pax': ['your-husband-isnt-here-but-i-am'],
    'Mya Blair': ['his-wife-got-some-scary-big-titties']
}
