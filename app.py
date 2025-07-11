from logging import error
from dash import Dash, dcc, html, Input, Output, callback, Input, Output, State, ctx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats
import pandas as pd
import base64
import io

import layout
import utils

app = Dash(__name__)
app.layout = layout.layout  # Assign the layout from layout.py

colors = {
    'background': '#FFFFFF',
    'text': '#2E2D29'
}



###### dcc.Store Debugger #######

@app.callback(
        Output('output-data', 'children'),  # Output to display the data
        Output('output-params', 'children'),  # Output to store the data
        Output('output-roc', 'children'),
        Input('stored-data', 'data'),  # Input from the Store component
        Input('fit-params', 'data'), #view params
        Input('roc_curves', 'data')
    )
def display_stored_data(stored_data, fitted_params, roc_curves):
        if stored_data and fitted_params and roc_curves:
            # Convert the data to a readable format (e.g., string)
            data_string_data = str(stored_data)
            data_string_params = str(fitted_params)
            data_string_roc = str(roc_curves)
            # Return the data string
            return data_string_data, data_string_params, data_string_roc
        else:
            return "No data stored yet.", "No parameters stored yet.", "No ROC data stored yet."

##################################




# Store data ready to graph
@callback(
    Output('stored-data', 'data', allow_duplicate=True),  # Output to store the data
    Output('fit-params', 'data', allow_duplicate=True),  # Output to store the data
    Output('roc_curves', 'data', allow_duplicate=True),
    Output('error-message', 'children'),  # Output to display the error
    Input('upload-data', 'contents'),  # Input from the upload component
    State('upload-data', 'filename'),  # State to get the filename
    State('stored-data', 'data'), # State to get existing stored data
    State('fit-params', 'data'), # State to get existing fit params
    State('roc_curves', 'data'), # State to get existing roc curves
    prevent_initial_call=True  # Prevent the callback from firing on initial load
)
def store_file(list_of_contents, list_of_filenames, existing_stored_data, existing_fitted_params, existing_roc_curves):
    if list_of_contents is not None:
      # Dictionary to store all file data
      all_files_data = existing_stored_data if existing_stored_data is not None else {}
      all_files_fit_params = existing_fitted_params if existing_fitted_params is not None else {}
      all_files_roc = existing_roc_curves if existing_roc_curves is not None else {}

      for content, filename in zip(list_of_contents, list_of_filenames):
        if isinstance(content, str):  # Check if content is a string
          content_type, content_string = content.split(',')
          decoded = base64.b64decode(content_string)

          try:
            # Read header to get column names
            with io.StringIO(decoded.decode('utf-8')) as f:
                header = f.readline().strip().split('\t')

            # Load data with skip_header and names
            data = np.genfromtxt(io.BytesIO(decoded), delimiter='\t', dtype=None,
                                encoding='utf-8', skip_header=1,
                                names=header, missing_values='', filling_values=0)

            #Manipulate data
            manipulated_data = utils.manipulate_data(data, header)

            #make roc curve
            roc_columns = {}
            for column in manipulated_data:
              roc_columns[column] = utils.make_roc_curve(manipulated_data[column]['positive']['data'], manipulated_data[column]['negative']['data'], manipulated_data[column]['unknown']['data'])


            fitted_data = utils.fit_params(manipulated_data)
            # Convert NumPy structured array to list of dictionaries
            # data_list = []
            # for row in data:
            #     data_list.append(dict(zip(header, row)))

            all_files_data[filename] = manipulated_data
            all_files_fit_params[filename] = fitted_data
            all_files_roc[filename] = roc_columns

          except Exception as e:
              error_message = f"Error processing file: {e}"
              print(error_message)
              return None, None, None, html.Div(error_message, style={'color': 'red'})
        else:
          error_message = "Invalid content type"
          print(error_message)
          return None, None, None, html.Div(error_message, style={'color': 'red'})
      # Return the dictionary containing all file data
      return all_files_data, all_files_fit_params, all_files_roc, html.Div("No Error Uploading File", style={'color': 'green'})
    return None, None, None, html.Div("No File Uploaded", style={'color': 'green'})

# Callback to select uploaded files
@app.callback(
    Output('file-select', 'options'),
    Output('file-select', 'value'),
    Input('stored-data', 'data'),
    State('file-select', 'value')
)
def update_file_select_options(stored_data, current_file_select_value):
    if stored_data:
        file_options = [{'label': filename, 'value': filename} for filename in stored_data.keys()]
        if current_file_select_value and current_file_select_value in stored_data.keys():
            file_value = current_file_select_value
        else:
            file_value = list(stored_data.keys())[0]
    else:
        file_options = []
        file_value = None
    return file_options, file_value

# Update Stored Data
@app.callback(
    Output('stored-data', 'data', allow_duplicate=True),
    Input('slider-position', 'value'),
    Input('range-slider', 'value'),
    State('stored-data', 'data'),
    State('file-select', 'value'),
    State('column-select', 'value'),
    prevent_initial_call=True  # Prevent the callback from firing on initial load
)
def update_stored_data(slider_position, range_slider_value, stored_data, selected_file, selected_column):
    if stored_data and selected_file and selected_column:
        column_data = stored_data[selected_file][selected_column]
        column_data['slider_value'] = slider_position
        column_data['range_value'] = range_slider_value
        #Update stored data
        stored_data[selected_file].update({selected_column: column_data})
        return stored_data
    else:
        return stored_data

# Callback to select column of uploaded files
@app.callback(
    Output('column-select', 'options'),
    Output('column-select', 'value'),
    Input('file-select', 'value'),
    State('stored-data', 'data')
)
def update_column_select_options(file_name, stored_data):
    if stored_data and file_name in stored_data:
        # Access column names for the selected file
        column_names = list(stored_data[file_name].keys())
        column_options = [{'label': col, 'value': col} for col in column_names]
        column_value = column_names[0]  # Set default to first column
    else:
        column_options = []
        column_value = None
    return column_options, column_value

# Callback for range slider updates
@callback(
    [Output('range-slider', 'min'),
     Output('range-slider', 'max'),
     Output('range-slider', 'value'),],
    Input('column-select', 'value'),
    Input('range-reset', 'n_clicks'),
    State('stored-data', 'data'),
    State('file-select', 'value')
)
def update_range_slider_range(selected_column, button, stored_data, selected_file):
    if stored_data and selected_column in stored_data.get(selected_file, {}):
        column_data = stored_data[selected_file][selected_column]

        range_min = column_data['range_min']
        range_max = column_data['range_max']

        initial_range = column_data.get('range_value', [range_min, range_max])

        if "range-reset" == ctx.triggered_id:
            initial_range = [range_min, range_max]

        return range_min, range_max, initial_range  # Return updated stored data
    else:
        return 0, 100, [0, 100]  # Return default values if data is not available

# Callback for slider updates
@callback(
    [Output('slider-position', 'min'),
    Output('slider-position', 'max'),],
    Input('range-slider', 'value')
)
def update_slider_range(selected_range):
    slider_min = selected_range[0]
    slider_max = selected_range[1]
    return slider_min, slider_max


# # Callback to make slider line faster
# @app.callback(
#     Output('graph', 'extendData'),
#     [Input('slider-position', 'value')],     # Input from range slider
#     [State('graph', 'figure')],
#     prevent_initial_call=True
# )
# def update_line_position(pos_x, fig):
#     if fig is not None:
#         # Assuming your line trace is the first trace (index 0)
#         # Update the line's x and y data based on pos_x
#         return dict(x=[[pos_x]], y=[[pos_x]]), [0]
#     return {},[] # This means no extension, do nothing.



# Update Graph Callback
@app.callback(
    Output('graph', 'figure'),
    Output('roc_table', 'figure'),
    [Input('stored-data', 'data'),
     Input('fit-params', 'data'),
     Input('roc_curves', 'data'),
     Input('file-select', 'value'),
     Input('column-select', 'value'),    # Input from dropdown
     Input('pos-statfit-select', 'value'), # Select fit lines
     Input('neg-statfit-select', 'value'), #
     Input('chart-type', 'value'),
     State('slider-position', 'value'),  # Input from slider, set to 'State' so it doesnt redraw graph everytime
     Input('range-slider', 'value'),     # Input from range slider
     Input('trace-select', 'value')],
     Input('unknown-chart', 'value'),
    prevent_initial_call=True  # Prevent the callback from firing on initial load
)
def update_graph(stored_data, fitted_params, roc_data, selected_file, selected_column, pos_fit_dist, neg_fit_dist, chart_type, pos_x, range_value, selected_traces, unknown_chart):
  if stored_data and selected_file and selected_column and fitted_params and roc_data:
    column_data = stored_data.get(selected_file, {}).get(selected_column)
    parameter_data = fitted_params.get(selected_file, {}).get(selected_column)
    roc_column = roc_data.get(selected_file, {}).get(selected_column)

    # Check if roc_column and its population_data are available and not empty
    if not roc_column or not roc_column.get('population_data'):
        return go.Figure(), go.Figure() # Return an empty figure if data is not ready or empty

    if column_data and parameter_data and pos_fit_dist and neg_fit_dist and roc_column:
    
      fig2 = make_subplots(rows=2, cols=2, row_heights=[0.93, 0.07], shared_xaxes= "columns",vertical_spacing=0.01,specs=[[{"secondary_y": True}, {"type": "xy"}], [{"type": "xy"}, None]])
      utils.plot_roc_curve(roc_column['TPR'], roc_column['FPR'], fig2)
      roc_table = utils.plot_roc_table(roc_column, pos_x)

      # Calculate Histogram points depending of ranger slider
      bin_edges = utils.calculate_bin_edges(column_data, range_value, selected_traces)
      positive_hist, positive_bin_edges = np.histogram(column_data['positive']['data'], bins=bin_edges, range=range_value)
      negative_hist, negative_bin_edges = np.histogram(column_data['negative']['data'], bins=bin_edges, range=range_value)
      unknown_hist, unknown_bin_edges   = np.histogram(column_data['unknown']['data'],  bins=bin_edges, range=range_value)

      positive_bar_widths = np.diff(positive_bin_edges)
      negative_bar_widths = np.diff(negative_bin_edges)
      unknown_bar_widths  = np.diff(unknown_bin_edges)

      positive_bar_center = positive_bin_edges[:-1] + positive_bar_widths / 2
      negative_bar_center = negative_bin_edges[:-1] + negative_bar_widths / 2
      unknown_bar_center  = unknown_bin_edges[:-1]  + unknown_bar_widths  / 2

      # Graph np bins depending on graph type
      if chart_type == 'Line':
        if 'Positive' in selected_traces:
          if pos_fit_dist == 'none':
              fig2.add_trace(go.Scatter(x=positive_bar_center, y=positive_hist, mode='lines', name='Positives', line_color='red'), row=1, col=1, secondary_y=True)
          else:
              pos_params = parameter_data['positive'][pos_fit_dist]
              # Create distribution object
              positive_dist = getattr(stats, pos_fit_dist)
              x_range_for_pdf = np.linspace(range_value[0], range_value[1], 100)
              positive_pdf = positive_dist.pdf(x_range_for_pdf, **pos_params)
              
              fig2.add_trace(go.Scatter(x=x_range_for_pdf, y=positive_pdf, mode='lines', name='Positives', line_color='red'), row=1, col=1, secondary_y=True) #y=positive_hist

        if 'Negative' in selected_traces:
          if neg_fit_dist == 'none':
               fig2.add_trace(go.Scatter(x=negative_bar_center, y=negative_hist, mode='lines', name='Positives', line_color='green'), row=1, col=1, secondary_y=True)
          else:
               neg_params = parameter_data['negative'][neg_fit_dist]
               # Create distribution object
               negative_dist = getattr(stats, neg_fit_dist)
               x_range_for_pdf = np.linspace(range_value[0], range_value[1], 100)
               negative_pdf = negative_dist.pdf(x_range_for_pdf, **neg_params)
               
               fig2.add_trace(go.Scatter(x=x_range_for_pdf, y=negative_pdf, mode='lines', name='Negatives', line_color='green'), row=1, col=1, secondary_y=True) #y=negative_hist

      elif chart_type == 'Histogram':
        # Graph Bars
        if 'Positive' in selected_traces:
          fig2.add_trace(go.Bar(x=positive_bar_center, y=positive_hist, name='Positives', marker_color='red', width=positive_bar_widths), row=1, col=1, secondary_y=True)




        if 'Negative' in selected_traces: 
          fig2.add_trace(go.Bar(x=negative_bar_center, y=negative_hist, name='Negatives', marker_color='green',  width=negative_bar_widths), row=1, col=1, secondary_y=True)

      if 'Unknown' in selected_traces:
        if unknown_chart == 'Histogram':
          fig2.add_trace(go.Bar(x=unknown_bar_center, y=unknown_hist, name='Unknown', marker_color='gray', width=unknown_bar_widths), row=1, col=1, secondary_y=False)


        if unknown_chart == 'Line':
          fig2.add_trace(go.Scatter(x=unknown_bar_center, y=unknown_hist, mode='lines', name='Unknown', line_color='gray'), row=1, col=1, secondary_y=False)

      fig2.add_trace(go.Box( #positive points  #draw original data points in boxplot below x axis
          x=column_data['positive']['data'],
          marker_symbol='line-ns-open',
          marker_color='red',
          boxpoints='all',
          jitter=1,
          fillcolor='rgba(255,255,255,0)',
          line_color='rgba(255,255,255,0)',
          hoveron='points',
          showlegend=False
          ), row=2, col=1)   

      fig2.add_trace(go.Box( #negative points  #draw original data points in boxplot below x axis
          x=column_data['negative']['data'],
          marker_symbol='line-ns-open',
          marker_color='green',
          boxpoints='all',
          jitter=1,
          fillcolor='rgba(255,255,255,0)',
          line_color='rgba(255,255,255,0)',
          hoveron='points',
          showlegend=False
          ), row=2, col=1)          


      fig2.add_vline(x=pos_x, line_width=3, line_dash="dashdot", line_color="orange",
                    annotation_text=pos_x, annotation_position="top",  # Position above the line
                    annotation_font=dict(size=18), row=1, col=1) # Customize font

      fig2.update_yaxes(showticklabels=False, row=2, col=1)
      fig2.update_xaxes(range=[range_value[0], range_value[1]], row=1, col=1)
      fig2.update_xaxes(range=[range_value[0], range_value[1]], row=2, col=1)
      fig2.update_layout(
         margin=dict(l=20, r=20, t=0, b=0),
        )





      '''fig.update_layout(
        yaxis={
            'showgrid': True,
            'gridcolor': 'lightgray',
            'gridwidth': 1,
            'griddash': 'solid'
        },
        yaxis2=dict(
            title='Unknown',  # Set title for y2 axis
            overlaying='y',  # Overlay on top of y axis
            side='right',  # Place y2 axis on the right
        )
      )

      fig.update_layout(
          plot_bgcolor=colors['background'],
          paper_bgcolor=colors['background'],
          font_color=colors['text'],
          barmode='overlay',
          xaxis_range=[range_value[0], range_value[1]], # Change graph range depending on slider range
        )
      fig.update_yaxes(showgrid=True)
      fig.update_traces(opacity=0.75)'''



      return fig2, roc_table
  else:
    return go.Figure(), go.Figure()


if __name__ == '__main__':
  app.run(debug=True)
