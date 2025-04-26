import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchResults = HTML.ElementFromString(req.text)

    for searchResult in searchResults.xpath('//ul[@class="bricks-layout-wrapper"]'):
        titleNoFormatting = PAutils.parseTitle(searchResult.xpath('//div[@class="bricks-layout-inner"]/div/h3/a/text()')[0], siteNum)
        curID = PAutils.Encode(searchResult.xpath('//div[@class="bricks-layout-inner"]/div/h3/a/@href')[0])
        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s]' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum)), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])

    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h1[contains(@class, "brxe-post-title")]/text()')[0].strip()

    # Summary
    try:
        summary = detailsPageElements.xpath('//div[contains(@class, "brxe-post-content")]/p/span/text()')[0]
    except:
        summary = detailsPageElements.xpath('//div[contains(@class, "brxe-post-content")]/p/text()')[0]

    if summary:
        metadata.summary = summary.strip()

    # Studio
    metadata.studio = 'PKJ Media'

    # Tagline and Collection(s)
    metadata.tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.collections.add(metadata.tagline)

    # Genres
    genres = PAutils.getDictValuesFromKey(genresDB, PAsearchSites.getSearchSiteName(siteNum))
    for genreName in genres:
        movieGenres.addGenre(genreName)

    # Actor(s)
    for actorLink in detailsPageElements.xpath('//div[contains(@class, "brxe-post-meta")]/span/a'):
        actorName = actorLink.text_content().strip()

        movieActors.addActor(actorName, '')

    # Posters
    art.append(detailsPageElements.xpath('//video[@class="bricks-plyr"]/@poster')[0])

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


genresDB = {
    'My POV Fam': ['Pov', 'Family'],
    'Perverted POV': ['Pov'],
    'Raw White Meat': ['Interracial'],
}
