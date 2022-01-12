'''
Copyright 2022 Joshua Henderson

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import math
import logging

logging.captureWarnings(capture=True) # Redirect warnings to the logs

# Import geodataframes (gdfs)
cities_DIR =   # Insert location of cities .shp file
counties_DIR = # Insert location of counties .shp file
cities_gdf = gpd.read_file( cities_DIR )
counties_gdf = gpd.read_file( counties_DIR )

# Make copies of the two gdfs so rows can be dropped while maintaining the originals
counties_five_states_gdf = counties_gdf.copy()
cities_five_states_gdf = cities_gdf.copy()

# Change the FIPS codes to integers for easier comparisons
cities_five_states_gdf['STATE_FIPS'] = np.int64(cities_five_states_gdf['STATE_FIPS'])
counties_five_states_gdf['STATEFP'] = np.int64(counties_five_states_gdf['STATEFP'])


fips= [17, 18, 19, 27, 46]                          # List of the FIPS codes we need
state = ['IL', 'IN', 'IA', 'MN', 'SD']              # List of the States those FIPS codes represent
for row in range(len(cities_five_states_gdf)):      # Iterate through the Cities 
    curr = cities_five_states_gdf.iloc[row]['STATE_FIPS']   # Get the FIPS code from the current city
    keep = False                                            # Initialize keep to false
    for n in fips:                                          # Cycle through the FIPS codes we need
        if n == curr:                                           # If this city has a FIPS code we need...
            keep = True                                             # Keep it
    if not keep:                                                # If we done need this city...
        cities_five_states_gdf['STATE_FIPS'][row] = np.nan          # Set the FIPS code to numpy nan (for dropping later)

for row in range(len(counties_five_states_gdf)):    # Repeat the above states for the counties
    curr = counties_five_states_gdf.iloc[row]['STATEFP']
    keep = False
    for n in fips:
        if n == curr:
            keep = True
    if not keep:
        counties_five_states_gdf['STATEFP'][row] = np.nan

# Drop the rows of the cities and counties that aren't in the five states that we need
cities_five_states_gdf.dropna(subset = ['STATE_FIPS'], inplace = True)
counties_five_states_gdf.dropna(subset = ['STATEFP'], inplace = True)

cities_five_states_gdf.drop(columns=['COUNTYFIPS', 'COUNTY'], inplace = True)   # Drop the COUNTYFIPS and COUNTY columns
cities_five_states_gdf = cities_five_states_gdf[cities_five_states_gdf.FEATURE == 'Civil']  # Filter feature to only include Civil

counties_projected_gdf = counties_five_states_gdf.to_crs('epsg:4087')       # Reproject the county dataframe    
cities_projected_gdf = cities_five_states_gdf.to_crs('epsg:4087')           # Reproject the cities dataframe (for joining later)
counties_projected_gdf['STATEFP'] = np.int64(counties_projected_gdf['STATEFP']) # Change FIPS to integer

IA_projected_gdf = counties_projected_gdf[counties_projected_gdf.STATEFP == 19]         # Iowa projected counties
IA_nonprojected_gdf = counties_gdf[counties_gdf.STATEFP == '19']  # Iowa non-projected counties

# Plot Iowa projected and non-projected counties on the same figure
# The best way I found to do this was side-by-side as this is the only way that shows the difference in axis marks
# If plotted on the same axis, the non-projected counties are invisible
# If plotted vertically separated, the axes don't show that the projected axes are much bigger than the nonprojected axes
fig, (ax1, ax2) = plt.subplots(1, 2)        # Create side-by-side subplots
'''
for curr in IA_projected_gdf['geometry']:
    if type(curr).__name__ == 'MultiPolygon':
        for poly in curr:
            ax1.plot(poly.exterior.xy[0], poly.exterior.xy[1], color='blue')
    else:
        ax1.plot(curr.exterior.xy[0], curr.exterior.xy[1], color='blue')
        
for curr in IA_nonprojected_gdf['geometry']:
    if type(curr).__name__ == 'MultiPolygon':
        for poly in curr:
            ax2.plot(poly.exterior.xy[0], poly.exterior.xy[1], color='red')
    else:
        ax2.plot(curr.exterior.xy[0], curr.exterior.xy[1], color='red')
        
plt.show()
'''
# === Short way of plotting, with counties filled in and proportionate scaling ===
IA_projected_gdf.plot(ax = ax1)             # Plot the projected counties
IA_nonprojected_gdf.plot(ax = ax2)          # Plot the non-projected counties
plt.show()                                  # Display the plot 


# Total area of a county is its land area plus its water area
counties_projected_gdf['TOTAL_AREA'] = counties_projected_gdf['ALAND']+counties_projected_gdf['AWATER']

joined_gdf = gpd.tools.sjoin(cities_projected_gdf, counties_projected_gdf, how='inner', op='within' )   # Spatial join the cities and counties
joined_gdf = joined_gdf.drop( columns = ['index_right'])                                                # Drop right index (useless)
joined_gdf.rename(columns={'NAME_right':'COUNTY'}, inplace = True)                                      # Rename column with names of counties
joined_gdf.rename(columns={'NAME_left':'CITY'}, inplace = True)                                         # Rename column with names of cities

print('\nFive Largest Cities\n')
for i in range(5):  # Loop through 0..4 to print out the names without the indices
    # Print out the city name of the ith largest city in the joined_gdf that is sorted by population in 2010
    # This loop has to be done because city names are not unique, so we can't group by city and just print them out
    print(joined_gdf.sort_values(by=['POP_2010'], ascending=False).iloc[i]['CITY'])

# Aggregation work and appending to the gdf
# I used COUNTYNS as the index as it appeared to be a unique identifier for individual counties

pop_totals_df = joined_gdf.groupby(['COUNTYNS']).agg({'POP_2010':'sum'})    # Sum up populations from all cities with the same countyns
pop_totals_df['COUNTY'] = [joined_gdf[joined_gdf.COUNTYNS == ID]['COUNTY'].iloc[0] for ID in pop_totals_df.index] # Get the county name for each countyns

# Add the population total for each county to the joined_gdf
joined_gdf['COUNTY_POP_TOTAL'] = [pop_totals_df[pop_totals_df.index == i]['POP_2010'].iloc[0] for i in joined_gdf['COUNTYNS']]
# Calculate the people per square meter for each county
joined_gdf['COUNTY_PEOPLE_PER_SQ_METER'] = joined_gdf['COUNTY_POP_TOTAL']/joined_gdf['TOTAL_AREA']

# Taking the mean of the county statistics from each city in a county doesn't change the statistic
# I used this to get a dataframe with just the counties and population densities
pop_density_df = joined_gdf.groupby(['COUNTYNS']).agg({'COUNTY_PEOPLE_PER_SQ_METER':'mean'})
pop_density_df['COUNTY'] = [joined_gdf[joined_gdf.COUNTYNS == ID]['COUNTY'].iloc[0] for ID in pop_density_df.index]

# Count the number of cities in each county
cities_per_county_df = joined_gdf.groupby(['COUNTYNS']).agg({'CITY':'count'})
cities_per_county_df['COUNTY'] = [joined_gdf[joined_gdf.COUNTYNS == ID]['COUNTY'].iloc[0] for ID in cities_per_county_df.index]

# Add the number of cities for each county to the joined_gdf
joined_gdf['COUNTY_NUM_CITIES'] = [cities_per_county_df[cities_per_county_df.index == i]['CITY'].iloc[0] for i in joined_gdf['COUNTYNS']]

print('\nMost Populous Counties by State\n')
for s in state:                                     # For each state
    print("\t\t",s)                                        # Print out the name of the state
    curr_df = joined_gdf[joined_gdf['STATE'] == s]  # Get all the cities from the current state
    # Group all those cities by county, adding up the population from 2010.
    # Then, sort by those population sums descending
    # Then, get the first five counties from that list (the biggest 5 counties)
    # Since county names are unique within a state, we can group by them here unlike earlier
    print(curr_df.groupby(['COUNTY']).agg({'POP_2010':'sum'}).sort_values(by=['POP_2010'], ascending = False).head(5))
    print() # Blank line for formatting
    
print('\nOverall Most Populous Counties\n')  # Print the 5 largest counties by population
print('COUNTY : POPULATION')
for i in range(5):
    print(pop_totals_df.sort_values(by=['POP_2010'], ascending=False).head(5).iloc[i]['COUNTY'],":",pop_totals_df.sort_values(by=['POP_2010'], ascending=False).head(5).iloc[i]['POP_2010'])

print('\nOverall Most Dense Counties\n')  # Print the 5 largest counties by population density
conv = 0.00000038610215855 # conversion factor for people per square meter to people per square mile
print('COUNTY : PEOPLE PER SQUARE MILE')
for i in range(5):
    print(pop_density_df.sort_values(by=['COUNTY_PEOPLE_PER_SQ_METER'], ascending=False).head(5).iloc[i]['COUNTY'],":", (pop_density_df.sort_values(by=['COUNTY_PEOPLE_PER_SQ_METER'], ascending=False).head(5).iloc[i]['COUNTY_PEOPLE_PER_SQ_METER']/conv))

# Get the population for each county and append it to the IA projected gdf
IA_projected_gdf['POPULATION'] = [pop_totals_df[pop_totals_df.index == ID].iloc[0]['POP_2010'] for ID in IA_projected_gdf['COUNTYNS']]
# Add a column for the log values of the populations
IA_projected_gdf['LOG_POPULATION'] = np.log(IA_projected_gdf['POPULATION'])
# Plot the counties with white representing 0, red representing the largest population, and the counties having black borders
IA_projected_gdf.plot(column = 'LOG_POPULATION', cmap = 'Reds', edgecolor='Black')


# ===== VISUALIZATION FOR ALL FIVE STATES ===== #

# =============================== NOTE ========================================
# There are two counties with no cities in them: 
#    Buffalo county and Oglala Lakota county, both in South Dakota
# Because of this, everything has to be done iteratively 
#    so that those counties can be replaced with zeros
# If I tried to do this using list comprehension, it would just return an error
#    because pop_totals_df doesn't have those counties in it
# =============================================================================

newArr = []                                     # Initialize empy list for the county populations
for ID in counties_projected_gdf['COUNTYNS']:   # For every county
    if ID in pop_totals_df.index:                   # If it has a population total...
        newArr.append(pop_totals_df[pop_totals_df.index == ID].iloc[0]['POP_2010'])   # Get the county's population
    else:                                           # Else...
        newArr.append(0)                                # Set its population to zero
counties_projected_gdf['POPULATION'] = newArr

# This loop is similar to the last. However, it is just avoiding the error that log(0) isn't legal
newArr2 = []
for n in counties_projected_gdf['POPULATION']:
    if n > 0:
        newArr2.append(math.log(n))     # Calculate the log of the population if greater than 0
    else:
        newArr2.append(0)               # Else, just set it to 0
counties_projected_gdf['LOG_POPULATION'] = newArr2

# Plot the counties with white representing 0, red representing the largest population, and the counties having black borders
counties_projected_gdf.plot(column = 'LOG_POPULATION', cmap = 'Reds', edgecolor='Black')
