import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    sceneID = None
    parts = searchData.title.split()
    if unicode(parts[0], 'UTF-8').isdigit():
        sceneID = int(parts[0])
        searchData.title = searchData.title.replace(parts[0], '').strip()

    actorName = PAutils.Encode(searchData.title)

    result = getPageData(siteNum, sceneID)

    searchResults = []
    googleResults = PAutils.getFromGoogleSearch(searchData.title, siteNum)
    for sceneURL in googleResults:
        if '/tag/' not in sceneURL and '/page/' not in sceneURL and '/category/' not in sceneURL:
            searchResults.append(sceneURL)

    if not searchResults:
        if result:
            titleNoFormatting = PAutils.parseTitle(result['updates']['short_title'], siteNum)
            sceneID = result['updates']['mysqlId']
            curID = sceneID

            date = result['updates']['release_date']
            if date:
                releaseDate = parse(date).strftime('%Y-%m-%d')
            else:
                releaseDate = searchData.dateFormat() if searchData.date else ''

            score = 100

            results.Append(MetadataSearchResult(id='%s|%d|%s|%s|%s' % (curID, siteNum, sceneID, releaseDate, actorName), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))
    else:
        re_videoid = re.compile(r'(?=\d).*(?=-)')
        for sceneURL in searchResults:
            req = PAutils.HTTPRequest(sceneURL)
            detailsPageElements = HTML.ElementFromString(req.text)

            videoID = None
            re_id = re_videoid.search(detailsPageElements.xpath('//source/@src')[0])
            if re_id:
                videoID = re_id.group(0)

            titleNoFormatting = ''
            curID = PAutils.Encode(sceneURL)
            date = None
            if result and videoID:
                if videoID == sceneID:
                    titleNoFormatting = result['updates']['short_title']
                    curID = result['updates']['mysqlId']

                    date = result['updates']['release_date']
            else:
                titleNoFormatting = detailsPageElements.xpath('//title')[0].text_content().split('|')[0].strip()

                date = detailsPageElements.xpath('//meta[@itemprop]/@content')[0].strip()

            titleNoFormatting = PAutils.parseTitle(titleNoFormatting, siteNum)

            if date:
                releaseDate = parse(date).strftime('%m-%d-%Y')
            else:
                releaseDate = searchData.dateFormat() if searchData.date else ''

            score = 100

            results.Append(MetadataSearchResult(id='%s|%d|%s|%s|%s' % (curID, siteNum, videoID, releaseDate, actorName), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    try:
        if unicode(metadata_id[0], 'UTF-8').isdigit():
            videoID = int(metadata_id[0])
        else:
            videoID = int(metadata_id[2])
    except:
        videoID = 0
    sceneURL = PAutils.Decode(metadata_id[0])

    sceneDate = metadata_id[3]
    actors = PAutils.Decode(metadata_id[4])

    Log('actors: %s' % actors)
    detailsPageElements = getPageData(siteNum, videoID)

    summaryPageElements = None
    if 'http' in sceneURL:
        req = PAutils.HTTPRequest(sceneURL)
        summaryPageElements = HTML.ElementFromString(req.text)

    # Title
    if summaryPageElements:
        metadata.title = summaryPageElements.xpath('//title')[0].text_content().split('|')[0].strip()
    else:
        metadata.title = PAutils.parseTitle(detailsPageElements['updates']['short_title'], siteNum)

    # Studio
    metadata.studio = 'NVG Network'

    # Summary
    if summaryPageElements:
        metadata.summary = summaryPageElements.xpath('//div[@class="the-content"]/p')[0].text_content().strip()

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    metadata.collections.add(tagline)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()

    # Actors
    movieActors.clearActors()
    for actor in actors.split(' and '):
        actorName = actor.strip()
        actorPhotoURL = ''

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    if summaryPageElements:
        imageURL = summaryPageElements.xpath('//video/@poster')[0]
    if detailsPageElements:
        imageURL = PAsearchSites.getSearchBaseURL(siteNum) + detailsPageElements['localFile']['childImageSharp']['fluid']['src']
    art.append(imageURL)

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
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata


def getPageData(siteNum, sceneID):
    headers = {
        'Referer': PAsearchSites.getSearchBaseURL(siteNum),
    }
    req = PAutils.HTTPRequest('https://netvideogirls.com/page-data/home/page-data.json', headers=headers)
    if req.ok:
        data = req.json()

        for scene in data['result']['data']['allMysqlTourStats']['edges']:
            if scene['node']['tour_thumbs']['updates']['mysqlId'] == sceneID:
                return scene['node']['tour_thumbs']
