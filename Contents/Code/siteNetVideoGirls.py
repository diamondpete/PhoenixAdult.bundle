import PAsearchSites
import PAgenres
import PAactors
import PAutils


def search(results, encodedTitle, searchTitle, siteNum, lang, searchDate):
    encodedTitle = searchTitle.lower().replace(' ', '-')
    directURL = PAsearchSites.getSearchSearchURL(siteNum) + encodedTitle + '.html'

    searchResults = [directURL]
    googleResults = PAutils.getFromGoogleSearch(searchTitle, siteNum)
    for sceneURL in googleResults:
        if '/trailers/' in sceneURL and sceneURL not in searchResults:
            searchResults.append(sceneURL)

    for sceneURL in searchResults:
        req = PAutils.HTTPRequest(sceneURL)
        detailsPageElements = HTML.ElementFromString(req.text)

        titleNoFormatting = detailsPageElements.xpath('//h1')[0].text_content().strip()
        curID = PAutils.Encode(sceneURL)

        score = 80 - Util.LevenshteinDistance(searchTitle, titleNoFormatting)

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s]' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum)), score=score, lang=lang))

    return results