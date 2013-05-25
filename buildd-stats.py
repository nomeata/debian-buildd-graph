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

conn = psycopg2.connect("service=wanna-build")
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

ARCH = 'i386'

DAYS_QUERY = '''SELECT (SELECT min(timestamp) FROM %(arch)s.pkg_histor '1' day * generate_series(0, (SELECT extract(day from max(timestamp)-min(timestamp)) FROM %(arch)s.pkg_history)::integer))''' % {'arch': ARCH}

pattern =re.compile('^([-_a-zA-Z0-9]*)\s*.*pkg-haskell-maintainers@lists.alioth.debian.org.*$')
pkgs = []
for line in file('/srv/buildd.debian.org/etc/Maintainers'):
    m = pattern.match(line)
    if m:
        pkgs.append(m.group(1))

QUERY = '''
	WITH allp AS (
		SELECT COUNT(*) as pkgs,
		       timestamp :: date AS day,
                       sum(build_time) as total_build_time
		FROM %(arch)s_public.pkg_history
                WHERE timestamp > '2010-01-01'
		GROUP BY day
		ORDER BY day
	), haskell as (
		SELECT COUNT(*) as haskell_pkgs,
		       timestamp :: date AS day,
		       sum(build_time) as haskell_total_build_time
		FROM %(arch)s_public.pkg_history
		WHERE package IN (%(pkgs)s)
                  AND timestamp > '2010-01-01'
		GROUP BY day
		ORDER BY day
	)
	SELECT *
	FROM allp FULL OUTER JOIN haskell USING (day);''' % \
	{ 'arch': ARCH,
	  'pkgs': ",".join(map(lambda s: "'%s'"%s, pkgs)) }

cur.execute(QUERY)

print 'Content-Type: text/html\n\n'
print '''
    <html>
    <head><title>Haskell Buildd exposure stats</title></head>
    <style type="text/css">
        #placeholder { width: 900px; height: 300 }
        #placeholder2 { width: 900px; height: 300 }
        #overview { width: 900px; height: 100px }

        .stats {
            border: 1px solid #DFDFDF;
            -moz-border-radius: 3px;
            -webkit-border-radius: 3px;
            border-radius: 3px;
            font-family: sans-serif;
        }
        .stats td, .stats th {
            border-top-color: white;
            border-bottom: 1px solid #DFDFDF;
        }
        .stats thead th {
            text-align: center;
        }
        .stats th {
            font-weight: bold;
            padding: 7px 7px 8px;
            text-align: left;
            line-height: 1.3em;
        }
        .stats td {
            padding: 4px 7px 2px;
            vertical-align: top;
            text-align: right;
        }

    </style>
    <script language="javascript" type="text/javascript" src="flot/jquery.js"></script>
    <script language="javascript" type="text/javascript" src="flot/jquery.flot.js"></script>
    <script language="javascript" type="text/javascript" src="flot/jquery.flot.time.js"></script>
    <script language="javascript" type="text/javascript" src="flot/jquery.flot.selection.js"></script>
    <script type="text/javascript">
        $(function() {
            function percFormatter(perc, axis) {
                return perc.toFixed(axis.tickDecimals) + "%";
            }
            function timespanFormatter(period, axis) {
                var timespan = 1;
                var format = 's';
                if (period > 31556926) {
                    // More than one year
                    format = 'y';
                    timespan = (period / 31556926).toFixed(2);
                }
                else if (period > 2629744) {
                    // More than one month
                    format = 'm';
                    timespan = (period / 2629744).toFixed(2);
                }
                else if (period > 604800) {
                    // More than one week
                    format = 'w';
                    timespan = (period / 604800).toFixed(2);
                }
                else if (period > 86400) {
                    // More than one day
                    format = 'd';
                    timespan = (period / 86400).toFixed(2);
                }
                else if (period > 3600) {
                    // More than one hour
                    format = 'h';
                    timespan = (period / 3600).toFixed(2);
                }
                else if (period > 60) {
                    // More than one minute
                    format = 'm';
                    timespan = (period / 60).toFixed(2);
                } else {
                    timespan = period.toFixed(2);
		}
                 
                /*
                // Remove the s
                if(timespan == 1) {
                    format = format.substr(0, format.length-1);
                }
                */
                 
                return timespan + '' + format;
            }

            var d_pkgs = [];
            var d_haskell_pkgs = [];
            var d_pkgs_perc = [];
            var d_buildtime = [];
            var d_haskell_buildtime = [];
            var d_buildtime_perc = [];
    '''
for rec in cur:
    timestamp = int(rec['day'].strftime('%s'))*1000 + 1000*60*60*12
    print "d_pkgs.push([%s, %s])\n" % (timestamp, rec['pkgs']);
    print "d_haskell_pkgs.push([%s, %s])\n" % (timestamp, rec['haskell_pkgs'] or 'null');
    print "d_pkgs_perc.push([%s, %s])\n" % (timestamp,
        float(rec['haskell_pkgs'] or 0)/float(rec['pkgs']) * 100);

    print "d_buildtime.push([%s, %s])\n" % (timestamp, rec['total_build_time'] or 0);
    print "d_haskell_buildtime.push([%s, %s])\n" % (timestamp, rec['haskell_total_build_time'] or 'null');
    print "d_buildtime_perc.push([%s, %s])\n" % (timestamp,
        float(rec['haskell_total_build_time'] or 0)/float(rec['total_build_time'] or 1) * 100);

print '''
            var d = [ 
                {
                    data: d_pkgs,
                    label: "# uploads",
                    lines: {
                        fill: true,
                        lineWidth: 0,
                    },
                }, {
                    data: d_haskell_pkgs,
                    label: "# haskell uploads",
                    lines: {
                        fill: 1,
                        lineWidth: 0,
                    },
                }, {
                    data: d_pkgs_perc,
                    label: "percentage",
                    yaxis: 2,
                    lines: { lineWidth: 1, },
                    shadowSize: 0
                } ];

            var d2 = [ 
                {
                    data: d_buildtime,
                    label: "buildtime",
                    lines: {
                        fill: true,
                        lineWidth: 0,
                    },
                }, {
                    data: d_haskell_buildtime,
                    label: "haskell buildtime",
                    fill: 1,
                    lines: {
                        fill: 1,
                        lineWidth: 0,
                    },
                }, {
                    data: d_buildtime_perc,
                    label: "percentage",
                    yaxis: 2,
                    lines: { lineWidth: 1, },
                    shadowSize: 0
                } ];

            var options = {
                xaxis: {
                    mode: "time",
                    minTickSize: [1, "day"],
                    },
                legend: { position: 'nw'},
                yaxes: [
                    {
                        min: 0,
                        labelWidth: 100,
                    }, {
                        min: 0,
                        max: 100,
                        tickFormatter: percFormatter,
                        position: 'right',
                    } ],
                selection: {mode: "x"},
            };
            var options2 = {
                xaxis: {
                    mode: "time",
                    minTickSize: [1, "day"],
                    },
                legend: { position: 'nw'},
                yaxes: [{
                        min: 0,
                        labelWidth: 100,
                        tickFormatter: timespanFormatter,
                        max: 60*60*24,
                    }, {
                        min: 0,
                        max: 100,
                        tickFormatter: percFormatter,
                        position: 'right',
                    } ],
                selection: {mode: "x"},
            };
            var plot = $.plot("#placeholder", d, options);
            var plot2 = $.plot("#placeholder2", d2, options2);
            var overview = $.plot("#overview", [d[0], d[1]], {
                xaxis: {
                    mode: "time",
                    minTickSize: [1, "year"],
                },
                yaxes: [ { show: false}, { show: false} ],
                selection: {mode: "x"},
                series: {
                    lines: {
                        show: true,
                        lineWidth: 1
                    },
                    shadowSize: 0
                },
                legend: { show: false },
            });

            function setRange(ranges) {
                // do the zooming
                plot = $.plot("#placeholder", d, $.extend(true, {}, options, {
                    xaxis: {
                        min: ranges.xaxis.from,
                        max: ranges.xaxis.to
                    }
                }));
                plot2 = $.plot("#placeholder2", d2, $.extend(true, {}, options2, {
                    xaxis: {
                        min: ranges.xaxis.from,
                        max: ranges.xaxis.to
                    }
                }));

                // don't fire event on the overview to prevent eternal loop
                overview.setSelection(ranges, true);

                // Calculate stats
                function sumup(array) {
                    var sum = 0;
                    for (var i = 0; i < array.length; i++) {
                        if(ranges.xaxis.from <= array[i][0] && array[i][0] <= ranges.xaxis.to) {
                            if (array[i][1]) sum += array[i][1];
                        }
                    }
                    return sum;
                }
                var alluploads = sumup(d_pkgs);
                var haskelluploads = sumup(d_haskell_pkgs);
                $("#alluploads").text(alluploads);
                $("#haskelluploads").text(haskelluploads);
		if (alluploads> 0) {
			$("#uploadsperc").text((haskelluploads/alluploads * 100).toFixed() + "%%");
		} else {
			$("#uploadsperc").text("\u2014");
		}

                var allbuildtime = sumup(d_buildtime);
                var haskellbuildtime = sumup(d_haskell_buildtime);
                $("#allbuildtime").text(timespanFormatter(allbuildtime));
                $("#haskellbuildtime").text(timespanFormatter(haskellbuildtime));
		if (allbuildtime > 0) {
			$("#buildtimeperc").text((haskellbuildtime/allbuildtime * 100).toFixed() + "%%");
		} else {
			$("#buildtimeperc").text("\u2014");
		}

		if (alluploads > 0) {
			var allavgbuildtime = allbuildtime / alluploads
                	$("#allavgbuildtime").text(timespanFormatter(allavgbuildtime));
		} else {
                	$("#allavgbuildtime").text("\u2014");
		}
		if (haskelluploads > 0) {
			var haskellavgbuildtime = haskellbuildtime / haskelluploads
                	$("#haskellavgbuildtime").text(timespanFormatter(haskellavgbuildtime));
		} else {
                	$("#haskellavgbuildtime").text("\u2014");
		}

                var wattage = 472; // http://www.vertatique.com/average-power-use-server
                var kgco2perkwh = 0.5925; // http://www.carbonfund.org/how-we-calculate
                var allco2 = ((allbuildtime / (60*60)) * wattage / 1000) * kgco2perkwh;
                var haskellco2 = ((haskellbuildtime / (60*60)) * wattage / 1000) * kgco2perkwh;
                $("#allco2").text(allco2.toFixed()+ "kg");
                $("#haskellco2").text(haskellco2.toFixed()+ "kg");
                $("#wattage").text(wattage);
                $("#kgco2perkwh").text(kgco2perkwh);
            }


            $("#placeholder").bind("plotselected", function (event, ranges) {
                setRange(ranges);
            });

            $("#placeholder2").bind("plotselected", function (event, ranges) {
                plot.setSelection(ranges);
            });
            $("#overview").bind("plotselected", function (event, ranges) {
                plot.setSelection(ranges);
            });

            function setRangeFromNow(days) {
                var now = new Date().getTime();
                var then = now - 1000*60*60*24*days;
                setRange({xaxis:{from: then, to: now}});
            }

            $("#lastweek").click(function(){setRangeFromNow(7)});
            $("#lastmonth").click(function(){setRangeFromNow(31)});
            $("#lastyear").click(function(){setRangeFromNow(266)});
            setRangeFromNow(7);

            function checkPerc(){ 
                d[2].lines.lineWidth = ($("#toggle-perc").is(':checked')? 1 : 0);
                plot.setData(d);
                plot.draw();
                d2[2].lines.lineWidth = ($("#toggle-perc").is(':checked')? 1 : 0);
                plot2.setData(d2);
                plot2.draw();   
            }
            checkPerc();
            $("#toggle-perc").change(checkPerc);

            $("#flotversion").text($.plot.version);
        });
    </script>
    </head>
    <body>
    <table>
    <tr>
    <td>
    <div id="placeholder" class="demo-placeholder"></div>
    <div id="placeholder2" class="demo-placeholder"></div>
    <div id="overview" class="demo-placeholder"></div>
    </td>
    <td valign="top">
    <h3>What is this?</h3>
    <p>
    This plots the number and buildtimes of uploads to the Debian buildd database
    on architecture %(arch)s, with special emphasis on packages by the Debian Haskell
    Group. The statistics below combine the data from the selected range; you can
    select ranges by dragging in the graphs, or by using the buttons below.
    </p>
    <p>
    This was created by Joachim Breitner &lt;<a
    href="mailto:nomeata@debian.org">nomeata@debian.org</a>&gt;, and the source can
    be found in the Debian Haskell Group's <a
    href="http://darcs.debian.org/pkg-haskell/tools/buildd-stats.py">tools
    repo</a>. Improvements are welcome, especially with regard to the HTML styling.
    </p>
    <p>
    The graphs are generated with <a href="http://www.flotcharts.org/">Flot</a> version <span id="flotversion"></span>.
    </p>

    <h3>Control</h3>
    <input checked="checked" type='checkbox' id="toggle-perc" name='toggle-perc'/><label for='toggle-perc'>Show percentages</label><br/>
    Select range: 
    <button id="lastweek" type="button">Last week</button> 
    <button id="lastmonth" type="button">Last month</button> 
    <button id="lastyear" type="button">Last year</button> 

    <h3>Statistics</h3>

    <table class="stats">
    <thead><th>&nbsp;</th><th>All</th><th colspan="2">Haskell</th></thead>
    <tbody>
    <tr><th># uploads:</th><td id="alluploads"/><td id="haskelluploads"/><td id="uploadsperc"/></tr>
    <tr><th>buildtime:</th><td id="allbuildtime"/><td id="haskellbuildtime"/><td id="buildtimeperc"/></tr>
    <tr><th>avg. buildtime:</th><td id="allavgbuildtime"/><td id="haskellavgbuildtime"/><td>&nbsp;</td></tr>
    <tr><th>CO<sub>2</sub>:<sup>*</sup></th><td id="allco2"/><td id="haskellco2"/><td>&nbsp;</td></tr>
    </tbody>
    </table>
    <div style="font-size:small; text-align:right">
    <sup>*</sup>CO<sub>2</sub> production based on <a href="http://www.vertatique.com/average-power-use-server"><span id="wattage"></span> Watt</a> and <a href="http://www.carbonfund.org/how-we-calculate"><span id="kgco2perkwh"></span> kg CO<sub>2</sub>/kWh</a>.
    </div>
    </td>
    </tr>
    </table>
	''' % { 'arch': ARCH }

print '''
    </body>
    </html>
    '''
