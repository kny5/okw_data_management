from metaflow import step, card, current
from metaflow.cards import Image, Markdown
import pandas as pd
from __visualisations__ import Plot, Tabular, generate_sparsity_plots


class TailSteps:

    @step
    def visualise(self):
        """Orchestrates the generation of visualizations and statistics for the output data."""
        id = current.flow_name[-2:]
        self.data_output["source"] = id

        # Branch into three parallel card-generating steps
        self.next(self.data_table, self.data_map, self.data_stats)

    @card(type="html")
    @step
    def data_table(self):
        """Renders the output DataFrame as an interactive HTML table."""
        self.html = Tabular(self.data_output).table_output()
        self.next(self.wrapup)

    @card(type="blank")
    @step
    def data_map(self):
        """Renders the output DataFrame on a map if the render_map parameter is set to True."""
        if getattr(self, "render_map_", False):  # Safely check for attribute
            current.card.append(Markdown(Plot(self.data_output).base64_iframe()))
        self.next(self.wrapup)

    @card  # (type="blank")
    @step
    def data_stats(self):
        """Calculates sparsity metrics and saves them as a table artifact."""

        url_line = (
            f"\n\n## Data origin:<br>{self.url}" if getattr(self, "url", None) else ""
        )

        markdown_text = (
            f"# Data Sparsity Analysis for {current.flow_name}"
            f"{url_line}"
            f"\n\n### Records: \n\nInput:\nColumns: {len(self.data_input.columns.tolist())}\nRecords: {len(self.data_input)}"
            f"\n\nOutput: {len(self.data_output.columns.tolist())}\nRecords: {len(self.data_output)}"
        )
        current.card.append(Markdown(markdown_text))

        ## Maps
        current.card.append(Markdown("### Input Data Map"))
        current.card.append(Markdown(Plot(self.data_input).base64_iframe()))

        current.card.append(Markdown("### Output Data Map"))
        current.card.append(Markdown(Plot(self.data_output).base64_iframe()))

        # Clean Dictionary to handle names without overwriting Metaflow state variables
        datasets = {"Input Data": self.data_input, "Output Data": self.data_output}

        for name, dt in datasets.items():
            current.card.append(Markdown(f"### {name} Sparsity"))

            if not dt.empty:
                col_sparsity = (dt.isnull().mean() * 100).round(2)
                avg_row_sparsity = round(dt.isnull().mean(axis=1).mean() * 100, 2)

                df = pd.DataFrame(
                    {
                        "Metric": [f"Col: {col}" for col in col_sparsity.index],
                        "Value": col_sparsity.values.tolist(),
                    }
                )

                df.sort_values(by="Value", ascending=False, inplace=True)
                current.card.append(Markdown(Tabular(df).base64_iframe()))

                # Only save the summary stats for the final Output Data for later steps
                if name == "Output Data":
                    self.sparsity_summary = {
                        "total_records": len(dt),
                        "avg_row_sparsity_pct": avg_row_sparsity,
                    }

        ## Generate sparsity plots ONCE outside the loop
        splot = generate_sparsity_plots([self])
        if splot and len(splot) >= 2:
            current.card.append(Image.from_matplotlib(splot[0]))
            current.card.append(Image.from_matplotlib(splot[1]))

        self.count = "Entries: {r[0]}, columns: {r[1]}, info: {c}".format(
            r=self.data_output.shape, c=self.data_output.columns.tolist()
        )

        ## Summary markdown
        current.card.append(
            Markdown(
                f"## Data Summary\n{self.count.split(', ')[0]} records with an average row sparsity of {self.sparsity_summary.get('avg_row_sparsity_pct', 'N/A')}%"
            )
        )

        self.next(self.wrapup)

    @card
    @step
    def wrapup(self, inputs):
        """Finalizes the output data by safely propagating the dataframes."""

        # Iterate to safely find the artifacts rather than blindly trusting inputs[0]
        for inp in inputs:
            if hasattr(inp, "data_output"):
                self.data_output = inp.data_output
            if hasattr(inp, "data_input"):
                self.data_input = inp.data_input

        print(self.data_output.shape)
        print(self.data_output.columns.tolist())
        self.next(self.end)

    @step
    def end(self):
        self.data_output
        self.data_input
        print("Success")
