#!/usr/bin/python

# (c) 2013 Joachim Breitner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import cgi
import cgitb; cgitb.enable()
import psycopg2
import psycopg2.extras
import re
import json
import sys

conn = psycopg2.connect("service=wanna-build")
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

DEFAULT_A = 'i386'
DEFAULT_P = 'pkg-haskell-maintainers@lists.alioth.debian.org'

# Read package list from the user
form = cgi.FieldStorage()
pkgs_raw = form.getfirst('p', DEFAULT_P).replace(',',' ').split()

def abort(s):
    print 'Content-Type: application/json'
    print
    print json.dumps({'error': s})
    sys.exit(0)

# Replace e-mail addresses by packages
pkgs = set()
pattern =re.compile('^([-_a-zA-Z0-9]*)\s*.*<(.*)>$')
for p in pkgs_raw:
    if "@" in p:
        for line in file('/srv/buildd.debian.org/etc/Maintainers'):
            m = pattern.match(line)
            if m and m.group(2) == p:
                pkgs.add(m.group(1))
    else:
        pkgs.add(p)
if not pkgs:
    abort("No packages selected. Maintainer address misspelled?")

pkg_list = list(pkgs)
pkg_list.sort()
if len(pkgs) > 10:
    pkg_list = ",".join(pkg_list[:10]) + ",..."
else:
    pkg_list = ",".join(pkg_list)

# Read arch from user
arch = form.getfirst('a',DEFAULT_A)
if not re.match('^[-0-9a-zA-Z]+$', arch):
    abort("Invalid architecture %s selected" % arch)

QUERY = '''
	WITH allp AS (
		SELECT COUNT(*) as pkgs,
		       timestamp :: date AS day,
                       sum(build_time) as total_build_time
		FROM pkg_history_public
                WHERE timestamp > '2010-01-01'
                  AND architecture = %(arch)s
		GROUP BY day
		ORDER BY day
	), selected as (
		SELECT COUNT(*) as selected_pkgs,
		       timestamp :: date AS day,
		       sum(build_time) as selected_total_build_time
		FROM pkg_history_public
		WHERE package IN %(pkgs)s
                  AND timestamp > '2010-01-01'
                  AND architecture = %(arch)s
		GROUP BY day
		ORDER BY day
	)
	SELECT *
	FROM allp FULL OUTER JOIN selected USING (day);'''

cur.execute(QUERY, {'pkgs': tuple(pkgs), 'arch' : arch })

d_data = []
for rec in cur:
    timestamp = int(rec['day'].strftime('%s'))*1000 + 1000*60*60*12
    d_data.append([
        timestamp,
        rec['pkgs'] or 0,
        rec['selected_pkgs'] or 0,
        float(rec['selected_pkgs'] or 0)/float(rec['pkgs']) * 100,
        rec['total_build_time'] or 0,
        rec['selected_total_build_time'] or None,
        float(rec['selected_total_build_time'] or 0)/float(rec['total_build_time'] or 1) * 100,         ])

print 'Content-Type: application/json\n\n'
print json.dumps({
    'arch':     arch,
    'p_query':  form.getfirst('p',DEFAULT_P),
    'n_pkg':    len(pkgs),
    'n_pkg_s':  "" if len(pkgs) == 1 else "s",
    'pkg_list': pkg_list,
    'data': d_data,
})
