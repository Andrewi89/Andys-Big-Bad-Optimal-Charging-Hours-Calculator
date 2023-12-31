# streamlit_app.py

import streamlit as st
import requests
import pandas as pd
import random
from datetime import datetime, timedelta, timezone


# OCTOPUS_API_URL = "https://api.octopus.energy/agile/v1/products/{product_id}/tariffs/{tariff_id}/standard-unit-rates/"
OCTOPUS_API_URL = "https://api.octopus.energy/v1/products/{product_id}/electricity-tariffs/{tariff_id}/standard-unit-rates/"
API_KEY = "YOUR_OCTOPUS_AGILE_API_KEY"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def fetch_prices(product_id="AGILE-FLEX-22-11-25", tariff_id="E-1R-AGILE-FLEX-22-11-25-B"):
    response = requests.get(OCTOPUS_API_URL.format(
        product_id=product_id, tariff_id=tariff_id), headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(data)
        return pd.DataFrame(response.json()["results"])
    else:
        return None


def mock_data():
    base_date_str = '2023-09-01T00:00:00'
    base_date = datetime.strptime(
        base_date_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    mock_prices = []

    for i in range(48):  # 48 half-hour periods in a day
        valid_from = base_date + timedelta(minutes=30*i)
        valid_to = valid_from + timedelta(minutes=30)

        # Generating mock prices.
        # Main price range is between 0.05 to 0.40.
        price = round(random.uniform(0.50, 50.00), 2)

        # Occasionally insert some negative prices or peaks
        if i % 10 == 0:  # Every 10th interval, we'll do something different
            if random.choice([True, False]):  # 50% chance to either spike or dip
                price = round(random.uniform(20.00, 30.00), 2)  # Spike
            else:
                price = round(random.uniform(-0.50, 0), 2)  # Dip into negative

        mock_prices.append({
            'value_inc_vat': price,
            'valid_from': valid_from.isoformat(),
            'valid_to': valid_to.isoformat()
        })

    return pd.DataFrame(mock_prices)


def select_cheapest_hours(prices_df, hours_required):
    half_hours_required = int(hours_required * 2)
    prices_df = prices_df.nsmallest(half_hours_required, 'value_inc_vat')
    return prices_df


def calculate_total_cost(prices_df, charge_kWh):
    # since each slot is half-hour, multiply by 0.5
    total_cost = (prices_df['value_inc_vat'] / 100 * charge_kWh * 0.5).sum()
    return total_cost


def display_with_highlight(df, cheapest_periods):
    # Highlight the selected periods
    def highlight_rows(row):
        if row['valid_from'] in cheapest_periods['valid_from'].values:
            return ['background-color: pink'] * len(row)
        return [''] * len(row)
    return df.style.apply(highlight_rows, axis=1)


st.title("Andy's Beta Calculator")
st.header("For Optimal Charging Hours")
st.subheader("On Octopus Agile")

battery_kWh = st.number_input('Enter remaining storage/battery/tank kWh', value=11.0)
charger_kW = st.number_input('Enter size of charger/diverter in kW', value=3.68)
solar_kWh = st.number_input('Enter daily solar generation in kWh', value=0.0)

col1, col2, col3 = st.columns(3)

remaining_kWh = battery_kWh - solar_kWh
col1.metric("Remaining Grid kWh:", f"{remaining_kWh:.2f} kWh",
            delta=None, delta_color="normal", help=None, label_visibility="visible")

charge_time = remaining_kWh / charger_kW
col2.metric("Estimated charging time:", f"{charge_time:.2f} hours",
            delta=None, delta_color="normal", help=None, label_visibility="visible")
# st.write(f"Estimated charging time: {charge_time:.2f} hours")

use_mock_data = st.checkbox('Use Mock Data')

if st.button('Calculate Optimal Charging Time'):
    if use_mock_data:
        prices_df = mock_data()
    else:
        prices_df = fetch_prices()

    if prices_df is not None:
        cheapest_periods = select_cheapest_hours(prices_df, charge_time)

        total_cost = calculate_total_cost(cheapest_periods, remaining_kWh)
        col3.metric("Estimated charging cost:", f"£{total_cost:.2f}",
                    delta=None, delta_color="normal", help=None, label_visibility="visible")

        # Display all time slots and highlight the optimal charging times
        st.dataframe(display_with_highlight(
            prices_df, cheapest_periods), use_container_width=True)

        # st.write("Optimal times to charge:")
        # st.write(cheapest_periods)
    else:
        st.write("Failed to retrieve data from Octopus Agile API.")
