#!/usr/bin/env python
# coding=utf-8
import cgitb
import cgi
import os,sys,string,requests
import xml.etree.ElementTree as ET
import os,sys,string,requests
import xml.etree.ElementTree as ET
import math
import matplotlib as plt
import numpy as np
import pandas as pd
import arrow
import string
from random import *
import matplotlib.pyplot as plt
import metpy.calc as mpcalc
from metpy.cbook import get_test_data
from metpy.plots import add_metpy_logo, SkewT
from metpy.units import units

cgitb.enable()

#Johannes Mikkola, 8/2018
#CGI - Python based webpage
#FMI radiosounding data to Skew-T or printed data

#how to use:
#this python script must be executable
#place python script in /cgi-bin/ and run server: python -m CGIHTTPServer
#and create empty directory /figures/

#notable information:
#*FMI open data available ~2015->
#*in 2018, FMI open data didn't include pressure levels of sounding measurements so pressure is calculated by function: height2pressure

def height2pressure(height):
    t0 = 288
    gamma = 6.5*0.001
    p0 = 1013.25
    g = 9.81
    Rd = 287.00
    return p0 * (1 - (gamma / t0) * height) ** (g / (Rd * gamma))

def getWindComponent(speed,wdir):
    u = -speed * np.sin(2*np.pi*wdir/360)
    v = -speed * np.cos(2*np.pi*wdir/360)
    return u, v

def fmi2skewt(station,time,img_name):

    apikey='e72a2917-1e71-4d6f-8f29-ff4abfb8f290'

    url = 'http://data.fmi.fi/fmi-apikey/' + str(apikey) + '/wfs?request=getFeature&storedquery_id=fmi::observations::weather::sounding::multipointcoverage&fmisid=' + str(station) + '&starttime=' + str(time) + '&endtime=' + str(time) + '&'

    req = requests.get(url)
    xmlstring = req.content
    tree=ET.ElementTree(ET.fromstring(xmlstring))
    root = tree.getroot()

    #reading location and time data to "positions" from XML
    positions = ""
    for elem in root.getiterator(tag='{http://www.opengis.net/gmlcov/1.0}positions'):
        positions = elem.text

    #'positions' is string type variable
    #--> split positions into a list by " "
    #then remove empty chars and "\n"
    # from pos_split --> data into positions_data

    try:
	       pos_split = positions.split(' ')
    except NameError:
	       return "Sounding data not found: stationid " + station + " time " + time

    pos_split = positions.split(' ')

    positions_data = []
    for i in range(0,len(pos_split)):
        if not (pos_split[i] == "" or pos_split[i] == "\n"):
            positions_data.append(pos_split[i])

    #index for height: 2,6,10 etc in positions_data
    height = []
    myList = range(2,len(positions_data))
    for i in myList[::4]:
        height.append(positions_data[i])

    p = []
    for i in range(0,len(height)):
        p.append(height2pressure(float(height[i])))

    #reading wind speed, wind direction, air temperature and dew point data to 'values'
    values = ""
    for elem in root.getiterator(tag='{http://www.opengis.net/gml/3.2}doubleOrNilReasonTupleList'):
        values = elem.text

    #split 'values' into a list by " "
    #then remove empty chars and "\n"

    val_split = values.split(' ')
    values_data = []
    for i in range(0,len(val_split)):
        if not(val_split[i] == "" or val_split[i]=="\n"):
            values_data.append(val_split[i])

    #data in values_data: w_speed, w_dir, t_air, t_dew
    wind_speed = []
    wind_dir = []
    T = []
    Td = []
    myList = range(0,len(values_data))
    for i in myList[::4]:
        wind_speed.append(float(values_data[i]))
        wind_dir.append(float(values_data[i+1]))
        T.append(float(values_data[i+2]))
        Td.append(float(values_data[i+3]))

    if stationid == "101104":
        loc_time = "Jokioinen Ilmala " + time1
    elif stationid == "101932":
        loc_time = "Sodankyla Tahtela " + time1
    else:
        return None

    #calculate wind components u,v:
    u = []
    v = []
    for i in range(0,len(wind_speed)):
        u1, v1 = getWindComponent(wind_speed[i], wind_dir[i])
        u.append(u1)
        v.append(v1)

    #find index for pressure < 100hPa (for number of wind bars)
    if min(p)>100:
        wthin = len(p)/20
        u_plot = u
        v_plot = v
        p_plot = p
    else:
        for i in range(0,len(p)):
            if p[i]-100<=0:
                wthin = i/20
                u_plot = u[0:i]
                v_plot = v[0:i]
                p_plot = p[0:i]
                break;

    #units
    wind_speed = wind_speed*units("m/s")
    wind_dir = wind_dir*units.deg
    T = T*units.degC
    Td = Td*units.degC
    p = p*units("hPa")

    #calculate pwat, lcl, cape, cin and plot cape
    pwat = mpcalc.precipitable_water(Td,p,bottom=None,top=None)
    lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
    prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')

    try:
        cape,cin = mpcalc.cape_cin(p,T,Td,prof)
    except IndexError:
        cape = 0*units("J/kg")
        cin = 0*units("J/kg")

    #__________________plotting__________________
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)
    font_par = {'family': 'monospace',
        'color':  'darkred',
        'weight': 'normal',
        'size': 10,
        }
    font_title = {'family': 'monospace',
        'color':  'black',
        'weight': 'normal',
        'size': 20,
        }
    font_axis = {'family': 'monospace',
        'color':  'black',
        'weight': 'normal',
        'size': 10,
        }
    # Plot the data using normal plotting functions, in this case using
    # log scaling in Y, as dictated by the typical meteorological plot
    skew.plot(p, T, 'k')
    skew.plot(p, Td, 'b')
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-40, 60)
    skew.plot_barbs(p_plot[0::wthin], u_plot[0::wthin], v_plot[0::wthin])
    skew.plot_dry_adiabats(alpha=0.4)
    skew.plot_moist_adiabats(alpha=0.4)
    skew.plot_mixing_lines(alpha=0.4)
    skew.shade_cape(p, T, prof,color="orangered")
    plt.title(loc_time,fontdict=font_title)
    plt.xlabel("T (C)",fontdict=font_axis)
    plt.ylabel("P (hPa)",fontdict=font_axis)

    #round and remove units from cape,cin,plcl,tlcl,pwat
    if cape.magnitude > 0:
        capestr = str(np.round(cape.magnitude))
    else:
        capestr = "NaN"

    if cin.magnitude > 0:
        cinstr = str(np.round(cin.magnitude))
    else:
        cinstr = "NaN"

    lclpstr = str(np.round(lcl_pressure.magnitude))
    lclTstr = str(np.round(lcl_temperature.magnitude))
    pwatstr = str(np.round(pwat.magnitude))

    str_par = "CAPE[J/kg]=" + capestr + " CIN[J/kg]=" + cinstr + " Plcl[hPa]=" + lclpstr + " Tlcl[C]=" + lclTstr + " pwat[mm]=" + pwatstr
    font = {'family': 'monospace',
        'color':  'darkred',
        'weight': 'normal',
        'size': 10,
        }
    plt.text(-20,1250,str_par,fontdict=font_par)
    save_file = "figures/" + img_name + ".png"
    plt.savefig(save_file)

def printfmidata(station,time):
    apikey='e72a2917-1e71-4d6f-8f29-ff4abfb8f290'

    url = 'http://data.fmi.fi/fmi-apikey/' + str(apikey) + '/wfs?request=getFeature&storedquery_id=fmi::observations::weather::sounding::multipointcoverage&fmisid=' + str(station) + '&starttime=' + str(time) + '&endtime=' + str(time) + '&'

    req = requests.get(url)
    xmlstring = req.content
    tree=ET.ElementTree(ET.fromstring(xmlstring))
    root = tree.getroot()

    #reading location and time data to "positions" from XML
    positions = ""
    for elem in root.getiterator(tag='{http://www.opengis.net/gmlcov/1.0}positions'):
        positions = elem.text

    #'positions' is string type variable
    #--> split positions into a list by " "
    #then remove empty chars and "\n"
    # from pos_split --> data into positions_data

    try:
	       pos_split = positions.split(' ')
    except NameError:
	       return "Sounding data not found: stationid " + station + " time " + time


    pos_split = positions.split(' ')

    positions_data = []
    for i in range(0,len(pos_split)):
        if not (pos_split[i] == "" or pos_split[i] == "\n"):
            positions_data.append(pos_split[i])

    #index for height: 2,6,10 etc in positions_data
    height = []
    myList = range(2,len(positions_data))
    for i in myList[::4]:
        height.append(positions_data[i])


    p = []
    for i in range(0,len(height)):
        p.append(height2pressure(float(height[i])))

    #reading wind speed, wind direction, air temperature and dew point data to 'values'
    values = ""
    for elem in root.getiterator(tag='{http://www.opengis.net/gml/3.2}doubleOrNilReasonTupleList'):
        values = elem.text

    #split 'values' into a list by " "
    #then remove empty chars and "\n"

    val_split = values.split(' ')
    values_data = []
    for i in range(0,len(val_split)):
        if not(val_split[i] == "" or val_split[i]=="\n"):
            values_data.append(val_split[i])

    #data in values_data: w_speed, w_dir, t_air, t_dew
    wind_speed = []
    wind_dir = []
    T = []
    Td = []
    myList = range(0,len(values_data))
    for i in myList[::4]:
        wind_speed.append(float(values_data[i]))
        wind_dir.append(float(values_data[i+1]))
        T.append(float(values_data[i+2]))
        Td.append(float(values_data[i+3]))

    if stationid == "101104":
        loc_time = "Jokioinen Ilmala " + time1
    elif stationid == "101932":
        loc_time = "Sodankyla Tahtela " + time1
    else:
        return None

    print '<div class = "text-center"><br><br>'

    str2 = loc_time + "<br><br>"
    print str2

    str2 = "Wspd Wdir T Tdew P z <br><br>"
    print str2

    myList = range(0,len(height))
    for i in myList[::1]:
        str2 = str(wind_speed[i]) + "  " + str(wind_dir[i]) + "  " + str(T[i]) + "  " + str(Td[i]) + "  " + str(np.round(p[i],decimals=0)) + "  " + str(height[i]) + '<br>'
        print str2

    print '<form method="post" action="open_data.py">'
    print '</div>'

#_______HTML___________________________

print("Content-Type: text/html\n\r\n\r")
print
print '''
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
</head>
<body>
<br><br><br>
'''

#today's date
date = arrow.now().format('YYYY-MM-DD')
date_split = date.split('-')
YYYY = date_split[0]
MM = date_split[1]
DD = date_split[2]


print '<form method="post" action="fmi2skewt.py">'
print '<div class = "text-center">'
#____input for time____
print '''
<div class="form-inline">
    <div class="xs-2">
        <label>Year</label>
        <input class="form-control" value="''' + YYYY + '''" type="text" name="year">
    </div><br>
    <div class="xs-2">
        <label for="month">Month</label>
        <input class="form-control" value="''' + MM + '''" type="text" name="month">
    </div><br>
    <div class="xs-2">
        <label for="day">Day</label>
        <input class="form-control" value="''' + DD + '''" type="text" name="day">
    </div><br>
</div>

<div class="radio-inline">
  <label><input type="radio" name="time" value="00">00</label>
</div>
<div class="radio-inline">
  <label><input type="radio" name="time" value="06">06</label>
</div>
<div class="radio-inline">
  <label><input type="radio" name="time" value="12">12</label>
</div>
<div class="radio-inline">
  <label><input type="radio" name="time" value="18">18</label>
</div>
<br><br>

'''
#____station____
print '''

<p class="text-info">Jokioinen: 00UTC, 06UTC, 12UTC and 18UTC<br>
Sodankylä: 00UTC and 12UTC</p>

<div class="radio-inline">
  <label><input type="radio" name="station" value="Jokioinen">Jokioinen</label>
</div>
<div class="radio-inline">
  <label><input type="radio" name="station" value="Sodankyla">Sodankyla</label>
</div>
<br><br>

'''

print '<input type="submit" class="btn btn-default" name="Skew-T" value="Skew-T">'
print '<input type="submit" class="btn btn-default" name="Data" value="Data">'

print "</form>"
print '<script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>'
print '<script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>'
print '<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js" integrity="sha384-smHYKdLADwkXOn1EmN1qk/HfnUcbVRZyYmZ4qpPea6sjB/pTJ0euyQp0Mk8ck+5T" crossorigin="anonymous"></script>'
print '</div>'

form = cgi.FieldStorage()

if "Skew-T" in form:
    try:
        year = form.getvalue("year")
        year = year.replace(" ","")
        month = form.getvalue("month")
        month = month.replace(" ","")
        if len(month)==1:
            month = "0" + month
        day = form.getvalue("day")
        day = day.replace(" ","")
        if len(day)==1:
            day = "0" + day
        hour = str(form.getvalue("time"))
        time1 = year + "-" + month + "-" + day + "T" + hour + ":00:00Z"
        if form.getvalue("station")=="Jokioinen":
            stationid = "101104"
        elif form.getvalue("station")=="Sodankyla":
            stationid = "101932"
        try:
            #generate random name for image file
            img_name = "".join(choice(string.ascii_letters) for x in range(8))
            fmi2skewt(stationid,time1,img_name)
            open_file = "figures/" + img_name + ".png"
            data_uri = open(open_file, 'rb').read().encode('base64').replace('\n', '')
            img_tag = '<img src="data:image/png;base64,{0}">'.format(data_uri)
            print "<center>"
            print(img_tag)
            print "</center>"

        except ValueError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
        except NameError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
        except IndexError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
    except TypeError:
        print "Please fill in required fields"
        exit()

if "Data" in form:
    try:
        year = form.getvalue("year")
        year = year.replace(" ","")
        month = form.getvalue("month")
        month = month.replace(" ","")
        if len(month)==1:
            month = "0" + month
        day = form.getvalue("day")
        day = day.replace(" ","")
        if len(day)==1:
            day = "0" + day
        hour = str(form.getvalue("time"))
        time1 = year + "-" + month + "-" + day + "T" + hour + ":00:00Z"
        if form.getvalue("station")=="Jokioinen":
            stationid = "101104"
        elif form.getvalue("station")=="Sodankyla":
            stationid = "101932"
        try:
            printfmidata(stationid,time1)
        except ValueError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
        except NameError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
        except IndexError:
            print "<center>"
            print "Data not found: " + form.getvalue("station") + " " + time1
            print "</center>"
    except TypeError:
        print "Please fill in required fields"

print "</body>"
print "</html>"
