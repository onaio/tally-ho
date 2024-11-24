from django.core.management.base import BaseCommand
import duckdb
from datetime import datetime
from django.utils.translation import gettext_lazy

results_path = 'data/results.csv'

class Command(BaseCommand):
    help = gettext_lazy("Process results.")

    def handle(self, *args, **kwargs):
        self.process_candidates_votes_with_duckdb()

    def process_candidates_votes_with_duckdb(self):
        """
        Process a CSV file to sum votes for duplicate candidates and
        recalculate total votes using DuckDB.

        Returns:
            str: The path to the output CSV file.
        """
        # Output file will be named with a timestamp
        date_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"processed_candidates_{date_time}.csv"

        try:
            # Create an in-memory DuckDB connection
            con = duckdb.connect(database=':memory:')

            # Load the CSV file into DuckDB
            sql =\
                str(
                    "CREATE TABLE candidates AS ",
                    f"SELECT * FROM read_csv_auto('{results_path}')"
                )
            con.execute(sql)

            # Validate the existence of required columns
            table_info =\
                con.execute("PRAGMA table_info('candidates')").fetchdf()
            required_columns = table_info['name'].tolist()

            if 'Name' in required_columns and 'Votes' in required_columns:
                # Aggregate votes by candidate name
                aggregated_df = con.execute("""
                    SELECT
                        "Name" AS candidate_name,
                        SUM(Votes) AS votes,
                        "Total Votes" AS total_votes,
                        "Status" as status,
                    FROM candidates
                    GROUP BY "Name", "Total Votes", "Status"
                """).fetchdf()

                # Recalculate total votes
                total_votes = aggregated_df['votes'].sum()
                print(f"Total Votes: {total_votes}")

                # Add a new column with the total votes for all rows
                aggregated_df['total_votes'] = total_votes

                # Save the result to a new CSV file
                aggregated_df.to_csv(output_file, index=False)
                print(f"Processed data saved to {output_file}")

                return output_file
            else:
                raise KeyError(
                    str("The required columns ('Candidate Name' and 'Votes') "
                        "are missing from the CSV file."))
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
