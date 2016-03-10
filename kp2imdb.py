#/usr/bin/env python

import urllib
import urllib2
import json
import re
import time

import csv
import HTMLParser
import unicodedata

USER_ID = ""

html = HTMLParser.HTMLParser()

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def are_titles_equal(web_title, ref_title):
    ref_title = unicode(ref_title, "utf-8")
    
    drop_the = lambda s : s[4:] if s[:4] == "The " else s
    
    t1 = drop_the(strip_accents(html.unescape(web_title))).lower()
    t2 = drop_the(ref_title).lower()
    
    return t1 == t2

RUS_NAME_COL = 0
ORIG_NAME_COL = 1
YEAR_COL = 2
RATING_COL = 7
PREMIERE_COL = 12

kp_ratings = ".csv"

def traverse_kp(kp):
    with open(kp, 'r') as csvfile:
        csvfile.readline()
        csvfile.readline()
        for row in csv.reader(csvfile):
            years = [int(row[YEAR_COL].strip()[:4])]
            year2 = row[PREMIERE_COL].strip()[:4]
            if len(year2) > 0 and int(year2) != years[0]:
                years.append(int(year2))
            yield unicode(row[RUS_NAME_COL], 'utf-8').strip(), row[ORIG_NAME_COL].strip(), years, row[RATING_COL].strip()

DATA_AUTH_RE = re.compile('.*?data-auth="(.*?)"', re.DOTALL)
def get_imdb_auth_token(cookie, movie_id):
    request = urllib2.Request('http://www.imdb.com/title/%s' % movie_id, headers={"Cookie" : cookie})
    response = urllib2.urlopen(request)
    data = response.read()
    res = DATA_AUTH_RE.match(data)
    return res.group(1)

def lookup_imdb_movie_id(title, year=None, verbose=False):
    """ returns None if no match
    """
    response = urllib2.urlopen('http://www.imdb.com/xml/find?json=1&nr=1&tt=on&q=%s' % urllib.quote_plus(title), timeout=10)
    data = response.read()
    # TODO: handle HTTPError

    parsed_candidates = json.loads(data)
    if len(parsed_candidates) == 0:  # no candidates =(
        return
        
    # get a group in priority order
    for key in [u'title_popular', u'title_exact', u'title_approx', u'title_substring']:
        if key in parsed_candidates:
            resp_type = key
            break

    # new logic:
    # if only one popular, take it,
    # if the year matches for only one item, should we return it even if the title is different?
    # same for exact
    # same for approx?
    
    # TODO: handle none 
    #TODO: handle multiple or none mathces
    match = None
    best_matches = parsed_candidates[resp_type]
    if len(best_matches) == 1:  # if only one candidate, do not compare (mistakes possible, but unlikely)
        match = best_matches[0]
    else:
        # TODO: if the year matches for only one item, should we return it even if the title is different?
        # TODO: kp is sometimes 1 year behind
        # TODO: if failed, look for other types
        for t in parsed_candidates[resp_type]:
            if are_titles_equal(t[u'title'], title) and (year is None or int(t[u'description'][:4]) in year):
                match = t
                break
               
    if match is not None:
        if verbose:
            print "Matched movie:", html.unescape(match[u'title']), re.sub('<[^<]+?>', '', html.unescape(match[u'description'])).strip()
        return match[u'id']

 def post_rating_to_imdb(cookie, movie_id, rating, auth_token):
    post_values = {'tconst' : movie_id, 'rating' : rating, 'auth' : auth_token, 'tracking_tag' : 'title-maindetails'}
    post_data = urllib.urlencode(post_values)
    request = urllib2.Request('http://www.imdb.com/ratings/_ajax/title', post_data, headers={"Cookie" : cookie})
    response = urllib2.urlopen(request)
    data = response.read()
    ok = True
    try:
        resp = json.loads(data)
        if not "status" in resp or resp["status"] != 200:
            ok = False
    except ValueError as ve:
        ok = False
        
    if not ok:
        raise HTTPError("Rating posting failure")


if __name__ == "__main__":
	verbose = True
	cookie = 'id=' + USER_ID + ';'
	for rus, orig, years, rating in traverse_kp(kp_ratings):
	    if len(orig) == 0:
	        print 'No latin name for "%s"; skipping!' % s
	        continue
	    
	    if verbose:
	        print 'Looking for the movie "%s" (%s)' % (orig, years[0])
	    timedout = False
	    try:
	        movie_id = lookup_imdb_movie_id(orig, year=years, verbose=True)

			auth_token = get_imdb_auth_token(cookie, movie_id)
			post_rating_to_imdb(cookie, movie_id, rating, auth_token)
	    except urllib2.URLError:
	        movie_id = None
	    
	    time.sleep(3)
	    
	    if movie_id is None:
	        print orig, ": lookup failed" + (" due to request timeout." if timedout else ".")
	        continue

