# Data_engineering_project

***Project Goals/ Dashboard requirements and design choices:***

The project has the aim of producing a dashboard based on the data contained in a database file (flights_database.db) that allows the access to information of flights related to New York City airports during 2023. The target users of this dashboard are analysts that require information to monitor the activity in such airports for that time frame.

The dashboard allows the user to acess information related to flight delays and airplane type usage through specific sub dashboards. Additionally, the dashboard also allows access to information related to CO2 emissions and noise levels produced, considering current ESG (Environmental, Social and Governance) focus by companies on sustainability and ethical impact of their business. In this context, additional sources of data listed in the "Additional Sources" section of this REAME.me file, were collected, ingested and processed to produce the metrics on these sub dashboards.

The dashboard was designed to be user friendly with a minimalist but functional graphical design while also allowing for flexibility in the selection of the airports of departure and/or arrival (and corresponding routes) and time period to be analysed.

---

***Repository structure and how to run the dashboard:***

The Github repository for this project is accessible on https://github.com/CarlosT789/Data_engineering_project.

This repository ir organized as follows component wise:

* dashboard.py - File that contains the overall dashboard structure, including subdashboards and user interface. This file is used to load the dashboard through Streamlit.
* data/ - This is a directory that contains the flights_database.db SQLite file that used by the dashboard as source of information.
* Auxiliary modules:
  * delay.py - includes functions called upon by the code on dashboard.py to calculate and produce visualizations related to flight delays statistics on the sub dashboard Delay.
  * planes.py - includes functions called upon by the code on dashboard.py to calculate and produce visualizations related to aircraft use on the sub dashboard Planes.
  * co2.py - includes functions called upon by the code on dashboard.py to calculate and produce visualizations related to CO2 emissions on the sub dashboard CO2.
  * noise.py - includes functions called upon by the code on dashboard.py to calculate and produce visualizations related to noise statistics on the sub dashboard Noise.
* README.md - Includes general description of the project and summary of design choices and instructions of how to run/access and use the dashboard .

To run the dashboard locally the suggested steps are as follows:

1. Clone repository from https://github.com/CarlosT789/Data_engineering_project.git
2. Create virtual environment on your preferred IDE.
3. Install required dependencies by running on the terminal of the IDE pip install -r requirements.txt
4. To run the dashboard with the command streamlit run dashboard.py on the terminal.
5. The dashboard will load on your predefined web browser.

The dashboard can also be used through Streamlit Community Cloud on https://dataengineeringproject-whryhujxtkuywfzr9ye6xu.streamlit.app/.

---

***How to Use the Dashboard:***

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

The noise levels in decibels are based on effective perceived noise level (EPNdB) of various aircraft models types operating at Schiphol Airport during take-off and landing. An assumption was used that each flight (irrespective of the departure and arrival airport) produced the EPNDB value of the corresponding airplane model.

Notes for Users
The dashboard is designed for interactive use, so different filters can strongly change the displayed results.
Some pages are based on direct data values, while others use estimates or simplified assumptions.
If a selected route or filter combination has no matching data, the dashboard will show a message indicating that no results are available.

---

***Additional Sources:***

1. ICAO Carbon Emissions Calculator Methodology - Methodology for estimating aircraft CO₂ emissions based on distance, aircraft type and load assumptions (https://icec.icao.int/Documents/Methodology%20ICAO%20Carbon%20Emissions%20Calculator_v13_Final.pdf)
2. IATA CORSIA Handbook - Overview of aviation carbon accounting principles and emission estimation frameworks. (https://www.iata.org/contentassets/fb745460050c48089597a3ef1b9fe7a8/corsia-handbook.pdf)
3. IATA Recommended Practice 1726 – Passenger CO₂ Methodology Guidance for estimating CO₂ emissions per passenger using load factors and flight distance.
   Link: https://www.iata.org/contentassets/139d686fa8f34c4ba7a41f7ba3e026e7/iata-rp-1726_passenger-co2.pdf
4. Simons, D.G., et al (2026). Contribution of aircraft types to noise levels across the NOMOS network of Amsterdam Airport Schiphol. Journal of AIr Transport Management, 131, 102910. https://doi.org/10.1016/j.jairtraman.2025.102910.

---
