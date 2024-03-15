import numpy as np
import pandas as pd


def _calculate_volume(environment):
    width = environment['width']
    height = environment['height']
    length = environment['length']
    return width * height * length


def _calculate_volumes(entities):
    volumes = {}
    for entity in entities:
        entity_name = entity.get('cellName', entity.get('name'))
        entity_radius = entity['radius']
        volumes[entity_name] = 4 / 3 * np.pi * (entity_radius ** 3)
    return volumes

def _calculate_diffusion_rates(molecules):
    diffusion_rates = {}
    for molecule in molecules:
        molecule_name = molecule['name']
        diffusion_rates[molecule_name] = molecule['diffusionRate']['exterior']
    return diffusion_rates

def preprocessing_data(df, config, n_divisions, future_step):
    total_volume = _calculate_volume(config['environment'])
    sector_volume = total_volume / (n_divisions ** 3)
    cell_volumes = _calculate_volumes(config['cells'])
    molecule_volumes = _calculate_volumes(config['agents']['molecules'])

    molecule_diffusion_rates = _calculate_diffusion_rates(config['agents']['molecules'])


    results = []

    limits = {
        'X': np.linspace(df['X'].min(), df['X'].max(), n_divisions + 1),
        'Y': np.linspace(df['Y'].min(), df['Y'].max(), n_divisions + 1),
        'Z': np.linspace(df['Z'].min(), df['Z'].max(), n_divisions + 1)
    }
    #Por ejemplo, si df['X'].min() es 0, df['X'].max() es 10, y n_divisions es 2, entonces np.linspace(0, 10, 3) generará [0, 5, 10].
    #Esto significa que el espacio en el eje X se dividirá en 2 sectores, con límites en 0, 5, y 10.

    targets = {}
    for timestep in sorted(df['Timestep'].unique()):
        future_timestep = timestep + future_step
        df_future = df[df['Timestep'] == future_timestep]
        for i in range(n_divisions):
            for j in range(n_divisions):
                for k in range(n_divisions):
                    df_future_sector = df_future[
                        (df_future['X'] >= limits['X'][i]) & (df_future['X'] < limits['X'][i + 1]) &
                        (df_future['Y'] >= limits['Y'][j]) & (df_future['Y'] < limits['Y'][j + 1]) &
                        (df_future['Z'] >= limits['Z'][k]) & (df_future['Z'] < limits['Z'][k + 1])
                    ]
                    for name in {**cell_volumes, **molecule_volumes}.keys():
                        num_entities = len(df_future_sector[df_future_sector['Name'] == name])
                        targets[(timestep, i, j, k, name)] = num_entities

    for timestep in df['Timestep'].unique():
        df_timestep = df[df['Timestep'] == timestep]
        sector = 0

        for i in range(n_divisions):
            for j in range(n_divisions):
                for k in range(n_divisions):
                    OccupiedSpace = 0

                    #limits['X'][i] y limits['X'][i + 1]: Son los límites en el eje X para el sector actual que se está analizando.
                    #limits['X'] es un array que contiene los puntos de inicio y fin de cada división en el eje X,
                    # i es el índice de la iteración actual en el bucle que recorre estas divisiones. limits['X'][i] es el límite inferior,
                    # y limits['X'][i + 1] es el límite superior del sector en el eje X.
                    # #(df_timestep['X'] >= limits['X'][i]) & (df_timestep['X'] < limits['X'][i + 1]):
                    # Esta condición selecciona solo las filas del DataFrame df_timestep donde el valor de la columna 'X'
                    # está dentro de los límites del sector actual en el eje X.

                    df_sector = df_timestep[
                        (df_timestep['X'] >= limits['X'][i]) & (df_timestep['X'] < limits['X'][i + 1]) &
                        (df_timestep['Y'] >= limits['Y'][j]) & (df_timestep['Y'] < limits['Y'][j + 1]) &
                        (df_timestep['Z'] >= limits['Z'][k]) & (df_timestep['Z'] < limits['Z'][k + 1])
                        ]

                    sector_data = {
                        'Timestep': timestep,
                        'Sector': sector,
                    }
                    # combinar dos diccionarios "unpacking operator" (**).
                    for name, volume in {**cell_volumes, **molecule_volumes}.items():
                        num_entities = len(df_sector[df_sector['Name'] == name])
                        sector_data[f'Num {name}'] = num_entities
                        sector_data[f'OccupiedSpace {name}'] = num_entities * volume
                        if name in molecule_diffusion_rates:
                            sector_data[f'Diffusion Rate {name}'] = molecule_diffusion_rates[name]
                        OccupiedSpace += num_entities * volume
                        key = (timestep, i, j, k, name)
                        sector_data[f'Target {name}'] = targets.get(key, 0)

                    sector_data['EmptySpace Sector'] = total_volume / n_divisions ** 3 - OccupiedSpace

                    results.append(sector_data)
                    sector = sector + 1

    return pd.DataFrame(results)
