import PAsearchSites
import PAutils


def getAPIKey(siteNum):
    url = PAsearchSites.getSearchBaseURL(siteNum) + '/en/login'
    token_key = urlparse.urlparse(url).hostname

    token = None
    if token_key and token_key in Dict:
        data = Dict[token_key]
        try:
            data = base64.b64decode(data).decode('UTF-8')
            if 'validUntil=' in data:
                timestamp = int(data.split('validUntil=')[1].split('&')[0])
                if timestamp > time.time():
                    token = Dict[token_key]
        except:
            pass

    if not token:
        req = PAutils.HTTPRequest(url)

        if not req.ok:
            url = PAsearchSites.getSearchBaseURL(siteNum) + '/en'
            req = PAutils.HTTPRequest(url)

        match = re.search(r'\"apiKey\":\"(.*?)\"', req.text)
        if match:
            token = match.group(1)

    if token_key and token:
        if token_key not in Dict or Dict[token_key] != token:
            Dict[token_key] = token
            Dict.Save()

    return token


def getAlgolia(url, indexName, params, referer):
    headers = {
        'Content-Type': 'application/json',
        'Referer': referer
    }
    params = json.dumps({'requests': [{'indexName': indexName, 'params': params}]})
    data = PAutils.HTTPRequest(url, headers=headers, params=params)
    data = data.json()

    return data['results'][0]['hits']


def search(results, lang, siteNum, searchData):
    searchData.title = searchData.encoded.replace('%20', ' ')
    sceneID = searchData.title.split(' ', 1)[0]
    if unicode(sceneID, 'UTF-8').isdigit():
        searchData.title = searchData.title.replace(sceneID, '', 1).strip()
    else:
        sceneID = None

    apiKEY = getAPIKey(siteNum)
    for sceneType in ['scenes', 'movies']:
        url = PAsearchSites.getSearchSearchURL(siteNum) + '?x-algolia-application-id=TSMKFA364Q&x-algolia-api-key=' + apiKEY
        if sceneID and not searchData.title:
            if sceneType == 'scenes':
                params = 'filters=clip_id=' + sceneID
            else:
                params = 'filters=movie_id=' + sceneID
        else:
            params = 'query=' + searchData.title

        searchResults = getAlgolia(url, 'all_' + sceneType, params, PAsearchSites.getSearchBaseURL(siteNum))
        for searchResult in searchResults:
            if sceneType == 'scenes':
                releaseDate = parse(searchResult['release_date'])
                curID = searchResult['clip_id']
            else:
                date = 'last_modified' if searchResult['last_modified'] else 'date_created'
                releaseDate = parse(searchResult[date])
                curID = searchResult['movie_id']

            titleNoFormatting = PAutils.parseTitle(searchResult['title'], siteNum)

            if 'mainchannel' in searchResult:
                subSite = searchResult['mainChannel']['name'].strip()
            elif 'serie_name' in searchResult:
                subSite = searchResult['serie_name'].strip()
            else:
                subSite = ''

            # Check if Scene matches the Sub Site
            if subSite.replace(' ', '').lower() == PAsearchSites.getSearchSiteName(siteNum).replace(' ', '').lower():
                score = 80
            else:
                score = 79

            # Check if Scene is a Behind the Scenes
            if 'BTS' in titleNoFormatting:
                score = score - 1
            if 'channels' in searchResult:
                for channel in searchResult['channels']:
                    if 'behindthescenes' in channel['id'] and 'BTS' not in titleNoFormatting:
                        titleNoFormatting = titleNoFormatting + ' BTS'
                        score = score - 1

            releaseDate = releaseDate.strftime('%Y-%m-%d')

            if sceneID:
                score = score - Util.LevenshteinDistance(sceneID, curID)
            elif searchData.date:
                score = score - Util.LevenshteinDistance(searchData.date, releaseDate)
            else:
                score = score - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            if 'dogfartnetwork' in PAsearchSites.getSearchBaseURL(siteNum):
                name = '%s [%s] %s' % (PAutils.parseTitle(titleNoFormatting, siteNum), subSite, releaseDate)
            else:
                name = '[%s] %s %s' % (sceneType.capitalize(), PAutils.parseTitle(titleNoFormatting, siteNum), releaseDate)

            results.Append(MetadataSearchResult(id='%d|%d|%s|%s' % (curID, siteNum, sceneType, releaseDate), name=name, score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    metadata_id = str(metadata.id).split('|')
    sceneID = int(metadata_id[0])
    sceneType = metadata_id[2]
    sceneIDName = 'clip_id' if sceneType == 'scenes' else 'movie_id'
    sceneDate = metadata_id[3]

    apiKEY = getAPIKey(siteNum)

    url = PAsearchSites.getSearchSearchURL(siteNum) + '?x-algolia-application-id=TSMKFA364Q&x-algolia-api-key=' + apiKEY
    data = getAlgolia(url, 'all_' + sceneType, 'filters=%s=%d' % (sceneIDName, sceneID), PAsearchSites.getSearchBaseURL(siteNum))
    detailsPageElements = data[0]

    data = getAlgolia(url, 'all_scenes', 'query=%s' % detailsPageElements['url_title'], PAsearchSites.getSearchBaseURL(siteNum))
    data = sorted(data, key=lambda i: i['clip_id'])
    scenesPagesElements = list(enumerate(data, 1))

    # Title
    title = None
    if 'dogfart' in PAsearchSites.getSearchBaseURL(siteNum).lower():
        title = '%s from %s.com' % (detailsPageElements['title'], detailsPageElements['serie_name'])
    elif sceneType == 'scenes' and len(scenesPagesElements) > 1 and 'filthykings' not in PAsearchSites.getSearchBaseURL(siteNum):
        for idx, scene in scenesPagesElements:
            if scene['clip_id'] == sceneID:
                title = '%s, Scene %d' % (PAutils.parseTitle(detailsPageElements['title'], siteNum), idx)
                break
    if not title:
        title = PAutils.parseTitle(detailsPageElements['title'], siteNum)

    metadata.title = PAutils.parseTitle(title, siteNum)

    # Summary
    metadata.summary = detailsPageElements['description'].replace('</br>', '\n').replace('<br>', '\n')

    # Studio
    if not detailsPageElements['network_name']:
        if 'filthykings' in PAsearchSites.getSearchBaseURL(siteNum):
            metadata.studio = PAutils.studio(detailsPageElements['sitename_pretty'], siteNum)
        else:
            metadata.studio = PAutils.studio(detailsPageElements['studio_name'], siteNum).replace('DFXtra', 'DogFart Network')
    else:
        metadata.studio = PAutils.studio(detailsPageElements['network_name'], siteNum).replace('DFXtra', 'DogFart Network')

    # Tagline and Collection(s)
    if not detailsPageElements['network_name']:
        if 'filthykings' in PAsearchSites.getSearchBaseURL(siteNum) or 'touchmywife' in PAsearchSites.getSearchBaseURL(siteNum):
            tagline = PAutils.parseTitle(detailsPageElements['serie_name'], siteNum)
            metadata.collections.add(tagline)
            metadata.tagline = tagline
        else:
            metadata.collections.add(PAutils.studio(detailsPageElements['studio_name'], siteNum))
    elif 'serie_name' in detailsPageElements:
        tagline = PAutils.parseTitle(detailsPageElements['serie_name'].replace("Devils Film", "Devil's Film"), siteNum)
        metadata.collections.add(PAutils.studio(tagline, siteNum))
        metadata.tagline = PAutils.studio(tagline, siteNum)
        metadata.collections.add(metadata.studio)
    elif 'studio_name' in detailsPageElements:
        tagline = PAutils.parseTitle(detailsPageElements['studio_name'].replace("Devils Film", "Devil's Film"), siteNum)
        metadata.collections.add(PAutils.studio(tagline, siteNum))

    # for collectionName in ['studio_name', 'serie_name']:
    #     if collectionName in detailsPageElements:
    #         metadata.collections.add(PAutils.parseTitle(detailsPageElements[collectionName].replace("Devils Film", "Devil's Film"), siteNum))
    # if (':' in detailsPageElements['title'] or '#' in detailsPageElements['title']) and len(scenesPagesElements) > 1:
    #     if 'movie_title' in detailsPageElements:
    #         metadata.collections.add(detailsPageElements['movie_title'])

    # Release Date
    date_object = parse(sceneDate)
    metadata.originally_available_at = date_object
    metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements['categories']:
        genreName = genreLink['name']
        if genreName:
            movieGenres.addGenre(genreName)

    if sceneType == 'movies':
        for idx, scene in scenesPagesElements:
            for genreLink in scene['categories']:
                genreName = genreLink['name']
                if genreName:
                    movieGenres.addGenre(genreName)

    # Actor(s)
    female = []
    male = []
    for actorLink in detailsPageElements['actors']:
        actorName = actorLink['name']

        actorData = getAlgolia(url, 'all_actors', 'filters=actor_id=' + actorLink['actor_id'], PAsearchSites.getSearchBaseURL(siteNum))[0]
        if 'pictures' in actorData and actorData['pictures']:
            max_quality = sorted(actorData['pictures'].keys())[-1]
            actorPhotoURL = 'https://images-fame.gammacdn.com/actors' + actorData['pictures'][max_quality]
        else:
            actorPhotoURL = ''

        if actorLink['gender'] == 'female':
            female.append((actorName, actorPhotoURL, 'female'))
        else:
            male.append((actorName, actorPhotoURL, 'male'))

    combined = female + male
    for actor in combined:
        movieActors.addActor(actor[0], actor[1], gender=actor[2])

    # Posters
    if not PAsearchSites.getSearchBaseURL(siteNum).endswith(('girlsway.com', 'puretaboo.com')):
        art.append('https://images-fame.gammacdn.com/movies/{0}/{0}_{1}_front_400x625.jpg'.format(detailsPageElements['movie_id'], detailsPageElements['url_title'].lower().replace('-', '_')))
        if 'url_movie_title' in detailsPageElements:
            art.append('https://images-fame.gammacdn.com/movies/{0}/{0}_{1}_front_400x625.jpg'.format(detailsPageElements['movie_id'], detailsPageElements['url_movie_title'].lower().replace('-', '_')))

    if 'pictures' in detailsPageElements and detailsPageElements['pictures']:
        max_quality = detailsPageElements['pictures']['nsfw']['top'].keys()[0]
        pictureURL = 'https://images-fame.gammacdn.com/movies/' + detailsPageElements['pictures'][max_quality]

        if sceneType == 'movies':
            art.append(pictureURL)
        else:
            art.insert(0, pictureURL)

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                images.append(image)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
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
