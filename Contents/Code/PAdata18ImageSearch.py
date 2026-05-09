import PAsearchSites
import PAutils
from difflib import SequenceMatcher


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def to_list(x):
    return [x] if isinstance(x, basestring) else x


def provider_similarity(a_provider, b_provider):
    a_list = to_list(a_provider)
    b_list = to_list(b_provider)
    return max(similarity(a, b) for a in a_list for b in b_list)


def date_match(date1, date2, tolerance_days=7):
    try:
        d1 = date1.replace(tzinfo=None)
        d2 = date2.replace(tzinfo=None)
    except:
        return 0
    return 1 if abs((d1 - d2).days) <= tolerance_days else 0


def accuracy_score(a, b, title=True):
    # dynamic weights
    w_date = 0.03 if title else 0.50
    w_provider = 0.90 if title else 0.50
    w_title = 0.07

    score = date_match(a["date"], b["date"]) * w_date
    score += provider_similarity(a["provider"], b["provider"]) * w_provider

    if title:
        score += similarity(a["title"], b["title"]) * w_title

    return round(score * 100, 2)


def getSceneURLFromData18(query, providers, sceneDate):
    encoded = re.sub(r'[^\w\s]', '', query)
    baseURL = PAsearchSites.getSearchSearchURL(1071)
    headers = {'Referer': 'https://www.data18.com'}
    cookies = {'data_user_captcha': '1'}

    def fetch_page(page):
        url = '%s%s&key2=%s&next=1&page=%d' % (baseURL, encoded, encoded, page)
        req = PAutils.HTTPRequest(url, headers=headers, cookies=cookies)
        return req.text, HTML.ElementFromString(req.text)

    # Fetch first page
    text, searchPage = fetch_page(0)

    # Determine number of pages (max 10)
    m = re.search(r'(?<=pages:\s)(\d+)', text)
    numPages = min(int(m.group(1)), 10) if m else 1

    # Pre-clean query once
    queryClean = re.sub(r'\W', '', query).lower()

    for page in range(numPages):
        for link in searchPage.xpath('//a'):
            href = link.xpath('./@href')
            sceneURL = href[0]
            titleNode = link.xpath('.//p[@class="gen12 bold"]')
            if not href or '/scenes/' not in sceneURL or not titleNode:
                continue

            titleRaw = titleNode[0].text_content().strip()
            titleClean = re.sub(r'\W', '', titleRaw).lower()

            # Date
            dateNode = link.xpath('.//span[@class="gen11"]/text()')
            dateRaw = dateNode[0].strip() if dateNode else ''
            if dateRaw and dateRaw != 'unknown':
                try:
                    searchDate = datetime.strptime(dateRaw, "%B %d, %Y")
                except:
                    searchDate = None
            else:
                searchDate = None

            # Provider
            providerNode = link.xpath('.//span[@class="gen11"]/i')
            provider = providerNode[0].text_content().strip() if providerNode else ''

            # Build comparison dicts
            networkData = {"title": queryClean, "date": sceneDate, "provider": providers}
            data18Data  = {"title": titleClean, "date": searchDate, "provider": provider}

            Log('From Network: %s | %s | %s' % (networkData["title"], networkData["date"], networkData["provider"]))
            Log('From  Data18: %s | %s | %s' % (data18Data["title"], data18Data["date"], data18Data["provider"]))

            # Special case for truncated titles
            if '...' in titleRaw and titleClean.split('...')[0].strip() in queryClean:
                accuracy = accuracy_score(networkData, data18Data, title=False)
            else:
                accuracy = accuracy_score(networkData, data18Data)

            Log('Accuracy: %.2f%%' % accuracy)

            min_accuracy = 100
            if Prefs['data18_accuracy'].isdigit() and (0 <= int(Prefs['data18_accuracy']) <= 100):
                min_accuracy = int(Prefs['data18_accuracy'])

            if accuracy >= min_accuracy:
                return sceneURL

        # Fetch next page if needed
        if page + 1 < numPages:
            text, searchPage = fetch_page(page + 1)

    return None



def getData18Images(sceneURL, art, metadata, detailsPageElements=None, **kwargs):
    headers = kwargs.pop('headers', {})
    cookies = kwargs.pop('cookies', {})

    # Fetch main page
    if not detailsPageElements:
        req = PAutils.HTTPRequest(sceneURL, cookies={'data_user_captcha': '1'})
        detailsPageElements = HTML.ElementFromString(req.text)

    if not detailsPageElements:
        Log('Possible IP BAN: Retry on VPN')
        return

    # Helpers
    def clean_thumb(url):
        return url.replace('/th8', '').replace('-th8', '')

    def fetch(url, hdr=None):
        try:
            return PAutils.HTTPRequest(url, headers=hdr or headers, cookies=cookies)
        except:
            return None

    # Extract scene ID
    sceneID = re.sub(r'.*/', '', sceneURL).split('-')[0]
    scenePrefix, sceneSuffix = sceneID[0], sceneID[1:]

    # Gallery XPaths
    thumb_xpaths = [
        '//img[@id="photoimg"]/@src',
        '//img[contains(@src, "th8")]/@src',
        '//img[contains(@data-original, "th8")]/@data-original',
    ]

    # Process galleries
    try:
        galleries = detailsPageElements.xpath('//div[@id="galleriesoff"]//div')

        for gallery in galleries:
            galleryID = int(gallery.xpath('./@id')[0].replace('gallery', ''))

            # Build viewer URL
            viewerURL = "%s/sys/media_photos.php?s=%s&scene=%s&pic=%s" % (PAsearchSites.getSearchBaseURL(1071), scenePrefix, sceneSuffix,galleryID)

            viewerReq = fetch(viewerURL)
            if not viewerReq:
                continue

            viewerPage = HTML.ElementFromString(viewerReq.text)

            # Collect thumbnails
            for xp in thumb_xpaths:
                for img in viewerPage.xpath(xp):
                    if '/th8_2' in img:
                        continue
                    full = clean_thumb(img)
                    if full not in art:
                        art.append(full)

            # Special galleries (1001 = photoset, 1101 = video stills)
            if galleryID in [1001, 1101, 1201, 1901]:
                try:
                    startUrl = clean_thumb(viewerPage.xpath('//img[contains(@src, "th8")]/@src')[0])
                    startNum = int(startUrl.split('/')[-1].split('.')[0])
                    total = int(viewerPage.xpath('//div[@id="primaryphoto"]/div/b')[0].text_content().split('of')[-1].strip())

                    endNum = startNum + (total * 2 if galleryID == 1101 else total)

                    for idx in range(startNum, endNum):
                        if galleryID == 1901:
                            img = '%s/t%02d.jpg' % (startUrl.rsplit('_', 1)[0], idx)
                        else:
                            img = '%s/%02d.jpg' % (startUrl.rsplit('/', 1)[0], idx)
                        if img not in art:
                            art.append(img)

                    # If preference is disabled and photoset exists, skip large or low quality galleries
                    if not Prefs['data18_extra_enable'] and galleryID in [1001, 1901]:
                        break
                except:
                    pass
    except:
        pass

    # Add main poster
    try:
        poster = detailsPageElements.xpath('//div[@id="moviewrap"]//@src')[0]
        art.append(poster)
    except:
        pass

    # Process images
    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))

    for idx, url in enumerate(art, 1):
        if PAsearchSites.posterAlreadyExists(url, metadata):
            continue

        # Fetch image with correct referer
        if 'data18.com' in url or 'dt18.com' in url:
            imgReq = fetch(url, hdr={'Referer': 'http://i.dt18.com'}) or fetch(url, hdr={'Referer': 'https://www.data18.com'})
        else:
            imgReq = fetch(url)

        if not imgReq:
            continue

        try:
            im = StringIO(imgReq.content)
            img = Image.open(im)
            w, h = img.size

            kind = classify_image(w, h)

            if kind == 'poster':
                posterExists = True
                metadata.posters[url] = Proxy.Media(imgReq.content, sort_order=idx)
            elif kind == 'art':
                images.append((imgReq, url))
                metadata.art[url] = Proxy.Media(imgReq.content, sort_order=idx)
            else:
                # ambiguous → treat as art but low priority
                images.append((imgReq, url))
                metadata.art[url] = Proxy.Media(imgReq.content, sort_order=idx + 1000)
        except:
            pass

    # If no posters found, promote landscape images
    if not posterExists:
        for idx, (imgReq, url) in enumerate(images, 1):
            try:
                im = StringIO(imgReq.content)
                img = Image.open(im)
                w, h = img.size
                if w > 1:
                    metadata.posters[url] = Proxy.Media(imgReq.content, sort_order=idx)
            except:
                pass

    return


def classify_image(width, height):
    # Basic orientation
    if height > width:
        orientation = "portrait"
    elif width > height:
        orientation = "landscape"
    else:
        orientation = "square"

    # Aspect ratio
    aspect = float(height) / float(width) if width else 0

    # Resolution
    resolution = width * height

    # Poster heuristics
    if orientation == "portrait":
        if aspect >= 1.2:            # tall enough
            if resolution >= 200000: # avoid tiny thumbs
                return "poster"

    # Art heuristics
    if orientation == "landscape":
        if aspect <= 0.8:            # wide enough
            if resolution >= 200000:
                return "art"

    # Square or ambiguous
    return "unknown"
