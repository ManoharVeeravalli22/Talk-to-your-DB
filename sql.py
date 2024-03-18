import streamlit as st
import os
import google.generativeai as genai  # Assuming you're using GenerativeAI
import pymongo
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import pyarrow.parquet as pq

username = "manu"  # Replace with your actual username
password = "MaxChimp@1"  # Replace with your actual password
escaped_username = urllib.parse.quote_plus(username)
escaped_password = urllib.parse.quote_plus(password)


uri = "mongodb+srv://" + escaped_username + ":" + escaped_password + "@cluster0.hxcbtef.mongodb.net/?retryWrites=true&w=majority"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

genai.configure(api_key="AIzaSyCXt3a2LlnxGUIrtExqy-bTn76lxG9vhlw")  # Assuming GenerativeAI key


def data_sort(df):
    df = df[df[' SERIES'] == " EQ"]
    df[' DATE1'] = pd.to_datetime(df[' DATE1'])
    # Extract month and year from 'Date' column
    df['Month'] = df[' DATE1'].dt.month
    df['Day'] = df[' DATE1'].dt.day
    df = df.sort_values(['Month','Day'])
    return(df)

def get_gemini_response(question, prompt):
  """
  Fetches response from GenerativeAI model.

  Args:
      question: User's question about the NoSQL data.
      prompt: Informative prompt describing the database schema.

  Returns:
      str: Text response from GenerativeAI.
  """
  model = genai.GenerativeModel('gemini-pro')
  response = model.generate_content([prompt[0], question])
  return response.text


def read_sql_query(query, collection_name="todo"):
  """
  Executes the NoSQL query and returns a DataFrame.

  Args:
      query: NoSQL query string (dictionary for filtering).
      collection_name: Name of the collection in the database (default: "todo").

  Returns:
      pd.DataFrame: DataFrame containing fetched data.
  """
  try:
    db = client[collection_name.split('.')[0]]
    collection = db[collection_name]
    fetched_data = list(collection.find(query))
    df = pd.DataFrame(fetched_data)
    return df
  except pymongo.errors.PyMongoError as e:
    print(f"Error fetching data: {e}")
    return None  # Handle error by returning None


prompt = [
    """
     You are an expert in converting English questions to No-SQL query!
    This database includes information about stocks, with columns like 'SERIES' (stock symbol), 'DATE-1' (date), 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRICE', 'DELIV_PER' (delivery percentage), and more.

    Here are some examples to get you started:

    * **Find all to-do items:**
    This would translate to a query like `{}` (finding all documents in the 'to-do' collection).

    * **Find to-do items with high delivery percentage:**
    You could use a query like `{" DELIV_PER": {"$gt": 50}}` to find entries where 'DELIV_PER' is greater than 50% remember the columns are database are having single space in the beginning of thier name like " DELIV_PER" except "SYMBOL" every column name has space in beginnig of them.
    don't include "$" in the column name
    if stock name is given please in the database with stock symbol represent in NSE or BSE reterive only stock symbol  for searching any stock data use SYMBOL column and SYMBOL doesn't have any space in begging of them like rest of the columns so use only SYMBOL without any spaces
    Don't space in front of SYMBOL column like you do with other columns this column doesn't have space in front of thier name don't use $match conditons for searching for the symbol
    your making too many errors please go through the examples for answering
     * * *for fetching the stock data**
     you could use a query like  "{ "SYMBOL": "RELIANCE"," SERIES" : " EQ"}"

    * **Calculate the average closing price for a specific date:**
    We can use aggregation for this:
    ```
      { "$match": { " DATE-1": "2023-10-20" } },
      { "$group": { _id: null, average_close_price: { "$avg": " CLOSE_PRICE" } } }
     also the sql code should not have ``` in beginning or end and no-sql word in output
    """
]


## Streamlit App

st.set_page_config(page_title="I can Retrieve Any No-SQL Query")
st.header("Gemini App To Retrieve No-SQL Data")

question = st.text_input("Input: ", key="input")

submit = st.button("Ask the question")


# if submit is clicked
if submit:
  response = get_gemini_response(question, prompt)
  # Print for debugging purposes (remove in production)
  print(response)

  # Assuming the response is a NoSQL query (dictionary)
  try:
    df = read_sql_query(eval(response))  # Assuming response is a valid dictionary string
    df['Action'] = df[' TTL_TRD_QNTY']/df[' NO_OF_TRADES']
    df[' DELIV_PER'] = df[' DELIV_PER'].apply(lambda x: float(x) if x != ' -' else 0.0)
    df['Action%'] = (df['Action']/df['Action'].mean())*100
    df = data_sort(df)
    df = df.sort_values(by= " DATE1",ascending=True)
    #st.subheader("The Response is:")
    #st.dataframe(df)
    left_column, right_column = st.columns(2)
    with left_column:
        st.text(f"AVERAGE ACTION : {df['Action'].mean()}")
        st.text(f"AVERAGE DELIVERY % : {df[' DELIV_PER'].mean()}")
        st.write(df)
    
    
    
    if df is not None:
        # Set 'Date' column as the DataFrame index
        df.set_index(' DATE1', inplace=True)

        # Create a figure with subplots for the line and bar charts
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add the line chart for close prices
        fig.add_trace(
            go.Scatter(x=df.index, y=df[' CLOSE_PRICE'], name='Close Price'),
            secondary_y=False
        )

        # Add the bar chart for Action%
        fig.add_trace(
            go.Bar(x=df.index, y=df['Action%'], name='Action%'),
            secondary_y=True
        )

        # Add the bar chart for Delivery%
        fig.add_trace(
            go.Bar(x=df.index, y=df[' DELIV_PER'], name='Delivery%'),
            secondary_y=True
        )

        # Set the axis labels and titles
        fig.update_layout(
            title='Stock Analysis',
            xaxis_title='Date',
            yaxis=dict(title='Close Price'),
            yaxis2=dict(title='Percentage'),
        )
        
        with right_column:
            st.plotly_chart(fig)
        
  except Exception as e:
    # Handle the error here, e.g., print an error message
    print(f"An error occurred: {e}")
    st.error("An error occurred while processing your request.")
