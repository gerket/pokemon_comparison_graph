import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import requests
import pandas as pd
import math

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


############# Make changes here

# Setting up the initial api url
url_parameters = dict(
    base_url = "pokeapi.co",
    directory = "api/v2/pokemon",
    pokemon_id = ''
)

endpoint  = "http://{base_url}/{directory}/{pokemon_id}".format(**url_parameters)

# Getting a result from the api that includes the number of pokemon
first_request = requests.get(endpoint)
first_results = first_request.json()

# Getting a result containing all of the pokemon's names and api urls
second_request = requests.get(endpoint + '?offset=0&limit='+str(first_results['count']))
second_results = second_request.json()

# Storing the Pokemon names and urls for later use
name_url = dict()
for i in second_results['results']:
    name_url[i['name'].capitalize()]=i['url']

pokemon_dataframe = pd.DataFrame()

#
app.layout = html.Div([

        html.Div([
            # Big header
            html.H1('Comparing Pokemon Statistics!'),
            # Little bit smaller header
            html.H2('Choose Pokemon to compare:'),

            # multi-select dropdown menu
            dcc.Dropdown(
                id='pokemon_choices',
                options=[{'label':i['name'].capitalize(), 'value':i['name'].capitalize()} for i in second_results['results']],
                value='Bulbasaur',
                multi=True
            ),

            # Little bit smaller header
            html.H2('Choose type of bar chart:'),
            dcc.RadioItems(
                id='bar_type',
                options=[
                    {'label':'Group by Pokemon', 'value':'group'},
                    {'label':'Group by Stat', 'value':'group_stat'},
                    {'label':'Stacked by Pokemon', 'value':'stack'},
                ],
                value='group',
            ),
        ]),
        html.Div([
            dcc.Graph(
                id='dataframe_table',
            ),
            # Little bit smaller header
            html.H2('Comparison Graphs:'),
            # Graph placement
            dcc.Graph(
                id='base_stat_bar_graph',
            ),
            dcc.Graph(
                id='base_stat_pie_graph',
            )
        ])
    ]
)

@app.callback(
    dash.dependencies.Output('dataframe_table', 'figure'),
    [dash.dependencies.Input('pokemon_choices','value')])
def update_df_table(input_pokemon_choices):
    update_dataframe(input_pokemon_choices)
    global pokemon_dataframe
    pokemon_dataframe.drop_duplicates(inplace=True)
    ret = [
        go.Table(
            header=dict(values=list(pokemon_dataframe.columns),
            fill = dict(color='#C2D4FF'),
            align = ['left']),
            cells=dict(
                values=[pokemon_dataframe[x] for x in pokemon_dataframe.columns],
                fill = dict(color='#F5F8FF'),
                align = ['left'] * 7)
        )
    ]
    return go.Figure(ret)

def update_dataframe(input_pokemon_choices):
    global pokemon_dataframe
    pokedex = dict()
    for i in input_pokemon_choices:
        # Adds a pokemon's data to the dataframe if it wasn't already added this session
        if pokemon_dataframe.empty or i not in pokemon_dataframe['Name'].values:
            temp_results = requests.get(name_url[i]).json()

            temp_poke_df = pd.DataFrame(temp_results['stats'])
            dat = [list(temp_poke_df['base_stat'])]
            dat[0].append(i.capitalize())
            cols = [x['name'].capitalize() for x in temp_poke_df['stat']]
            cols.append('Name')
            pokemon_dataframe = pokemon_dataframe.append(
                pd.DataFrame(
                    data=dat, columns=cols
                )
            )

@app.callback(
    dash.dependencies.Output('base_stat_bar_graph', 'figure'),
    [dash.dependencies.Input('pokemon_choices','value'),
     dash.dependencies.Input('bar_type','value')])
def update_bar_graph(input_pokemon_choices, bar_type):
    if type(input_pokemon_choices)==str:
        input_pokemon_choices = [input_pokemon_choices]

    update_dataframe(input_pokemon_choices)
    global pokemon_dataframe
    pokemon_dataframe.drop_duplicates(inplace=True)

    current_df = pokemon_dataframe[pokemon_dataframe['Name'].isin(input_pokemon_choices)].sort_values(['Name'])

    if bar_type=='group_stat':
        traces = [
            go.Bar({
                'x':[col for col in current_df.columns if col != 'Name'],
                'y':current_df[current_df['Name']==name].values[0][:-1],
                'name':name
            }) for name in current_df['Name'].values
        ]

        layout = {
            'barmode':'group'
        }

    else:
    # List comprehension to create data for the graph
        traces = [
            go.Bar({
                'x':list(current_df['Name']),
                'y':list(current_df[col]),
                'name':col
            }) for col in current_df.columns if col != 'Name'
        ]

        layout = {
            'barmode':bar_type
        }

    fig={'data':traces, 'layout':go.Layout(layout)}
    return go.Figure(fig)


@app.callback(
    dash.dependencies.Output('base_stat_pie_graph', 'figure'),
    [dash.dependencies.Input('pokemon_choices','value')])
def update_pie_graph(input_pokemon_choices):
    if type(input_pokemon_choices)==str:
        input_pokemon_choices = [input_pokemon_choices]

    update_dataframe(input_pokemon_choices)
    global pokemon_dataframe
    pokemon_dataframe.drop_duplicates(inplace=True)

    current_df = pokemon_dataframe[pokemon_dataframe['Name'].isin(input_pokemon_choices)].sort_values(['Name'])


    # List comprehension to create data for the graph
    traces, layout = create_pie_traces(current_df, input_pokemon_choices)

    fig={'data':traces, 'layout':go.Layout(layout)}
    return go.Figure(fig)

def create_pie_traces(current_df, input_pokemon_choices):
    traces = []

    row = 0
    col = 0
    num_row_col = math.sqrt(len(input_pokemon_choices))
    if num_row_col%1!=0:
        num_row_col+=1
    num_row_col=int(num_row_col)


    for name in input_pokemon_choices:
        traces.append({
            'labels':[col for col in current_df.columns if col != 'Name'],
            'values':current_df[current_df['Name']==name].values[0][:-1],
            'name':name,
            'textinfo':'value',
            'hoverinfo':'label+value',
            'type':'pie',
            'title':name,
            'domain':{'row':row,'column':col},
        })

        col+=1
        if col >= num_row_col:
            col = 0
            row += 1

    if len(input_pokemon_choices) == 2:
        layout = {'title': 'Multiple Pie Charts',
            'showlegend': True,
            'grid':go.layout.Grid(rows=1,columns=num_row_col)}

    else:
        layout = {'title': 'Multiple Pie Charts',
            'showlegend': True,
            'grid':go.layout.Grid(rows=num_row_col,columns=num_row_col)}

    return traces, layout

###### Don't change anything here

if __name__ == '__main__':
    app.run_server()
