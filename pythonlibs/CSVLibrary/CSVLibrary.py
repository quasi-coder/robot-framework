import csv

class CSVLibrary:

    def read_CSV_file(self, filename):
        """Reads CSV file and returns list of rows.

        Takes one argument, which is a path to a .csv file. It returns a list of rows,
        with each row being a list of the data in each column.

        Examples:
            | Read CSV File | ${CURDIR}${/}input.csv |
        """
        data = []
        with open(filename, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                data.append(row)
        return data