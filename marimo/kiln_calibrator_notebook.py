import marimo

__generated_with = "0.13.15"
app = marimo.App(width="columns")


@app.cell(column=0, hide_code=True)
def _(mo):
    mo.md(r"""# Imports""")
    return


@app.cell
def _():
    import duckdb
    import hashlib
    import time
    import marimo as mo
    import pandas as pd
    return duckdb, hashlib, mo, pd


@app.cell
def _(duckdb):
    db_file = "persistent_db.duckdb"
    con = duckdb.connect(db_file)
    return (con,)


@app.cell
def _():
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_style("ticks")
    return (plt,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""# Utils""")
    return


@app.cell
def _(hashlib):
    def create_hash(input_string):
        return hashlib.sha256(input_string.encode()).hexdigest()

    # Example usage
    my_string = "Hello, World!"
    my_hash = create_hash(my_string)
    my_hash

    return (create_hash,)


@app.function
def remove_first(generator):
    """Removes the first element of a generator and returns a new generator."""
    iterator = iter(generator)
    first = next(iterator, None)  # Consume the first element
    return first, iterator


@app.cell(column=1, hide_code=True)
def _(mo):
    mo.md(r"""# Real data conditioning""")
    return


@app.cell
def _(pd):
    firing_data_df = pd.read_csv('./data/kiln/firing_A.csv', sep=";")

    # Get the first value in the original "Time" column (still in datetime format)
    first_time = pd.to_datetime(firing_data_df['Time'].iloc[0], format='%d/%m/%Y %H:%M')

    # Calculate the difference in seconds from the first timestamp
    firing_data_df['relative_time'] = (pd.to_datetime(firing_data_df['Time'], format='%d/%m/%Y %H:%M') - first_time).dt.total_seconds()

    # Calculate the difference in seconds between each row and the previous one
    firing_data_df['time_delta'] = firing_data_df['relative_time'].diff().fillna(0)

    # Create a new column "duty_cycle" calculated from the "equivalent_on_resistances" column divided by 4
    firing_data_df['duty_cycle'] = firing_data_df['equivalent_on_resistances'] / 4

    firing_data_df  # Display the updated DataFrame

    return (firing_data_df,)


@app.cell
def _(firing_data_df, plt):
    fig, ax1 = plt.subplots(figsize=(13, 6))

    # Plot the compensated_temperature on the primary y-axis
    ax1.plot(firing_data_df["relative_time"], firing_data_df["compensated_temperature"], color='b', label='Compensated Temperature')
    ax1.set_xlabel('Relative Time')
    ax1.set_ylabel('Compensated Temperature', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    # Create a secondary y-axis for duty_cycle
    ax2 = ax1.twinx()
    ax2.plot(firing_data_df["relative_time"], firing_data_df["duty_cycle"], color='g', label='Duty Cycle')
    ax2.set_ylabel('Duty Cycle', color='g')
    ax2.tick_params(axis='y', labelcolor='g')

    # Add title and legend
    plt.title('Temperature and Duty Cycle over Time')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    plt.gca()

    return


@app.function
def firing_data_iterator(dataframe):
    for index, row in dataframe.iterrows():
        yield (row["time_delta"], row["duty_cycle"], row["compensated_temperature"])


@app.cell(column=2, hide_code=True)
def _(mo):
    mo.md(r"""# Simulation definition/validation""")
    return


@app.cell
def _(con, create_hash, plt):
    class SimulatedKiln:
        def __init__(self, max_power, ambient_temp, heat_capacity, heat_loss, initial_temp = None, initial_duty = 0, initial_time = 0, init_real_data=True):
            if initial_temp is None:
                initial_temp = ambient_temp
            self.table_name = "simulation_"+create_hash(f"{max_power}{ambient_temp}{heat_capacity}{heat_loss}{initial_temp}")
        
            self.max_power = max_power           # W ~ J/s
            self.ambient_temp = ambient_temp     # °C
            self.heat_capacity = heat_capacity   # J/°C
            self.heat_loss = heat_loss           # W/°C
            self.temp = initial_temp             # °C
            self.duty = initial_duty             # NA
            self.time = initial_time             # S
            self._create_table()
        
            if init_real_data:
                self._insert_data(initial_time, initial_temp, initial_duty, initial_temp)
            else:
                self._insert_data(initial_time, initial_temp, initial_duty)

        def _create_table(self):
            # Criar a tabela "kiln_data"
            con.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            con.execute(f"""
            CREATE TABLE {self.table_name} (
                time FLOAT,
                duty FLOAT,
                simulated_temperature FLOAT,
                real_temperature FLOAT,
                absolute_error FLOAT
            )
            """)
    
        def _insert_data(self, time, simulated_temperature, duty, real_temperature="NULL"):
            absolute_error = "NULL"
            if real_temperature != "NULL":
                absolute_error = abs(simulated_temperature - real_temperature)
            con.execute(f"INSERT INTO {self.table_name} VALUES ({time}, {duty}, {simulated_temperature}, {real_temperature}, {absolute_error})")
    
        def simulate(self, timestep, duty, real_temperature="NULL"):
            self.time += timestep
            self.duty = duty
            power_in = self.max_power * self.duty
            power_loss = self.heat_loss * (self.temp - self.ambient_temp)
            power = power_in - power_loss
            delta_temp = power * timestep / self.heat_capacity
            self.temp += delta_temp
            self._insert_data(self.time, self.temp, self.duty, real_temperature)

        @property
        def simulation_df(self):
            return con.sql(f"SELECT * FROM {self.table_name}").df()

        def plot_simulation(self, log_scale_temp=False, plot_real_temp=True):     
            fig, ax1 = plt.subplots(figsize=(13, 6))
            simulation_df = self.simulation_df
        
            # Plot the simulated_temperature on the primary y-axis
            ax1.plot(simulation_df["time"], simulation_df["simulated_temperature"], color='b', label='Simulated Temperature')
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Temperature', color='b')
            ax1.tick_params(axis='y', labelcolor='b')
        
            # Set log scale for simulated_temperature if specified
            if log_scale_temp:
                ax1.set_yscale('log')
        
            # Create a secondary y-axis for duty
            ax2 = ax1.twinx()
            ax2.plot(simulation_df["time"], simulation_df["duty"], color='g', label='Duty')
            ax2.set_ylabel('Duty', color='g')
            ax2.tick_params(axis='y', labelcolor='g')
        
            # Plot real_temperature if the flag is set to True
            if plot_real_temp:
                ax1.plot(simulation_df["time"], simulation_df["real_temperature"], color='r', label='Real Temperature')
    
            # Add title and legend
            plt.title('Simulated Temperature and Duty over Time')
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
        
            return plt.gca()


    kiln = SimulatedKiln(
        max_power=2000,
        ambient_temp=20,
        heat_capacity=30000,
        heat_loss=2,
    )

    kiln.simulation_df
    return SimulatedKiln, kiln


@app.cell
def _(kiln):
    for _ in range(10):
        kiln.simulate(120, 1, 30)
    
    for _ in range(10):
        kiln.simulate(120, 0, 45)

    kiln.plot_simulation()
    return


@app.cell
def _(kiln):
    kiln.simulation_df.simulated_temperature.max()
    return


@app.cell
def _(
    con,
    mo,
    simulation_c8513ae419a2693824820cffafafb50f102800d2081141d2b88f946711d0449f,
):
    _df = mo.sql(
        f"""
        SELECT * FROM simulation_c8513ae419a2693824820cffafafb50f102800d2081141d2b88f946711d0449f ORDER BY ROWID DESC LIMIT 100

        """,
        engine=con
    )
    return


@app.cell(column=3)
def _(SimulatedKiln, firing_data_df):
    def simulate_and_compare(firing_data_df):
        firing_data_gen = firing_data_iterator(firing_data_df)
        (_, initial_duty, initial_temp), firing_data_gen = remove_first(firing_data_gen)
    
        # simulated_kiln = SimulatedKiln(
        #     max_power=2000,
        #     ambient_temp=20,
        #     heat_capacity=30000,
        #     heat_loss=1.8,
        #     initial_temp=initial_temp,
        #     initial_duty=initial_duty
        # )

        simulated_kiln = SimulatedKiln(
            max_power=2000,
            ambient_temp=20,
            heat_capacity=30000,
            heat_loss=1.8,
            initial_temp=initial_temp,
            initial_duty=initial_duty
        )

        for timestep, duty, real_temperature in firing_data_gen:
            simulated_kiln.simulate(timestep, duty, real_temperature)

        return simulated_kiln

    simulation_result = simulate_and_compare(firing_data_df)
    simulation_result_df = simulation_result.simulation_df
    simulation_result_df
    return simulation_result, simulation_result_df


@app.cell
def _(simulation_result_df):
    simulation_result_df.absolute_error.mean()
    return


@app.cell
def _(simulation_result):
    simulation_result.plot_simulation()
    return


@app.cell(column=4)
def _():
    return


@app.cell
def _(con):
    con.execute("DROP TABLE IF EXISTS firing_A")
    con.execute("DROP TABLE IF EXISTS tbl")
    # con.execute("CREATE TABLE firing_A AS SELECT * FROM './data/kiln/firing_A.csv'")
    return


@app.cell
def _(con, firing_A, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM firing_A LIMIT 100
        """,
        engine=con
    )
    return


if __name__ == "__main__":
    app.run()
