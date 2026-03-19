# Data_engineering_project



Carlos Tam - Teste number 1



Project Goals/ Dashboard requirements and design choices: 



----------------------------------------------------------------------------

----------------------------------------------------------------------------
How to Use the Dashboard:
This dashboard gives an interactive overview of flight operations, delays, aircraft usage, estimated CO2 emissions and airport noise. It is designed for users who want to explore the dataset through filters and visual summaries.
General Navigation: The dashboard is divided into two main parts:
- a filter panel on the left
- the main dashboard area on the right

At the top of the main area, the dashboard shows a general information section and a map. Below that, users can switch between four analytical pages: Delay, Planes, CO2 and Noise. The dashboard opens directly on the Delay page.
How to use filters:
The dashboard can be filtered by:
- Departure and Arrival airport
- Timeframe (where also single days can be selected as a timeframe)

The Departure filter contains airports that appear as origins in the dataset and the Arrival filter contains airports that appear in the dataset as destinations. After choosing filters, users must click Submit to update the dashboard (to improve performance).
This means the dashboard does not update immediately while selecting options. The Clear button resets all filters to the default state and returns the dashboard to its initial overview.
If no specific route is selected, the dashboard shows aggregated results across all available flights in the selected timeframe. When a timeframe and/or Arrival/Destination is selected all Sections (Delay, Planes, CO2, Noise) display information on these set filters. 
General Information Section
The general information section gives a quick summary of the currently selected data. It includes:
- Total flights
- Average duration
- Average departure delay
- Average arrival delay
- Total distance flown
- Equivalent around-Earth trips based on the total distance flown

Map
The map displays airport locations and selected flight routes.
- In the initial state, the map shows all available airports, focused on North America
- If a departure and arrival airport are selected, the map shows the selected route as a curved line
- The user can also open a larger map view for easier inspection

Delay
The Delay page focuses on operational performance and delay behaviour.
It includes:
- Delay percentage
- Average delay time
- Average delay time for delayed flights only
- Delay percentage by origin airport
- Distribution of delay times
- Delay percentage by hour of departure
- Delay percentage by month
- Best destination airports by delay percentage
- Worst destination airports by delay percentage

Planes
The Planes page focuses on aircraft usage and fleet characteristics.
It includes:
- Average flight speed
- Top aircraft models by number of flights
- Top aircraft models by total distance flown
- Top manufacturers
- Top aircraft models by average speed
- Aircraft type distribution
- Aircraft body type distribution (e.g. narrow-body vs wide-body)

CO2
The CO2 page presents estimated environmental impact measures.
It includes:
- Total fuel usage
- Average fuel usage
- Total CO2 emissions
- Average CO2 emissions
- Average CO2 per passenger
- Estimated compensation per passenger
- Top airlines by total CO2 emissions
- Average CO2 emissions per flight by airline
- CO2 emissions by aircraft family
- CO2 emissions over time

The page also includes an assumptions and interpretation section, because the CO2 values are estimated from flight distance and aircraft assumptions rather than exact airline fuel data.
Noise
The Noise page focuses on estimated airport noise exposure of the three airports in New York.
It includes:
- Total cumulative noise
- Average noise per flight
- Average daily noise
- Ranking of NYC airports by noise
- Noise production by hour of day

Notes for Users
The dashboard is designed for interactive use, so different filters can strongly change the displayed results.
Some pages are based on direct data values, while others use estimates or simplified assumptions.
If a selected route or filter combination has no matching data, the dashboard will show a message indicating that no results are available.

----------------------------------------------------------------------------

----------------------------------------------------------------------------



How to run:



