# In[]:
# Import libraries and set options

import pandas
import seaborn
import matplotlib
import json
import folium
import branca

pandas.set_option("display.max_columns", 7)
pandas.set_option("display.max_colwidth", 30)
# ======

# In[]:
# Define functions


def fGetCountyFromCityState(iDFCityState):
    tCounties = pandas.DataFrame(columns=["County", "County FIPS"])
    for i, city in iDFCityState.iterrows():
        tCandidates = (
            iDBCities.loc[(iDBCities["State"] == city["State"])
                          & (iDBCities["City"] == city["City"]),
                          ["County", "County FIPS"]])

        if len(tCandidates) == 1:
            tCounties = tCounties.append(tCandidates,
                                         ignore_index=True, sort=False)
        else:
            tCounties = tCounties.append(
                pandas.DataFrame([["NotFound", "NotFound"]],
                                 columns=["County", "County FIPS"]),
                ignore_index=True, sort=False)
    return tCounties


def fGetCountyFIPSFromCountyState(iDFCountyState):
    tFIPS = pandas.DataFrame(columns=["County FIPS"])
    for i, county in iDFCountyState.iterrows():
        tCandidates = (
            wDBCities.loc[(wDBCities["State"] == county["State"])
                          & (wDBCities["County"] == county["County"]),
                          ["County FIPS"]])
        if len(tCandidates) > 0:
            tFIPS = tFIPS.append(tCandidates.iloc[0, :],
                                 ignore_index=True, sort=False)
        else:
            tFIPS = tFIPS.append(
                pandas.DataFrame([["NotFound"]], columns=["County FIPS"]),
                ignore_index=True, sort=False)
    return tFIPS


# ======

# In[]:
# Import data

# https://chronicdata.cdc.gov/500-Cities/500-Cities-Local-Data-for-Better-Health-2018-relea/6vp6-wxuq
# This is a 220MB csv file.
# Click on Export > CSV
iDBHealth = pandas.read_csv(
    "data\\500_Cities__Local_Data_for_Better_Health__2017_release.csv",
    usecols=["StateAbbr", "StateDesc", 'CityName', 'Data_Value', "Measure",
             "GeoLocation", "DataValueTypeID", "GeographicLevel"])
iDBHealth = (
    iDBHealth
    .loc[(iDBHealth["StateAbbr"] != "US")
         & (iDBHealth["DataValueTypeID"] == "AgeAdjPrv")
         & (iDBHealth["GeographicLevel"] == "City"),
         ["StateDesc", 'CityName', "Measure",
          'Data_Value', "GeoLocation"]]
    .sort_values(["StateDesc", "CityName"]))


# https://simplemaps.com/data/us-cities
iDBCities = (
    pandas
    .read_csv("data\\uscitiesv1.4.csv",
              usecols=["city", "state_name", "county_name", "county_fips"])
    .sort_values(["state_name", "city"]))
iDBCities.columns = ["City", "State", "County FIPS", "County"]
iDBCities["County FIPS"] = iDBCities["County FIPS"].astype(str)
iDBCities["County FIPS"] = iDBCities["County FIPS"].apply(lambda f: f.zfill(5))

# https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_2015.zip
iDBAir = (
    pandas
    .read_csv("data\\annual_aqi_by_county_2015.csv",
              usecols=["State", "County", "Days with AQI",
                       "Unhealthy for Sensitive Groups Days", "Unhealthy Days",
                       "Very Unhealthy Days", "Hazardous Days", "Median AQI"]))
iDBAir.at[iDBAir["State"] == "District Of Columbia", "State"] = (
    "District of Columbia")
iDBAir["County"] = iDBAir["County"].apply(str.rstrip)

# http://www2.census.gov/geo/tiger/GENZ2015/shp/cb_2015_us_county_5m.zip
# Upload .zip file to mapshaper.org and export as GeoJSON
with open("data\\cb_2015_us_county_5m.json", "r") as geo:
    iGeoData = json.load(geo)
# =====

# In[]:
# Select and prepare the asthma and smoking data

wDBHealth = (iDBHealth.loc[
    (iDBHealth["Measure"] == 'Current asthma among adults aged >=18 Years'),
    ["StateDesc", 'CityName', "GeoLocation", 'Data_Value']]
    .reset_index(drop=True))

wDBHealth.columns = ["State", "City", "GeoLocation", "Asthma Prevalence"]

wDBHealth["State"] = (
        wDBHealth["State"]
        .apply(lambda name: name.replace("Carolin", "Carolina"))
        .apply(lambda name: name.replace("District of C",
                                         "District of Columbia")))

tDBSmoking = iDBHealth.loc[
    (iDBHealth["Measure"] == "Current smoking among adults aged >=18 Years"),
    'Data_Value'].reset_index(drop=True)
tDBSmoking = tDBSmoking.rename("Smoking Prevalence")

wDBHealth = pandas.concat([wDBHealth, tDBSmoking], axis=1)

wDBHealth["City"] = (
    wDBHealth["City"]
    .apply(lambda name: name.replace("St.", "Saint")))

wDBHealth['Lat'], wDBHealth['Lon'] = \
    wDBHealth['GeoLocation'].str.split(',', 1).str
wDBHealth['Lat'] = wDBHealth['Lat'].apply(lambda s: s[1:]).astype(float)
wDBHealth['Lon'] = wDBHealth['Lon'].apply(lambda s: s[:-1]).astype(float)
wDBHealth["GeoLocation"] = list(zip(wDBHealth.Lat, wDBHealth.Lon))

# Get the county of each city (some were found manually)
wDBHealth = pandas.concat([wDBHealth,
                           fGetCountyFromCityState
                           (wDBHealth[["State", "City"]])], axis=1)
wDBHealth.loc[wDBHealth.index[110], 'County'] = "Ventura"
wDBHealth.loc[wDBHealth.index[220], 'County'] = "Ada"
wDBHealth.loc[wDBHealth.index[307], 'County'] = "Jackson"
wDBHealth.loc[wDBHealth.index[461], 'County'] = "Salt Lake"
# =====

# In[]:
# Select and prepare the air quality database
wDBAir = iDBAir.copy()
wDBAir["County"] = (
    wDBAir["County"]
    .apply(lambda name: name.replace(" City", " (city)"))
    .apply(lambda name: name.replace(" (City)", " (city)"))
    .apply(lambda name: name.replace("Saint ", "St. "))
    .apply(lambda name: name.replace("Sainte ", "Ste. ")))

wDBAir.loc[wDBAir.index[254], 'County'] = "LaSalle"
wDBAir.loc[wDBAir.index[549], 'County'] = "Carson City (city)"
wDBAir.loc[wDBAir.index[584], 'County'] = "Doña Ana"
wDBAir.loc[wDBAir.index[941], 'County'] = "Charles City"

# Get the county FIPS of each county (some were found manually)
wDBCities = iDBCities.drop_duplicates(["State", "County"])
wDBAir = pandas.concat([wDBAir,
                        fGetCountyFIPSFromCountyState
                        (wDBAir[["State", "County"]])], axis=1)
wDBAir = wDBAir.drop([143, 514, 808, 809, 933, 934], axis=0)
# =====

# In[]:
# Merge the datasets and cleanup

wDBAsthma = wDBHealth.merge(wDBAir, on="County FIPS")
wDBAsthma = wDBAsthma.iloc[:, [0, 7, 8, 1, 2, 3, 4, 11, 12, 13, 14, 15, 16]]
wDBAsthma.columns = [
    'State', 'County', 'County FIPS', 'City', "Coords", "Asthma Prevalence",
    "Smoking Prevalence", 'Days with AQI',
    'Unhealthy for Sensitive Groups Days', 'Unhealthy Days',
    'Very Unhealthy Days', 'Hazardous Days', 'Median AQI']
wDBAsthma = wDBAsthma.reset_index(drop=True)

wDBAsthma.iloc[:, 5:] = (
    wDBAsthma.iloc[:, 5:]
    .astype(float))

wDBAsthma["Proportion of days with bad air quality"] = (
    (wDBAsthma
     .loc[:, ["Unhealthy for Sensitive Groups Days", 'Unhealthy Days',
              'Very Unhealthy Days', 'Hazardous Days']]
     .sum(axis=1))
    / wDBAsthma.loc[:, 'Days with AQI'])

wDBAsthma = wDBAsthma[['State', 'County', "County FIPS", 'City', "Coords",
                       "Asthma Prevalence", "Smoking Prevalence", "Median AQI",
                       "Proportion of days with bad air quality"]]


# In[]:
oFig, oAx = matplotlib.pyplot.subplots(figsize=(11.7, 8.27))
oAsthmaSmokeAQI = seaborn.scatterplot(
    "Median AQI", "Smoking Prevalence",
    hue="Asthma Prevalence", ax=oAx, data=wDBAsthma)
oAsthmaSmokeAQI.set_xlabel("Median Air Quality Index (lower is better)")
oAsthmaSmokeAQI.set_ylabel("Age Adjusted Smoking Prevalence")
oAsthmaSmokeAQI.get_legend().set_title("Age Ajusted ")
oAsthmaSmokeAQI.set(title="Relationship between AQI, smoking and asthma in "
                          + "474 big cities of the USA (2015)")
oAsthmaSmokeAQI.get_figure().savefig("Asthma_Smoking_and_AQI.jpg")
# =====

# In[]:
# Create a choropleth map of air quality
oMap = folium.Map((39.8283, -98.5795), zoom_start=5, tiles="Stamen Toner")

# Only use the counties for which air quality data is available
wGeoData = dict({"type": "FeatureGroup", "features": []})
tListFIPS = set(wDBAir["County FIPS"].tolist())
for f in iGeoData["features"]:
    if f["properties"]["GEOID"] in tListFIPS:
        wGeoData["features"].append(f)
wChoroLayer = folium.Choropleth(wGeoData,
                                data=wDBAir,
                                name="Air Quality Index",
                                columns=("County FIPS", "Median AQI"),
                                key_on="feature.properties.GEOID",
                                fill_color="YlOrRd",
                                fill_opacity=0.9)

# Place the cities and color their marker according to the asthma prevalence
wCityLayer = folium.FeatureGroup(name="Cities")
fColor = (
    branca
    .colormap
    .LinearColormap(["green", "yellow", "red"],
                    vmin=min(wDBAsthma["Asthma Prevalence"]),
                    vmax=max(wDBAsthma["Asthma Prevalence"])))
wDBAsthma["Color"] = wDBAsthma["Asthma Prevalence"].apply(fColor)

for name, col, coord in zip(wDBAsthma["City"], wDBAsthma["Color"],
                            wDBAsthma["Coords"]):
    wCityLayer.add_child(
        folium.CircleMarker(location=coord, tooltip=name, radius=3,
                            fill_color=col, fill_opacity=1, color=None))


oMap.add_child(wChoroLayer)
oMap.add_child(wCityLayer)
oMap.add_child(folium.LayerControl())
oMap.save("Asthma_and_Air_Quality_map.html")
