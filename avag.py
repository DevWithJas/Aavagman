
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import streamlit as st

# Selenium and WebDriver imports for Firefox
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

# Import for Google Transit Feed Specification Realtime (GTFS-realtime) bindings
import gtfs_realtime_pb2

# Initialize headless Firefox WebDriver
import gtfs_realtime_pb2

# Initialize headless Firefox WebDriver
def init_headless_firefox_driver():
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--headless")
    # Additional Firefox options can be added as needed

    driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), options=firefox_options)
    return driver

# Other functions and Streamlit app code remain the same...

# Function to initialize headless Chrome WebDriver
def init_headless_chrome_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Automatically manage the correct version of ChromeDriver
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

# Function to fetch all bus IDs
def fetch_all_bus_ids(api_key):
    url = f"https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb?key={api_key}"
    response = requests.get(url)
    bus_ids = []

    if response.status_code == 200:
        data = gtfs_realtime_pb2.FeedMessage()
        data.ParseFromString(response.content)
        bus_ids = [entity.id for entity in data.entity]

    return bus_ids

# Function to fetch and display data for a particular bus ID
def fetch_and_display_data_for_id(api_key, selected_bus_id):
    url = f"https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb?key={api_key}"
    response = requests.get(url)

    if response.status_code == 200 and selected_bus_id:
        data = gtfs_realtime_pb2.FeedMessage()
        data.ParseFromString(response.content)

        table_data = []

        for entity in data.entity:
            if entity.id == selected_bus_id:
                bus_info = {
                    "Entity ID": entity.id,
                    "Trip ID": entity.vehicle.trip.trip_id,
                    "Start Time": entity.vehicle.trip.start_time,
                    "Start Date": entity.vehicle.trip.start_date,
                    "Schedule Relationship": entity.vehicle.trip.schedule_relationship,
                    "Route ID": entity.vehicle.trip.route_id,
                    "Latitude": entity.vehicle.position.latitude,
                    "Longitude": entity.vehicle.position.longitude,
                    "Speed": entity.vehicle.position.speed,
                    "Timestamp": entity.vehicle.timestamp,
                    "Vehicle ID": entity.vehicle.vehicle.id,
                    "Vehicle Label": entity.vehicle.vehicle.label
                }
                table_data.append(bus_info)

        if table_data:
            st.table(table_data)  # This will display the data in a table
        else:
            st.warning(f"No data found for bus ID: {selected_bus_id}")
    else:
        st.error("Failed to fetch data. Please check the API key, URL, or selected bus ID.")

# Function to get driving route data
def get_driving_route(api_key, start_location, end_location):
    url = f"http://dev.virtualearth.net/REST/V1/Routes/Driving?wp.0={start_location}&wp.1={end_location}&avoid=minimizeTolls&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to display relevant route information
def display_route_info(route_data):
    if 'resourceSets' in route_data and route_data['resourceSets']:
        route_set = route_data['resourceSets'][0]
        if 'resources' in route_set and route_set['resources']:
            route = route_set['resources'][0]
            st.write(f"Total Duration: {route['travelDuration'] // 60} minutes")
            st.write(f"Total Distance: {route['travelDistance']} kilometers")
            st.write("Steps:")
            for index, step in enumerate(route['routeLegs'][0]['itineraryItems']):
                st.write(f"{index + 1}. {step['instruction']['text']}")
        else:
            st.write("No route information found.")
    else:
        st.write("No route information found.")

# Function to create and display an interactive map URL with the highlighted route
def create_interactive_route_link(start_location, end_location):
    start_location_encoded = start_location.replace(' ', '%20')
    end_location_encoded = end_location.replace(' ', '%20')
    route_url = f"https://bing.com/maps/default.aspx?rtp=adr.{start_location_encoded}~adr.{end_location_encoded}"
    st.markdown(f"Interactive Route Map: [View Route]({route_url})")


def fetch_and_display_bus_stops(bus_number):
    request_url = f"https://www.dtcbusroutes.in/bus/search/?{urlencode({'bus': bus_number})}"
    try:
        response = requests.get(request_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            stops = soup.find_all('p', {'itemtype': 'http://schema.org/BusStop'})
            stops_list = [stop.get_text(strip=True) for stop in stops]
            return stops_list
        else:
            st.error(f"Failed to fetch bus stops: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")

def format_directions(stops_list):
    formatted_stops = [stop.split('.', 1)[-1].strip() for stop in stops_list]
    return formatted_stops

# Function to enter directions on Bing Maps
def enter_directions(driver, *destinations):
    try:
        # Open Bing Maps in a new tab using JavaScript
        driver.execute_script("window.open('https://www.bing.com/maps');")
        
        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[1])
        
        # Click on the directions button using XPath
        directions_button_xpath = '//*[@title="Directions"]'
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, directions_button_xpath))).click()

        # Wait for the 'From' input field to be visible
        from_input_xpath = '//*[@title="From"]'
        from_input = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, from_input_xpath)))
        from_input.send_keys(destinations[0])

        # Wait for the 'To' input field to be visible
        to_input_xpath = '//*[@title="To"]'
        to_input = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, to_input_xpath)))
        to_input.send_keys(destinations[1])
        to_input.send_keys(Keys.ENTER)  # Press ENTER to confirm the first destination

        # Add additional destinations if any
        add_destination_xpath = '//*[@id="directionsPanelRoot"]/div/div[3]/div[3]/a'
        for index, destination in enumerate(destinations[2:], start=2):
            WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, add_destination_xpath))).click()
            new_destination_input_xpath = f'((//input[@title="To"])[{index}])'
            new_destination_input = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, new_destination_input_xpath)))
            new_destination_input.send_keys(destination)
            new_destination_input.send_keys(Keys.ENTER)  # Press ENTER to confirm each additional destination

        # Click the 'Go' button to initiate the search
        go_button_xpath = '//*[@data-tag="dirBtnGo"]'
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, go_button_xpath))).click()

    except TimeoutException as e:
        st.error("Timeout occurred while trying to find an element. Check if the XPath is correct and the page has loaded.")
        print(e)
    except Exception as e:
        st.error("An error occurred in the Selenium function.")
        print(e)

        st.info("The browser will remain open for 2 minutes. Please close it manually when done.")
    try:
        for remaining in range(120, 0, -1):
            st.info(f"Browser will close automatically in {remaining} seconds...")
            time.sleep(1)
    except:
        pass  # Ignore any exceptions, such as the user closing the window early

    # Close the browser
    driver.quit()

# Streamlit app code
st.title("Aavagaman (आवागमन)")

# Insert GIF
gif_url = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/46271a16479553.562ac7123e5fa.gif"
st.image(gif_url)

# Section 1: Real-time Bus Information
st.header("Real-time Bus Information")

api_key_delhi_transit = "Giy8xwSFhYI3wZyvzJfb34dgsXJ6DKXQ"  # Replace with your actual API key
bus_ids = fetch_all_bus_ids(api_key_delhi_transit)
selected_bus_id = st.sidebar.selectbox("Select Bus ID", bus_ids)

if st.button("Fetch and Display Data"):
    fetch_and_display_data_for_id(api_key_delhi_transit, selected_bus_id)

# Section 2: Driving Route Information
st.header("Driving Route Information for Cars and Two wheelers")

api_key_bing_maps = "AgqADJTOx82qOKC_psLFZfW2sD7FnadzMv9yR1W4tP8WiR_2b0VBvbuSVxzF5NEZ" # Replace with your actual API key
start_location = st.text_input("Enter Start Location")
end_location = st.text_input("Enter End Location")

if st.button("Find Route") and api_key_bing_maps and start_location and end_location:
    route_data = get_driving_route(api_key_bing_maps, start_location, end_location)
    if route_data:
        display_route_info(route_data)
        create_interactive_route_link(start_location, end_location)
    else:
        st.write("Route data not found.")

# New Section: User-Input for Bus Route on Bing Maps
st.header("User-Input for Bus Route on Bing Maps")

user_start_location = st.text_input("Enter the Start Location for Bus Route (e.g., Rohini)", "")
user_end_location = st.text_input("Enter the End Location for Bus Route (e.g., Pitampura)", "")

if st.button("Show Bus Route on Bing Maps"):
    if user_start_location and user_end_location:
        # Encoding the locations for URL
        start_location_encoded = user_start_location.replace(' ', '%20')
        end_location_encoded = user_end_location.replace(' ', '%20')
        bus_route_url = f"https://bing.com/maps/default.aspx?rtp=adr.{start_location_encoded}~adr.{end_location_encoded}&mode=T"
        st.markdown(f"Bus Route Map: [View Route on Bing Maps]({bus_route_url})")
    else:
        st.warning("Please enter both start and end locations.")

# Function to create a route using Bing Maps API with multiple waypoints
def create_route_with_bus_stops(api_key, bus_stops):
    base_url = "http://dev.virtualearth.net/REST/v1/Routes/Driving?"

    # Constructing the route using 'wayPoint' for the start and end, and 'viaWaypoint' for the others
    waypoints = f'wayPoint.0={bus_stops[0]["Latitude"]},{bus_stops[0]["Longitude"]}'
    for index, stop in enumerate(bus_stops[1:], start=1):  # All stops as via waypoints
        waypoints += f'&viaWaypoint.{index}={stop["Latitude"]},{stop["Longitude"]}'

    final_url = f"{base_url}{waypoints}&optimize=timeWithTraffic&key={api_key}"

    response = requests.get(final_url)
    if response.status_code == 200:
        return response.json()  # This is the JSON response with the route details
    else:
        return None

def display_route_on_map(bus_stops):
    # Constructing the URL for Bing Maps with the bus stops coordinates
    points = '~'.join([f'point.{stop["Latitude"]}_{stop["Longitude"]}' 
                       for stop in bus_stops if stop["Latitude"] != 'Not found' and stop["Longitude"] != 'Not found'])

    # The level (lvl) and style can be adjusted as needed
    map_url = f"https://www.bing.com/maps?lvl=11&style=r&sp={points}"

    # Displaying the map URL in Streamlit
    st.markdown(f"Route Map: [View Route on Bing Maps]({map_url})")

# Bus Stops Information Section
st.header("Bus Stops Information with Selenium")
bus_number = st.text_input("Enter the Bus Number to fetch stops", "")
# Usage in your Streamlit app
if st.button("Fetch Stops and Process with Selenium"):
    if bus_number:
        stops_list = fetch_and_display_bus_stops(bus_number)
        if stops_list:
            # Display bus stops in the Streamlit app
            st.subheader("Bus Stops:")
            for stop in stops_list:
                st.text(stop)

            formatted_stops = format_directions(stops_list)

            # Initialize the headless Firefox WebDriver
            driver = init_headless_firefox_driver()

            try:
                # Use the enter_directions function with formatted bus stops
                enter_directions(driver, *formatted_stops)
                st.success("Processed data with Selenium. Please close the browser manually when done.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                driver.quit()
        else:
            st.error("No stops found for the given bus number.")
    else:
        st.warning("Please enter a bus number.")
