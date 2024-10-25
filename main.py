import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Steam Games DB",)

# Establishing a connection with the database
conn = st.connection('mysql', type='sql')

def query_A(start_year, end_year):
    query = conn.query(f"""
    SELECT 
        dg.genre_name,
        dd.year,
        COUNT(fg.game_id) AS sub_total
    FROM dim_date dd
        JOIN fact_games fg ON fg.date_id = dd.date_id
        JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    WHERE dd.year BETWEEN '{start_year}' AND '{end_year}'
    GROUP BY dg.genre_name, dd.year

    UNION 

    SELECT 
        dg.genre_name,
        NULL AS year,
    COUNT(fg.game_id) AS sub_total
    FROM dim_date dd
        JOIN fact_games fg ON fg.date_id = dd.date_id
        JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    WHERE dd.year BETWEEN '{start_year}' AND '{end_year}'
    GROUP BY dg.genre_name

    UNION 

    SELECT 
        'Total' AS genre_name,
        NULL AS year,
        COUNT(fg.game_id) AS sub_total
    FROM dim_date dd
        JOIN fact_games fg ON fg.date_id = dd.date_id
    WHERE dd.year BETWEEN '{start_year}' AND '{end_year}'
    ORDER BY 
        genre_name,year;""")
    return pd.DataFrame(query)

def query_B(start_year, end_year, genre):
    query = conn.query(f"""
    SELECT 
        g.genre_name,
        p.platform_name,
        COUNT(fg.game_id) AS platform_distribution
    FROM fact_games fg
        INNER JOIN dim_date dd ON fg.date_id = dd.date_id
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre g ON ggb.genre_id = g.genre_id
        INNER JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
        INNER JOIN dim_platform p ON gpb.platform_id = p.platform_id
    WHERE 
        dd.year BETWEEN {start_year} AND {end_year} AND
        g.genre_name = '{genre}'
    GROUP BY g.genre_name, p.platform_name
    ORDER BY g.genre_name, platform_distribution DESC;""")
    return pd.DataFrame(query)

def query_C():
    query = conn.query("""
    SELECT
        dg.genre_name AS Genre,
        ROUND(AVG(fg.price), 2) AS Average_Price
    FROM
        fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    GROUP BY
        dg.genre_name
    ORDER BY
        dg.genre_name;
    """)
    return pd.DataFrame(query)

def query_D():
    query = conn.query("""
            SELECT
            dp.platform_name AS Platform,
            dg.genre_name AS Genre,
            dd.year AS Year,
            SUM(fg.total_positive_reviews + fg.total_negative_reviews) AS Total_Reviews
        FROM
            fact_games fg
            INNER JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
            INNER JOIN dim_platform dp ON gpb.platform_id = dp.platform_id
            INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
            INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
            INNER JOIN dim_date dd ON fg.date_id = dd.date_id
        GROUP BY
            dp.platform_name,
            dg.genre_name,
            dd.year
        ORDER BY
            dp.platform_name, dg.genre_name, dd.year;""")
    return pd.DataFrame(query)

def query_D1():
    query = conn.query("""
    SELECT
        dg.genre_name AS Genre,
        CONCAT(FORMAT(SUM(fg.total_positive_reviews), 0), ':', FORMAT(SUM(fg.total_negative_reviews), 0)) AS Positive_Negative_Ratio
    FROM
        fact_games fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
    GROUP BY
        dg.genre_name
    ORDER BY
        dg.genre_name;""")
    return pd.DataFrame(query)

def query_D2(percentage):
    query = conn.query(f"""
    SELECT
        fg.game_id,
        dg.genre_name AS Genre,
        dp.platform_name AS Platform,
        dd.year AS Year,
        fg.total_positive_reviews,
        fg.total_negative_reviews,
        ROUND((fg.total_positive_reviews * 100.0) / NULLIF((fg.total_positive_reviews + fg.total_negative_reviews), 0), 2) AS Positive_Review_Percentage
    FROM
    (
        SELECT
            game_id,
            total_positive_reviews,
            total_negative_reviews
        FROM
            fact_games
        WHERE
            (total_positive_reviews * 100.0) / NULLIF((total_positive_reviews + total_negative_reviews), 0) > {percentage}
    ) fg
        INNER JOIN game_genre_bridge ggb ON fg.game_id = ggb.game_id
        INNER JOIN dim_genre dg ON ggb.genre_id = dg.genre_id
        INNER JOIN game_platform_bridge gpb ON fg.game_id = gpb.game_id
        INNER JOIN dim_platform dp ON gpb.platform_id = dp.platform_id
        INNER JOIN dim_date dd ON fg.game_id = dd.date_id
    ORDER BY
        dg.genre_name, dp.platform_name, dd.year;""")
    return pd.DataFrame(query)

def generate_report_A(start_year, end_year):
    data = query_A(start_year, end_year) # fetch data from query

    # pivot table to better visualize the results
    pivot_data = data.pivot_table(
        index='genre_name',
        columns='year',
        values='sub_total',
        fill_value=0
    )

    # rename column and remove decimals from Year
    pivot_data.columns = [int(col) if isinstance(col, float) else col for col in pivot_data.columns]
    pivot_data['Total'] = pivot_data.sum(axis=1)

    # rename axis
    pivot_data = pivot_data.rename_axis('Genre').reset_index()
    return pivot_data # return streamlit dataframe

def generate_report_B(start_year, end_year, genre):
    data = query_B(start_year, end_year, genre) #fetch data from query

    data = data.rename(columns={
        'genre_name': 'Genre',
        'platform_name': 'Platform',
        'platform_distribution': 'Platform Distribution',
    })

    return data # return streamlit dataframe

def generate_report_C():
    data = query_C() # fetch data from query

    # Generate altair bar Chart
    chart = alt.Chart(data).mark_bar().encode(
        x=alt.X('Genre', axis=alt.Axis(title='Game Genre')),
        y=alt.Y('Average_Price', axis=alt.Axis(title='Average Price ($)'),
                scale=alt.Scale(domain=[0, data['Average_Price'].max()])),
        size=alt.Size('Average_Price', title='Size Based on Average Price ($)')
    ).properties(width=1000).interactive()

    return chart #return altair bar chart

def generate_report_D():
    test_df = query_D() # fetch data from query

    custom_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', '#637939', '#8ca252', '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39',
        '#e7ba52', '#e7cb94', '#843c39', '#ad494a', '#d6616b', '#e7969c', '#7b4173', '#a55194', '#ce6dbd', '#de9ed6',
        '#6b486b', '#a05d56', '#d0743c', '#ff8c00', '#98abc5', '#8a89a6', '#7b6888', '#6b486b', '#a05d56', '#d0743c',
        '#ff8c00', '#e377c2', '#bcbd22', '#17becf', '#bcbd22', '#7f7f7f', '#7b6888', '#8ca252', '#6b6ecf'
    ]

    # Generate altair line Chart
    chart = alt.Chart(test_df).mark_line().encode(
        x=alt.X('Year:O', axis=alt.Axis(title='Year')),
        y=alt.Y('Total_Reviews:Q', axis=alt.Axis(title='Total Reviews')),
        color=alt.Color('Genre:N', scale=alt.Scale(range=custom_colors)),
        facet='Platform:N'
    ).properties(width=1000).interactive()

    return chart # return altair line chart

def generate_report_D1():
    df = query_D1() # fetch data from query

    # Splice ratios to get positive and negative reviews
    df['Positive_Reviews'] = df['Positive_Negative_Ratio'].apply(lambda x: int(x.split(':')[0].replace(',', '')))
    df['Negative_Reviews'] = df['Positive_Negative_Ratio'].apply(lambda x: int(x.split(':')[1].replace(',', '')))

    # Generate altair bar chart
    chart = alt.Chart(df).transform_fold(
        ['Positive_Reviews', 'Negative_Reviews'],  # Columns to fold
        as_=['Review_Type', 'Count']  # New column names
    ).mark_bar().encode(
        x=alt.X('Genre:N', title='Genre'),
        y=alt.Y('Count:Q', title='Number of Reviews'),
        color='Review_Type:N',
        xOffset='Review_Type:N'
    ).properties(width=800).interactive()

    return chart # returns altair bar chart

def generate_report_D2(percentage):
    df = query_D2(percentage) # fetch data from query

    # Generate altair line chart
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X('Year:O', title='Year'),
        y=alt.Y('Positive_Review_Percentage:Q', title='Positive Review %'),
        color='Genre:N',
        facet='Platform:N'
    ).properties(width=500).interactive()

    return chart # return altair line chart

def main():
    st.title("Steam Games DB")

    with st.sidebar:
        st.title("Navigation bar")

        option = st.selectbox(
            "Select report to generate",
            ("Report A", "Report B", "Report C", "Report D", "Report D1", "Report D2"),
            index=None,
            placeholder="Select report...",
        )



    # Initialize session states
    if 'start_yearA' not in st.session_state:
        st.session_state.start_yearA = 1997
    if 'end_yearA' not in st.session_state:
        st.session_state.end_yearA = 2025
    if 'start_yearB' not in st.session_state:
        st.session_state.start_yearB = 1997
    if 'end_yearB' not in st.session_state:
        st.session_state.end_yearB = 2025
    if 'genreB' not in st.session_state:
        st.session_state.genreB = 'action'
    if 'percentageD2' not in st.session_state:
        st.session_state.percentageD2 = 100

    if option == "Report A":
        st.write("No. of Games Released within a Range of Two Different Years by Genre")

        with st.form(key='year_selection_formA'):
            start_year, end_year = st.select_slider(
                "Select a range between two different years",
                options=list(range(1997, 2026)),
                value=(st.session_state.start_yearA, st.session_state.end_yearA)
            )
            submit = st.form_submit_button(label="Run Query")

            if submit:
                st.session_state.start_yearA = start_year
                st.session_state.end_yearA = end_year

                # Form validation
                if start_year == end_year:
                    st.toast("Warning: Start year cannot be equal to end year.")
                elif end_year < start_year:
                    st.toast("Warning: End year cannot be less than start year.")
                else:
                    st.toast("Generating Report...")
                    chart = generate_report_A(start_year, end_year)
                    st.dataframe(chart)

    if option == "Report B":
        st.write("Platform Distribution of a Specific Genre Released Within a Range of Two Different Years")

        with st.form(key='year_selection_formB'):
            start_year, end_year = st.select_slider(
                "Select a range between two different years",
                options=list(range(1997, 2026)),
                value=(st.session_state.start_yearB, st.session_state.end_yearB)
            )

            option = st.selectbox(
                "Select Genre",
                options = ["360 video", "accounting", "action",
                           "adventure", "animation & modeling",
                           "audio production", "casual", "design & illustration",
                           "documentary", "early access", "education", "episodic",
                           "free to play", "game development", "gore", "indie",
                           "massively multiplayer", "movie", "nudity", "photo editing",
                           "racing", "rpg", "sexual content", "short", "simulation",
                           "software training", "sports", "strategy", "tutorial", "utilities",
                           "video production", "violent", "web publishing"]
,
                index=None,
                placeholder="Select Genre...",
            )

            submit = st.form_submit_button(label="Run Query")

            if submit:
                st.session_state.start_yearB = start_year
                st.session_state.end_yearB = end_year
                st.session_state.genreB = option

                # Form validation
                if start_year == end_year:
                    st.toast("Warning: Start year cannot be equal to end year.")
                elif end_year < start_year:
                    st.toast("Warning: End year cannot be less than start year.")
                else:
                    st.toast("Generating Report...")
                    chart = generate_report_B(start_year, end_year, option)
                    st.dataframe(chart)

    if option == "Report C":
        st.write("Average Price of Games Per Genre")
        chartC = generate_report_C()
        st.altair_chart(chartC)

    if option == "Report D":
        st.write("Total Reviews of Genres by Year and Platform")
        chartD = generate_report_D()
        st.altair_chart(chartD)

    if option == "Report D1":
        st.write("Comparison between the Positive and Negative Reviews of Games by Genre")
        chartD1 = generate_report_D1()
        st.altair_chart(chartD1)

    if option == "Report D2":
        st.write("Games with X% positive reviews throughout the Years")

        with st.form(key='year_selection_formD2'):
            percentage = st.select_slider(
                "Select a percentage of positive reviews",
                options=list(range(1, 101)),
                value=(st.session_state.percentageD2)
            )

            submit = st.form_submit_button(label="Run Query")

            if submit:
                chartD2 = generate_report_D2(percentage)
                st.altair_chart(chartD2)

if __name__ == "__main__":
  main()